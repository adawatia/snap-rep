"""Weight persistence, observed workout metrics, and backup compatibility."""

from datetime import date, datetime, timedelta
import math

import pytest

from insights import body_weight_series, exercise_progress, weight_goal_summary, workout_summary
from models import SetRecord, WeightEntry
from state import AppState
from storage import AppStorage


def stamp(days_ago=0, hour=8):
    return (datetime.now().astimezone() - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0, microsecond=0
    ).isoformat(timespec="minutes")


def test_measured_workout_bests_and_sparse_weeks():
    today = date.today()
    records = [
        SetRecord("Deadlift", 5, 100, timestamp=f"{today} 08:00:00"),
        SetRecord("Deadlift", 3, 110, timestamp=f"{today} 09:00:00"),
        SetRecord("Deadlift", 4, 110, timestamp=f"{today} 10:00:00"),
        SetRecord("Push-ups", 20, 0, timestamp=f"{today} 11:00:00"),
    ]
    summary = workout_summary(records, today)
    assert summary["sets"] == 4
    assert summary["reps"] == 32
    assert summary["active_days"] == 1
    assert len(summary["weeks"]) == 8
    assert summary["weeks"][-1][1] == 4
    assert sum(count for _, count in summary["weeks"]) == 4
    assert summary["exercises"]["Deadlift"]["max_weight"] == 110
    assert summary["exercises"]["Deadlift"]["reps_at_max"] == 4
    assert summary["exercises"]["Push-ups"]["max_reps"] == 20
    assert exercise_progress(summary["exercises"]["Push-ups"]["records"], False) == [(today, 20.0)]


def test_weight_history_multiple_readings_daily_mean_and_goal(tmp_path):
    state = AppState(storage=AppStorage(storage_dir=tmp_path))
    first = state.save_weight_entry(90, stamp(2))
    state.save_weight_entry(89, stamp(1, 8))
    state.save_weight_entry(87, stamp(1, 18))
    latest = state.save_weight_entry(86, stamp(0))
    assert len(state.weight_history) == 4
    assert len(body_weight_series(state.weight_history)) == 3
    assert body_weight_series(state.weight_history)[1][1] == 88
    state.set_target_weight(80)
    goal = weight_goal_summary(state.weight_history, 80)
    assert goal["start"] == 90 and goal["current"] == 86
    assert goal["change"] == -4 and goal["remaining"] == -6
    assert goal["progress"] == pytest.approx(0.4)
    state.save_weight_entry(85, latest.recorded_at, latest.id)
    assert len(state.weight_history) == 4
    state.delete_weight_entry(first.id)
    assert len(state.weight_history) == 3
    assert AppState(storage=AppStorage(storage_dir=tmp_path)).weight_history[0].weight_kg == 89


def test_weight_validation_and_gain_goal(tmp_path):
    state = AppState(storage=AppStorage(storage_dir=tmp_path))
    for bad in (0, -1, math.nan, math.inf):
        with pytest.raises(ValueError):
            state.save_weight_entry(bad, stamp(1))
        with pytest.raises(ValueError):
            state.set_target_weight(bad)
    with pytest.raises(ValueError):
        state.save_weight_entry(70, stamp(-1))
    state.save_weight_entry(70, stamp(2))
    state.save_weight_entry(73, stamp(1))
    goal = weight_goal_summary(state.weight_history, 76)
    assert goal["change"] == 3
    assert goal["progress"] == pytest.approx(0.5)
    assert goal["remaining"] == 3


def test_weight_backup_v2_merge_replace_and_legacy_preserve(tmp_path):
    storage = AppStorage(storage_dir=tmp_path)
    old = WeightEntry(91, stamp(3))
    storage.upsert_weight_entry(old)
    storage.save_settings({**storage.load_settings(), "target_weight_kg": 80})
    backup = storage.create_backup()[2]
    assert backup["version"] == 2
    assert backup["weight_history"] == [old.to_dict()]
    newer = WeightEntry(90, stamp(2))
    merged = {**backup, "weight_history": [old.to_dict(), newer.to_dict()]}
    storage.restore_backup(merged, mode="merge")
    assert len(storage.load_weight_history()) == 2
    storage.restore_backup(merged, mode="merge")
    assert len(storage.load_weight_history()) == 2
    storage.restore_backup({"version": 1, "history": [], "settings": {}}, mode="replace")
    assert len(storage.load_weight_history()) == 2
    assert storage.load_settings()["target_weight_kg"] == 80
    storage.restore_backup({"version": 2, "weight_history": [newer.to_dict()]}, mode="replace")
    assert [entry.id for entry in storage.load_weight_history()] == [newer.id]


def test_weight_only_backup_and_csv(tmp_path):
    storage = AppStorage(storage_dir=tmp_path)
    entry = WeightEntry(78.4, stamp(1))
    storage.restore_backup({"version": 2, "weight_history": [entry.to_dict()]}, mode="merge")
    path, content = storage.export_weight_to_csv()
    assert not path.exists()
    assert "Recorded_at,Weight_kg" in content
    assert entry.id in content


def test_trend_uses_readings_before_visible_window():
    today = date.today()
    entries = [
        WeightEntry(80, datetime.combine(today - timedelta(days=30), datetime.min.time()).astimezone().isoformat()),
        WeightEntry(82, datetime.combine(today - timedelta(days=29), datetime.min.time()).astimezone().isoformat()),
    ]
    assert body_weight_series(entries, 30, today) == [(today - timedelta(days=29), 82, 81)]


def test_malformed_weight_backup_cannot_clear_existing_readings(tmp_path):
    storage = AppStorage(storage_dir=tmp_path)
    entry = WeightEntry(78.4, stamp(1))
    storage.upsert_weight_entry(entry)
    with pytest.raises(ValueError, match="weight history must be a list"):
        storage.restore_backup({"weight_history": "bad"}, mode="replace")
    assert [item.id for item in storage.load_weight_history()] == [entry.id]
