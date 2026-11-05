"""Comprehensive tests for SnapRep data models, storage, state management, and edge cases."""

import asyncio
import csv
from pathlib import Path
import pytest
import tempfile

from config import DEFAULT_EXERCISES_DATA, DEFAULT_SETTINGS, EXERCISE_CATEGORIES
from models import DEFAULT_EXERCISES, Exercise, SetRecord
from state import AppState
from storage import AppStorage
from theme import resolve_theme_mode
import flet as ft


def test_default_exercises_and_categories():
    assert len(DEFAULT_EXERCISES) >= 10
    pushup = next(e for e in DEFAULT_EXERCISES if e.name == "Push-ups")
    assert pushup.default_reps == 15
    assert "Chest" in EXERCISE_CATEGORIES
    assert "Calisthenics" in EXERCISE_CATEGORIES


def test_exercise_serialization():
    ex = Exercise(name="Incline DB Press", category="Chest", default_reps=12, default_weight=24.0, is_custom=True)
    data = ex.to_dict()
    assert data["name"] == "Incline DB Press"
    assert data["category"] == "Chest"
    assert data["default_reps"] == 12
    assert data["default_weight"] == 24.0
    assert data["is_custom"] is True

    restored = Exercise.from_dict(data)
    assert restored.name == ex.name
    assert restored.category == ex.category
    assert restored.default_reps == ex.default_reps
    assert restored.default_weight == ex.default_weight
    assert restored.is_custom is True


def test_set_record_serialization():
    record = SetRecord(exercise="Pull-ups", reps=10, weight_kg=0.0, notes="Felt strong")
    data = record.to_dict()
    assert data["exercise"] == "Pull-ups"
    assert data["reps"] == 10
    assert data["notes"] == "Felt strong"

    restored = SetRecord.from_dict(data)
    assert restored.exercise == "Pull-ups"
    assert restored.reps == 10
    assert restored.notes == "Felt strong"
    assert restored.id == record.id


def test_storage_history_and_single_set_deletion():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))

        assert storage.load_history() == []

        rec1 = SetRecord(exercise="Bench Press", reps=8, weight_kg=70.0)
        rec2 = SetRecord(exercise="Bench Press", reps=6, weight_kg=75.0)
        storage.add_record(rec1)
        storage.add_record(rec2)

        history = storage.load_history()
        assert len(history) == 2
        assert history[0].weight_kg == 75.0

        # Delete single set
        storage.delete_set(rec2.id)
        history_after = storage.load_history()
        assert len(history_after) == 1
        assert history_after[0].id == rec1.id

        # Clear
        storage.clear_history()
        assert storage.load_history() == []


def test_custom_exercises_duplicate_detection():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        exercises = storage.load_exercises()
        assert len(exercises) == len(DEFAULT_EXERCISES)

        # Add unique custom exercise
        custom = Exercise("Hammer Curl", "Arms", default_reps=12, default_weight=16.0)
        updated = storage.add_exercise(custom)
        assert len(updated) == len(DEFAULT_EXERCISES) + 1
        assert updated[0].name == "Hammer Curl"
        assert updated[0].is_custom is True

        # Duplicate exercise addition raises ValueError
        dup = Exercise("hammer curl", "Arms", default_reps=10, default_weight=14.0)
        with pytest.raises(ValueError, match="already exists"):
            storage.add_exercise(dup)

        # Delete custom exercise
        after_delete = storage.delete_custom_exercise("Hammer Curl")
        assert len(after_delete) == len(DEFAULT_EXERCISES)
        assert not any(e.name == "Hammer Curl" for e in after_delete)


def test_csv_export():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))

        rec1 = SetRecord(exercise="Barbell Squat", reps=10, weight_kg=80.0)
        rec2 = SetRecord(exercise="Push-ups", reps=25, weight_kg=0.0)
        storage.add_record(rec1)
        storage.add_record(rec2)

        export_file, csv_content = storage.export_history_to_csv()

        assert export_file.exists()
        assert export_file.suffix == ".csv"

        reader = list(csv.reader(csv_content.strip().splitlines()))
        assert reader[0] == ["ID", "Timestamp", "Exercise", "Reps", "Weight_kg", "Volume_kg", "Notes"]
        assert len(reader) == 3  # Header + 2 sets

        # Check calculated volume
        assert reader[1][2] == "Push-ups"
        assert reader[1][3] == "25"
        assert reader[1][5] == "0.0"

        assert reader[2][2] == "Barbell Squat"
        assert reader[2][3] == "10"
        assert reader[2][4] == "80.0"
        assert reader[2][5] == "800.0"


def test_theme_resolution():
    assert resolve_theme_mode("dark") == ft.ThemeMode.DARK
    assert resolve_theme_mode("light") == ft.ThemeMode.LIGHT
    assert resolve_theme_mode("system") == ft.ThemeMode.SYSTEM
    assert resolve_theme_mode("unknown") == ft.ThemeMode.SYSTEM


@pytest.mark.asyncio
async def test_app_state_rep_and_weight_clamping():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Reps clamping
        await state.update_reps(delta=-100)
        assert state.current_reps == 0

        await state.update_reps(absolute=1500)
        assert state.current_reps == 999

        # Weight clamping
        await state.update_weight(delta=-200.0)
        assert state.current_weight == 0.0

        await state.update_weight(absolute=2000.0)
        assert state.current_weight == 1000.0


@pytest.mark.asyncio
async def test_app_state_log_set_validation():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Cannot log set with 0 reps
        await state.update_reps(absolute=0)
        success, msg = await state.log_set()
        assert success is False
        assert "at least 1" in msg
        assert len(state.history) == 0

        # Can log set with positive reps
        await state.update_reps(absolute=12)
        await state.update_weight(absolute=50.0)
        success, msg = await state.log_set()
        assert success is True
        assert len(state.history) == 1
        assert state.history[0].reps == 12
        assert state.history[0].weight_kg == 50.0
        assert state.current_set_number == 2

        # Clean timer cleanup
        state.cancel_timer_task()


@pytest.mark.asyncio
async def test_app_state_timer_flow():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Set preset
        await state.set_timer_preset(10)
        assert state.timer_running is True
        assert state.timer_seconds_remaining == 10
        assert state.timer_task is not None

        # Pause
        await state.toggle_timer()
        assert state.timer_running is False
        assert state.timer_task is None

        # Reset
        await state.reset_timer()
        assert state.timer_running is False
        assert state.timer_seconds_remaining == 0


