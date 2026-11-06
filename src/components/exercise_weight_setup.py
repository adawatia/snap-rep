"""One-time starting weight prompt for newly imported loaded exercises."""

import math
import flet as ft

from state import AppState


def show_weight_setup(page: ft.Page, state: AppState) -> None:
    exercise = state.current_exercise
    name = exercise.name
    field = ft.TextField(
        label="Starting weight (kg)",
        hint_text="For example, 20",
        value="",
        keyboard_type=ft.KeyboardType.NUMBER,
        border=ft.OutlineInputBorder(border_radius=12),
        autofocus=True,
    )

    def finish(value: float) -> None:
        if state.current_exercise.name != name:
            page.pop_dialog()
            return
        state.set_selected_default_weight(value)
        page.pop_dialog()
        page.update()

    def save(_):
        try:
            value = float((field.value or "").strip())
            if not math.isfinite(value) or not 0 <= value <= 1000:
                raise ValueError
        except ValueError:
            field.error_text = "Enter a weight from 0 to 1000 kg."
            page.update()
            return
        finish(value)

    page.show_dialog(ft.AlertDialog(
        title=ft.Text("Set a starting weight"),
        content=ft.Container(
            width=min(320, max(120, (getattr(page, "width", None) or 360) - 80)),
            content=ft.Column(
                tight=True,
                spacing=14,
                controls=[
                    ft.Text(f"{name} uses external weight. Choose a starting value; you can change it while tracking."),
                    field,
                ],
            ),
        ),
        actions=[
            ft.TextButton("Use 0 kg", on_click=lambda _: finish(0.0)),
            ft.FilledButton("Save weight", on_click=save),
        ],
        scrollable=True,
        inset_padding=ft.Padding(16, 16, 16, 16),
    ))
