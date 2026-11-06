"""A short, replayable first-run guide to the workout flow."""

import flet as ft

from state import AppState
from storage import AppStorage


STEPS = (
    (ft.Icons.FITNESS_CENTER, "Choose an exercise", "Tap Select Exercise on the Tracker. Pick a movement from the library or add your own."),
    (ft.Icons.TUNE, "Set your target", "Adjust reps and weight, then log a set. The rest timer starts automatically when it is enabled."),
    (ft.Icons.HISTORY, "Review your progress", "History keeps your logged sets. Stats shows your trends, and Settings lets you back up your data."),
)


def is_first_launch(storage: AppStorage) -> bool:
    """Existing installs should not see the guide after an app update."""
    return not any(
        path.exists()
        for path in (storage.settings_file, storage.history_file, storage.exercises_file, storage.weight_file)
    )


def show_quick_tour(page: ft.Page, state: AppState) -> None:
    step = 0
    icon = ft.Icon(STEPS[0][0], size=32, color=ft.Colors.PRIMARY)
    title = ft.Text(STEPS[0][1], size=20, weight=ft.FontWeight.BOLD)
    description = ft.Text(STEPS[0][2], size=14, color=ft.Colors.ON_SURFACE_VARIANT)
    progress = ft.Text("1 of 3", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
    back_button = ft.TextButton("Back", visible=False)
    next_button = ft.FilledButton("Next")

    def remember_dismissal(_=None) -> None:
        if not state.settings.get("quick_tour_seen", False):
            state.update_setting("quick_tour_seen", True)

    def close(_=None) -> None:
        remember_dismissal()
        page.pop_dialog()
        page.update()

    def render() -> None:
        icon.icon, title.value, description.value = STEPS[step]
        progress.value = f"{step + 1} of {len(STEPS)}"
        back_button.visible = step > 0
        next_button.content = "Got it" if step == len(STEPS) - 1 else "Next"
        page.update()

    def back(_):
        nonlocal step
        step = max(0, step - 1)
        render()

    def next_step(_):
        nonlocal step
        if step == len(STEPS) - 1:
            close()
            return
        step += 1
        render()

    back_button.on_click = back
    next_button.on_click = next_step
    page.show_dialog(
        ft.AlertDialog(
            title="Quick start",
            icon=icon,
            content=ft.Container(
                width=320,
                content=ft.Column(
                    tight=True,
                    spacing=12,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[title, description, progress],
                ),
            ),
            scrollable=True,
            on_dismiss=remember_dismissal,
            actions=[
                ft.TextButton("Skip", on_click=close),
                back_button,
                next_button,
            ],
            actions_alignment=ft.MainAxisAlignment.END,
        )
    )