@pytest.mark.asyncio
async def test_app_state_custom_exercise_and_deletion():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Add exercise
        new_ex = await state.add_custom_exercise("Overhead Tricep Extension", "Arms", 12, 20.0)
        assert new_ex.name == "Overhead Tricep Extension"
        assert state.current_exercise.name == "Overhead Tricep Extension"

        # Duplicate check raises
        with pytest.raises(ValueError, match="already exists"):
            await state.add_custom_exercise("overhead tricep extension", "Arms", 10, 15.0)

        # Delete exercise
        await state.delete_custom_exercise("Overhead Tricep Extension")
        assert not any(e.name == "Overhead Tricep Extension" for e in state.exercises)
        assert state.current_exercise.name != "Overhead Tricep Extension"


@pytest.mark.asyncio
async def test_update_default_and_custom_exercise():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # 1. Update built-in exercise defaults (name remains preserved)
        updated_pushups = await state.update_exercise(
            original_name="Push-ups",
            name="Push-ups Renamed Attempt",
            category="Chest",
            default_reps=25,
            default_weight=5.0,
        )
        assert updated_pushups.name == "Push-ups"  # built-in preserves canonical name
        assert updated_pushups.category == "Chest"
        assert updated_pushups.default_reps == 25
        assert updated_pushups.default_weight == 5.0
        assert updated_pushups.is_custom is False

        # 2. Add and update a custom exercise
        await state.add_custom_exercise("Pistol Squat", "Legs", 5, 0.0)
        updated_custom = await state.update_exercise(
            original_name="Pistol Squat",
            name="Single Leg Squat",
            category="Legs",
            default_reps=8,
            default_weight=10.0,
        )
        assert updated_custom.name == "Single Leg Squat"
        assert updated_custom.default_reps == 8
        assert updated_custom.default_weight == 10.0
        assert updated_custom.is_custom is True

        # 3. Collision with existing exercise raises ValueError
        with pytest.raises(ValueError, match="already exists"):
            await state.update_exercise(
                original_name="Single Leg Squat",
                name="Push-ups",
                category="Chest",
                default_reps=10,
                default_weight=0.0,
            )


@pytest.mark.asyncio
async def test_duplicate_set_prevention_in_log_set():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        state.update_setting("default_rest_timer", 0)  # Disable auto-timer to test pure debounce

        await state.update_reps(absolute=10)
        await state.update_weight(absolute=50.0)

        # 1st log succeeds
        success1, msg1 = await state.log_set()
        assert success1 is True
        assert len(state.history) == 1

        # Rapid 2nd log with identical params is debounced and ignored
        success2, msg2 = await state.log_set()
        assert success2 is False
        assert "Duplicate set ignored" in msg2
        assert len(state.history) == 1

        # Changing reps allows logging immediately
        await state.update_reps(absolute=11)
        success3, msg3 = await state.log_set()
        assert success3 is True
        assert len(state.history) == 2

        state.cancel_timer_task()


@pytest.mark.asyncio
async def test_default_rest_timer_configuration():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Configure default rest timer to 90 seconds
        state.update_setting("default_rest_timer", 90)
        assert state.settings["default_rest_timer"] == 90

        await state.update_reps(absolute=10)
        await state.log_set()
        assert state.timer_running is True
        assert state.timer_seconds_remaining == 90
        await state.reset_timer()

        # Configure default rest timer to 0 (disabled)
        state.update_setting("default_rest_timer", 0)
        await state.update_reps(absolute=12)
        await state.log_set()
        assert state.timer_running is False
        state.cancel_timer_task()


class MockPage:
    def __init__(self):
        self.controls = []
        self.services = []
        self.dialog = None
        self.theme_mode = "dark"

    def update(self):
        pass

    def show_dialog(self, dialog):
        self.dialog = dialog

    def pop_dialog(self):
        self.dialog = None


def test_calendar_and_grouped_history_view():
    from views.history_view import HistoryView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        # Seed records across two distinct dates
        rec1 = SetRecord(exercise="Push-ups", reps=20, weight_kg=0.0, timestamp="2026-11-01 10:00:00")
        rec2 = SetRecord(exercise="Barbell Bench Press", reps=10, weight_kg=70.0, timestamp="2026-11-03 09:00:00")
        rec3 = SetRecord(exercise="Barbell Bench Press", reps=8, weight_kg=75.0, timestamp="2026-11-03 09:05:00")
        storage.add_record(rec1)
        storage.add_record(rec2)
        storage.add_record(rec3)

        state = AppState(storage=storage)
        page = MockPage()
        history_view = HistoryView(page, state)

        # Select 2026-11-03
        history_view._select_date("2026-11-03")
        assert history_view.selected_date_str == "2026-11-03"
        assert history_view.view_mode == "day"
        # Renders 2 set cards in the classic format containing individual delete buttons
        assert len(history_view.day_exercise_list.controls) == 2
        assert "2 sets" in history_view.selected_date_stats.value

        # Select 2026-11-01
        history_view._select_date("2026-11-01")
        assert len(history_view.day_exercise_list.controls) == 1
        assert "1 sets" in history_view.selected_date_stats.value

        # Select a rest day (e.g. 2026-11-02)
        history_view._select_date("2026-11-02")
        assert "No sets recorded" in history_view.selected_date_stats.value

        # Attempting to select a future date is strictly blocked
        current_sel = history_view.selected_date_str
        history_view._select_date("2099-12-31")
        assert history_view.selected_date_str == current_sel

        # Switch to All History view
        history_view._set_view_mode("all")
        assert history_view.view_mode == "all"
        assert len(history_view.day_exercise_list.controls) == 3


@pytest.mark.asyncio
async def test_settings_view_preferences():
    from views.settings_view import SettingsView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        page = MockPage()
        settings_view = SettingsView(page, state)

        appearance = settings_view.root.content.controls[0]
        palette_row = appearance.controls[1].content.controls[1]
        theme_row = appearance.controls[1].content.controls[3]
        workout = settings_view.root.content.controls[1]
        rest_row = workout.controls[1].content.controls[0]
        assert palette_row.controls == [settings_view.palette_dropdown]
        assert theme_row.controls == [settings_view.theme_dropdown]
        assert rest_row.controls == [settings_view.rest_timer_dropdown]
        assert settings_view.palette_dropdown.expand is True
        assert settings_view.theme_dropdown.expand is True
        assert settings_view.rest_timer_dropdown.expand is True

        # Default is light theme
        assert settings_view.theme_dropdown.value == "light"
        assert settings_view.palette_dropdown.value == "coral"

        settings_view.palette_dropdown.value = "gruvbox"
        await settings_view._on_palette_select(None)
        assert state.settings["theme_palette"] == "gruvbox"
        assert storage.load_settings()["theme_palette"] == "gruvbox"

        # Check theme change to dark
        settings_view.theme_dropdown.value = "dark"
        await settings_view._on_theme_select(None)
        assert state.settings["theme_mode"] == "dark"

        # Check rest timer change
        settings_view.rest_timer_dropdown.value = "120"
        await settings_view._on_rest_timer_select(None)
        assert state.settings["default_rest_timer"] == 120

        # Check haptic toggle
        settings_view.haptic_switch.value = False
        await settings_view._on_haptic_toggle(None)
        assert state.settings["haptic_feedback"] is False


