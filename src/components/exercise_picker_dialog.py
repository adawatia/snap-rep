"""Exercise picker bottom sheet: Fast, searchable, and category-filtered exercise selection."""

import asyncio
from typing import Callable, List, Optional
import flet as ft

from components.add_exercise_dialog import show_add_exercise_dialog
from config import EXERCISE_CATEGORIES
from models import Exercise
from state import AppState


def show_exercise_picker(
    page: ft.Page,
    state: AppState,
    on_select: Optional[Callable[[Exercise], None]] = None,
) -> None:
    search_query = ""
    selected_category = "All"

    categories = ["All", "Custom Only"] + list(EXERCISE_CATEGORIES)

    # 1. Header controls
    sheet_title = ft.Text("Select Exercise", size=17, weight=ft.FontWeight.BOLD)
    count_badge = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT)

    # 2. Search input
    def on_search_change(e):
        nonlocal search_query
        search_query = (e.control.value or "").strip().lower()
        render_list()
        page.update()

    search_field = ft.TextField(
        hint_text="Search exercise or category...",
        prefix_icon=ft.Icons.SEARCH,
        dense=True,
        content_padding=ft.Padding(12, 8, 12, 8),
        border_radius=12,
        filled=True,
        fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        on_change=on_search_change,
        expand=True,
        autofocus=False,
    )

    # 3. Category pills row
    category_row = ft.Row(
        scroll=ft.ScrollMode.HIDDEN,
        spacing=6,
        controls=[],
    )

    def select_category(cat: str):
        nonlocal selected_category
        selected_category = cat
        render_categories()
        render_list()
        page.update()

    def render_categories():
        pills: List[ft.Control] = []
        for cat in categories:
            is_active = (cat == selected_category)
            pills.append(
                ft.Container(
                    content=ft.Text(
                        cat,
                        size=11,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                        color=ft.Colors.ON_PRIMARY if is_active else ft.Colors.ON_SURFACE_VARIANT,
                    ),
                    bgcolor=ft.Colors.PRIMARY if is_active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=ft.Padding(10, 5, 10, 5),
                    border_radius=14,
                    on_click=lambda _, c=cat: select_category(c),
                )
            )
        category_row.controls = pills

    # 4. Exercise list column
    list_column = ft.Column(spacing=6, scroll=ft.ScrollMode.ADAPTIVE)
    list_container = ft.Container(
        content=list_column,
        height=320,
        expand=True,
    )

    def open_add_custom(initial_name: str = ""):
        page.pop_dialog()
        show_add_exercise_dialog(
            page,
            state,
            initial_name=initial_name,
            on_success=lambda ex: on_select(ex) if on_select else None,
        )

    async def choose_exercise(ex: Exercise):
        await state.select_exercise(ex.name)
        page.pop_dialog()
        if on_select:
            on_select(ex)
        page.update()

    def render_list():
        # Defensive deduplication across all exercises
        seen_names = set()
        deduped_exercises: List[Exercise] = []
        for ex in state.exercises:
            clean = ex.name.strip().lower()
            if clean and clean not in seen_names:
                seen_names.add(clean)
                deduped_exercises.append(ex)

        # Filtering
        filtered: List[Exercise] = []
        for ex in deduped_exercises:
            # Query match on name or category
            if search_query:
                if (
                    search_query not in ex.name.lower()
                    and search_query not in ex.category.lower()
                ):
                    continue

            # Category filter
            if selected_category == "Custom Only" and not ex.is_custom:
                continue
            if selected_category not in ("All", "Custom Only") and ex.category.lower() != selected_category.lower():
                continue

            filtered.append(ex)

        count_badge.value = f"Showing {len(filtered)} of {len(deduped_exercises)} exercises"

        cards: List[ft.Control] = []
        if not filtered:
            cards.append(
                ft.Container(
                    padding=ft.Padding(16, 24, 16, 24),
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.SEARCH_OFF, size=36, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.Text(
                                f"No exercises matching '{search_query}'" if search_query else "No exercises in this category",
                                size=13,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            *(
                                [
                                    ft.Button(
                                        content=ft.Row(
                                            spacing=4,
                                            alignment=ft.MainAxisAlignment.CENTER,
                                            controls=[
                                                ft.Icon(ft.Icons.ADD, size=16),
                                                ft.Text(f"Add '{search_query.title()}' as Custom", weight=ft.FontWeight.BOLD, size=12),
                                            ],
                                        ),
                                        on_click=lambda _: open_add_custom(search_query.title()),
                                    )
                                ]
                                if search_query
                                else []
                            ),
                        ],
                    ),
                )
            )
            list_column.controls = cards
            return

        current_name_clean = state.current_exercise.name.strip().lower()

        for ex in filtered:
            is_current = (ex.name.strip().lower() == current_name_clean)
            wt_str = f"{int(ex.default_weight) if ex.default_weight.is_integer() else ex.default_weight} kg"
            badge_color = ft.Colors.PRIMARY if ex.is_custom else ft.Colors.OUTLINE
            badge_text = "Custom" if ex.is_custom else "Built-in"

            card_border = (
                ft.Border.all(1.5, ft.Colors.PRIMARY)
                if is_current
                else ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
            )
            card_bgcolor = (
                ft.Colors.PRIMARY_CONTAINER
                if is_current
                else ft.Colors.SURFACE_CONTAINER_HIGHEST
            )

            item = ft.Container(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=10,
                            expand=True,
                            controls=[
                                ft.Icon(
                                    ft.Icons.CHECK_CIRCLE if is_current else ft.Icons.FITNESS_CENTER,
                                    size=18,
                                    color=ft.Colors.PRIMARY if is_current else ft.Colors.ON_SURFACE_VARIANT,
                                ),
                                ft.Column(
                                    spacing=2,
                                    expand=True,
                                    controls=[
                                        ft.Text(
                                            ex.name,
                                            weight=ft.FontWeight.BOLD,
                                            size=14,
                                            max_lines=1,
                                            overflow=ft.TextOverflow.ELLIPSIS,
                                        ),
                                        ft.Text(
                                            f"{ex.category} • Default {ex.default_reps} reps @ {wt_str}",
                                            size=11,
                                            color=ft.Colors.ON_SURFACE_VARIANT,
                                        ),
                                    ],
                                ),
                            ],
                        ),
                        ft.Container(
                            content=ft.Text(
                                badge_text,
                                size=9,
                                weight=ft.FontWeight.BOLD,
                                color=badge_color,
                            ),
                            padding=ft.Padding(5, 2, 5, 2),
                            border=ft.Border.all(1, badge_color),
                            border_radius=6,
                        ),
                    ],
                ),
                padding=ft.Padding(12, 9, 12, 9),
                border=card_border,
                border_radius=10,
                bgcolor=card_bgcolor,
                on_click=lambda _, target=ex: asyncio.create_task(choose_exercise(target)),
            )
            cards.append(item)

        list_column.controls = cards

    # Initial renders
    render_categories()
    render_list()

    sheet_content = ft.Container(
        padding=ft.Padding(16, 8, 16, 16),
        content=ft.Column(
            spacing=10,
            tight=True,
            controls=[
                # Top Header Row: Title, count, + Custom icon, close icon
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(ft.Icons.FITNESS_CENTER, size=20, color=ft.Colors.PRIMARY),
                                sheet_title,
                            ],
                        ),
                        ft.Row(
                            spacing=2,
                            controls=[
                                ft.IconButton(
                                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                    icon_color=ft.Colors.PRIMARY,
                                    tooltip="Add Custom Exercise",
                                    icon_size=22,
                                    on_click=lambda _: open_add_custom(),
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.CLOSE,
                                    icon_size=20,
                                    tooltip="Close",
                                    on_click=lambda _: page.pop_dialog(),
                                ),
                            ],
                        ),
                    ],
                ),
                # Search Bar Row
                search_field,
                # Category Filter Pills
                category_row,
                # Info badge
                count_badge,
                # Scrollable exercises list
                list_container,
            ],
        ),
    )

    page.show_dialog(
        ft.BottomSheet(
            content=sheet_content,
            show_drag_handle=True,
            maintain_bottom_view_insets_padding=True,
            shape=ft.RoundedRectangleBorder(
                radius=ft.BorderRadius(top_left=24, top_right=24, bottom_left=0, bottom_right=0)
            ),
        )
    )
