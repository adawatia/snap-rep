"""Bundled, offline Free Exercise DB catalog and SnapRep category mapping."""

from functools import lru_cache
import json
from pathlib import Path


SOURCE_COMMIT = "f00c92c7dcf1216a928a52c3706c7ce8e2f71ed5"

# Existing SnapRep names remain canonical so old logs and saved targets still match.
LEGACY_ALIASES = {
    "pushups": "Push-ups",
    "pullups": "Pull-ups",
    "bodyweight squat": "Bodyweight Squats",
    "barbell deadlift": "Deadlift",
    "barbell bench press - medium grip": "Barbell Bench Press",
    "triceps pushdown": "Tricep Pushdown",
}
LEGACY_SOURCE_NAMES = {name.casefold(): source for source, name in LEGACY_ALIASES.items()}

_MUSCLE_CATEGORIES = {
    "chest": "Chest",
    "lats": "Back", "middle back": "Back", "lower back": "Back", "traps": "Back",
    "quadriceps": "Legs", "hamstrings": "Legs", "glutes": "Legs",
    "calves": "Legs", "adductors": "Legs", "abductors": "Legs",
    "shoulders": "Shoulders",
    "biceps": "Arms", "triceps": "Arms", "forearms": "Arms",
    "abdominals": "Core",
    "neck": "Neck",
}

CATALOG_TYPE_LABELS = {
    "strength": "Strength",
    "stretching": "Mobility",
    "plyometrics": "Plyometrics",
    "powerlifting": "Powerlifting",
    "olympic weightlifting": "Olympic Lifting",
    "strongman": "Strongman",
    "cardio": "Cardio",
}


@lru_cache(maxsize=1)
def catalog() -> tuple[dict, ...]:
    path = Path(__file__).parent / "data" / "free_exercises.json"
    with path.open(encoding="utf-8") as source:
        return tuple(json.load(source))


@lru_cache(maxsize=1)
def catalog_by_name() -> dict[str, dict]:
    return {item["name"].strip().casefold(): item for item in catalog()}


def catalog_entry(name: str) -> dict | None:
    clean = name.strip().casefold()
    return catalog_by_name().get(LEGACY_SOURCE_NAMES.get(clean, clean))


def app_category(item: dict) -> str:
    if item.get("category") == "cardio":
        return "Cardio"
    if item.get("category") == "stretching":
        return "Mobility"
    muscles = item.get("primaryMuscles") or []
    return _MUSCLE_CATEGORIES.get(muscles[0].casefold(), "Other") if muscles else "Other"


def catalog_type(item: dict) -> str:
    return CATALOG_TYPE_LABELS.get(item.get("category"), "Other")


def needs_weight_setup(item: dict) -> bool:
    """Only prompt when the dataset identifies load-bearing equipment."""
    return item.get("equipment") in {
        "barbell", "dumbbell", "cable", "machine", "kettlebells",
        "bands", "medicine ball", "e-z curl bar",
    }
