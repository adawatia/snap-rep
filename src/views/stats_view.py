"""Observed workout totals and exercise personal bests."""

from datetime import date

import flet as ft
import flet_charts as fch

from insights import exercise_progress, workout_summary
from state import AppState


class StatsView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state
        self.selected_exercise: str | None = None
        self.show_charts = False
        self.week_detail = ft.Text("Tap a bar to read that week's total.", size=12,
                                   color=ft.Colors.ON_SURFACE_VARIANT)
        self.progress_detail = ft.Text("Tap a point to read its logged value.", size=12,
                                       color=ft.Colors.ON_SURFACE_VARIANT)
        self.stats_column = ft.Column(
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.root = ft.Container(
            padding=ft.Padding(16, 14, 16, 24),
            expand=True,
            content=self.stats_column,
        )
        self.update_ui()

    @staticmethod
    def _metric(label: str, value: str) -> ft.Control:
        return ft.Column(
            spacing=3,
            expand=True,
            controls=[
                ft.Text(label, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(value, size=21, weight=ft.FontWeight.BOLD),
            ],
        )

    def _on_exercise_select(self, e) -> None:
        self.selected_exercise = e.control.value
        self.progress_detail.value = "Tap a point to read its logged value."
        self.update_ui()
        self.page.update()

    def _toggle_charts(self, _) -> None:
        self.show_charts = not self.show_charts
        self.update_ui()
        self.page.update()

    def update_ui(self) -> None:
        summary = workout_summary(self.state.history)
        if not self.state.history:
            self.stats_column.controls = [
                ft.Container(
                    padding=ft.Padding(28, 36, 28, 36),
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=16,
                    content=ft.Column(
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.INSIGHTS, size=40, color=ft.Colors.PRIMARY),
                            ft.Text("Your progress starts here", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text("Log a set in Tracker to see personal bests and trends.", size=13,
                                    color=ft.Colors.ON_SURFACE_VARIANT, text_align=ft.TextAlign.CENTER),
                        ],
                    ),
                )
            ]
            return

        weeks = summary["weeks"]
        weekly_top = max(1, max(count for _, count in weeks))
        def on_week_event(e):
            if getattr(e, "type", None) not in (fch.ChartEventType.TAP_UP, "tapUp"):
                return
            index = getattr(e, "group_index", -1)
            if index is not None and 0 <= index < len(weeks):
                day, count = weeks[index]
                self.week_detail.value = f"Week of {day:%d %b %Y}: {count} set{'s' if count != 1 else ''}"
                self.page.update()

        weekly_chart = fch.BarChart(
            height=215,
            tooltip=fch.BarChartTooltip(fit_inside_horizontally=True, fit_inside_vertically=True),
            on_event=on_week_event,
            min_y=0,
            max_y=weekly_top * 1.18,
            groups=[
                fch.BarChartGroup(
                    x=index,
                    rods=[fch.BarChartRod(
                        to_y=count, width=17, color=ft.Colors.PRIMARY,
                        border_radius=ft.BorderRadius(top_left=5, top_right=5, bottom_left=0, bottom_right=0),
                        tooltip=f"{day:%d %b}: {count} set{'s' if count != 1 else ''}",
                    )],
                )
                for index, (day, count) in enumerate(weeks)
            ],
            bottom_axis=fch.ChartAxis(
                label_size=28,
                labels=[fch.ChartAxisLabel(value=index, label=ft.Text(day.strftime("%d %b"), size=10))
                        for index, (day, _) in enumerate(weeks) if index % 2 == 0],
            ),
            left_axis=fch.ChartAxis(
                title=ft.Text("Sets", size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                title_size=16, label_size=24,
                labels=[fch.ChartAxisLabel(value=value, label=ft.Text(str(value), size=10))
                        for value in sorted({0, round(weekly_top / 2), weekly_top})],
            ),
            horizontal_grid_lines=fch.ChartGridLines(color=ft.Colors.OUTLINE_VARIANT, width=0.5),
        )
        controls: list[ft.Control] = [
            ft.Text("Workout activity", size=18, weight=ft.FontWeight.BOLD),
            ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER, border_radius=16,
                padding=ft.Padding(16, 16, 16, 12),
                content=ft.Row(spacing=12, controls=[
                    self._metric("Sets", f"{summary['sets']:,}"),
                    self._metric("Reps", f"{summary['reps']:,}"),
                    self._metric("Active days", f"{summary['active_days']:,}"),
                ]),
            ),
        ]

        exercises = summary["exercises"]
        names = sorted(exercises, key=str.casefold)
        if self.selected_exercise not in exercises:
            self.selected_exercise = names[0]
        selected = exercises[self.selected_exercise]
        weighted = selected["max_weight"] > 0
        progress = exercise_progress(selected["records"], weighted)
        start_day = progress[0][0]
        x_values = [(day - start_day).days for day, _ in progress]
        x_pad = max(2, x_values[-1] * 0.16)
        values = [value for _, value in progress]
        span = max(1.0, max(values) - min(values))
        min_y = max(0, min(values) - span * 0.18)
        max_y = max(values) + span * 0.18
        def on_progress_event(e):
            if getattr(e, "type", None) not in (fch.ChartEventType.TAP_UP, "tapUp"):
                return
            for spot in getattr(e, "spots", []) or []:
                index = getattr(spot, "spot_index", -1)
                if 0 <= index < len(progress):
                    day, value = progress[index]
                    self.progress_detail.value = f"{day:%d %b %Y}: {value:g} {'kg' if weighted else 'reps'}"
                    self.page.update()
                    break

        progress_chart = fch.LineChart(
            height=245,
            tooltip=fch.LineChartTooltip(fit_inside_horizontally=True, fit_inside_vertically=True),
            on_event=on_progress_event,
            min_x=-x_pad,
            max_x=x_values[-1] + x_pad,
            min_y=min_y,
            max_y=max_y,
            data_series=[fch.LineChartData(
                color=ft.Colors.PRIMARY, stroke_width=3, point=True,
                points=[fch.LineChartDataPoint(
                    x, value, tooltip=f"{day:%d %b %Y}: {value:g} {'kg' if weighted else 'reps'}",
                ) for (day, value), x in zip(progress, x_values)],
            )],
            bottom_axis=fch.ChartAxis(
                title=ft.Text("Date", size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                title_size=16, label_size=28,
                labels=[fch.ChartAxisLabel(value=x_values[index],
                                           label=ft.Text(progress[index][0].strftime("%d %b"), size=10))
                        for index in sorted({0, len(progress) - 1})],
            ),
            left_axis=fch.ChartAxis(
                title=ft.Text("kg" if weighted else "Reps", size=10,
                              color=ft.Colors.ON_SURFACE_VARIANT),
                title_size=16, label_size=35,
                labels=[fch.ChartAxisLabel(value=value, label=ft.Text(f"{value:g}", size=10))
                        for value in (min_y, (min_y + max_y) / 2, max_y)],
            ),
            horizontal_grid_lines=fch.ChartGridLines(color=ft.Colors.OUTLINE_VARIANT, width=0.5),
        )
        selector = ft.Dropdown(
            label="Exercise", value=self.selected_exercise, expand=True,
            options=[ft.DropdownOption(name, name) for name in names],
            on_select=self._on_exercise_select,
        )
        controls.append(ft.TextButton(
            "Hide charts" if self.show_charts else "Show charts",
            icon=ft.Icons.INSIGHTS_OUTLINED,
            on_click=self._toggle_charts,
        ))
        if self.show_charts:
            controls.extend([
                ft.Column(spacing=6, controls=[
                    ft.Text("Sets by week", size=15, weight=ft.FontWeight.W_600),
                    ft.Text("Last 8 calendar weeks · including weeks with no sets", size=11,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                    weekly_chart,
                    ft.Row(alignment=ft.MainAxisAlignment.CENTER, controls=[
                        ft.Text("Week", size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                    ]),
                    self.week_detail,
                ]),
                ft.Text("Exercise progress", size=18, weight=ft.FontWeight.BOLD),
                ft.Row(controls=[selector]),
                ft.Text("Heaviest logged weight" if weighted else "Most reps in a set", size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT),
                progress_chart,
                self.progress_detail,
            ])
        controls.append(ft.Text("Personal bests", size=18, weight=ft.FontWeight.BOLD))
        for name in names:
            data = exercises[name]
            if data["max_weight"] > 0:
                best = f"{data['max_weight']:g} kg × {data['reps_at_max']} reps"
            else:
                best = f"{data['max_reps']} reps"
            controls.append(ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER, border_radius=14,
                padding=ft.Padding(16, 14, 16, 14),
                content=ft.Row(spacing=12, controls=[
                    ft.Column(expand=True, spacing=4, controls=[
                        ft.Text(name, size=15, weight=ft.FontWeight.BOLD, max_lines=2,
                                overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(f"{data['sets']} sets · {data['reps']} reps", size=12,
                                color=ft.Colors.ON_SURFACE_VARIANT),
                    ]),
                    ft.Text(best, size=13, weight=ft.FontWeight.W_600, color=ft.Colors.PRIMARY,
                            text_align=ft.TextAlign.RIGHT),
                ]),
            ))
        self.stats_column.controls = controls
