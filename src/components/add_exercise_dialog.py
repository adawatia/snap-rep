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
        border=ft.OutlineInputBorder(border_radius=12),
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
        expand=True,
        options=[ft.DropdownOption(cat, cat) for cat in EXERCISE_CATEGORIES],
    )
    reps_field = ft.TextField(
        label="Reps",
        value="10",
        border=ft.OutlineInputBorder(border_radius=12),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    weight_field = ft.TextField(
        label="Weight (kg)",
        value="0",
        border=ft.OutlineInputBorder(border_radius=12),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    status_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)
    save_button = ft.FilledButton("Save exercise", style=ft.ButtonStyle(padding=ft.Padding(20, 12, 20, 12)))

    def show_error(message: str, field: ft.TextField | None = None) -> None:
        status_text.value = message
        status_text.visible = True
        if field is not None:
            field.error_text = message
        page.update()

    async def handle_save(e):
        nonlocal is_saving
        if is_saving:
            return
        clean_name = (name_field.value or "").strip()
        name_field.error_text = None
        reps_field.error_text = None
        weight_field.error_text = None
        status_text.visible = False

        if not clean_name:
            show_error("Enter an exercise name to save it.", name_field)
            return

        if state.storage.has_exercise(clean_name):
            show_error(f"'{clean_name}' already exists. Choose another name.", name_field)
            return

        try:
            reps = int((reps_field.value or "").strip())
            if not 1 <= reps <= 999:
                raise ValueError
        except ValueError:
            show_error("Enter a rep target from 1 to 999.", reps_field)
            return

        try:
            wt = float((weight_field.value or "").strip())
            if not 0 <= wt <= 1000:
                raise ValueError
        except ValueError:
            show_error("Enter a weight from 0 to 1000 kg.", weight_field)
            return

        is_saving = True
        save_button.disabled = True
        save_button.content = "Saving…"
        page.update()
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
            show_error(str(err), name_field)
        except Exception:
            show_error("Could not save the exercise. Try again.")
        finally:
            is_saving = False
            save_button.disabled = False
            save_button.content = "Save exercise"
            page.update()

    save_button.on_click = handle_save
    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text("Add Custom Exercise", weight=ft.FontWeight.BOLD),
            content=ft.Container(
                width=min(340, max(120, (getattr(page, "width", None) or 390) - 80)),
                content=ft.Column(
                    spacing=12,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                    controls=[
                        name_field,
                        ft.Row(controls=[category_field], expand=False),
                        ft.Row(
                            spacing=8,
                            controls=[
                                ft.Container(reps_field, expand=1),
                                ft.Container(weight_field, expand=1),
                            ],
                        ),
                        status_text,
                    ],
                ),
            ),
            actions=[
                ft.TextButton("Cancel", on_click=lambda _: page.pop_dialog()),
                save_button,
            ],
            scrollable=True,
            inset_padding=ft.Padding(16, 16, 16, 16),
        )
    )