@pytest.mark.asyncio
async def test_main_mount():
    from main import main

    page = MockPage()
    page.services = []
    page.controls = []
    page.add = lambda ctrl: page.controls.append(ctrl)

    await main(page)

    assert len(page.controls) == 1
    assert page.navigation_bar is not None
    assert page.appbar is not None
    assert page.navigation_bar.selected_index == 0
    assert len(page.navigation_bar.destinations) == 5


@pytest.mark.asyncio
async def test_dynamic_color_service_skipped_in_web_preview(monkeypatch):
    import main as app_module

    class NativeColor:
        def __init__(self, **kwargs):
            pass

    monkeypatch.setattr(app_module, "SnaprepDynamicColor", NativeColor)
    page = MockPage()
    page.web = True
    page.platform = ft.PagePlatform.ANDROID
    page.add = lambda ctrl: page.controls.append(ctrl)

    await app_module.main(page)

    assert not any(isinstance(service, NativeColor) for service in page.services)


@pytest.mark.asyncio
async def test_missing_native_color_listener_falls_back_once(monkeypatch):
    import main as app_module

    class NativeColor:
        calls = 0

        def __init__(self, **kwargs):
            pass

        async def refresh(self):
            self.calls += 1
            raise RuntimeError("Timeout waiting for invoke method listener")

    monkeypatch.setattr(app_module, "SnaprepDynamicColor", NativeColor)
    page = MockPage()
    page.web = False
    page.platform = ft.PagePlatform.ANDROID
    page.add = lambda ctrl: page.controls.append(ctrl)
    tasks = []
    page.run_task = lambda handler: tasks.append(handler)

    await app_module.main(page)
    assert len(tasks) == 1
    await tasks[0]()
    await page.on_app_lifecycle_state_change(
        type("Event", (), {"state": ft.AppLifecycleState.RESUME})()
    )
    native_color = next(service for service in page.services if isinstance(service, NativeColor))
    assert native_color.calls == 1


def test_tracker_view_weight_and_input():
    from views.tracker_view import TrackerView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        page = MockPage()
        tracker = TrackerView(page, state)

        # Check initial weight input and spacious stepper controls
        assert tracker.weight_input.value == "0"
        assert tracker.default_weight_btn is not None

        # Typing in weight input updates state
        class MockEvent:
            class control:
                value = "72.5"
        tracker._on_weight_input_change(MockEvent())
        assert state.current_weight == 72.5

        # Update UI syncs formatted text
        tracker.update_ui()
        assert tracker.weight_input.value == "72.5"


def test_tracker_uses_compact_layout_on_short_screens(tmp_path):
    from views.tracker_view import TrackerView

    page = MockPage()
    page.height = 640
    tracker = TrackerView(page, AppState(storage=AppStorage(storage_dir=tmp_path)))
    assert tracker.root.content.scroll is None
    assert tracker.weight_shortcuts.visible is False
    assert tracker.reps_display.size == 44

    tracker.update_viewport_layout(800)
    assert tracker.weight_shortcuts.visible is True
    assert tracker.reps_display.size == 52


def test_history_view_long_exercise_name_no_overflow():
    from views.history_view import HistoryView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        long_rec = SetRecord(
            exercise="Extremely Long Custom Exercise Name That Could Overflow Any Mobile Screen Bench Press",
            reps=10,
            weight_kg=100.0,
            timestamp="2026-11-03 10:00:00",
        )
        storage.add_record(long_rec)
        state = AppState(storage=storage)
        page = MockPage()
        history_view = HistoryView(page, state)

        history_view._select_date("2026-11-03")
        assert len(history_view.day_exercise_list.controls) == 1
        card = history_view.day_exercise_list.controls[0]
        card_content = card.content.content
        # Ensure left side is expand=True so delete button on right is never pushed out
        left_row = card_content.controls[0]
        assert left_row.expand is True
        right_row = card_content.controls[1]
        # Delete icon button is present on the right
        assert right_row.controls[1].icon == ft.Icons.DELETE_OUTLINE


def test_edit_exercise_dialog_creation_no_type_error():
    from components.edit_exercise_dialog import show_edit_exercise_dialog

    page = MockPage()
    state = AppState(storage=AppStorage(storage_dir=Path(tempfile.mkdtemp())))

    # Built-in exercise dialog
    pushups = next(e for e in state.exercises if e.name == "Push-ups")
    show_edit_exercise_dialog(page, state, pushups)
    assert page.dialog is not None
    assert "Push-ups" in page.dialog.title.value

    # Custom exercise dialog
    custom_ex = Exercise("Custom Chin-up", "Calisthenics", 10, 0.0, is_custom=True)
    show_edit_exercise_dialog(page, state, custom_ex)
    assert page.dialog is not None
    assert "Custom Chin-up" in page.dialog.title.value


@pytest.mark.asyncio
async def test_edit_exercise_save_shows_validation_and_updates_defaults(tmp_path):
    from components.edit_exercise_dialog import show_edit_exercise_dialog

    state = AppState(storage=AppStorage(storage_dir=tmp_path))
    exercise = next(ex for ex in state.exercises if ex.name == "Push-ups")
    page = MockPage()
    show_edit_exercise_dialog(page, state, exercise)
    dialog = page.dialog
    name_field, _, defaults_row, status = dialog.content.content.controls
    save_button = dialog.actions[1]

    name_field.value = ""
    await save_button.on_click(None)
    assert status.visible is True
    assert "name" in status.value

    name_field.value = "Push-ups"
    defaults_row.controls[0].content.value = "20"
    await save_button.on_click(None)
    assert next(ex for ex in state.exercises if ex.name == "Push-ups").default_reps == 20
    assert save_button.disabled is False


@pytest.mark.asyncio
async def test_add_exercise_save_feedback_and_validation(tmp_path):
    from components.add_exercise_dialog import show_add_exercise_dialog

    state = AppState(storage=AppStorage(storage_dir=tmp_path))
    page = MockPage()
    saved = []
    show_add_exercise_dialog(page, state, on_success=saved.append)

    dialog = page.dialog
    name_field, category_row, defaults_row, status = dialog.content.content.controls
    reps_field = defaults_row.controls[0].content
    weight_field = defaults_row.controls[1].content
    save_button = dialog.actions[1]

    await save_button.on_click(None)
    assert status.visible is True
    assert "name" in status.value
    assert name_field.error_text == status.value

    name_field.value = "Cable Fly"
    reps_field.value = "abc"
    await save_button.on_click(None)
    assert "1 to 999" in status.value
    assert not saved

    reps_field.value = "12"
    weight_field.value = "-1"
    await save_button.on_click(None)
    assert "0 to 1000" in status.value
    assert not saved

    weight_field.value = "5"
    await save_button.on_click(None)
    assert len(saved) == 1
    assert saved[0].name == "Cable Fly"
    assert saved[0].default_reps == 12
    assert saved[0].default_weight == 5
    assert save_button.disabled is False


