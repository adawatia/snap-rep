"""Measured workout and body-weight summaries; no predicted strength or health claims."""

from collections import defaultdict
from datetime import date, datetime, timedelta
import math
from statistics import mean

from models import SetRecord, WeightEntry


def workout_summary(records: list[SetRecord], today: date | None = None) -> dict:
    today = today or date.today()
    week_start = today - timedelta(days=today.weekday())
    weeks = [(week_start - timedelta(weeks=offset), 0) for offset in range(7, -1, -1)]
    counts = {day: 0 for day, _ in weeks}
    exercises: dict[str, dict] = {}
    active_days = set()
    for record in records:
        try:
            day = date.fromisoformat(record.timestamp[:10])
        except ValueError:
            continue
        active_days.add(day)
        bucket = day - timedelta(days=day.weekday())
        if bucket in counts:
            counts[bucket] += 1
        key = record.exercise.strip()
        item = exercises.setdefault(key, {"sets": 0, "reps": 0, "max_weight": 0.0, "reps_at_max": 0, "max_reps": 0, "records": []})
        item["sets"] += 1
        item["reps"] += record.reps
        item["max_reps"] = max(item["max_reps"], record.reps)
        if (record.weight_kg, record.reps) > (item["max_weight"], item["reps_at_max"]):
            item["max_weight"] = record.weight_kg
            item["reps_at_max"] = record.reps
        item["records"].append((day, record.weight_kg, record.reps))
    return {
        "sets": len(records),
        "reps": sum(record.reps for record in records),
        "active_days": len(active_days),
        "weeks": [(day, counts[day]) for day, _ in weeks],
        "exercises": exercises,
    }


def exercise_progress(records: list[tuple[date, float, int]], weighted: bool) -> list[tuple[date, float]]:
    by_day: dict[date, float] = {}
    for day, weight, reps in records:
        value = weight if weighted else float(reps)
        by_day[day] = max(by_day.get(day, 0), value)
    return sorted(by_day.items())


def body_weight_series(entries: list[WeightEntry], days: int | None = None, today: date | None = None) -> list[tuple[date, float, float]]:
    today = today or date.today()
    start = today - timedelta(days=days - 1) if days else None
    by_day: dict[date, list[float]] = defaultdict(list)
    for entry in entries:
        day = datetime.fromisoformat(entry.recorded_at).date()
        by_day[day].append(entry.weight_kg)
    daily = [(day, mean(values)) for day, values in sorted(by_day.items())]
    return [
        (day, value, mean(weight for prior_day, weight in daily if day - timedelta(days=6) <= prior_day <= day))
        for day, value in daily if start is None or day >= start
    ]


def weight_goal_summary(entries: list[WeightEntry], target: float | None) -> dict | None:
    if not entries:
        return None
    ordered = sorted(entries, key=lambda item: datetime.fromisoformat(item.recorded_at))
    start, current = ordered[0].weight_kg, ordered[-1].weight_kg
    try:
        target = float(target) if target is not None else None
    except (TypeError, ValueError):
        target = None
    if target is not None and (not math.isfinite(target) or target <= 0):
        target = None
    change = round(current - start, 2)
    result = {"start": start, "current": current, "change": change, "target": target}
    if target is not None:
        distance = target - start
        result["remaining"] = round(target - current, 2)
        result["progress"] = None if distance == 0 else max(0.0, min(1.0, (current - start) / distance))
    return result
