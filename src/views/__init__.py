"""Views module for SnapRep."""

from views.tracker_view import TrackerView
from views.history_view import HistoryView
from views.exercises_view import ExercisesView
from views.stats_view import StatsView
from views.settings_view import SettingsView
from views.weight_view import WeightView

__all__ = [
    "TrackerView",
    "HistoryView",
    "ExercisesView",
    "StatsView",
    "SettingsView",
    "WeightView",
]