@pytest.mark.asyncio
async def test_add_exercise_save_disables_repeat_taps(tmp_path, monkeypatch):
    from components.add_exercise_dialog import show_add_exercise_dialog

    state = AppState(storage=AppStorage(storage_dir=tmp_path))
    page = MockPage()
    show_add_exercise_dialog(page, state, initial_name="Cable Fly")
    dialog = page.dialog
    save_button = dialog.actions[1]
    started = asyncio.Event()
    release = asyncio.Event()
    original_add = state.add_custom_exercise
    calls = 0

    async def delayed_add(**kwargs):
        nonlocal calls
        calls += 1
        started.set()
        await release.wait()
        return await original_add(**kwargs)

    monkeypatch.setattr(state, "add_custom_exercise", delayed_add)
    first_tap = asyncio.create_task(save_button.on_click(None))
    await started.wait()
    assert save_button.disabled is True
    assert save_button.content == "Saving…"
    await save_button.on_click(None)
    assert calls == 1
    release.set()
    await first_tap
    assert save_button.disabled is False
    assert calls == 1


def test_exercises_view_library_and_filtering():
    from views.exercises_view import ExercisesView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        page = MockPage()
        view = ExercisesView(page, state)

        # Initially shows all default exercises
        assert len(view.exercise_list_column.controls) >= 10
        assert "Showing" in view.count_badge.value

        # Filter by category
        view._select_category("Chest")
        assert len(view.exercise_list_column.controls) >= 1

        # Search filter
        class MockEvent:
            class control:
                value = "bench"
        view._on_search_change(MockEvent())
        assert len(view.exercise_list_column.controls) == 1


def test_exercises_search_and_filters_stay_outside_results_scroll():
    from views.exercises_view import ExercisesView

    with tempfile.TemporaryDirectory() as tmpdir:
        view = ExercisesView(MockPage(), AppState(storage=AppStorage(storage_dir=Path(tmpdir))))
        layout = view.root.content
        search_row, category_row, count_row, results = layout.controls

        assert layout.scroll is None
        assert search_row.controls == [view.search_field]
        assert category_row is view.category_row
        assert count_row.controls[0] is view.count_badge
        assert results.expand is True
        assert results.content is view.exercise_list_column
        assert view.exercise_list_column.expand is True
        assert view.exercise_list_column.scroll == ft.ScrollMode.ADAPTIVE
        assert all(not isinstance(control, ft.Column) for control in layout.controls[:3])


def test_exercise_library_row_opens_details_and_actions():
    from views.exercises_view import ExercisesView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        view = ExercisesView(page, state)

        builtin_row = next(control for control in view.exercise_list_column.controls if isinstance(control, ft.ListTile))
        builtin_row.on_click(None)
        assert isinstance(page.dialog, ft.BottomSheet)
        builtin_actions = page.dialog.content.content.controls
        assert any(isinstance(control, ft.FilledButton) for control in builtin_actions)
        assert not any(isinstance(control, ft.TextButton) for control in builtin_actions)
        next(control for control in builtin_actions if isinstance(control, ft.FilledButton)).on_click(None)
        assert isinstance(page.dialog, ft.AlertDialog)

        custom = Exercise("Floor press", "Chest", 8, 20.0, is_custom=True)
        state.exercises.insert(0, custom)
        view.update_ui()
        custom_row = next(control for control in view.exercise_list_column.controls if isinstance(control, ft.ListTile))
        custom_row.on_click(None)
        custom_actions = page.dialog.content.content.controls
        assert any(isinstance(control, ft.TextButton) and control.content == "Delete exercise" for control in custom_actions)
        next(control for control in custom_actions if isinstance(control, ft.TextButton)).on_click(None)
        assert isinstance(page.dialog, ft.AlertDialog)


def test_history_view_no_duplicate_sets_on_repeated_renders():
    from views.history_view import HistoryView
    from datetime import date

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        today_str = date.today().strftime("%Y-%m-%d")

        # Add 3 distinct sets
        rec1 = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, timestamp=f"{today_str} 10:00:00")
        rec2 = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, timestamp=f"{today_str} 10:02:00")
        rec3 = SetRecord(exercise="Bench Press", reps=8, weight_kg=70.0, timestamp=f"{today_str} 10:05:00")
        storage.add_record(rec1)
        storage.add_record(rec2)
        storage.add_record(rec3)

        state = AppState(storage=storage)
        page = MockPage()
        history_view = HistoryView(page, state)

        # Select today
        history_view._select_date(today_str)

        # Simulate 10 rapid update_ui calls
        for _ in range(10):
            history_view.update_ui()

        # Day view must strictly have 3 set cards
        assert len(history_view.day_exercise_list.controls) == 3

        # Switch to all view and simulate 10 update_ui calls
        history_view._set_view_mode("all")
        for _ in range(10):
            history_view.update_ui()

        # All view must strictly have 3 set cards
        assert len(history_view.day_exercise_list.controls) == 3


@pytest.mark.asyncio
async def test_timer_decoupled_notifications():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        global_notify_count = 0
        timer_notify_count = 0

        def on_global_notify():
            nonlocal global_notify_count
            global_notify_count += 1

        def on_timer_notify():
            nonlocal timer_notify_count
            timer_notify_count += 1

        state.subscribe(on_global_notify)
        state.subscribe_timer(on_timer_notify)

        # Second tick must ONLY notify timer subscribers
        state.timer_seconds_remaining = 30
        state.timer_running = True
        state._notify_timer()

        assert timer_notify_count == 1
        assert global_notify_count == 0

        # Unsubscribe timer
        state.unsubscribe_timer(on_timer_notify)
        state._notify_timer()
        assert timer_notify_count == 1


def test_storage_deduplication():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        rec = SetRecord(exercise="Squats", reps=10, weight_kg=80.0)

        # Add once
        storage.add_record(rec)
        assert len(storage.load_history()) == 1

        # Adding same record with identical ID must not duplicate
        storage.add_record(rec)
        assert len(storage.load_history()) == 1

        # Adding another record with different ID but identical exercise, reps, weight and timestamp is rejected
        rec2 = SetRecord(exercise="Squats", reps=10, weight_kg=80.0, timestamp=rec.timestamp)
        storage.add_record(rec2)
        assert len(storage.load_history()) == 1


