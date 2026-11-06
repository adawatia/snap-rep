"""Centralized application state and business logic for SnapRep."""

import asyncio
from datetime import datetime
import math
from pathlib import Path
from typing import Any, Callable, List, Optional, Tuple

import flet as ft

from config import DEFAULT_EXERCISES_DATA, DEFAULT_SETTINGS
from models import Exercise, SetRecord, WeightEntry
from storage import AppStorage


class AppState:
    def __init__(self, storage: Optional[AppStorage] = None):
        self.storage = storage or AppStorage()
        self.settings: dict = self.storage.load_settings()
        self.history: List[SetRecord] = self.storage.load_history()
        self.weight_history: List[WeightEntry] = self.storage.load_weight_history()
        self.exercises: List[Exercise] = self.storage.load_exercises()

        # Fallback exercise if list is somehow empty
        if not self.exercises:
            self.exercises = [
                Exercise(name="Push-ups", category="Calisthenics", default_reps=15, default_weight=0.0)
            ]

        self.current_exercise: Exercise = self.exercises[0]
        self.current_reps: int = max(0, min(999, self.current_exercise.default_reps))
        self.current_weight: float = max(0.0, min(1000.0, self.current_exercise.default_weight))
        self.current_set_number: int = 1
        self._recalculate_current_set_number()

        # Timer state
        self.timer_seconds_remaining: int = 0
        self.timer_running: bool = False
        self.timer_task: Optional[asyncio.Task] = None

        # Duplicate log prevention
        self._last_logged_time: Optional[datetime] = None
        self._last_logged_tuple: Optional[Tuple[str, int, float]] = None
        self._log_lock = asyncio.Lock()
        self._logging_in_progress: bool = False  # synchronous gate before the async lock
        self._exercise_lock = asyncio.Lock()
        self._exercise_op_in_progress: bool = False

        # Services
        self.haptic: Optional[ft.HapticFeedback] = None
        self.clipboard: Optional[ft.Clipboard] = None
        self.file_picker: Optional[ft.FilePicker] = None

        # Listeners for UI reactivity
        self._listeners: List[Callable[[], None]] = []
        self._timer_listeners: List[Callable[[], None]] = []

    def subscribe(self, callback: Callable[[], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    def notify(self) -> None:
        for callback in list(self._listeners):
            try:
                callback()
            except Exception:
                pass

    def subscribe_timer(self, callback: Callable[[], None]) -> None:
        if callback not in self._timer_listeners:
            self._timer_listeners.append(callback)

    def unsubscribe_timer(self, callback: Callable[[], None]) -> None:
        if callback in self._timer_listeners:
            self._timer_listeners.remove(callback)

    def _notify_timer(self) -> None:
        for callback in list(self._timer_listeners):
            try:
                callback()
            except Exception:
                pass

    # --- Haptic Feedback ---

    async def trigger_haptic(self, kind: str = "click") -> None:
        if not self.settings.get("haptic_feedback", True) or not self.haptic:
            return
        try:
            if kind == "vibrate":
                await self.haptic.vibrate()
            else:
                await self.haptic.light_impact()
        except Exception:
            pass

    # --- Tracker Actions ---

    async def update_reps(self, delta: int = 0, absolute: Optional[int] = None) -> None:
        if absolute is not None:
            self.current_reps = max(0, min(999, int(absolute)))
        else:
            self.current_reps = max(0, min(999, self.current_reps + delta))
        await self.trigger_haptic("click")
        self.notify()

    async def update_weight(self, delta: float = 0.0, absolute: Optional[float] = None) -> None:
        candidate = float(absolute) if absolute is not None else self.current_weight + delta
        if not math.isfinite(candidate):
            raise ValueError("Weight must be a finite number.")
        if absolute is not None:
            self.current_weight = max(0.0, min(1000.0, round(candidate, 2)))
        else:
            self.current_weight = max(0.0, min(1000.0, round(candidate, 2)))
        await self.trigger_haptic("click")
        self.notify()

    def set_weight_from_text(self, text: str) -> bool:
        try:
            val = float(text.strip())
            if not math.isfinite(val) or not 0 <= val <= 1000:
                return False
            self.current_weight = round(val, 2)
            return True
        except (ValueError, TypeError):
            return False

    def _recalculate_current_set_number(self) -> None:
        """Keep current_set_number accurately in sync with today's logged sets for current_exercise."""
        try:
            today_str = datetime.now().strftime("%Y-%m-%d")
            matching = [
                r for r in self.history
                if r.timestamp.startswith(today_str)
                and r.exercise.strip().lower() == self.current_exercise.name.strip().lower()
            ]
            self.current_set_number = len(matching) + 1
        except Exception:
            self.current_set_number = 1

    async def select_exercise(self, name: str) -> None:
        clean = name.strip().lower()
        matched = next((ex for ex in self.exercises if ex.name.strip().lower() == clean), None)
        if matched:
            self.current_exercise = matched
            self.current_reps = max(0, min(999, matched.default_reps))
            self.current_weight = max(0.0, min(1000.0, matched.default_weight)) if math.isfinite(matched.default_weight) else 0.0
            self._recalculate_current_set_number()
            await self.trigger_haptic("click")
            self.notify()

    def set_selected_default_weight(self, weight_kg: float) -> None:
        """Finish the one-time weight setup for a catalog exercise."""
        if not math.isfinite(weight_kg) or not 0 <= weight_kg <= 1000:
            raise ValueError("Enter a weight from 0 to 1000 kg.")
        exercise = self.current_exercise
        exercise.default_weight = round(weight_kg, 2)
        exercise.weight_setup_pending = False
        self.current_weight = exercise.default_weight
        self.storage.save_exercises(self.exercises)
        self.notify()

    async def log_set(self, notes: Optional[str] = None) -> Tuple[bool, str]:
        # Synchronous gate: reject instantly if a log is already in flight
        if self._logging_in_progress:
            return False, "Already logging a set, please wait."

        # Block logging if rest timer is currently running
        if self.timer_running and self.timer_seconds_remaining > 0:
            return (
                False,
                f"Rest timer is running ({self.timer_seconds_remaining}s remaining). Wait or reset timer to log next set.",
            )

        now = datetime.now()
        cur_tuple = (
            self.current_exercise.name.strip().lower(),
            self.current_reps,
            round(self.current_weight, 2),
        )
        # Immediate synchronous debounce rejection
        if (
            self._last_logged_time is not None
            and (now - self._last_logged_time).total_seconds() < 3.0
            and self._last_logged_tuple == cur_tuple
        ):
            return False, "Duplicate set ignored (just logged)."

        # Validate minimum reps
        if self.current_reps <= 0:
            return False, "Reps must be at least 1 to log a set."
        if not math.isfinite(self.current_weight) or not 0 <= self.current_weight <= 1000:
            return False, "Enter a valid weight from 0 to 1000 kg."

        self._logging_in_progress = True
        self._last_logged_time = now
        self._last_logged_tuple = cur_tuple
        try:
            async with self._log_lock:
                record = SetRecord(
                    exercise=self.current_exercise.name,
                    reps=self.current_reps,
                    weight_kg=self.current_weight,
                    notes=notes,
                    set_number=self.current_set_number,
                )
                self.history = self.storage.add_record(record)
                logged_set_num = self.current_set_number
                self._recalculate_current_set_number()

                await self.trigger_haptic("vibrate")

                # Auto-start configured rest timer if enabled (> 0s), or reset if disabled.
                # Use _silent variants to avoid multiple notify() calls before we return.
                default_rest = int(self.settings.get("default_rest_timer", 60))
                if default_rest > 0:
                    await self._set_timer_preset_silent(default_rest)
                else:
                    await self._reset_timer_silent()

                # Single notify at the end of the entire log operation
                self.notify()

                wt_str = f"{int(self.current_weight) if self.current_weight.is_integer() else self.current_weight} kg"
                msg = f"Logged Set {logged_set_num}: {self.current_reps} reps @ {wt_str} ({self.current_exercise.name})"
                return True, msg
        finally:
            self._logging_in_progress = False

    # --- Rest Timer Actions ---

    async def _run_timer_loop(self) -> None:
        try:
            while self.timer_running and self.timer_seconds_remaining > 0:
                await asyncio.sleep(1)
                if not self.timer_running:
                    break
                self.timer_seconds_remaining -= 1
                self._notify_timer()

            if self.timer_seconds_remaining == 0 and self.timer_running:
                self.timer_running = False
                await self.trigger_haptic("vibrate")
                self.notify()
        except asyncio.CancelledError:
            # Clean exit on task cancellation
            pass

    async def set_timer_preset(self, seconds: int) -> None:
        self.cancel_timer_task()
        self.timer_seconds_remaining = max(1, seconds)
        self.timer_running = True
        await self.trigger_haptic("click")
        self.notify()
        self.timer_task = asyncio.create_task(self._run_timer_loop())

    async def _set_timer_preset_silent(self, seconds: int) -> None:
        """Set timer without emitting a notify — use from within log_set to avoid double-notify."""
        self.cancel_timer_task()
        self.timer_seconds_remaining = max(1, seconds)
        self.timer_running = True
        self.timer_task = asyncio.create_task(self._run_timer_loop())

    async def _reset_timer_silent(self) -> None:
        """Reset timer without emitting a notify — use from within log_set to avoid double-notify."""
        self.timer_running = False
        self.cancel_timer_task()
        self.timer_seconds_remaining = 0

    async def toggle_timer(self) -> None:
        if self.timer_running:
            self.timer_running = False
            self.cancel_timer_task()
        else:
            if self.timer_seconds_remaining > 0:
                self.timer_running = True
                self.timer_task = asyncio.create_task(self._run_timer_loop())
        await self.trigger_haptic("click")
        self.notify()

    async def reset_timer(self) -> None:
        self.timer_running = False
        self.cancel_timer_task()
        self.timer_seconds_remaining = 0
        await self.trigger_haptic("click")
        self.notify()

    def cancel_timer_task(self) -> None:
        if self.timer_task and not self.timer_task.done():
            self.timer_task.cancel()
            self.timer_task = None

    # --- Custom Exercise Actions ---

    async def add_custom_exercise(
        self, name: str, category: str, default_reps: int, default_weight: float
    ) -> Exercise:
        if self._exercise_op_in_progress:
            raise ValueError("Exercise addition is already in progress.")

        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Exercise name cannot be empty.")

        self._exercise_op_in_progress = True
        try:
            async with self._exercise_lock:
                if self.storage.has_exercise(clean_name):
                    raise ValueError(f"An exercise named '{clean_name}' already exists.")

                reps = max(1, min(999, default_reps))
                weight = max(0.0, min(1000.0, default_weight))

                new_ex = Exercise(
                    name=clean_name,
                    category=category or "Other",
                    default_reps=reps,
                    default_weight=weight,
                    is_custom=True,
                )
                self.exercises = self.storage.add_exercise(new_ex)
                await self.select_exercise(new_ex.name)
                await self.trigger_haptic("vibrate")
                self.notify()
                return new_ex
        finally:
            self._exercise_op_in_progress = False

    async def update_exercise(
        self,
        original_name: str,
        name: str,
        category: str,
        default_reps: int,
        default_weight: float,
    ) -> Exercise:
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Exercise name cannot be empty.")

        reps = max(1, min(999, default_reps))
        weight = max(0.0, min(1000.0, round(default_weight, 2)))

        clean_orig = original_name.strip().lower()
        orig_ex = next((e for e in self.exercises if e.name.strip().lower() == clean_orig), None)
        if not orig_ex:
            raise ValueError(f"Exercise '{original_name}' not found.")

        # Keep default exercise's original name intact; custom exercises can rename
        target_name = clean_name if orig_ex.is_custom else orig_ex.name

        updated_ex = Exercise(
            name=target_name,
            category=category or orig_ex.category,
            default_reps=reps,
            default_weight=weight,
            is_custom=orig_ex.is_custom,
        )
        self.exercises = self.storage.update_exercise(original_name, updated_ex)

        # If currently selected exercise was updated, synchronize it
        if self.current_exercise.name.strip().lower() == clean_orig:
            self.current_exercise = updated_ex
            if self.current_set_number == 1:
                self.current_reps = updated_ex.default_reps
                self.current_weight = updated_ex.default_weight

        await self.trigger_haptic("vibrate")
        self.notify()
        return updated_ex

    async def delete_custom_exercise(self, name: str) -> None:
        self.exercises = self.storage.delete_custom_exercise(name)
        if self.current_exercise.name.strip().lower() == name.strip().lower():
            fallback = self.exercises[0] if self.exercises else Exercise("Push-ups", "Calisthenics", 15, 0.0)
            await self.select_exercise(fallback.name)
        self.notify()

    # --- History & Data Management ---

    async def delete_set(self, record_id: str) -> None:
        self.history = self.storage.delete_set(record_id)
        self._recalculate_current_set_number()
        await self.trigger_haptic("click")
        self.notify()

    async def clear_history(self) -> None:
        self.storage.clear_history()
        self.history = []
        self.current_set_number = 1
        await self.trigger_haptic("vibrate")
        self.notify()

    def save_weight_entry(self, weight_kg: float, recorded_at: str, entry_id: str | None = None) -> WeightEntry:
        recorded = datetime.fromisoformat(recorded_at)
        now = datetime.now().astimezone()
        if recorded.tzinfo is None:
            recorded = recorded.astimezone()
        if recorded > now:
            raise ValueError("Date and time cannot be in the future.")
        value = float(weight_kg)
        if not math.isfinite(value) or value <= 0:
            raise ValueError("Enter a weight greater than zero.")
        if entry_id and not any(item.id == entry_id for item in self.weight_history):
            raise ValueError("This weigh-in no longer exists.")
        entry = WeightEntry(weight_kg=round(value, 2), recorded_at=recorded.isoformat(timespec="minutes"), **({"id": entry_id} if entry_id else {}))
        self.weight_history = self.storage.upsert_weight_entry(entry)
        self.notify()
        return entry

    def delete_weight_entry(self, entry_id: str) -> None:
        self.weight_history = self.storage.delete_weight_entry(entry_id)
        self.notify()

    def set_target_weight(self, value: float | None) -> None:
        if value is not None:
            value = float(value)
            if not math.isfinite(value) or value <= 0:
                raise ValueError("Enter a target greater than zero.")
            value = round(value, 2)
        self.update_setting("target_weight_kg", value)

    async def export_csv(self) -> Tuple[Path, str, bool]:
        if not self.history:
            return Path(""), "", False

        export_file, csv_content = self.storage.export_history_to_csv()
        copied = False
        if self.clipboard:
            try:
                await self.clipboard.set(csv_content)
                copied = True
            except Exception:
                pass

        await self.trigger_haptic("vibrate")
        return export_file, csv_content, copied

    async def create_backup(self) -> Tuple[Path, str, dict, bool]:
        """Prepare a portable JSON backup for an explicit save or copy action."""
        backup_file, json_str, backup_data = self.storage.create_backup()
        return backup_file, json_str, backup_data, False

    async def restore_backup(
        self,
        backup_data: Any,
        mode: str = "merge",
    ) -> Tuple[int, int, bool]:
        """Restores data from a backup and synchronizes the active state."""
        restored_sets, restored_exercises, settings_restored = self.storage.restore_backup(
            backup_data, mode=mode
        )
        self.history = self.storage.load_history()
        self.weight_history = self.storage.load_weight_history()
        self.exercises = self.storage.load_exercises()
        if not self.exercises:
            self.exercises = [
                Exercise(name="Push-ups", category="Calisthenics", default_reps=15, default_weight=0.0)
            ]
        self.settings = self.storage.load_settings()
        self._recalculate_current_set_number()
        await self.trigger_haptic("vibrate")
        self.notify()
        return restored_sets, restored_exercises, settings_restored

    # --- Settings Management ---

    def update_setting(self, key: str, value: Any) -> None:
        self.settings[key] = value
        self.storage.save_settings(self.settings)
        self.notify()
