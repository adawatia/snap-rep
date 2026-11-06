"""Local persistence for SnapRep workouts, custom exercises, and settings."""

import csv
from datetime import datetime
import io
import json
import os
from pathlib import Path
import tempfile
from typing import Any, List, Optional, Tuple, Union

from config import DEFAULT_SETTINGS
from models import DEFAULT_EXERCISES, Exercise, SetRecord, WeightEntry, get_default_exercises


def _atomic_write_json(file_path: Path, data: Any) -> None:
    """Safely writes JSON data to a temporary file before atomic rename to prevent corruption."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = file_path.with_suffix(".tmp")
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        f.flush()
        os.fsync(f.fileno())
    temp_path.replace(file_path)


def _is_rapid_duplicate(r1: SetRecord, r2: SetRecord) -> bool:
    """Fast check for duplicate workout set within 3.0s, optimizing out strptime when possible."""
    if (
        r1.exercise.strip().lower() != r2.exercise.strip().lower()
        or r1.reps != r2.reps
        or abs(r1.weight_kg - r2.weight_kg) >= 0.01
    ):
        return False
    # Exact string match
    if r1.timestamp == r2.timestamp:
        return True
    # Fast date pre-filter: must be on the same date (YYYY-MM-DD)
    if len(r1.timestamp) >= 10 and len(r2.timestamp) >= 10:
        if r1.timestamp[:10] != r2.timestamp[:10]:
            return False
    try:
        t1 = datetime.strptime(r1.timestamp, "%Y-%m-%d %H:%M:%S")
        t2 = datetime.strptime(r2.timestamp, "%Y-%m-%d %H:%M:%S")
        return abs((t1 - t2).total_seconds()) < 3.0
    except Exception:
        return False


def get_default_storage_dir() -> Path:
    """Returns a guaranteed writable storage directory across Android, iOS, and Desktop."""
    candidates: List[Path] = []

    # 1. Flet mobile runtime environment variable (persisted under application-support/data)
    flet_data = os.environ.get("FLET_APP_STORAGE_DATA")
    if flet_data:
        candidates.append(Path(flet_data) / ".snap_rep")
        candidates.append(Path(flet_data))

    # 2. Android sandbox fallback
    for env_var in ("ANDROID_PRIVATE", "ANDROID_APP_PATH", "APP_DATA_DIR"):
        val = os.environ.get(env_var)
        if val:
            candidates.append(Path(val) / ".snap_rep")

    # 3. User home (excluding root-level system paths such as /data, /, /root)
    try:
        home = Path.home()
        home_norm = str(home).replace("\\", "/").rstrip("/")
        if home_norm and home_norm not in ["/data", "/", "/root"]:
            candidates.append(home / ".snap_rep")
    except Exception:
        pass

    # 4. Current working directory fallback (if not system root)
    try:
        cwd = Path.cwd()
        cwd_norm = str(cwd).replace("\\", "/").rstrip("/")
        if cwd_norm and cwd_norm not in ["/data", "/", "/root"]:
            candidates.append(cwd / ".snap_rep")
    except Exception:
        pass

    # 5. OS temporary directory fallback
    candidates.append(Path(tempfile.gettempdir()) / ".snap_rep")

    # Select the first directory that can be created and written to
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            test_file = candidate / ".write_probe"
            test_file.touch(exist_ok=True)
            test_file.unlink(missing_ok=True)
            return candidate
        except (PermissionError, OSError):
            continue

    fallback = Path(tempfile.gettempdir()) / ".snap_rep"
    try:
        fallback.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return fallback


class AppStorage:
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            storage_dir = get_default_storage_dir()
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "history.json"
        self.settings_file = self.storage_dir / "settings.json"
        self.exercises_file = self.storage_dir / "exercises.json"
        self.weight_file = self.storage_dir / "weight_history.json"
        self.exports_dir = self.storage_dir / "exports"
        self.backups_dir = self.storage_dir / "backups"

        # In-memory write-through caches
        self._history_cache: Optional[List[SetRecord]] = None
        self._settings_cache: Optional[dict] = None
        self._exercises_cache: Optional[List[Exercise]] = None
        self._weight_cache: Optional[List[WeightEntry]] = None

    def load_weight_history(self) -> List[WeightEntry]:
        if self._weight_cache is not None:
            return list(self._weight_cache)
        try:
            raw = json.loads(self.weight_file.read_text(encoding="utf-8")) if self.weight_file.exists() else []
            seen = set()
            entries = []
            for item in raw:
                try:
                    entry = WeightEntry.from_dict(item)
                    if entry.id not in seen:
                        entries.append(entry)
                        seen.add(entry.id)
                except (KeyError, TypeError, ValueError):
                    continue
            self._weight_cache = sorted(entries, key=lambda item: datetime.fromisoformat(item.recorded_at))
        except (OSError, ValueError, TypeError):
            self._weight_cache = []
        return list(self._weight_cache)

    def save_weight_history(self, entries: List[WeightEntry]) -> None:
        ordered = sorted(entries, key=lambda item: datetime.fromisoformat(item.recorded_at))
        _atomic_write_json(self.weight_file, [item.to_dict() for item in ordered])
        self._weight_cache = list(ordered)

    def upsert_weight_entry(self, entry: WeightEntry) -> List[WeightEntry]:
        entries = [item for item in self.load_weight_history() if item.id != entry.id]
        entries.append(entry)
        self.save_weight_history(entries)
        return self.load_weight_history()

    def delete_weight_entry(self, entry_id: str) -> List[WeightEntry]:
        self.save_weight_history([item for item in self.load_weight_history() if item.id != entry_id])
        return self.load_weight_history()

    # --- History Operations ---

    def load_history(self) -> List[SetRecord]:
        if self._history_cache is not None:
            return list(self._history_cache)

        if not self.history_file.exists():
            self._history_cache = []
            return []
        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                seen_ids = set()
                records: List[SetRecord] = []
                for item in data:
                    if isinstance(item, dict):
                        try:
                            rec = SetRecord.from_dict(item)
                        except (KeyError, TypeError, ValueError, OverflowError):
                            continue
                        if rec.id in seen_ids:
                            continue
                        if not any(_is_rapid_duplicate(existing, rec) for existing in records):
                            seen_ids.add(rec.id)
                            records.append(rec)
                self._history_cache = records
                return list(records)
        except Exception:
            self._history_cache = []
            return []

    def save_history(self, records: List[SetRecord]) -> None:
        try:
            seen_ids = set()
            deduped: List[SetRecord] = []
            for r in records:
                if r.id in seen_ids:
                    continue
                if not any(_is_rapid_duplicate(existing, r) for existing in deduped):
                    seen_ids.add(r.id)
                    deduped.append(r)
            self._history_cache = deduped
            _atomic_write_json(self.history_file, [r.to_dict() for r in deduped])
        except Exception:
            pass

    def add_record(self, record: SetRecord) -> List[SetRecord]:
        records = self.load_history()
        # 1. Guard against duplicate ID
        if any(r.id == record.id for r in records):
            return list(records)
        # 2. Guard against duplicate set within 3.0s of any recent record
        if any(_is_rapid_duplicate(existing, record) for existing in records):
            return list(records)
        records.insert(0, record)
        self.save_history(records)
        return list(self._history_cache or records)

    def delete_set(self, record_id: str) -> List[SetRecord]:
        records = self.load_history()
        records = [r for r in records if r.id != record_id]
        self.save_history(records)
        return list(self._history_cache or records)

    def clear_history(self) -> None:
        self._history_cache = []
        if self.history_file.exists():
            try:
                self.history_file.unlink()
            except Exception:
                self.save_history([])

    # --- Exercises Operations ---

    def load_exercises(self) -> List[Exercise]:
        if self._exercises_cache is not None:
            return list(self._exercises_cache)
        if not self.exercises_file.exists():
            defaults = get_default_exercises()
            self.save_exercises(defaults)
            return list(defaults)
        try:
            with open(self.exercises_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                seen_names = set()
                deduped: List[Exercise] = []
                for item in data:
                    if isinstance(item, dict):
                        try:
                            ex = Exercise.from_dict(item)
                        except (KeyError, TypeError, ValueError, OverflowError):
                            continue
                        clean = ex.name.strip().lower()
                        if clean and clean not in seen_names:
                            seen_names.add(clean)
                            deduped.append(ex)
                if not deduped:
                    defaults = get_default_exercises()
                    self.save_exercises(defaults)
                    return list(defaults)
                # Upgrade older libraries without changing a user's saved targets.
                defaults = get_default_exercises()
                default_categories = {item.name.casefold(): item.category for item in defaults}
                changed = False
                for exercise in deduped:
                    if (not exercise.is_custom and exercise.category == "Other"
                            and default_categories.get(exercise.name.casefold()) == "Neck"):
                        exercise.category = "Neck"
                        changed = True
                for exercise in defaults:
                    clean = exercise.name.strip().casefold()
                    if clean not in seen_names:
                        seen_names.add(clean)
                        deduped.append(exercise)
                        changed = True
                if changed:
                    self.save_exercises(deduped)
                else:
                    self._exercises_cache = deduped
                return list(deduped)
        except Exception:
            return get_default_exercises()

    def save_exercises(self, exercises: List[Exercise]) -> None:
        seen_names = set()
        deduped: List[Exercise] = []
        for e in exercises:
            clean = e.name.strip().lower()
            if clean and clean not in seen_names:
                seen_names.add(clean)
                deduped.append(e)
        self._exercises_cache = deduped
        try:
            _atomic_write_json(self.exercises_file, [e.to_dict() for e in deduped])
        except Exception:
            pass

    def has_exercise(self, name: str) -> bool:
        clean_name = name.strip().lower()
        if not clean_name:
            return False
        exercises = self.load_exercises()
        return any(e.name.strip().lower() == clean_name for e in exercises)

    def add_exercise(self, exercise: Exercise) -> List[Exercise]:
        clean_name = exercise.name.strip().lower()
        if not clean_name:
            raise ValueError("Exercise name cannot be empty.")
        if self.has_exercise(exercise.name):
            raise ValueError(
                f"An exercise named '{exercise.name.strip()}' already exists."
            )

        exercises = self.load_exercises()
        exercise.is_custom = True
        exercise.name = exercise.name.strip()
        exercises.insert(0, exercise)
        self.save_exercises(exercises)
        return list(self._exercises_cache or exercises)

    def delete_custom_exercise(self, name: str) -> List[Exercise]:
        exercises = self.load_exercises()
        clean_name = name.strip().lower()
        updated = [
            e
            for e in exercises
            if not (e.name.strip().lower() == clean_name and e.is_custom)
        ]
        if not updated:
            updated = get_default_exercises()
        self.save_exercises(updated)
        return updated

    def update_exercise(self, original_name: str, updated: Exercise) -> List[Exercise]:
        exercises = self.load_exercises()
        clean_orig = original_name.strip().lower()
        clean_new = updated.name.strip().lower()

        if clean_orig != clean_new and any(
            e.name.strip().lower() == clean_new for e in exercises
        ):
            raise ValueError(
                f"An exercise named '{updated.name.strip()}' already exists."
            )

        found = False
        for ex in exercises:
            if ex.name.strip().lower() == clean_orig:
                ex.name = updated.name.strip()
                ex.category = updated.category
                ex.default_reps = max(1, min(999, updated.default_reps))
                ex.default_weight = max(0.0, min(1000.0, updated.default_weight))
                found = True
                break

        if not found:
            raise ValueError(f"Exercise '{original_name}' not found.")

        self.save_exercises(exercises)
        return exercises

    # --- CSV Export Operations ---

    def export_history_to_csv(self) -> Tuple[Path, str]:
        records = self.load_history()
        buffer = io.StringIO()
        writer = csv.writer(buffer, quoting=csv.QUOTE_MINIMAL)
        writer.writerow(
            ["ID", "Timestamp", "Exercise", "Reps", "Weight_kg", "Volume_kg", "Notes"]
        )

        for r in records:
            volume = round(r.reps * r.weight_kg, 2)
            writer.writerow(
                [
                    r.id,
                    r.timestamp,
                    r.exercise,
                    r.reps,
                    r.weight_kg,
                    volume,
                    r.notes or "",
                ]
            )

        csv_content = buffer.getvalue()
        buffer.close()

        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        export_file = Path(f"snaprep_history_{timestamp_str}.csv")

        return export_file, csv_content

    def export_weight_to_csv(self) -> Tuple[Path, str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["ID", "Recorded_at", "Weight_kg"])
        for entry in self.load_weight_history():
            writer.writerow([entry.id, entry.recorded_at, entry.weight_kg])
        content = buffer.getvalue()
        buffer.close()
        filename = f"snaprep_weight_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        export_file = Path(filename)
        return export_file, content

    # --- Settings Operations ---

    def load_settings(self) -> dict:
        if self._settings_cache is not None:
            return dict(self._settings_cache)
        if not self.settings_file.exists():
            self._settings_cache = dict(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)
        try:
            with open(self.settings_file, "r", encoding="utf-8") as f:
                settings = json.load(f)
                merged = {**DEFAULT_SETTINGS, **settings}
                self._settings_cache = merged
                return dict(merged)
        except Exception:
            self._settings_cache = dict(DEFAULT_SETTINGS)
            return dict(DEFAULT_SETTINGS)

    def save_settings(self, settings: dict) -> None:
        self._settings_cache = dict(settings)
        try:
            _atomic_write_json(self.settings_file, settings)
        except Exception:
            pass

    # --- Backup & Restore Operations ---

    def create_backup(self) -> Tuple[Path, str, dict]:
        """Creates a portable full JSON backup of history, exercises, and settings."""
        records = self.load_history()
        exercises = self.load_exercises()
        settings = self.load_settings()
        weight_entries = self.load_weight_history()

        backup_data = {
            "version": 2,
            "app": "SnapRep",
            "app_version": "0.1.0",
            "created_at": datetime.now().isoformat(),
            "history": [r.to_dict() for r in records],
            "weight_history": [entry.to_dict() for entry in weight_entries],
            "exercises": [e.to_dict() for e in exercises],
            "settings": settings,
        }

        json_str = json.dumps(backup_data, indent=2, ensure_ascii=False)
        timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = Path(f"snaprep_backup_{timestamp_str}.json")

        return backup_file, json_str, backup_data

    def get_local_backups(self) -> List[Path]:
        """Returns list of local backup files sorted newest first."""
        if not self.backups_dir.exists():
            return []
        files = list(self.backups_dir.glob("snaprep_backup_*.json"))
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files

    def restore_backup(
        self,
        backup_data: Union[dict, str, list],
        mode: str = "merge",
    ) -> Tuple[int, int, bool]:
        """Restore history, exercises, and settings from a backup.

        Args:
            backup_data: JSON string, parsed dict, or raw list of records.
            mode: 'merge' (default, non-destructive deduplication) or 'replace' (overwrites current data).

        Returns:
            Tuple of (restored_sets_count, restored_exercises_count, settings_restored_bool).
        """
        if isinstance(backup_data, str):
            backup_data = json.loads(backup_data)

        if isinstance(backup_data, list):
            history_items = backup_data
            exercise_items = []
            settings_items = {}
            weight_items = None
            sections = {"history"}
        elif isinstance(backup_data, dict):
            history_items = backup_data.get("history", [])
            exercise_items = backup_data.get("exercises", [])
            settings_items = backup_data.get("settings", {})
            weight_items = backup_data.get("weight_history")
            sections = set(backup_data)
        else:
            raise ValueError("Invalid backup format: expected JSON object or array.")

        if mode not in ("merge", "replace"):
            raise ValueError("Restore mode must be Merge or Replace.")
        for label, items in (("history", history_items), ("exercises", exercise_items)):
            if not isinstance(items, list):
                raise ValueError(f"Invalid backup: {label} must be a list.")
        if weight_items is not None and not isinstance(weight_items, list):
            raise ValueError("Invalid backup: weight history must be a list.")
        if not isinstance(settings_items, dict):
            raise ValueError("Invalid backup: settings must be an object.")

        # 1. Parse valid SetRecords
        new_records: List[SetRecord] = []
        for item in history_items:
            if isinstance(item, dict):
                try:
                    new_records.append(SetRecord.from_dict(item))
                except Exception:
                    continue

        # 2. Parse valid Exercises
        new_exercises: List[Exercise] = []
        for item in exercise_items:
            if isinstance(item, dict):
                try:
                    new_exercises.append(Exercise.from_dict(item))
                except Exception:
                    continue

        new_weights: List[WeightEntry] = []
        if isinstance(weight_items, list):
            for item in weight_items:
                if isinstance(item, dict):
                    try:
                        new_weights.append(WeightEntry.from_dict(item))
                    except (KeyError, TypeError, ValueError):
                        continue

        restored_sets = 0
        restored_exercises = 0
        settings_restored = False

        if mode == "replace":
            # Overwrite history
            if "history" in sections:
                self.save_history(new_records)
                restored_sets = len(new_records)

            # Rebuild exercises, preserving standard defaults
            base_exercises = get_default_exercises()
            existing_names = {e.name.strip().lower() for e in base_exercises}
            final_exercises = list(base_exercises)
            for ex in new_exercises:
                clean_name = ex.name.strip().lower()
                if clean_name not in existing_names:
                    final_exercises.append(ex)
                    existing_names.add(clean_name)
                    restored_exercises += 1
                else:
                    for target in final_exercises:
                        if target.name.strip().lower() == clean_name:
                            target.default_reps = ex.default_reps
                            target.default_weight = ex.default_weight
            if "exercises" in sections:
                self.save_exercises(final_exercises)

            if weight_items is not None:
                self.save_weight_history(new_weights)

            # Replace settings
            if settings_items and isinstance(settings_items, dict):
                merged_settings = {**DEFAULT_SETTINGS, **settings_items}
                if "target_weight_kg" not in settings_items:
                    merged_settings["target_weight_kg"] = self.load_settings().get("target_weight_kg")
                self.save_settings(merged_settings)
                settings_restored = True

        else:  # mode == "merge"
            current_history = self.load_history()
            seen_ids = {r.id for r in current_history}
            merged_history = list(current_history)

            for rec in new_records:
                if rec.id not in seen_ids and not any(
                    _is_rapid_duplicate(existing, rec) for existing in merged_history
                ):
                    seen_ids.add(rec.id)
                    merged_history.append(rec)
                    restored_sets += 1

            merged_history.sort(key=lambda r: r.timestamp, reverse=True)
            self.save_history(merged_history)

            if weight_items is not None:
                current_weights = self.load_weight_history()
                seen_weight_ids = {item.id for item in current_weights}
                for entry in new_weights:
                    if entry.id not in seen_weight_ids:
                        current_weights.append(entry)
                        seen_weight_ids.add(entry.id)
                self.save_weight_history(current_weights)

            current_exercises = self.load_exercises()
            curr_names = {e.name.strip().lower() for e in current_exercises}
            merged_exercises = list(current_exercises)

            for ex in new_exercises:
                clean_name = ex.name.strip().lower()
                if clean_name not in curr_names:
                    curr_names.add(clean_name)
                    merged_exercises.append(ex)
                    restored_exercises += 1

            self.save_exercises(merged_exercises)

            if settings_items and isinstance(settings_items, dict):
                current_settings = self.load_settings()
                for k, v in settings_items.items():
                    if k not in current_settings or (k == "target_weight_kg" and current_settings[k] is None):
                        current_settings[k] = v
                        settings_restored = True
                if settings_restored:
                    self.save_settings(current_settings)

        return restored_sets, restored_exercises, settings_restored