@pytest.mark.asyncio
async def test_state_rapid_log_debounce():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        state.update_setting("default_rest_timer", 0)  # Pure debounce without auto-timer

        # First log succeeds
        success1, _ = await state.log_set()
        assert success1 is True

        # Rapid second log within 3 seconds with identical parameters is rejected
        success2, msg2 = await state.log_set()
        assert success2 is False
        assert "Duplicate set ignored" in msg2


@pytest.mark.asyncio
async def test_log_blocked_while_rest_timer_running():
    """Validates user requirement: till rest timer is running you cant log another set."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        state.update_setting("default_rest_timer", 60)

        # 1. First log starts 60s rest timer
        success1, _ = await state.log_set()
        assert success1 is True
        assert state.timer_running is True
        assert state.timer_seconds_remaining == 60

        # 2. Second log is blocked because timer is running
        success2, msg2 = await state.log_set()
        assert success2 is False
        assert "Rest timer is running" in msg2

        # 3. Stopping/resetting the timer unblocks logging
        await state.reset_timer()
        assert state.timer_running is False

        # Now can log again (with different reps or after debounce)
        await state.update_reps(absolute=20)
        success3, _ = await state.log_set()
        assert success3 is True
        state.cancel_timer_task()


@pytest.mark.asyncio
async def test_log_blocked_while_in_flight():
    """Synchronous _logging_in_progress flag prevents concurrent log calls."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Manually set the in-flight flag (simulates concurrent button tap)
        state._logging_in_progress = True
        success, msg = await state.log_set()
        assert success is False
        assert "Already logging" in msg
        # Flag should NOT have been cleared by this call (it was set externally)
        state._logging_in_progress = False


@pytest.mark.asyncio
async def test_tracker_log_btn_blocked_during_timer():
    from views.tracker_view import TrackerView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        page = MockPage()
        tracker = TrackerView(page, state)

        # An exercise must be chosen before the first set can be logged.
        assert tracker._is_log_blocked()
        await state.select_exercise("Pull-ups")
        tracker.update_ui()
        assert not tracker._is_log_blocked()

        # Simulate timer running
        state.timer_running = True
        state.timer_seconds_remaining = 60
        assert tracker._is_log_blocked()

        # Simulate timer finished
        state.timer_running = False
        state.timer_seconds_remaining = 0
        assert not tracker._is_log_blocked()


def test_set_record_model_set_number():
    rec = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, set_number=3)
    d = rec.to_dict()
    assert d["set_number"] == 3

    restored = SetRecord.from_dict(d)
    assert restored.set_number == 3

    # Backwards compatibility when set_number is missing in JSON
    legacy_d = {"id": "123", "exercise": "Squats", "reps": 10, "weight_kg": 50.0}
    legacy_rec = SetRecord.from_dict(legacy_d)
    assert legacy_rec.set_number == 1


@pytest.mark.asyncio
async def test_dynamic_set_number_recalculation():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        state.update_setting("default_rest_timer", 0)

        # Starts at Set 1
        assert state.current_set_number == 1

        # Log Set 1
        success1, _ = await state.log_set()
        assert success1 is True
        assert state.current_set_number == 2

        # Log Set 2 (with different reps to bypass debounce)
        await state.update_reps(absolute=20)
        success2, _ = await state.log_set()
        assert success2 is True
        assert state.current_set_number == 3

        # Switch to Bench Press (no sets today) -> set number resets to 1
        bench = next(e for e in state.exercises if "Bench" in e.name)
        await state.select_exercise(bench.name)
        assert state.current_set_number == 1

        # Switch back to Push-ups -> set number continues at 3
        pushups = next(e for e in state.exercises if e.name == "Push-ups")
        await state.select_exercise(pushups.name)
        assert state.current_set_number == 3

        # Deleting a set reduces current set number
        rec_to_delete = state.history[0].id
        await state.delete_set(rec_to_delete)
        assert state.current_set_number == 2

        # Clear all resets to 1
        await state.clear_history()
        assert state.current_set_number == 1


@pytest.mark.asyncio
async def test_tracker_filled_button_and_history_badges():
    from datetime import date
    from views.tracker_view import TrackerView
    from views.history_view import HistoryView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        page = MockPage()
        tracker = TrackerView(page, state)

        # The initial action prompts for an exercise.
        assert isinstance(tracker.log_btn, ft.FilledButton)
        assert tracker.log_btn.content == "SELECT AN EXERCISE"
        assert tracker.log_btn.disabled is True
        await state.select_exercise("Pull-ups")
        tracker.update_ui()
        assert tracker.log_btn.content == "LOG THIS SET"
        assert tracker.log_btn.disabled is False

        # Simulate timer running -> direct button content update
        state.timer_running = True
        state.timer_seconds_remaining = 45
        tracker._sync_log_btn_state()
        assert tracker.log_btn.disabled is True
        assert tracker.log_btn.content == "REST IN PROGRESS"

        # Stop timer -> button reverts
        state.timer_running = False
        state.timer_seconds_remaining = 0
        tracker._sync_log_btn_state()
        assert tracker.log_btn.disabled is False
        assert tracker.log_btn.content == "LOG THIS SET"

        # History View renders SET badges
        today_str = date.today().strftime("%Y-%m-%d")
        r1 = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, timestamp=f"{today_str} 10:00:00", set_number=1)
        r2 = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, timestamp=f"{today_str} 10:02:00", set_number=2)
        storage.add_record(r1)
        storage.add_record(r2)
        state.history = storage.load_history()

        history_view = HistoryView(page, state)
        history_view._select_date(today_str)
        cards = history_view.day_exercise_list.controls
        assert len(cards) == 2

        # Check SET badges in cards
        for card in cards:
            assert card.key.startswith("set_card_")
            card_content = card.content.content
            left_row = card_content.controls[0]
            set_badge = left_row.controls[0]
            assert "SET" in set_badge.content.value


@pytest.mark.asyncio
async def test_log_button_static_rest_label_during_timer():
    from views.tracker_view import TrackerView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        page = MockPage()
        tracker = TrackerView(page, state)

        # Set timer running
        await state.select_exercise("Pull-ups")
        tracker.update_ui()
        state.timer_running = True
        state.timer_seconds_remaining = 30
        tracker._sync_log_btn_state()
        assert tracker.log_btn.content == "REST IN PROGRESS"
        assert tracker.log_btn.disabled is True

        # Simulate ticks: timer_display updates, but log_btn stays static (no countdown in button)
        state.timer_seconds_remaining = 29
        tracker._on_timer_tick()
        assert tracker.timer_display.value == "00:29"
        assert tracker.log_btn.content == "REST IN PROGRESS"

        state.timer_seconds_remaining = 28
        tracker._on_timer_tick()
        assert tracker.timer_display.value == "00:28"
        assert tracker.log_btn.content == "REST IN PROGRESS"


