"""Shared presentation rules for the exercise library and picker."""

from models import Exercise
from exercise_catalog import catalog_entry, catalog_type


BROWSE_PAGE_SIZE = 80


def exercise_count_label(visible: int, matches: int, total: int) -> str:
    if matches == total:
        return f"{visible} of {total} exercises"
    return f"{visible} of {matches} matches"


def filter_exercises(exercises: list[Exercise], query: str, category: str) -> tuple[list[Exercise], int]:
    """Return matching exercises and the deduplicated library size."""
    seen: set[str] = set()
    unique: list[Exercise] = []
    for exercise in exercises:
        name = exercise.name.strip().casefold()
        if name and name not in seen:
            seen.add(name)
            unique.append(exercise)

    search = query.strip().casefold()
    matches = []
    for exercise in unique:
        entry = catalog_entry(exercise.name) if not exercise.is_custom else None
        source_type = catalog_type(entry) if entry else ""
        searchable = (
            exercise.name,
            exercise.category,
            source_type,
            (entry.get("equipment") or "") if entry else "",
            *(entry.get("primaryMuscles") or [] if entry else []),
        )
        if search and not any(search in part.casefold() for part in searchable):
            continue
        if category == "Custom Only":
            if not exercise.is_custom:
                continue
        elif category != "All" and category.casefold() not in (
            exercise.category.casefold(), source_type.casefold()
        ):
            continue
        matches.append(exercise)
    return matches, len(unique)


def exercise_defaults(exercise: Exercise) -> str:
    """Format the defaults consistently on both browse surfaces."""
    result = f"{exercise.default_reps} reps"
    if exercise.default_weight and exercise.category.casefold() != "calisthenics":
        weight = f"{exercise.default_weight:g}"
        result += f" · {weight} kg"
    return result


def exercise_category_label(exercise: Exercise) -> str:
    """Show special movement types alongside the primary muscle category."""
    entry = catalog_entry(exercise.name) if not exercise.is_custom else None
    source_type = catalog_type(entry) if entry else ""
    if source_type and source_type not in ("Strength", exercise.category):
        return f"{exercise.category} · {source_type}"
    return exercise.category
