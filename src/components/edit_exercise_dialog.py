"""Dialog component for editing exercise parameters (reps, weight, category, and name for custom exercises)."""

from typing import Callable, Optional
import flet as ft

from config import EXERCISE_CATEGORIES
from models import Exercise
from state import AppState


def show_edit_exercise_dialog(
    page: ft.Page,
    state: AppState,
    exercise: Exercise,
    on_success: Optional[Callable[[Exercise], None]] = None,
) -> None:
    is_custom = exercise.is_custom

    name_field = ft.TextField(
        label="Exercise Name" if is_custom else "Exercise Name (Built-in)",
        value=exercise.name,
        disabled=not is_custom,
        helper=None if is_custom else "Built-in exercise names cannot be changed.",
        autofocus=is_custom,
        border_radius=12,
    )
    category_value = exercise.category if exercise.category in EXERCISE_CATEGORIES else EXERCISE_CATEGORIES[0]
    category_field = ft.Dropdown(
        label="Category",
        label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
        value=category_value,
        border={
            ft.ControlState.DEFAULT: ft.OutlineInputBorder(
                border_radius=12,
                side=ft.BorderSide(color=ft.Colors.OUTLINE_VARIANT),
            ),
            ft.ControlState.FOCUSED: ft.OutlineInputBorder(
                border_radius=12,
                side=ft.BorderSide(color=ft.Colors.PRIMARY, width=1.5),
            ),
        },
        filled=True,
        fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        content_padding=ft.Padding(12, 8, 12, 8),
        menu_height=260,
        options=[ft.DropdownOption(cat, cat) for cat in EXERCISE_CATEGORIES],
    )
    reps_field = ft.TextField(
        label="Default Reps",
        value=str(exercise.default_reps),
        border_radius=12,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    formatted_wt = str(int(exercise.default_weight) if exercise.default_weight.is_integer() else exercise.default_weight)
    weight_field = ft.TextField(
        label="Default Weight (kg)",
        value=formatted_wt,
        border_radius=12,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    async def handle_save(e):
        clean_name = (name_field.value or "").strip()
        name_field.error_text = None

        if not clean_name:
            name_field.error_text = "Exercise name cannot be empty."
            page.update()
            return

        try:
            reps = int(reps_field.value or exercise.default_reps)
            if reps <= 0 or reps > 999:
                reps = max(1, min(999, reps))
        except ValueError:
            reps = exercise.default_reps

        try:
            wt = float(weight_field.value or exercise.default_weight)
            if wt < 0 or wt > 1000:
                wt = max(0.0, min(1000.0, wt))
        except ValueError:
            wt = exercise.default_weight

        try:
            updated_ex = await state.update_exercise(
                original_name=exercise.name,
                name=clean_name,
                category=category_field.value or exercise.category,
                default_reps=reps,
                default_weight=wt,
            )
            page.pop_dialog()
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"Updated defaults for '{updated_ex.name}'"),
                    show_close_icon=True,
                )
            )
            if on_success:
                on_success(updated_ex)
            page.update()
        except ValueError as err:
            name_field.error_text = str(err)
            page.update()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(f"Edit {exercise.name}", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=340,
                content=ft.Column(
                    spacing=12,
                    tight=True,
                    controls=[
                        name_field,
                        category_field,
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Container(reps_field, expand=1),
                                ft.Container(weight_field, expand=1),
                            ],
                        ),
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                ft.Button("Save Changes", on_click=handle_save),
            ],
        )
    )