def test_storage_in_memory_caching_and_fast_dedup():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))

        # Initially empty cache
        assert storage._history_cache is None
        history = storage.load_history()
        assert history == []
        assert storage._history_cache == []

        # Add record
        r1 = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0)
        storage.add_record(r1)
        assert len(storage._history_cache) == 1

        # load_history uses in-memory cache directly
        loaded = storage.load_history()
        assert len(loaded) == 1
        assert loaded[0].exercise == "Push-ups"

        # Settings cache
        settings = storage.load_settings()
        assert storage._settings_cache is not None
        storage.save_settings({"theme_mode": "dark"})
        assert storage._settings_cache["theme_mode"] == "dark"

        # Exercises cache
        exercises = storage.load_exercises()
        assert storage._exercises_cache is not None
        assert len(exercises) >= 10


def test_tracker_timer_tick_tab_awareness():
    from views.tracker_view import TrackerView

    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        update_calls = 0
        class TrackingPage(MockPage):
            def update(self):
                nonlocal update_calls
                update_calls += 1

        page = TrackingPage()
        tracker = TrackerView(page, state)

        # Active tab: _on_timer_tick updates timer_display
        tracker.is_active = True
        state.timer_seconds_remaining = 15
        tracker._on_timer_tick()
        assert tracker.timer_display.value == "00:15"

        # Inactive tab (user on History or Stats): _on_timer_tick skips UI update
        tracker.is_active = False
        state.timer_seconds_remaining = 14
        tracker._on_timer_tick()
        assert tracker.timer_display.value == "00:14"


def test_get_default_storage_dir_mobile_and_desktop(monkeypatch, tmp_path):
    from storage import get_default_storage_dir

    # 1. Flet mobile runtime environment variable
    flet_data = tmp_path / "flet_data"
    monkeypatch.setenv("FLET_APP_STORAGE_DATA", str(flet_data))
    path = get_default_storage_dir()
    assert str(path) == str(flet_data / ".snap_rep")

    # 2. Android sandbox fallback
    android_private = tmp_path / "android_private"
    monkeypatch.delenv("FLET_APP_STORAGE_DATA", raising=False)
    monkeypatch.setenv("ANDROID_PRIVATE", str(android_private))
    path = get_default_storage_dir()
    assert str(path) == str(android_private / ".snap_rep")

    # 3. Guard against Android returning root-owned '/data'
    monkeypatch.delenv("ANDROID_PRIVATE", raising=False)
    monkeypatch.setattr(Path, "home", lambda: Path("/data"))
    path = get_default_storage_dir()
    assert path != Path("/data/.snap_rep")
    assert path.exists()


def test_create_backup_structure():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        storage.add_record(SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0))
        storage.add_exercise(Exercise(name="Muscle-ups", category="Back", default_reps=5, default_weight=0.0))
        storage.save_settings({"theme_mode": "light", "default_rest_timer": 90})

        backup_file, json_str, backup_data = storage.create_backup()

        assert backup_file.exists()
        assert backup_file.parent == storage.backups_dir
        assert backup_data["app"] == "SnapRep"
        assert backup_data["version"] == 1
        assert len(backup_data["history"]) == 1
        assert any(e["name"] == "Muscle-ups" for e in backup_data["exercises"])
        assert backup_data["settings"]["theme_mode"] == "light"
        assert backup_data["settings"]["default_rest_timer"] == 90

        # Verify get_local_backups
        backups = storage.get_local_backups()
        assert len(backups) == 1
        assert backups[0] == backup_file


@pytest.mark.asyncio
async def test_recent_backup_button_opens_restore_preview(tmp_path):
    from components.restore_dialog import show_restore_dialog

    storage = AppStorage(storage_dir=tmp_path)
    storage.add_record(SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0))
    storage.create_backup()
    state = AppState(storage=storage)
    page = MockPage()

    await show_restore_dialog(page, state)
    picker = page.dialog
    recent_button = next(
        control for control in picker.content.content.controls
        if isinstance(control, ft.OutlinedButton)
        and isinstance(control.content, ft.Row)
        and control.content.controls[1].value.endswith(".json")
    )
    await recent_button.on_click(None)

    assert page.dialog is not picker
    assert page.dialog.title.controls[1].value == "Confirm Restore"


@pytest.mark.asyncio
async def test_backup_copy_button_reports_unavailable_clipboard(tmp_path):
    from components.backup_dialog import show_backup_dialog

    state = AppState(storage=AppStorage(storage_dir=tmp_path))
    page = MockPage()
    page.platform = ft.PagePlatform.LINUX
    await show_backup_dialog(page, state)
    dialog = page.dialog
    copy_button = dialog.content.content.controls[-1]
    status_text = dialog.content.content.controls[-3].controls[1]

    await copy_button.on_click(None)
    assert "unavailable" in status_text.value
    assert status_text.color == ft.Colors.ERROR


def test_restore_backup_merge_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        # Existing set
        rec1 = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, timestamp="2026-11-01 10:00:00")
        storage.add_record(rec1)

        # Backup has rec1 AND rec2, plus a custom exercise
        rec2 = SetRecord(exercise="Pull-ups", reps=10, weight_kg=0.0, timestamp="2026-11-02 10:00:00")
        backup_dict = {
            "version": 1,
            "app": "SnapRep",
            "history": [rec1.to_dict(), rec2.to_dict()],
            "exercises": [
                {"name": "Pike Push-ups", "category": "Shoulders", "default_reps": 12, "default_weight": 0.0, "is_custom": True}
            ],
            "settings": {"default_rest_timer": 45},
        }

        restored_sets, restored_ex, settings_done = storage.restore_backup(backup_dict, mode="merge")

        assert restored_sets == 1  # Only rec2 added, rec1 duplicate was skipped
        assert restored_ex == 1    # Pike Push-ups added
        history = storage.load_history()
        assert len(history) == 2
        assert any(r.exercise == "Pull-ups" for r in history)
        assert any(r.exercise == "Push-ups" for r in history)
        assert storage.has_exercise("Pike Push-ups")


