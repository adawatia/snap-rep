"""Dialog component for creating custom exercises with validation."""

from typing import Callable, Optional
import flet as ft

from config import EXERCISE_CATEGORIES
from models import Exercise
from state import AppState


def show_add_exercise_dialog(
    page: ft.Page,
    state: AppState,
    on_success: Optional[Callable[[Exercise], None]] = None,
    initial_name: str = "",
) -> None:
    is_saving = False

    name_field = ft.TextField(
        label="Exercise Name (e.g. Incline DB Press)",
        value=initial_name,
        autofocus=True,
        border_radius=12,
    )
    category_field = ft.Dropdown(
        label="Category",
        label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
        value=EXERCISE_CATEGORIES[0],
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
        value="10",
        border_radius=12,
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    weight_field = ft.TextField(
        label="Default Weight (kg)",
        value="0",
        border_radius=12,
        keyboard_type=ft.KeyboardType.NUMBER,
    )

    async def handle_save(e):
        nonlocal is_saving
        if is_saving:
            return
        is_saving = True

        clean_name = (name_field.value or "").strip()
        name_field.error_text = None

        if not clean_name:
            name_field.error_text = "Exercise name cannot be empty."
            is_saving = False
            page.update()
            return

        if state.storage.has_exercise(clean_name):
            name_field.error_text = f"'{clean_name}' already exists."
            is_saving = False
            page.update()
            return

        try:
            reps = int(reps_field.value or 10)
        except ValueError:
            reps = 10

        try:
            wt = float(weight_field.value or 0.0)
        except ValueError:
            wt = 0.0

        try:
            new_ex = await state.add_custom_exercise(
                name=clean_name,
                category=category_field.value or "Other",
                default_reps=reps,
                default_weight=wt,
            )
            page.pop_dialog()
            page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(f"Added custom exercise: {new_ex.name}"),
                    show_close_icon=True,
                )
            )
            if on_success:
                on_success(new_ex)
            page.update()
        except ValueError as err:
            name_field.error_text = str(err)
            is_saving = False
            page.update()

    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Add Custom Exercise", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=320,
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
                ft.Button("Save Exercise", on_click=handle_save),
            ],
        )
    )
