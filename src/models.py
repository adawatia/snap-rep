"""Data models for SnapRep."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional
import uuid

from config import DEFAULT_EXERCISES_DATA, EXERCISE_CATEGORIES


@dataclass
class Exercise:
    name: str
    category: str
    default_reps: int = 10
    default_weight: float = 0.0
    is_custom: bool = False

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "category": self.category,
            "default_reps": self.default_reps,
            "default_weight": self.default_weight,
            "is_custom": self.is_custom,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Exercise":
        return cls(
            name=data["name"],
            category=data.get("category", "Other"),
            default_reps=int(data.get("default_reps", 10)),
            default_weight=float(data.get("default_weight", 0.0)),
            is_custom=bool(data.get("is_custom", False)),
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
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            exercise=data["exercise"],
            reps=int(data["reps"]),
            weight_kg=float(data.get("weight_kg", 0.0)),
            timestamp=data.get(
                "timestamp", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ),
            notes=data.get("notes"),
            set_number=int(data.get("set_number", 1)),
        )


def get_default_exercises() -> List[Exercise]:
    """Returns a fresh list of default Exercise instances."""
    return [
        Exercise(
            name=item.name,
            category=item.category,
            default_reps=item.default_reps,
            default_weight=item.default_weight,
            is_custom=False,
        )
        for item in DEFAULT_EXERCISES_DATA
    ]


DEFAULT_EXERCISES: List[Exercise] = get_default_exercises()
