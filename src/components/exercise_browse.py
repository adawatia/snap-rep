"""Shared presentation rules for the exercise library and picker."""

from models import Exercise


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
    matches = [
        exercise
        for exercise in unique
        if (not search or search in exercise.name.casefold() or search in exercise.category.casefold())
        and (category == "All" or (exercise.is_custom if category == "Custom Only" else exercise.category.casefold() == category.casefold()))
    ]
    return matches, len(unique)


def exercise_defaults(exercise: Exercise) -> str:
    """Format the defaults consistently on both browse surfaces."""
    result = f"{exercise.default_reps} reps"
    if exercise.default_weight and exercise.category.casefold() != "calisthenics":
        weight = f"{exercise.default_weight:g}"
        result += f" · {weight} kg"
    return result
