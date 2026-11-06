"""Application configuration and constants for SnapRep."""

from dataclasses import dataclass
from typing import List


@dataclass
class ExerciseTemplate:
    name: str
    category: str
    default_reps: int = 10
    default_weight: float = 0.0


DEFAULT_EXERCISES_DATA: List[ExerciseTemplate] = [
    ExerciseTemplate("Push-ups", "Calisthenics", default_reps=15, default_weight=0.0),
    ExerciseTemplate("Pull-ups", "Calisthenics", default_reps=8, default_weight=0.0),
    ExerciseTemplate("Dips", "Calisthenics", default_reps=12, default_weight=0.0),
    ExerciseTemplate("Bodyweight Squats", "Legs", default_reps=20, default_weight=0.0),
    ExerciseTemplate("Barbell Bench Press", "Chest", default_reps=10, default_weight=60.0),
    ExerciseTemplate("Barbell Squat", "Legs", default_reps=8, default_weight=80.0),
    ExerciseTemplate("Deadlift", "Back", default_reps=5, default_weight=100.0),
    ExerciseTemplate("Overhead Press", "Shoulders", default_reps=8, default_weight=40.0),
    ExerciseTemplate("Dumbbell Bicep Curl", "Arms", default_reps=12, default_weight=14.0),
    ExerciseTemplate("Tricep Pushdown", "Arms", default_reps=15, default_weight=25.0),
    ExerciseTemplate("Lateral Raise", "Shoulders", default_reps=15, default_weight=8.0),
]

EXERCISE_CATEGORIES = [
    "Chest",
    "Back",
    "Legs",
    "Shoulders",
    "Arms",
    "Core",
    "Neck",
    "Calisthenics",
    "Cardio",
    "Mobility",
    "Strength",
    "Plyometrics",
    "Powerlifting",
    "Olympic Lifting",
    "Strongman",
    "Other",
]

DEFAULT_SETTINGS = {
    "haptic_feedback": True,
    "quick_tour_seen": False,
    "target_weight_kg": None,
    "theme_palette": "coral",
    "theme_mode": "light",
    "unit": "kg",
    "default_rest_timer": 60,
}

REST_TIMER_OPTIONS = [
    (30, "30 seconds"),
    (60, "60 seconds (Standard)"),
    (90, "90 seconds (Hypertrophy)"),
    (120, "2 minutes (Strength)"),
    (180, "3 minutes (Power)"),
    (0, "Disabled (Manual only)"),
]

APP_TITLE = "SnapRep"
APP_SUBTITLE = "Every rep recorded."
APP_VERSION = "0.1.0"
