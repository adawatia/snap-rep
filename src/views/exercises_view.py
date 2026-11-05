"""Exercises view: Dedicated library tab to browse, search, filter,
add custom exercises, and edit exercise defaults.
"""

import flet as ft

from components.add_exercise_dialog import show_add_exercise_dialog
from components.confirm_dialog import show_confirm_dialog
from components.edit_exercise_dialog import show_edit_exercise_dialog
from components.exercise_browse import exercise_defaults, filter_exercises
from config import EXERCISE_CATEGORIES
from models import Exercise
from state import AppState

class ExercisesView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state

        self._filter_query = ""
        self._selected_category = "All"

        # Search field (Minimal, borderless)
        self.search_field = ft.TextField(
            hint_text="Search exercises",
            prefix_icon=ft.Icons.SEARCH,
            border=ft.OutlineInputBorder(
                border_radius=12,
                side=ft.BorderSide(color=ft.Colors.TRANSPARENT),
            ),
            dense=True,
            content_padding=ft.Padding(14, 10, 14, 10),
            filled=True,
            fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            on_change=self._on_search_change,
            expand=True,
        )

        # Category filter row
        self.category_row = ft.Row(
            scroll=ft.ScrollMode.AUTO,
            spacing=6,
            controls=[],
        )

        # Exercise count stays visible while only the results list scrolls.
        self.count_badge = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.exercise_list_column = ft.ListView(
            spacing=0,
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
            padding=ft.Padding(0, 8, 0, 12),
        )

        self.root = self._build_layout()
        self.update_ui()

    def _on_search_change(self, e) -> None:
        self._filter_query = (e.control.value or "").strip()
        self._render_exercises()
        self.page.update()

    def _select_category(self, cat: str) -> None:
        self._selected_category = cat
        self._render_category_pills()
        self._render_exercises()
        self.page.update()

    def _open_add_dialog(self, e=None, initial_name: str = "") -> None:
        show_add_exercise_dialog(
            self.page,
            self.state,
            initial_name=initial_name,
            on_success=lambda _: self.update_ui(),
        )

    def _open_edit_dialog(self, exercise: Exercise) -> None:
        show_edit_exercise_dialog(
            self.page,
            self.state,
            exercise,
            on_success=lambda _: self.update_ui(),
        )

    def _open_details(self, exercise: Exercise) -> None:
        def edit(_):
            self.page.pop_dialog()
            self._open_edit_dialog(exercise)

        def delete(_):
            self.page.pop_dialog()
            self._confirm_delete_exercise(exercise.name)

        actions = [
            ft.FilledButton("Edit defaults", icon=ft.Icons.EDIT_OUTLINED, on_click=edit),
        ]
        if exercise.is_custom:
            actions.append(
                ft.TextButton(
                    "Delete exercise",
                    icon=ft.Icons.DELETE_OUTLINE,
                    style=ft.ButtonStyle(color=ft.Colors.ERROR),
                    on_click=delete,
                )
            )

        details = ft.Container(
            padding=ft.Padding(20, 8, 20, 24),
            content=ft.Column(
                tight=True,
                spacing=16,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Exercise details", size=18, weight=ft.FontWeight.BOLD),
                            ft.IconButton(icon=ft.Icons.CLOSE, tooltip="Close details", on_click=lambda _: self.page.pop_dialog()),
                        ],
                    ),
                    ft.Text(exercise.name, size=22, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{exercise.category} · {'Custom exercise' if exercise.is_custom else 'Built-in exercise'}",
                        size=13,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    ft.Container(
                        padding=16,
                        bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                        border_radius=12,
                        content=ft.Column(
                            spacing=4,
                            controls=[
                                ft.Text("DEFAULT TARGET", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
                                ft.Text(exercise_defaults(exercise), size=18, weight=ft.FontWeight.W_600),
                            ],
                        ),
                    ),
                    *actions,
                ],
            ),
        )
        self.page.show_dialog(
            ft.BottomSheet(
                content=details,
                show_drag_handle=True,
                scrollable=True,
                maintain_bottom_view_insets_padding=True,
                shape=ft.RoundedRectangleBorder(
                    radius=ft.BorderRadius(top_left=24, top_right=24, bottom_left=0, bottom_right=0)
                ),
            )
        )

    def _confirm_delete_exercise(self, name: str) -> None:
        async def do_delete():
            await self.state.delete_custom_exercise(name)
            self.update_ui()
            self.page.update()

        show_confirm_dialog(
            self.page,
            title="Delete Custom Exercise?",
            message=f"Are you sure you want to delete '{name}'?",
            confirm_text="Delete",
            is_destructive=True,
            on_confirm=do_delete,
        )

    def _render_category_pills(self) -> None:
        categories = ["All", "Custom Only"] + list(EXERCISE_CATEGORIES)
        pills = []
        for cat in categories:
            is_active = (cat == self._selected_category)
            pills.append(
                ft.OutlinedButton(
                    content=ft.Text(
                        cat,
                        size=12,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                    ),
                    height=44,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PRIMARY if is_active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        color=ft.Colors.ON_PRIMARY if is_active else ft.Colors.ON_SURFACE_VARIANT,
                        shape=ft.RoundedRectangleBorder(radius=16),
                        padding=ft.Padding(12, 8, 12, 8),
                    ),
                    on_click=lambda _, c=cat: self._select_category(c),
                )
            )
        self.category_row.controls = pills

    def _render_exercises(self) -> None:
        filtered, total = filter_exercises(
            self.state.exercises, self._filter_query, self._selected_category
        )
        self.count_badge.value = f"Showing {len(filtered)} of {total} exercises"
        self.exercise_list_column.key = f"library:{self._filter_query.casefold()}:{self._selected_category.casefold()}"

        if not filtered:
            has_search = bool(self._filter_query)
            controls = [
                ft.Icon(ft.Icons.SEARCH_OFF, size=32, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(
                    "No matching exercises" if has_search else "No exercises in this category",
                    size=15,
                    weight=ft.FontWeight.W_600,
                ),
                ft.Text(
                    "Try another search or category.",
                    size=12,
                    color=ft.Colors.ON_SURFACE_VARIANT,
                ),
            ]
            if self._selected_category != "All":
                controls.append(
                    ft.TextButton(
                        "Show all categories",
                        on_click=lambda _: self._select_category("All"),
                    )
                )
            if has_search and self._selected_category == "All":
                controls.append(
                    ft.OutlinedButton(
                        "Add as custom exercise",
                        icon=ft.Icons.ADD,
                        on_click=lambda _: self._open_add_dialog(initial_name=self._filter_query),
                    )
                )
            self.exercise_list_column.controls = [
                ft.Container(
                    padding=ft.Padding(24, 36, 24, 36),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        controls=controls,
                    ),
                )
            ]
            return

        rows: list[ft.Control] = []
        for exercise in filtered:
            meta = f"{exercise.category} · {exercise_defaults(exercise)}"
            if exercise.is_custom:
                meta += " · Custom"
            rows.append(
                ft.ListTile(
                    title=ft.Text(
                        exercise.name,
                        size=14,
                        weight=ft.FontWeight.W_600,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    subtitle=ft.Text(
                        meta,
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        max_lines=1,
                        overflow=ft.TextOverflow.ELLIPSIS,
                    ),
                    trailing=ft.Icon(
                        ft.Icons.CHEVRON_RIGHT,
                        size=20,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    min_height=64,
                    content_padding=ft.Padding(12, 6, 12, 6),
                    on_click=lambda _, target=exercise: self._open_details(target),
                )
            )
            rows.append(ft.Divider(height=1, color=ft.Colors.OUTLINE_VARIANT))
        self.exercise_list_column.controls = rows[:-1]

    def update_ui(self) -> None:
        self._render_category_pills()
        self._render_exercises()

    def _build_layout(self) -> ft.Container:
        return ft.Container(
            padding=ft.Padding(16, 16, 16, 8),
            expand=True,
            content=ft.Column(
                expand=True,
                spacing=10,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Row(controls=[self.search_field]),
                    self.category_row,
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Container(self.count_badge, expand=True),
                            ft.IconButton(
                                icon=ft.Icons.ADD,
                                icon_color=ft.Colors.ON_PRIMARY,
                                bgcolor=ft.Colors.PRIMARY,
                                tooltip="Add exercise",
                                on_click=self._open_add_dialog,
                            ),
                        ],
                    ),
                    ft.Container(
                        expand=True,
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        border_radius=14,
                        clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
                        content=self.exercise_list_column,
                    ),
                ],
            ),
        )