def test_restore_backup_replace_mode():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        old_rec = SetRecord(exercise="Push-ups", reps=15, weight_kg=0.0, timestamp="2026-11-01 10:00:00")
        storage.add_record(old_rec)

        new_rec = SetRecord(exercise="Deadlift", reps=5, weight_kg=120.0, timestamp="2026-11-03 10:00:00")
        backup_dict = {
            "version": 1,
            "app": "SnapRep",
            "history": [new_rec.to_dict()],
            "exercises": [
                {"name": "Trap Bar Deadlift", "category": "Back", "default_reps": 5, "default_weight": 100.0, "is_custom": True}
            ],
            "settings": {"theme_mode": "light", "default_rest_timer": 120},
        }

        restored_sets, restored_ex, settings_done = storage.restore_backup(backup_dict, mode="replace")

        assert restored_sets == 1
        history = storage.load_history()
        assert len(history) == 1
        assert history[0].exercise == "Deadlift"
        assert not any(r.exercise == "Push-ups" for r in history)
        assert storage.has_exercise("Trap Bar Deadlift")
        assert storage.load_settings()["theme_mode"] == "light"
        assert storage.load_settings()["default_rest_timer"] == 120


def test_restore_raw_history_list():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        rec1 = SetRecord(exercise="Squat", reps=10, weight_kg=80.0, timestamp="2026-11-02 12:00:00")
        raw_list = [rec1.to_dict()]

        restored_sets, restored_ex, settings_done = storage.restore_backup(raw_list, mode="merge")
        assert restored_sets == 1
        assert len(storage.load_history()) == 1
        assert storage.load_history()[0].exercise == "Squat"


def test_restore_corrupted_json():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        with pytest.raises(Exception):
            storage.restore_backup("NOT_VALID_JSON{", mode="merge")
        with pytest.raises(ValueError):
            storage.restore_backup(12345, mode="merge")


@pytest.mark.asyncio
async def test_state_create_and_restore_backup():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        notifications = []
        state.subscribe(lambda: notifications.append(True))

        state.current_reps = 12
        state.current_weight = 0.0
        success, msg = await state.log_set()
        assert success is True
        assert len(state.history) == 1

        backup_file, json_str, backup_data, copied = await state.create_backup()
        assert backup_file.exists()
        assert state.current_exercise.name in json_str

        # Clear history
        await state.clear_history()
        assert len(state.history) == 0

        # Restore from backup JSON string
        restored_sets, restored_ex, settings_done = await state.restore_backup(json_str, mode="merge")
        assert restored_sets == 1
        assert len(state.history) == 1
        assert len(notifications) > 0


def test_stats_view_rendering():
    from views.stats_view import StatsView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # 1. Empty state
        stats_view = StatsView(page, state)
        assert len(stats_view.stats_column.controls) == 1

        # 2. Populated with sets (weighted and bodyweight)
        state.storage.add_record(SetRecord(exercise="Bench Press", reps=10, weight_kg=80.0))
        state.storage.add_record(SetRecord(exercise="Push-ups", reps=25, weight_kg=0.0))
        state.history = state.storage.load_history()

        stats_view.update_ui()
        assert len(stats_view.stats_column.controls) >= 3









def test_storage_exercise_deduplication():
    import json
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        # Write json with duplicate custom exercises
        raw_data = [
            {"name": "Push-ups", "category": "Calisthenics", "default_reps": 15, "default_weight": 0.0, "is_custom": False},
            {"name": "Lateral Raise", "category": "Shoulders", "default_reps": 12, "default_weight": 10.0, "is_custom": True},
            {"name": "lateral raise", "category": "Shoulders", "default_reps": 12, "default_weight": 10.0, "is_custom": True},
            {"name": "  Lateral Raise  ", "category": "Shoulders", "default_reps": 12, "default_weight": 10.0, "is_custom": True},
        ]
        with open(storage.exercises_file, "w", encoding="utf-8") as f:
            json.dump(raw_data, f)

        # Clear cache to force reload
        storage._exercises_cache = None
        exercises = storage.load_exercises()
        names = [e.name for e in exercises]
        assert names.count("Push-ups") == 1
        assert names.count("Lateral Raise") == 1
        assert len(exercises) == 2


@pytest.mark.asyncio
async def test_add_custom_exercise_concurrent_guard():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        t1 = asyncio.create_task(state.add_custom_exercise("Hammer Curl", "Arms", 10, 16.0))
        t2 = asyncio.create_task(state.add_custom_exercise("Hammer Curl", "Arms", 10, 16.0))
        results = await asyncio.gather(t1, t2, return_exceptions=True)
        # Exactly one should succeed, and one should fail with ValueError
        succeeded = [r for r in results if isinstance(r, Exercise)]
        failed = [r for r in results if isinstance(r, ValueError)]
        assert len(succeeded) == 1
        assert len(failed) == 1
        assert sum(1 for e in state.exercises if e.name.strip().lower() == "hammer curl") == 1


def test_exercise_picker_dialog_search_and_category():
    from components.exercise_picker_dialog import show_exercise_picker

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        # Add custom exercise
        storage.add_exercise(Exercise("Incline DB Flye", "Chest", 12, 18.0, is_custom=True))
        state.exercises = storage.load_exercises()

        selected_holder = []
        show_exercise_picker(page, state, on_select=lambda ex: selected_holder.append(ex))
        assert page.dialog is not None
        bs_content = page.dialog.content
        column_controls = bs_content.content.controls

        # Check search input, category row, and list container
        search_field = column_controls[1].controls[0]
        category_row = column_controls[2]
        list_container = column_controls[4]
        list_column = list_container.content

        # Initial list contains all exercises
        assert len(list_column.controls) == len(state.exercises)

        # 1. Test search filter
        search_field.value = "incline"
        search_field.on_change(type("Event", (), {"control": search_field})())
        assert len(list_column.controls) == 1

        # 2. Test category filter for "Chest" (clear search query first)
        search_field.value = ""
        search_field.on_change(type("Event", (), {"control": search_field})())
        chest_pill = next(p for p in category_row.controls if p.content.value == "Chest")
        chest_pill.on_click(None)
        # Should match Incline DB Flye and Barbell Bench Press
        assert len(list_column.controls) >= 2

        # 3. Test "Custom Only"
        custom_pill = next(p for p in category_row.controls if p.content.value == "Custom Only")
        custom_pill.on_click(None)
        assert len(list_column.controls) == 1


@pytest.mark.asyncio
async def test_tracker_exercise_picker_card_updates_state():
    from views.tracker_view import TrackerView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        tracker = TrackerView(page, state)

        assert tracker.exercise_name_label.value == "Select Exercise"

        # Select a different exercise via state (which the picker calls)
        await state.select_exercise("Barbell Squat")
        tracker.update_ui()
        assert tracker.exercise_name_label.value == "Barbell Squat"
        assert state.current_exercise.name == "Barbell Squat"
        assert tracker.exercise_category_label.value.startswith("Legs")


