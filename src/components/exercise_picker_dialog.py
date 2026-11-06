"""Exercise picker bottom sheet: Fast, searchable, and category-filtered exercise selection."""

from typing import Callable, List, Optional
import flet as ft

from components.add_exercise_dialog import show_add_exercise_dialog
from components.exercise_browse import BROWSE_PAGE_SIZE, exercise_category_label, exercise_count_label, exercise_defaults, filter_exercises
from components.exercise_weight_setup import show_weight_setup
from config import EXERCISE_CATEGORIES
from models import Exercise
from state import AppState


def show_exercise_picker(
    page: ft.Page,
    state: AppState,
    on_select: Optional[Callable[[Exercise], None]] = None,
    highlight_current: bool = False,
) -> None:
    search_query = ""
    selected_category = "All"
    visible_limit = BROWSE_PAGE_SIZE

    categories = ["All", "Custom Only"] + list(EXERCISE_CATEGORIES)

    # 1. Header controls
    sheet_title = ft.Text("Select Exercise", size=17, weight=ft.FontWeight.BOLD)
    count_badge = ft.Text("", size=11, color=ft.Colors.ON_SURFACE_VARIANT)

    # 2. Search input (Minimal, borderless, no icon)
    def on_search_change(e):
        nonlocal search_query, visible_limit
        search_query = (e.control.value or "").strip()
        visible_limit = BROWSE_PAGE_SIZE
        render_list()
        page.update()

    search_field = ft.TextField(
        hint_text="Search exercise or category...",
        border=ft.OutlineInputBorder(
            border_radius=12,
            side=ft.BorderSide(color=ft.Colors.TRANSPARENT),
        ),
        dense=True,
        content_padding=ft.Padding(14, 10, 14, 10),
        filled=True,
        fill_color=ft.Colors.SURFACE_CONTAINER_HIGHEST,
        on_change=on_search_change,
        expand=True,
        autofocus=False,
    )

    # 3. Category pills row
    category_row = ft.Row(
        scroll=ft.ScrollMode.AUTO,
        spacing=6,
        controls=[],
    )

    def select_category(cat: str):
        nonlocal selected_category, visible_limit
        selected_category = cat
        visible_limit = BROWSE_PAGE_SIZE
        render_categories()
        render_list()
        page.update()

    def render_categories():
        pills: List[ft.Control] = []
        for cat in categories:
            is_active = (cat == selected_category)
            pills.append(
                ft.OutlinedButton(
                    content=ft.Text(
                        cat,
                        size=11,
                        weight=ft.FontWeight.BOLD if is_active else ft.FontWeight.W_500,
                    ),
                    height=48,
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PRIMARY if is_active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                        color=ft.Colors.ON_PRIMARY if is_active else ft.Colors.ON_SURFACE_VARIANT,
                        shape=ft.RoundedRectangleBorder(radius=14),
                        padding=ft.Padding(12, 8, 12, 8),
                    ),
                    on_click=lambda _, c=cat: select_category(c),
                )
            )
        category_row.controls = pills

    # 4. Exercise list column
    list_column = ft.ListView(
        spacing=8,
        scroll=ft.ScrollMode.ADAPTIVE,
        padding=ft.Padding(0, 8, 0, 12),
    )
    viewport_height = getattr(page, "height", None) or 700
    list_container = ft.Container(
        content=list_column,
        height=min(350, max(120, viewport_height * 0.4)),
        expand=False,
    )

    def open_add_custom(initial_name: str = ""):
        page.pop_dialog()
        show_add_exercise_dialog(
            page,
            state,
            initial_name=initial_name,
            on_success=lambda ex: on_select(ex) if on_select else None,
        )

    is_choosing = False

    async def choose_exercise(ex: Exercise):
        nonlocal is_choosing
        if is_choosing:
            return
        is_choosing = True
        try:
            matched = next((item for item in state.exercises if item.name.strip().casefold() == ex.name.strip().casefold()), None)
            if matched is None:
                render_list()
                page.update()
                return
            await state.select_exercise(matched.name)
            page.pop_dialog()
            if on_select:
                on_select(matched)
            if matched.weight_setup_pending:
                show_weight_setup(page, state)
            page.update()
        finally:
            is_choosing = False

    def render_list():
        filtered, total = filter_exercises(state.exercises, search_query, selected_category)
        visible = filtered[:visible_limit]

        is_filtering = bool(search_query or selected_category != "All")
        count_badge.value = exercise_count_label(len(visible), len(filtered), total)
        count_badge.visible = is_filtering or len(filtered) > len(visible)
        list_column.key = f"picker:{search_query.casefold()}:{selected_category.casefold()}"

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
                                "No matching exercises" if search_query else "No exercises in this category",
                                size=13,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                text_align=ft.TextAlign.CENTER,
                            ),
                            *(
                                [ft.Text("Try another search or category.", size=12, color=ft.Colors.ON_SURFACE_VARIANT)]
                                if search_query or selected_category != "All" else []
                            ),
                            *(
                                [ft.TextButton("Show all categories", on_click=lambda _: select_category("All"))]
                                if selected_category != "All" else []
                            ),
                            *(
                                [
                                    ft.OutlinedButton(
                                        "Add as custom exercise",
                                        icon=ft.Icons.ADD,
                                        on_click=lambda _: open_add_custom(search_query),
                                    )
                                ]
                                if search_query and selected_category == "All"
                                else []
                            ),
                        ],
                    ),
                )
            )
            list_column.controls = cards
            return

        current_name_clean = state.current_exercise.name.strip().casefold()

        for ex in visible:
            is_current = highlight_current and (ex.name.strip().casefold() == current_name_clean)
            target_str = f"{exercise_category_label(ex)} • {exercise_defaults(ex)}"

            card_border = (
                ft.Border.all(1.5, ft.Colors.PRIMARY)
                if is_current
                else ft.Border.all(1, ft.Colors.OUTLINE_VARIANT)
            )
            card_bgcolor = (
                ft.Colors.PRIMARY_CONTAINER
                if is_current
                else ft.Colors.SURFACE_CONTAINER
            )

            # Left controls: show checkmark for selected, clean text with no icon for unselected
            left_controls: List[ft.Control] = []
            if is_current:
                left_controls.append(
                    ft.Icon(
                        ft.Icons.CHECK_CIRCLE,
                        size=18,
                        color=ft.Colors.PRIMARY,
                    )
                )

            left_controls.append(
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
                            target_str,
                            size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT,
                            max_lines=1,
                            overflow=ft.TextOverflow.ELLIPSIS,
                        ),
                    ],
                )
            )

            # Right badge: only show Custom badge for custom exercises (built-in badge removed for minimal UI)
            right_controls: List[ft.Control] = []
            if ex.is_custom:
                right_controls.append(
                    ft.Container(
                        content=ft.Text(
                            "Custom",
                            size=9,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.PRIMARY,
                        ),
                        padding=ft.Padding(5, 2, 5, 2),
                        border=ft.Border.all(1, ft.Colors.PRIMARY),
                        border_radius=6,
                    )
                )

            async def on_pick(_, target=ex):
                await choose_exercise(target)

            item = ft.Container(
                content=ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        ft.Row(
                            spacing=10,
                            expand=True,
                            controls=left_controls,
                        ),
                        *right_controls,
                    ],
                ),
                padding=ft.Padding(12, 10, 12, 10),
                border=card_border,
                border_radius=10,
                bgcolor=card_bgcolor,
                ink=True,
                on_click=on_pick,
            )
            cards.append(item)

        if len(filtered) > len(visible):
            cards.append(ft.Container(
                alignment=ft.Alignment.CENTER,
                padding=12,
                content=ft.OutlinedButton("Show more exercises", on_click=lambda _: show_more()),
            ))

        list_column.controls = cards

    def show_more():
        nonlocal visible_limit
        visible_limit += BROWSE_PAGE_SIZE
        render_list()
        page.update()

    # Initial renders
    render_categories()
    render_list()

    sheet_content = ft.Container(
        padding=ft.Padding(16, 8, 16, 16),
        content=ft.Column(
            spacing=6,
            tight=True,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
            controls=[
                # Top Header Row: Clean minimal title, + Custom button, Close button
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                    controls=[
                        sheet_title,
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
                # Minimal Borderless Search Bar
                ft.Row(controls=[search_field]),
                # Category Filter Pills
                category_row,
                # Info badge (visible only when actively filtering)
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
            draggable=True,
            scrollable=True,
            maintain_bottom_view_insets_padding=True,
            shape=ft.RoundedRectangleBorder(
                radius=ft.BorderRadius(top_left=24, top_right=24, bottom_left=0, bottom_right=0)
            ),
        )
    )
