"""Dialog component for editing exercise parameters (reps, weight, category, and name for custom exercises)."""

from typing import Callable, Optional
import math
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
    is_saving = False

    name_field = ft.TextField(
        label="Exercise Name" if is_custom else "Exercise Name (Built-in)",
        value=exercise.name,
        disabled=not is_custom,
        helper=None if is_custom else "Built-in exercise names cannot be changed.",
        autofocus=is_custom,
        border=ft.OutlineInputBorder(border_radius=12),
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
        label="Reps",
        value=str(exercise.default_reps),
        border=ft.OutlineInputBorder(border_radius=12),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    formatted_wt = str(int(exercise.default_weight) if exercise.default_weight.is_integer() else exercise.default_weight)
    weight_field = ft.TextField(
        label="Weight (kg)",
        value=formatted_wt,
        border=ft.OutlineInputBorder(border_radius=12),
        keyboard_type=ft.KeyboardType.NUMBER,
    )
    status_text = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)
    save_button = ft.FilledButton("Save changes", style=ft.ButtonStyle(padding=ft.Padding(20, 12, 20, 12)))

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
            name_field.error_text = "Enter an exercise name to save changes."
            status_text.value = name_field.error_text
            status_text.visible = True
            page.update()
            return

        try:
            reps = int((reps_field.value or "").strip())
            if not 1 <= reps <= 999:
                raise ValueError
        except (ValueError, TypeError):
            reps_field.error_text = "Enter 1–999 reps."
            page.update()
            return

        try:
            wt = float((weight_field.value or "").strip())
            if not math.isfinite(wt) or not 0 <= wt <= 1000:
                raise ValueError
        except (ValueError, TypeError):
            weight_field.error_text = "Enter 0–1000 kg."
            page.update()
            return

        is_saving = True
        save_button.disabled = True
        save_button.content = "Saving…"
        page.update()
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
            status_text.value = str(err)
            status_text.visible = True
        except Exception:
            status_text.value = "Could not save changes. Try again."
            status_text.visible = True
        finally:
            is_saving = False
            save_button.disabled = False
            save_button.content = "Save changes"
            page.update()

    save_button.on_click = handle_save
    page.show_dialog(
        ft.AlertDialog(
            title=ft.Text(f"Edit {exercise.name}", weight=ft.FontWeight.BOLD,
                          max_lines=1, overflow=ft.TextOverflow.ELLIPSIS),
            content=ft.Container(
                width=min(340, max(120, (getattr(page, "width", None) or 390) - 80)),
                content=ft.Column(
                    spacing=12,
                    tight=True,
                    horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
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
