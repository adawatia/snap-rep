"""History view: Summary metrics, interactive monthly workout calendar,
date-filtered exercise list, single set deletion, and CSV export.
Future dates are strictly disabled.
"""

import asyncio
import calendar
from datetime import date, datetime
from typing import List
import flet as ft

from components.confirm_dialog import show_confirm_dialog
from components.export_dialog import show_export_dialog
from models import SetRecord
from state import AppState


class HistoryView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state

        today = date.today()
        self.cal_year = today.year
        self.cal_month = today.month
        self.selected_date_str = today.strftime("%Y-%m-%d")
        self.view_mode = "day"  # "day" or "all"
        self._all_history_limit = 50

        # Metric labels
        self.today_reps_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.total_sets_text = ft.Text("0", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.SECONDARY)
        self.total_volume_text = ft.Text("0 kg", size=24, weight=ft.FontWeight.BOLD, color=ft.Colors.TERTIARY)

        # Calendar controls
        self.month_year_text = ft.Text("", size=15, weight=ft.FontWeight.BOLD)
        self.prev_month_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_LEFT,
            icon_size=20,
            tooltip="Previous month",
            on_click=self._prev_month,
        )
        self.next_month_btn = ft.IconButton(
            icon=ft.Icons.CHEVRON_RIGHT,
            icon_size=20,
            tooltip="Next month",
            on_click=self._next_month,
        )
        self.calendar_grid = ft.Column(spacing=4)

        # Dynamic workout content container
        self.selected_date_label = ft.Text("", size=16, weight=ft.FontWeight.BOLD)
        self.selected_date_stats = ft.Text("", size=12, color=ft.Colors.OUTLINE)
        self.day_exercise_list = ft.Column(spacing=8)
        self.day_exercise_container = ft.Container(content=self.day_exercise_list)

        # View toggle
        self.day_view_btn = ft.Container()
        self.all_view_btn = ft.Container()
        self.toggle_container = ft.Row(spacing=6)

        self.root = self._build_layout()
        self.update_ui()

    # --- Navigation & Calendar Actions ---

    def _prev_month(self, e) -> None:
        if self.cal_month == 1:
            self.cal_month = 12
            self.cal_year -= 1
        else:
            self.cal_month -= 1
        self._render_calendar()
        self.page.update()

    def _next_month(self, e) -> None:
        today = date.today()
        # Prevent navigating beyond current month
        if self.cal_year > today.year or (self.cal_year == today.year and self.cal_month >= today.month):
            return

        if self.cal_month == 12:
            self.cal_month = 1
            self.cal_year += 1
        else:
            self.cal_month += 1
        self._render_calendar()
        self.page.update()

    def _go_to_today(self, e) -> None:
        today = date.today()
        self.cal_year = today.year
        self.cal_month = today.month
        self.selected_date_str = today.strftime("%Y-%m-%d")
        self.view_mode = "day"
        self.update_ui()
        self.page.update()

    def _select_date(self, date_str: str) -> None:
        try:
            sel_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            if sel_date > date.today():
                return  # Prevent selecting any future dates
        except Exception:
            return

        self.selected_date_str = date_str
        self.view_mode = "day"
        self._render_calendar()
        self._render_history_data()
        self.page.update()

    def _set_view_mode(self, mode: str) -> None:
        self.view_mode = mode
        self.update_ui()
        self.page.update()

    def _on_export_click(self, e) -> None:
        asyncio.create_task(show_export_dialog(self.page, self.state))

    def _on_clear_all_click(self, e) -> None:
        async def do_clear():
            await self.state.clear_history()
            self.update_ui()
            self.page.update()

        show_confirm_dialog(
            self.page,
            title="Clear All History?",
            message="This will permanently delete all recorded workout sets.",
            confirm_text="Clear All",
            is_destructive=True,
            on_confirm=do_clear,
        )

    def _delete_single_set(self, record_id: str, set_desc: str) -> None:
        async def do_delete():
            await self.state.delete_set(record_id)
            self.update_ui()
            self.page.update()

        show_confirm_dialog(
            self.page,
            title="Delete Set?",
            message=f"Remove this set ({set_desc}) from your history?",
            confirm_text="Delete",
            is_destructive=True,
            on_confirm=do_delete,
        )

    # --- Calendar Grid Builder ---

    def _render_calendar(self) -> None:
        today = date.today()
        month_name = calendar.month_name[self.cal_month]
        self.month_year_text.value = f"{month_name} {self.cal_year}"

        # Disable next month if currently viewing current month
        is_next_disabled = (self.cal_year > today.year or (self.cal_year == today.year and self.cal_month >= today.month))
        self.next_month_btn.disabled = is_next_disabled
        self.next_month_btn.icon_color = ft.Colors.OUTLINE_VARIANT if is_next_disabled else None

        # Check memoization key to avoid rebuilding 40+ child controls when month, history length, and selection are identical
        cal_key = (self.cal_year, self.cal_month, len(self.state.history), self.selected_date_str)
        if getattr(self, "_last_cal_key", None) == cal_key and len(self.calendar_grid.controls) > 0:
            return
        self._last_cal_key = cal_key

        # Fast set lookup for workout presence
        workout_dates = {rec.timestamp[:10] for rec in self.state.history if len(rec.timestamp) >= 10}
        today_str = today.strftime("%Y-%m-%d")

        # Days of week header
        days_header = ["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]
        header_row = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_AROUND,
            controls=[
                ft.Container(
                    width=40,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text(day_name, size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
                )
                for day_name in days_header
            ],
        )

        grid_rows = [header_row]
        weeks = calendar.monthcalendar(self.cal_year, self.cal_month)

        for week in weeks:
            cell_controls = []
            for day in week:
                if day == 0:
                    cell_controls.append(ft.Container(width=40, height=38))
                    continue

                cell_date = date(self.cal_year, self.cal_month, day)
                date_str = f"{self.cal_year:04d}-{self.cal_month:02d}-{day:02d}"
                is_future = (cell_date > today)

                if is_future:
                    # Future dates are completely disabled and unclickable
                    cell_controls.append(
                        ft.Container(
                            width=40,
                            height=38,
                            alignment=ft.Alignment.CENTER,
                            content=ft.Text(
                                str(day),
                                size=12,
                                color=ft.Colors.OUTLINE_VARIANT,
                            ),
                        )
                    )
                    continue

                is_selected = (date_str == self.selected_date_str and self.view_mode == "day")
                has_workout = date_str in workout_dates
                is_today = (date_str == today_str)

                # Visual indicators
                cell_bg = ft.Colors.PRIMARY if is_selected else (
                    ft.Colors.SURFACE_CONTAINER_HIGHEST if has_workout else None
                )
                text_color = ft.Colors.ON_PRIMARY if is_selected else (
                    ft.Colors.PRIMARY if has_workout else (
                        ft.Colors.ON_SURFACE if is_today else ft.Colors.ON_SURFACE_VARIANT
                    )
                )

                dot_color = ft.Colors.ON_PRIMARY if is_selected else ft.Colors.PRIMARY

                day_stack = ft.Column(
                    alignment=ft.MainAxisAlignment.CENTER,
                    horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                    spacing=1,
                    controls=[
                        ft.Text(
                            str(day),
                            size=12,
                            weight=ft.FontWeight.BOLD if (has_workout or is_selected or is_today) else ft.FontWeight.NORMAL,
                            color=text_color,
                        ),
                        # Workout Indicator Dot
                        ft.Container(
                            width=4,
                            height=4,
                            border_radius=2,
                            bgcolor=dot_color if has_workout else ft.Colors.TRANSPARENT,
                        ),
                    ],
                )

                border = ft.Border.all(1, ft.Colors.PRIMARY) if (is_today and not is_selected) else None

                cell_controls.append(
                    ft.Container(
                        width=40,
                        height=38,
                        alignment=ft.Alignment.CENTER,
                        border_radius=8,
                        bgcolor=cell_bg,
                        border=border,
                        content=day_stack,
                        on_click=lambda _, d=date_str: self._select_date(d),
                    )
                )

            grid_rows.append(
                ft.Row(
                    alignment=ft.MainAxisAlignment.SPACE_AROUND,
                    controls=cell_controls,
                )
            )

        self.calendar_grid.controls = grid_rows

    # --- History Data Renderers ---

    def _render_history_data(self) -> None:
        if self.view_mode == "day":
            self._render_day_view()
        else:
            self._render_all_view()

    def _render_day_view(self) -> None:
        # Fast linear filter (deduplication is guaranteed by AppStorage)
        day_sets: List[SetRecord] = [
            r for r in self.state.history if r.timestamp.startswith(self.selected_date_str)
        ]

        try:
            sel_date_obj = datetime.strptime(self.selected_date_str, "%Y-%m-%d")
            formatted_date = sel_date_obj.strftime("%A, %b %d, %Y")
        except Exception:
            formatted_date = self.selected_date_str

        self.selected_date_label.value = formatted_date

        cards: List[ft.Control] = []

        if not day_sets:
            self.selected_date_stats.value = "No sets recorded on this day."
            cards.append(
                ft.Container(
                    padding=24,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=8,
                        controls=[
                            ft.Icon(ft.Icons.EVENT_BUSY_OUTLINED, size=36, color=ft.Colors.OUTLINE),
                            ft.Text("Rest Day or No Logs", size=14, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
                            ft.Text("Select a highlighted date with a dot to view recorded sets.", size=12, color=ft.Colors.OUTLINE),
                        ],
                    ),
                )
            )
            self.day_exercise_list = ft.Column(spacing=8, controls=cards)
            self.day_exercise_container.content = self.day_exercise_list
            return

        total_day_reps = sum(r.reps for r in day_sets)
        total_day_volume = sum(r.reps * r.weight_kg for r in day_sets)
        self.selected_date_stats.value = (
            f"{len(day_sets)} sets • {total_day_reps} reps • {int(total_day_volume)} kg total volume"
        )

        # Compute accurate set numbering for each exercise chronologically
        chrono = sorted(day_sets, key=lambda s: s.timestamp)
        ex_counts: dict[str, int] = {}
        set_num_map: dict[str, int] = {}
        for s in chrono:
            c = ex_counts.get(s.exercise, 0) + 1
            ex_counts[s.exercise] = c
            set_num_map[s.id] = getattr(s, "set_number", None) or c

        # Render each set in the classic, familiar card layout with single-set deletion
        for item in day_sets:
            set_num = set_num_map.get(item.id, getattr(item, "set_number", 1))
            wt_label = f"{int(item.weight_kg) if item.weight_kg.is_integer() else item.weight_kg} kg"
            set_summary = f"Set {set_num}: {item.reps} reps @ {wt_label}"

            set_badge = ft.Container(
                content=ft.Text(f"SET {set_num}", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                padding=ft.Padding(8, 4, 8, 4),
                border_radius=6,
            )

            card_content = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=10,
                        expand=True,
                        controls=[
                            set_badge,
                            ft.Column(
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        item.exercise,
                                        weight=ft.FontWeight.BOLD,
                                        size=14,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(item.timestamp, size=11, color=ft.Colors.OUTLINE),
                                    *(
                                        [
                                            ft.Text(
                                                f"Note: {item.notes}",
                                                size=11,
                                                color=ft.Colors.OUTLINE,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            )
                                        ]
                                        if item.notes else []
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                spacing=2,
                                controls=[
                                    ft.Text(f"{item.reps} REPS", weight=ft.FontWeight.BOLD, size=14),
                                    ft.Text(wt_label, size=11, color=ft.Colors.OUTLINE),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=18,
                                icon_color=ft.Colors.OUTLINE,
                                tooltip="Delete this set",
                                on_click=lambda _, rec_id=item.id, desc=set_summary: self._delete_single_set(rec_id, desc),
                            ),
                        ],
                    ),
                ],
            )
            cards.append(
                ft.Card(
                    key=f"set_card_{item.id}",
                    content=ft.Container(padding=ft.Padding(10, 8, 10, 8), content=card_content),
                )
            )

        self.day_exercise_list = ft.Column(spacing=8, controls=cards)
        self.day_exercise_container.content = self.day_exercise_list

    def _render_all_view(self) -> None:
        self.selected_date_label.value = "All Workout History"
        deduped_history: List[SetRecord] = list(self.state.history)

        total_count = len(deduped_history)
        self.selected_date_stats.value = f"Showing latest {min(self._all_history_limit, total_count)} of {total_count} total sets"

        cards: List[ft.Control] = []

        if not deduped_history:
            cards.append(
                ft.Container(
                    padding=24,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Text("No sets recorded yet.", size=13, color=ft.Colors.OUTLINE),
                )
            )
            self.day_exercise_list = ft.Column(spacing=8, controls=cards)
            self.day_exercise_container.content = self.day_exercise_list
            return

        chrono_all = sorted(deduped_history, key=lambda s: s.timestamp)
        all_ex_counts: dict[str, int] = {}
        all_set_num_map: dict[str, int] = {}
        for s in chrono_all:
            d_prefix = s.timestamp[:10] if len(s.timestamp) >= 10 else ""
            k = f"{d_prefix}_{s.exercise}"
            c = all_ex_counts.get(k, 0) + 1
            all_ex_counts[k] = c
            all_set_num_map[s.id] = getattr(s, "set_number", None) or c

        for item in deduped_history[: self._all_history_limit]:
            set_num = all_set_num_map.get(item.id, getattr(item, "set_number", 1))
            wt_label = f"{int(item.weight_kg) if item.weight_kg.is_integer() else item.weight_kg} kg"
            set_summary = f"Set {set_num}: {item.reps} reps @ {wt_label}"

            set_badge = ft.Container(
                content=ft.Text(f"SET {set_num}", size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY),
                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                padding=ft.Padding(8, 4, 8, 4),
                border_radius=6,
            )

            card_content = ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Row(
                        spacing=10,
                        expand=True,
                        controls=[
                            set_badge,
                            ft.Column(
                                spacing=2,
                                expand=True,
                                controls=[
                                    ft.Text(
                                        item.exercise,
                                        weight=ft.FontWeight.BOLD,
                                        size=14,
                                        max_lines=1,
                                        overflow=ft.TextOverflow.ELLIPSIS,
                                    ),
                                    ft.Text(item.timestamp, size=11, color=ft.Colors.OUTLINE),
                                    *(
                                        [
                                            ft.Text(
                                                f"Note: {item.notes}",
                                                size=11,
                                                color=ft.Colors.OUTLINE,
                                                max_lines=1,
                                                overflow=ft.TextOverflow.ELLIPSIS,
                                            )
                                        ]
                                        if item.notes else []
                                    ),
                                ],
                            ),
                        ],
                    ),
                    ft.Row(
                        spacing=4,
                        alignment=ft.MainAxisAlignment.END,
                        controls=[
                            ft.Column(
                                horizontal_alignment=ft.CrossAxisAlignment.END,
                                spacing=2,
                                controls=[
                                    ft.Text(f"{item.reps} REPS", weight=ft.FontWeight.BOLD, size=14),
                                    ft.Text(wt_label, size=11, color=ft.Colors.OUTLINE),
                                ],
                            ),
                            ft.IconButton(
                                icon=ft.Icons.DELETE_OUTLINE,
                                icon_size=18,
                                icon_color=ft.Colors.OUTLINE,
                                tooltip="Delete this set",
                                on_click=lambda _, rec_id=item.id, desc=set_summary: self._delete_single_set(rec_id, desc),
                            ),
                        ],
                    ),
                ],
            )
            cards.append(
                ft.Card(
                    key=f"all_set_card_{item.id}",
                    content=ft.Container(padding=ft.Padding(10, 8, 10, 8), content=card_content),
                )
            )

        if total_count > self._all_history_limit:
            def load_more(e):
                self._all_history_limit += 50
                self.update_ui()
                self.page.update()

            cards.append(
                ft.Container(
                    alignment=ft.Alignment.CENTER,
                    padding=10,
                    content=ft.Button("Load More Records...", on_click=load_more),
                )
            )

        self.day_exercise_list = ft.Column(spacing=8, controls=cards)
        self.day_exercise_container.content = self.day_exercise_list

    def update_ui(self) -> None:
        today_str = date.today().strftime("%Y-%m-%d")
        today_reps = 0
        total_vol = 0.0
        for r in self.state.history:
            if r.timestamp.startswith(today_str):
                today_reps += r.reps
            total_vol += r.reps * r.weight_kg
        total_sets = len(self.state.history)

        self.today_reps_text.value = str(today_reps)
        self.total_sets_text.value = str(total_sets)
        self.total_volume_text.value = f"{int(total_vol)} kg"

        # Update view toggle buttons
        is_day = (self.view_mode == "day")
        self.day_view_btn.bgcolor = ft.Colors.PRIMARY if is_day else ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.day_view_btn.content = ft.Text(
            "Selected Day",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_PRIMARY if is_day else None,
        )
        self.all_view_btn.bgcolor = ft.Colors.PRIMARY if not is_day else ft.Colors.SURFACE_CONTAINER_HIGHEST
        self.all_view_btn.content = ft.Text(
            "All History",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_PRIMARY if not is_day else None,
        )

        self._render_calendar()
        self._render_history_data()

    def _build_layout(self) -> ft.Container:
        # View toggle buttons
        self.day_view_btn = ft.Container(
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=8,
            on_click=lambda _: self._set_view_mode("day"),
        )
        self.all_view_btn = ft.Container(
            padding=ft.Padding(12, 6, 12, 6),
            border_radius=8,
            on_click=lambda _: self._set_view_mode("all"),
        )
        self.toggle_container.controls = [self.day_view_btn, self.all_view_btn]

        return ft.Container(
            padding=14,
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=14,
                controls=[
                    # 1. Summary Cards Row
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        controls=[
                            ft.Card(
                                expand=1,
                                content=ft.Container(
                                    padding=10,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Column(
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2,
                                        controls=[
                                            ft.Text("TODAY REPS", size=10, weight=ft.FontWeight.BOLD),
                                            self.today_reps_text,
                                        ],
                                    ),
                                ),
                            ),
                            ft.Card(
                                expand=1,
                                content=ft.Container(
                                    padding=10,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Column(
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2,
                                        controls=[
                                            ft.Text("TOTAL SETS", size=10, weight=ft.FontWeight.BOLD),
                                            self.total_sets_text,
                                        ],
                                    ),
                                ),
                            ),
                            ft.Card(
                                expand=1,
                                content=ft.Container(
                                    padding=10,
                                    alignment=ft.Alignment.CENTER,
                                    content=ft.Column(
                                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                        spacing=2,
                                        controls=[
                                            ft.Text("VOLUME", size=10, weight=ft.FontWeight.BOLD),
                                            self.total_volume_text,
                                        ],
                                    ),
                                ),
                            ),
                        ],
                    ),

                    # 2. Interactive Calendar Card
                    ft.Card(
                        content=ft.Container(
                            padding=12,
                            content=ft.Column(
                                spacing=10,
                                controls=[
                                    # Month Navigation Header
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Row(
                                                spacing=4,
                                                controls=[
                                                    self.prev_month_btn,
                                                    self.month_year_text,
                                                    self.next_month_btn,
                                                ],
                                            ),
                                            ft.TextButton(
                                                "Today",
                                                icon=ft.Icons.TODAY,
                                                on_click=self._go_to_today,
                                            ),
                                        ],
                                    ),
                                    # Month Grid
                                    self.calendar_grid,
                                ],
                            ),
                        )
                    ),

                    # 3. View Mode Toggle (Centered, giving full room)
                    ft.Row(
                        alignment=ft.MainAxisAlignment.CENTER,
                        controls=[self.toggle_container],
                    ),

                    # 4. Actions Toolbar (Export CSV & Clear All - The beloved old format, never overflows)
                    ft.Row(
                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Text("Workout Sets", size=16, weight=ft.FontWeight.BOLD),
                            ft.Row(
                                spacing=2,
                                controls=[
                                    ft.TextButton(
                                        "Export CSV",
                                        icon=ft.Icons.DOWNLOAD,
                                        on_click=self._on_export_click,
                                    ),
                                    ft.TextButton(
                                        "Clear All",
                                        icon=ft.Icons.DELETE_OUTLINE,
                                        icon_color=ft.Colors.ERROR,
                                        on_click=self._on_clear_all_click,
                                    ),
                                ],
                            ),
                        ],
                    ),

                    # 4. Selected Date Header & Stats
                    ft.Column(
                        spacing=2,
                        controls=[
                            self.selected_date_label,
                            self.selected_date_stats,
                        ],
                    ),

                    # 5. Scalable Exercise / Sets List
                    self.day_exercise_container,
                ],
            ),
        )
