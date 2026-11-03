"""Local persistence for SnapRep workouts, custom exercises, and settings."""

import csv
from datetime import datetime
import io
import json
import os
from pathlib import Path
from typing import Any, List, Optional, Tuple

from config import DEFAULT_SETTINGS
from models import DEFAULT_EXERCISES, Exercise, SetRecord, get_default_exercises


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


class AppStorage:
    def __init__(self, storage_dir: Optional[Path] = None):
        if storage_dir is None:
            storage_dir = Path.home() / ".snap_rep"
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.history_file = self.storage_dir / "history.json"
        self.settings_file = self.storage_dir / "settings.json"
        self.exercises_file = self.storage_dir / "exercises.json"
        self.exports_dir = self.storage_dir / "exports"
        self.exports_dir.mkdir(parents=True, exist_ok=True)

        # In-memory write-through caches
        self._history_cache: Optional[List[SetRecord]] = None
        self._settings_cache: Optional[dict] = None
        self._exercises_cache: Optional[List[Exercise]] = None

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
                        rec = SetRecord.from_dict(item)
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
                loaded = [
                    Exercise.from_dict(item) for item in data if isinstance(item, dict)
                ]
                if not loaded:
                    defaults = get_default_exercises()
                    self.save_exercises(defaults)
                    return list(defaults)
                self._exercises_cache = loaded
                return list(loaded)
        except Exception:
            return get_default_exercises()

    def save_exercises(self, exercises: List[Exercise]) -> None:
        self._exercises_cache = list(exercises)
        try:
            _atomic_write_json(self.exercises_file, [e.to_dict() for e in exercises])
        except Exception:
            pass

    def has_exercise(self, name: str) -> bool:
        clean_name = name.strip().lower()
        if not clean_name:
            return False
        exercises = self.load_exercises()
        return any(e.name.strip().lower() == clean_name for e in exercises)

    def add_exercise(self, exercise: Exercise) -> List[Exercise]:
        if self.has_exercise(exercise.name):
            raise ValueError(
                f"An exercise named '{exercise.name.strip()}' already exists."
            )

        exercises = self.load_exercises()
        exercise.is_custom = True
        exercise.name = exercise.name.strip()
        exercises.insert(0, exercise)
        self.save_exercises(exercises)
        return exercises

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
        export_file = self.exports_dir / f"snaprep_history_{timestamp_str}.csv"
        try:
            with open(export_file, "w", encoding="utf-8", newline="") as f:
                f.write(csv_content)
        except Exception:
            pass

        return export_file, csv_content

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
