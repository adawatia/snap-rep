"""Data models for SnapRep."""

from dataclasses import dataclass, field
from datetime import datetime
import math
from typing import List, Optional
import uuid

from config import DEFAULT_EXERCISES_DATA, EXERCISE_CATEGORIES
from exercise_catalog import LEGACY_ALIASES, app_category, catalog, needs_weight_setup


@dataclass
class Exercise:
    name: str
    category: str
    default_reps: int = 10
    default_weight: float = 0.0
    is_custom: bool = False
    weight_setup_pending: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "default_reps": self.default_reps,
            "default_weight": self.default_weight,
            "is_custom": self.is_custom,
            "weight_setup_pending": self.weight_setup_pending,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Exercise":
        name = str(data["name"]).strip()
        reps = int(data.get("default_reps", 10))
        weight = float(data.get("default_weight", 0.0))
        if not name or reps < 1 or not math.isfinite(weight) or weight < 0:
            raise ValueError("Invalid exercise defaults")
        return cls(
            name=name,
            category=data.get("category", "Other"),
            default_reps=reps,
            default_weight=weight,
            is_custom=bool(data.get("is_custom", False)),
            weight_setup_pending=bool(data.get("weight_setup_pending", False)),
        )


@dataclass
class SetRecord:
    exercise: str
    reps: int
    weight_kg: float = 0.0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: str = field(
        default_factory=lambda: datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    notes: Optional[str] = None
    set_number: int = 1

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "exercise": self.exercise,
            "reps": self.reps,
            "weight_kg": self.weight_kg,
            "timestamp": self.timestamp,
            "notes": self.notes,
            "set_number": self.set_number,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SetRecord":
        name = str(data["exercise"]).strip()
        reps = int(data["reps"])
        weight = float(data.get("weight_kg", 0.0))
        if not name or reps < 1 or not math.isfinite(weight) or weight < 0:
            raise ValueError("Invalid workout set")
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            exercise=name,
            reps=reps,
            weight_kg=weight,
            timestamp=data.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            notes=data.get("notes"),
            set_number=int(data.get("set_number", 1)),
        )


def get_default_exercises() -> List[Exercise]:
    """Returns a fresh list of default Exercise instances."""
    defaults = [
        Exercise(
            name=item.name,
            category=item.category,
            default_reps=item.default_reps,
            default_weight=item.default_weight,
            is_custom=False,
        )
        for item in DEFAULT_EXERCISES_DATA
    ]
    names = {exercise.name.casefold() for exercise in defaults}
    for item in sorted(catalog(), key=lambda row: row["name"].casefold()):
        name = item["name"].strip()
        if not name or name.casefold() in names or name.casefold() in LEGACY_ALIASES:
            continue
        names.add(name.casefold())
        defaults.append(Exercise(
            name=name,
            category=app_category(item),
            default_reps=10,
            default_weight=0.0,
            weight_setup_pending=needs_weight_setup(item),
        ))
    return defaults


DEFAULT_EXERCISES: List[Exercise] = get_default_exercises()


@dataclass
class WeightEntry:
    weight_kg: float
    recorded_at: str = field(default_factory=lambda: datetime.now().astimezone().isoformat(timespec="minutes"))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def __post_init__(self) -> None:
        self.weight_kg = float(self.weight_kg)
        if not math.isfinite(self.weight_kg) or self.weight_kg <= 0:
            raise ValueError("Enter a weight greater than zero.")
        parsed = datetime.fromisoformat(self.recorded_at)
        if parsed.tzinfo is None:
            parsed = parsed.astimezone()
        if parsed > datetime.now().astimezone():
            raise ValueError("Date and time cannot be in the future.")
        self.recorded_at = parsed.isoformat(timespec="minutes")

    def to_dict(self) -> dict:
        return {"id": self.id, "weight_kg": self.weight_kg, "recorded_at": self.recorded_at}

    @classmethod
    def from_dict(cls, data: dict) -> "WeightEntry":
        return cls(
            id=str(data.get("id") or uuid.uuid4()),
            weight_kg=data["weight_kg"],
            recorded_at=data["recorded_at"],
        )
