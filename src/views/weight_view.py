"""Body-weight log, goal, and measured trend."""

from datetime import date, datetime

import flet as ft
import flet_charts as fch

from components.confirm_dialog import show_confirm_dialog
from insights import body_weight_series, weight_goal_summary
from models import WeightEntry
from state import AppState


class WeightView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state
        self.selected_days: int | None = 30
        self.show_trend = False
        self._history_limit = 30
        self.chart_detail = ft.Text("Tap a point to read that day's average.", size=12,
                                    color=ft.Colors.ON_SURFACE_VARIANT)
        self.column = ft.Column(scroll=ft.ScrollMode.ADAPTIVE, expand=True, spacing=20,
                                horizontal_alignment=ft.CrossAxisAlignment.STRETCH)
        self.root = ft.Container(padding=ft.Padding(16, 14, 16, 24), expand=True, content=self.column)
        self.update_ui()

    def _dialog_width(self) -> float:
        return min(340, max(240, (getattr(self.page, "width", None) or 390) - 48))

    def _edit_entry(self, entry: WeightEntry | None = None) -> None:
        timestamp = datetime.fromisoformat(entry.recorded_at) if entry else datetime.now().astimezone()
        selected_date = timestamp.date()
        selected_time = timestamp.time().replace(second=0, microsecond=0, tzinfo=None)
        weight_field = ft.TextField(
            label="Body weight (kg)", value=f"{entry.weight_kg:g}" if entry else "",
            keyboard_type=ft.KeyboardType.NUMBER, autofocus=True,
            border=ft.OutlineInputBorder(border_radius=12),
        )
        date_button = ft.TextButton("")
        time_button = ft.TextButton("")
        error = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        def refresh_labels() -> None:
            date_button.content = selected_date.strftime("%d %b %Y")
            time_button.content = selected_time.strftime("%I:%M %p")
            self.page.update()

        def on_date_change(e) -> None:
            nonlocal selected_date
            if e.control.value:
                value = e.control.value
                selected_date = value.date() if isinstance(value, datetime) else value
                refresh_labels()

        def on_time_change(e) -> None:
            nonlocal selected_time
            if e.control.value:
                selected_time = e.control.value
                refresh_labels()

        date_picker = ft.DatePicker(value=selected_date, first_date=date(1900, 1, 1),
                                    last_date=date.today(), on_change=on_date_change)
        time_picker = ft.TimePicker(value=selected_time, on_change=on_time_change)
        date_button.on_click = lambda _: self.page.show_dialog(date_picker)
        time_button.on_click = lambda _: self.page.show_dialog(time_picker)
        refresh_labels()

        def save(_) -> None:
            try:
                recorded = datetime.combine(selected_date, selected_time).astimezone().isoformat(timespec="minutes")
                self.state.save_weight_entry(float((weight_field.value or "").strip()), recorded,
                                             entry.id if entry else None)
            except (ValueError, OverflowError) as exc:
                error.value = str(exc) if str(exc) else "Enter a valid weight and time."
                error.visible = True
                self.page.update()
                return
            self.page.pop_dialog()
            self.page.update()

        self.page.show_dialog(ft.AlertDialog(
            title="Edit weigh-in" if entry else "Add weigh-in",
            content=ft.Container(width=self._dialog_width(), content=ft.Column(
                tight=True, spacing=10, horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[weight_field, ft.Text("Measured on", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                          ft.Row(controls=[date_button, time_button], wrap=True), error],
            )),
            scrollable=True,
            actions=[ft.TextButton("Cancel", on_click=lambda _: self.page.pop_dialog()),
                     ft.FilledButton("Save", on_click=save)],
        ))
        self.page.update()

    def _edit_target(self, _) -> None:
        current = self.state.settings.get("target_weight_kg")
        field = ft.TextField(label="Target weight (kg)", value=f"{current:g}" if current else "",
                             keyboard_type=ft.KeyboardType.NUMBER,
                             border=ft.OutlineInputBorder(border_radius=12))
        error = ft.Text("", size=12, color=ft.Colors.ERROR, visible=False)

        def save(_):
            try:
                self.state.set_target_weight(float((field.value or "").strip()))
            except (ValueError, OverflowError) as exc:
                error.value = str(exc) if str(exc) else "Enter a valid target."
                error.visible = True
                self.page.update()
                return
            self.page.pop_dialog()
            self.page.update()

        def clear(_):
            self.state.set_target_weight(None)
            self.page.pop_dialog()
            self.page.update()

        actions = [ft.TextButton("Cancel", on_click=lambda _: self.page.pop_dialog())]
        if current is not None:
            actions.append(ft.TextButton("Remove target", on_click=clear))
        actions.append(ft.FilledButton("Save", on_click=save))
        self.page.show_dialog(ft.AlertDialog(
            title="Weight target", scrollable=True,
            content=ft.Container(width=self._dialog_width(), content=ft.Column(
                tight=True, spacing=8,
                controls=[field, ft.Text("Your first weigh-in is the starting point.", size=12,
                                         color=ft.Colors.ON_SURFACE_VARIANT), error],
            )), actions=actions,
        ))
        self.page.update()

    def _delete_entry(self, entry: WeightEntry) -> None:
        async def delete() -> None:
            self.state.delete_weight_entry(entry.id)
        show_confirm_dialog(
            self.page, title="Delete weigh-in?", message="Remove this reading from your history?",
            confirm_text="Delete", is_destructive=True,
            on_confirm=delete,
        )

    def _set_days(self, days: int | None) -> None:
        self.selected_days = days
        self.chart_detail.value = "Tap a point to read that day's average."
        self.update_ui()
        self.page.update()

    def _toggle_trend(self, _) -> None:
        self.show_trend = not self.show_trend
        self.update_ui()
        self.page.update()

    def _chart(self, series: list[tuple[date, float, float]]) -> ft.Control:
        if not series:
            return ft.Text("No readings in this period.", size=13, color=ft.Colors.ON_SURFACE_VARIANT)
        start_day = series[0][0]
        x_values = [(day - start_day).days for day, _, _ in series]
        x_pad = max(2, x_values[-1] * 0.16)
        values = [value for _, daily, trend in series for value in (daily, trend)]
        span = max(1.0, max(values) - min(values))
        min_y = max(0, min(values) - span * 0.25)
        max_y = max(values) + span * 0.25
        def on_chart_event(e):
            if getattr(e, "type", None) not in (fch.ChartEventType.TAP_UP, "tapUp"):
                return
            for spot in getattr(e, "spots", []) or []:
                index = getattr(spot, "spot_index", -1)
                line = getattr(spot, "bar_index", -1)
                if 0 <= index < len(series) and line in (0, 1):
                    day, daily, trend = series[index]
                    label = "Daily average" if line == 0 else "7-day average"
                    self.chart_detail.value = f"{day:%d %b %Y} · {label}: {(daily if line == 0 else trend):.1f} kg"
                    self.page.update()
                    break

        return fch.LineChart(
            height=250, min_x=-x_pad, max_x=x_values[-1] + x_pad,
            min_y=min_y, max_y=max_y,
            tooltip=fch.LineChartTooltip(fit_inside_horizontally=True, fit_inside_vertically=True),
            on_event=on_chart_event,
            data_series=[
                fch.LineChartData(color=ft.Colors.PRIMARY, stroke_width=2, point=True,
                    points=[fch.LineChartDataPoint(x, daily, tooltip=f"{day:%d %b}: {daily:.1f} kg daily average")
                            for x, (day, daily, _) in zip(x_values, series)]),
                fch.LineChartData(color=ft.Colors.TERTIARY, stroke_width=3, point=True,
                    points=[fch.LineChartDataPoint(x, trend, tooltip=f"{day:%d %b}: {trend:.1f} kg 7-day average")
                            for x, (day, _, trend) in zip(x_values, series)]),
            ],
            bottom_axis=fch.ChartAxis(
                title=ft.Text("Date", size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                title_size=16, label_size=28,
                labels=[fch.ChartAxisLabel(value=x_values[index],
                                           label=ft.Text(series[index][0].strftime("%d %b"), size=10))
                        for index in sorted({0, len(series) - 1})],
            ),
            left_axis=fch.ChartAxis(
                title=ft.Text("kg", size=10, color=ft.Colors.ON_SURFACE_VARIANT),
                title_size=16, label_size=36,
                labels=[fch.ChartAxisLabel(value=value, label=ft.Text(f"{value:.1f}", size=10))
                        for value in (min_y, (min_y + max_y) / 2, max_y)],
            ),
            horizontal_grid_lines=fch.ChartGridLines(color=ft.Colors.OUTLINE_VARIANT, width=0.5),
        )

    def update_ui(self) -> None:
        entries = self.state.weight_history
        summary = weight_goal_summary(entries, self.state.settings.get("target_weight_kg"))
        controls: list[ft.Control] = []
        if summary:
            change = summary["change"]
            change_text = "No change yet" if change == 0 else f"{abs(change):g} kg {'gained' if change > 0 else 'lost'} since first weigh-in"
            controls.append(ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER, border_radius=16,
                padding=ft.Padding(18, 16, 18, 16),
                content=ft.Column(spacing=8, controls=[
                    ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                        ft.Text("Latest reading", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.FilledButton("Add weigh-in", icon=ft.Icons.ADD,
                                        on_click=lambda _: self._edit_entry()),
                    ]),
                    ft.Text(f"{summary['current']:g} kg", size=30, weight=ft.FontWeight.BOLD),
                    ft.Text(change_text, size=13),
                ]),
            ))
        else:
            controls.append(ft.Container(
                bgcolor=ft.Colors.SURFACE_CONTAINER, border_radius=16,
                padding=ft.Padding(24, 28, 24, 28),
                content=ft.Column(spacing=8, controls=[
                    ft.Text("Start with a weigh-in", size=17, weight=ft.FontWeight.BOLD),
                    ft.Text("Add a reading to see your history and trend.", size=13,
                            color=ft.Colors.ON_SURFACE_VARIANT),
                    ft.FilledButton("Add weigh-in", on_click=lambda _: self._edit_entry()),
                ]),
            ))
        target = summary["target"] if summary else self.state.settings.get("target_weight_kg")
        goal_controls: list[ft.Control] = [
            ft.Row(alignment=ft.MainAxisAlignment.SPACE_BETWEEN, controls=[
                ft.Text("Target weight", size=16, weight=ft.FontWeight.BOLD),
                ft.TextButton("Edit" if target else "Set target", on_click=self._edit_target),
            ]),
        ]
        if target is None:
            goal_controls.append(ft.Text("Set a target to see progress from your first reading.", size=12,
                                         color=ft.Colors.ON_SURFACE_VARIANT))
        elif summary:
            remaining = summary["remaining"]
            direction = target - summary["start"]
            if remaining == 0:
                goal_status = "at target"
            elif direction and remaining * direction < 0:
                goal_status = f"{abs(remaining):g} kg past target"
            else:
                goal_status = f"{abs(remaining):g} kg to target"
            goal_controls.extend([
                ft.Text(f"{target:g} kg target · {goal_status}", size=13),
                ft.ProgressBar(value=summary["progress"]) if summary["progress"] is not None
                else ft.Text("Maintaining your starting weight", size=12),
            ])
        else:
            goal_controls.append(ft.Text(f"{target:g} kg target · add a reading to track progress", size=12))
        controls.append(ft.Column(spacing=8, controls=goal_controls))

        if entries:
            series = body_weight_series(entries, self.selected_days)
            controls.append(ft.TextButton(
                "Hide trend" if self.show_trend else "Show trend",
                icon=ft.Icons.INSIGHTS_OUTLINED,
                on_click=self._toggle_trend,
            ))
            if self.show_trend:
                controls.extend([
                ft.Text("Weight trend", size=17, weight=ft.FontWeight.BOLD),
                ft.Row(spacing=4, controls=[
                    ft.TextButton(label, on_click=lambda _, d=days: self._set_days(d),
                                  style=ft.ButtonStyle(color=ft.Colors.PRIMARY if self.selected_days == days
                                                       else ft.Colors.ON_SURFACE_VARIANT))
                    for days, label in ((30, "30 days"), (90, "90 days"), (None, "All"))
                ]),
                self._chart(series),
                ft.Row(spacing=14, wrap=True, controls=[
                    ft.Row(spacing=5, controls=[
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.PRIMARY),
                        ft.Text("Daily average", size=11),
                    ]),
                    ft.Row(spacing=5, controls=[
                        ft.Container(width=8, height=8, border_radius=4, bgcolor=ft.Colors.TERTIARY),
                        ft.Text("7-day average", size=11),
                    ]),
                ]),
                self.chart_detail,
                ])
            controls.append(ft.Text("History", size=17, weight=ft.FontWeight.BOLD))
            rows = []
            for entry in reversed(entries[-self._history_limit:]):
                timestamp = datetime.fromisoformat(entry.recorded_at)
                rows.append(ft.ListTile(
                    title=ft.Text(f"{entry.weight_kg:g} kg", size=15, weight=ft.FontWeight.W_600),
                    subtitle=ft.Text(timestamp.strftime("%d %b %Y · %I:%M %p"), size=12),
                    trailing=ft.Row(tight=True, controls=[
                        ft.IconButton(icon=ft.Icons.EDIT_OUTLINED, tooltip="Edit weigh-in",
                                      on_click=lambda _, item=entry: self._edit_entry(item)),
                        ft.IconButton(icon=ft.Icons.DELETE_OUTLINE, tooltip="Delete weigh-in",
                                      on_click=lambda _, item=entry: self._delete_entry(item)),
                    ]),
                ))
            controls.append(ft.Column(spacing=0, controls=rows))
            if len(entries) > self._history_limit:
                controls.append(ft.OutlinedButton(
                    f"Show more readings ({len(entries) - self._history_limit} remaining)",
                    on_click=self._show_more_history,
                ))
        self.column.controls = controls

    def _show_more_history(self, e) -> None:
        self._history_limit += 30
        self.update_ui()
        self.page.update()
