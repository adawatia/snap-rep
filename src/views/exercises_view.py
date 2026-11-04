"""Exercises view: Dedicated library tab to browse, search, filter,
add custom exercises, and edit exercise defaults.
"""

import asyncio
from typing import Optional
import flet as ft

from components.add_exercise_dialog import show_add_exercise_dialog
from components.confirm_dialog import show_confirm_dialog
from components.edit_exercise_dialog import show_edit_exercise_dialog
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
            hint_text="Search exercise name or category...",
            border=ft.NoInputBorder(),
            dense=True,
            content_padding=ft.Padding(14, 10, 14, 10),
            border_radius=12,
            filled=True,
            fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
            on_change=self._on_search_change,
            expand=True,
        )

        # Category filter row
        self.category_row = ft.Row(
            scroll=ft.ScrollMode.HIDDEN,
            spacing=6,
            controls=[],
        )

        # Exercises count badge & list column
        self.count_badge = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)
        self.exercise_list_column = ft.Column(spacing=8)

        self.root = self._build_layout()
        self.update_ui()

    def _on_search_change(self, e) -> None:
        self._filter_query = (e.control.value or "").strip().lower()
        self._render_exercises()
        self.page.update()

    def _select_category(self, cat: str) -> None:
        self._selected_category = cat
        self._render_category_pills()
        self._render_exercises()
        self.page.update()

    def _open_add_dialog(self, e) -> None:
        show_add_exercise_dialog(
            self.page,
            self.state,
            on_success=lambda _: self.update_ui(),
        )

    def _open_edit_dialog(self, exercise: Exercise) -> None:
        show_edit_exercise_dialog(
            self.page,
            self.state,
            exercise,
            on_success=lambda _: self.update_ui(),
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
                ft.Container(
                    content=ft.Text(
                        cat,
                        size=12,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                        color=ft.Colors.ON_PRIMARY if is_active else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    bgcolor=ft.Colors.PRIMARY if is_active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=ft.Padding(12, 6, 12, 6),
                    border_radius=16,
                    on_click=lambda _, c=cat: self._select_category(c),
                )
            )
        self.category_row.controls = pills

    def _render_exercises(self) -> None:
        query = self._filter_query
        cat = self._selected_category

        # Defensive deduplication across all exercises
        seen_names = set()
        deduped_exercises: list[Exercise] = []
        for ex in self.state.exercises:
            clean = ex.name.strip().lower()
            if clean and clean not in seen_names:
                seen_names.add(clean)
                deduped_exercises.append(ex)

        filtered = []
        for ex in deduped_exercises:
            # Query match
            if query and query not in ex.name.lower() and query not in ex.category.lower():
                continue
            # Category match
            if cat == "Custom Only" and not ex.is_custom:
                continue
            if cat not in ("All", "Custom Only") and ex.category.lower() != cat.lower():
                continue
            filtered.append(ex)

        self.count_badge.value = f"Showing {len(filtered)} of {len(deduped_exercises)} exercises"

        cards: list[ft.Control] = []
        if not filtered:
            controls_list = [
                ft.Icon(ft.Icons.SEARCH_OFF, size=36, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text("No exercises match your search.", size=14, color=ft.Colors.ON_SURFACE_VARIANT),
            ]
            if query:
                controls_list.append(
                    ft.Button(
                        content=ft.Row(
                            spacing=4,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                ft.Icon(ft.Icons.ADD, size=16),
                                ft.Text(f"Add '{query.title()}' as Custom", weight=ft.FontWeight.BOLD, size=12),
                            ],
                        ),
                        on_click=lambda _: show_add_exercise_dialog(
                            self.page,
                            self.state,
                            initial_name=query.title(),
                            on_success=lambda _: self.update_ui(),
                        ),
                    )
                )

            cards.append(
                ft.Container(
                    padding=32,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=controls_list,
                    ),
                )
            )
            self.exercise_list_column.controls = cards
            return

        for ex in filtered:
            if ex.default_weight == 0 or ex.category.lower() == "calisthenics":
                target_str = f"{ex.category} • Default {ex.default_reps} reps"
            else:
                wt_str = f"{int(ex.default_weight) if ex.default_weight.is_integer() else ex.default_weight} kg"
                target_str = f"{ex.category} • Default {ex.default_reps} reps @ {wt_str}"
            badge_color = ft.Colors.PRIMARY if ex.is_custom else ft.Colors.OUTLINE
            badge_text = "Custom" if ex.is_custom else "Built-in"

            row_actions = [
                ft.IconButton(
                    icon=ft.Icons.EDIT_OUTLINED,
                    icon_size=18,
                    icon_color=ft.Colors.PRIMARY,
                    tooltip=f"Edit defaults for {ex.name}",
                    on_click=lambda _, target=ex: self._open_edit_dialog(target),
                )
            ]

            if ex.is_custom:
                row_actions.append(
                    ft.IconButton(
                        icon=ft.Icons.DELETE_OUTLINE,
                        icon_size=18,
                        icon_color=ft.Colors.ERROR,
                        tooltip="Delete custom exercise",
                        on_click=lambda _, name=ex.name: self._confirm_delete_exercise(name),
                    )
                )

            item_card = ft.Card(
                content=ft.Container(
                    padding=ft.Padding(12, 10, 12, 10),
                    content=ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            # Left: Icon & Info (expand=True so actions never overflow)
                            ft.Row(
                                spacing=10,
                                expand=True,
                                controls=[
                                    ft.Icon(
                                        ft.Icons.FITNESS_CENTER,
                                        size=20,
                                        color=ft.Colors.PRIMARY if ex.is_custom else ft.Colors.SECONDARY,
                                    ),
                                    ft.Column(
                                        spacing=2,
                                        expand=True,
                                        controls=[
                                            ft.Row(
                                                spacing=6,
                                                controls=[
                                                    ft.Container(
                                                        content=ft.Text(
                                                            ex.name,
                                                            weight=ft.FontWeight.BOLD,
                                                            size=14,
                                                            max_lines=1,
                                                            overflow=ft.TextOverflow.ELLIPSIS,
                                                        ),
                                                        expand=True,
                                                    ),
                                                    ft.Container(
                                                        content=ft.Text(
                                                            badge_text,
                                                            size=10,
                                                            weight=ft.FontWeight.BOLD,
                                                            color=badge_color,
                                                        ),
                                                        padding=ft.Padding(5, 2, 5, 2),
                                                        border=ft.Border.all(1, badge_color),
                                                        border_radius=6,
                                                    ),
                                                ],
                                            ),
                                            ft.Text(
                                                target_str,
                                                size=12,
                                                color=ft.Colors.ON_SURFACE_VARIANT,
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                            # Right: Edit / Delete action buttons
                            ft.Row(
                                spacing=2,
                                controls=row_actions,
                            ),
                        ],
                    ),
                )
            )
            cards.append(item_card)

        self.exercise_list_column.controls = cards

    def update_ui(self) -> None:
        self._render_category_pills()
        self._render_exercises()

    def _build_layout(self) -> ft.Container:
        return ft.Container(
            padding=14,
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=12,
                controls=[
                    # Header: Title + Add Button
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Text("Exercise Library", size=18, weight=ft.FontWeight.BOLD),
                            ft.Button(
                                content=ft.Row(
                                    spacing=4,
                                    controls=[
                                        ft.Icon(ft.Icons.ADD, size=16),
                                        ft.Text("Add Exercise", size=12, weight=ft.FontWeight.BOLD),
                                    ],
                                ),
                                on_click=self._open_add_dialog,
                            ),
                        ],
                    ),

                    # Search Bar
                    ft.Row(controls=[self.search_field]),

                    # Category Filter Pills
                    self.category_row,

                    # Count info
                    self.count_badge,

                    # Exercise List
                    self.exercise_list_column,
                ],
            ),
        )