def test_exercises_view_search_no_duplicates():
    from views.exercises_view import ExercisesView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)

        # Inject duplicate custom exercises directly into raw state
        custom_ex1 = Exercise("Concentration Curl", "Arms", 10, 14.0, is_custom=True)
        custom_ex2 = Exercise("concentration curl", "Arms", 10, 14.0, is_custom=True)
        custom_ex3 = Exercise("  Concentration Curl  ", "Arms", 10, 14.0, is_custom=True)
        state.exercises.extend([custom_ex1, custom_ex2, custom_ex3])

        view = ExercisesView(page, state)
        view.search_field.value = "concentration"
        view._on_search_change(type("Event", (), {"control": view.search_field})())

        # Despite 3 duplicate instances in state, search results must display exactly 1 card
        assert len(view.exercise_list_column.controls) == 1
        assert "Showing 1 of" in view.count_badge.value


def test_light_theme_coral_palette():
    from theme import (
        COLOR_CONTAINER_HIGHEST_LIGHT,
        COLOR_CONTAINER_LIGHT,
        COLOR_OUTLINE_VARIANT_LIGHT,
        COLOR_PRIMARY_CONTAINER_LIGHT,
        COLOR_PRIMARY_LIGHT,
        COLOR_SURFACE_LIGHT,
        get_light_theme,
    )
    theme = get_light_theme()
    cs = theme.color_scheme
    assert COLOR_CONTAINER_LIGHT == "#FFFCF8"
    assert cs.surface_container == COLOR_CONTAINER_LIGHT
    assert COLOR_CONTAINER_HIGHEST_LIGHT == "#EDE5DD"
    assert cs.surface_container_highest == COLOR_CONTAINER_HIGHEST_LIGHT
    assert COLOR_PRIMARY_LIGHT == "#AA3934"
    assert COLOR_PRIMARY_CONTAINER_LIGHT == "#FCE4DC"
    assert COLOR_SURFACE_LIGHT == "#F8F5F1"
    assert COLOR_OUTLINE_VARIANT_LIGHT == "#CEC8C2"


def test_tracker_calisthenics_and_weighted_subtitles():
    from views.tracker_view import TrackerView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        tracker = TrackerView(page, state)

        # The selector prompts for a choice before displaying exercise details.
        tracker.update_ui()
        assert tracker.exercise_name_label.value == "Select Exercise"
        assert tracker.exercise_category_label.value == "Tap to choose a movement"
        asyncio.run(state.select_exercise("Pull-ups"))
        tracker.update_ui()
        assert tracker.exercise_category_label.value == "Calisthenics • 8 reps"
        assert "@ 0" not in tracker.exercise_category_label.value

        # 2. Weighted exercise (Barbell Squat: default 8 reps, 80 kg)
        asyncio.run(state.select_exercise("Barbell Squat"))
        tracker.update_ui()
        assert tracker.exercise_name_label.value == "Barbell Squat"
        assert tracker.exercise_category_label.value == "Legs • 8 reps @ 80kg"


def test_minimal_search_field_and_bottom_sheet_styling():
    from components.exercise_picker_dialog import show_exercise_picker

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        show_exercise_picker(page, state)

        assert page.dialog is not None
        bs_content = page.dialog.content
        column_controls = bs_content.content.controls

        # The search field expands horizontally inside its row without growing vertically.
        search_row = column_controls[1]
        assert isinstance(search_row, ft.Row)
        search_field = search_row.controls[0]
        assert isinstance(search_field.border, ft.OutlineInputBorder)
        assert search_field.border.side.color == ft.Colors.TRANSPARENT
        assert search_field.prefix_icon is None
        assert search_field.filled is True
        assert search_field.fill_color == ft.Colors.SURFACE_CONTAINER_HIGHEST
        assert search_field.expand is True
        assert bs_content.content.horizontal_alignment == ft.CrossAxisAlignment.STRETCH
        assert bs_content.content.spacing == 6
        assert column_controls[4].expand is False

        # Count badge is hidden when not filtering
        count_badge = column_controls[3]
        assert count_badge.visible is False

        # Count badge becomes visible when searching
        search_field.value = "push-ups"
        search_field.on_change(type("Event", (), {"control": search_field})())
        assert count_badge.visible is True
        assert "Showing 1 of" in count_badge.value



@pytest.mark.asyncio
async def test_appbar_no_dumbbell_icon():
    from main import main

    page = MockPage()
    page.services = []
    page.controls = []
    page.add = lambda ctrl: page.controls.append(ctrl)
    await main(page)

    # Dumbbell icon removed from AppBar leading
    assert page.appbar is not None
    assert getattr(page.appbar, "leading", None) is None
    assert page.appbar.automatically_imply_leading is False
    assert page.appbar.center_title is False


def test_tracker_no_dumbbell_no_search_badge_minimal_ui():
    from views.tracker_view import TrackerView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        tracker = TrackerView(page, state)

        # Tactical ink ripple effect enabled
        assert tracker.exercise_selector_card.ink is True

        # Built-in exercise: built-in badge is hidden
        tracker.update_ui()
        assert tracker.exercise_badge.visible is False

        # Verify no dumbbell icon and no search badge inside the selector card
        card_content = tracker.exercise_selector_card.content
        assert isinstance(card_content, ft.Row)

        def check_no_dumbbell_or_search(ctrl):
            if isinstance(ctrl, ft.Icon):
                assert ctrl.icon != ft.Icons.FITNESS_CENTER
            if isinstance(ctrl, ft.Text):
                assert ctrl.value != "Search"
            if hasattr(ctrl, "controls") and ctrl.controls:
                for child in ctrl.controls:
                    check_no_dumbbell_or_search(child)
            if hasattr(ctrl, "content") and ctrl.content:
                check_no_dumbbell_or_search(ctrl.content)

        check_no_dumbbell_or_search(tracker.exercise_selector_card)

        # Custom exercise: custom badge becomes visible
        asyncio.run(state.add_custom_exercise("Ring Dips", "Calisthenics", 12, 0))
        asyncio.run(state.select_exercise("Ring Dips"))
        tracker.update_ui()
        assert tracker.exercise_badge.visible is True
        assert tracker.exercise_badge_text.value == "Custom"


def test_exercises_view_no_repetitive_dumbbell_icons():
    from views.exercises_view import ExercisesView

    page = MockPage()
    with tempfile.TemporaryDirectory() as tmpdir:
        storage = AppStorage(storage_dir=Path(tmpdir))
        state = AppState(storage=storage)
        view = ExercisesView(page, state)

        # Each result is one tappable row; no repeated exercise icon is needed.
        rows = [control for control in view.exercise_list_column.controls if isinstance(control, ft.ListTile)]
        assert rows
        for row in rows:
            assert row.on_click is not None
            assert row.leading is None
            assert row.trailing.icon == ft.Icons.CHEVRON_RIGHT
