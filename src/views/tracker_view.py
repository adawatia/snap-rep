"""Tracker view: exercise selection, rep and weight controls, rest timer, and set logging."""

import asyncio
import flet as ft

from components.add_exercise_dialog import show_add_exercise_dialog
from components.exercise_picker_dialog import show_exercise_picker
from state import AppState


class TrackerView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state
        self._has_selected_exercise = False
        self._initial_exercise_name = state.current_exercise.name

        # Reps display
        self.reps_display = ft.Text(
            str(self.state.current_reps),
            size=52,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.PRIMARY,
        )
        self.set_badge = ft.Text(
            f"SET {self.state.current_set_number}",
            size=12,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_PRIMARY_CONTAINER,
        )
        self.default_reps_btn = ft.TextButton(
            content=ft.Text(f"Default ({self.state.current_exercise.default_reps})", size=11),
            icon=ft.Icons.RESTORE,
            icon_color=ft.Colors.OUTLINE,
            on_click=lambda _: asyncio.create_task(
                self.state.update_reps(absolute=self.state.current_exercise.default_reps)
            ),
        )

        # Weight input field and default button
        self.weight_input = ft.TextField(
            value=self._format_weight(self.state.current_weight),
            suffix="kg",
            keyboard_type=ft.KeyboardType.NUMBER,
            width=110,
            text_align=ft.TextAlign.CENTER,
            text_size=16,
            dense=True,
            content_padding=ft.Padding(10, 6, 10, 6),
            on_change=self._on_weight_input_change,
        )
        self.default_weight_btn = ft.TextButton(
            content=ft.Text(f"Default ({self._format_weight(self.state.current_exercise.default_weight)}kg)", size=11),
            icon=ft.Icons.RESTORE,
            icon_color=ft.Colors.OUTLINE,
            on_click=lambda _: asyncio.create_task(
                self.state.update_weight(absolute=self.state.current_exercise.default_weight)
            ),
        )

        # Rest Timer display & controls
        self.timer_display = ft.Text(
            "00:00",
            size=22,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.SECONDARY,
        )
        self.timer_status_label = ft.Text(
            "Rest Timer",
            size=12,
            weight=ft.FontWeight.W_500,
            color=ft.Colors.ON_SURFACE_VARIANT,
        )
        self.timer_toggle_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=18,
            size_constraints=ft.BoxConstraints(min_width=48, min_height=48),
            tooltip="Pause / Resume",
            on_click=lambda _: asyncio.create_task(self.state.toggle_timer()),
        )
        self.timer_reset_btn = ft.IconButton(
            icon=ft.Icons.STOP,
            icon_size=18,
            icon_color=ft.Colors.ERROR,
            size_constraints=ft.BoxConstraints(min_width=48, min_height=48),
            tooltip="Reset timer",
            on_click=lambda _: asyncio.create_task(self.state.reset_timer()),
        )
        self.timer_pills_container = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[],
        )
        self.weight_shortcuts = self._build_weight_pills()

        # Exercise Selector Card (Minimal, simple, zero truncation)
        self.exercise_name_label = ft.Text(
            "Select Exercise",
            size=15,
            weight=ft.FontWeight.BOLD,
            color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.exercise_category_label = ft.Text(
            "Tap to choose a movement",
            size=12,
            color=ft.Colors.ON_SURFACE_VARIANT,
            max_lines=1,
            overflow=ft.TextOverflow.ELLIPSIS,
        )
        self.exercise_badge_text = ft.Text("Custom", size=9, weight=ft.FontWeight.BOLD, color=ft.Colors.PRIMARY)
        self.exercise_badge = ft.Container(
            content=self.exercise_badge_text,
            padding=ft.Padding(5, 2, 5, 2),
            border_radius=6,
            border=ft.Border.all(1, ft.Colors.PRIMARY),
            visible=False,
        )

        self.exercise_selector_card = ft.Container(
            expand=True,
            padding=ft.Padding(14, 8, 14, 8),
            border_radius=12,
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
            ink=True,
            on_click=self._open_exercise_picker,
            content=ft.Row(
                alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    ft.Column(
                        spacing=2,
                        expand=True,
                        controls=[
                            ft.Row(
                                spacing=6,
                                vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    self.exercise_name_label,
                                    self.exercise_badge,
                                ],
                            ),
                            self.exercise_category_label,
                        ],
                    ),
                    ft.Icon(
                        ft.Icons.KEYBOARD_ARROW_DOWN,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                        size=20,
                    ),
                ],
            ),
        )

        self._refresh_timer_pills()
        self._is_logging: bool = False  # synchronous in-flight guard
        self.is_active: bool = True  # whether Tracker tab is currently visible
        self.log_btn = self._build_log_btn()
        self.root = self._build_layout()
        self.update_viewport_layout()
        self.state.subscribe_timer(self._on_timer_tick)
        self.update_ui()

    def update_viewport_layout(self, height: float | None = None) -> None:
        """Keep the primary tracker controls visible on short phone screens."""
        compact = (height or getattr(self.page, "height", None) or 800) < 700
        self.weight_shortcuts.visible = not compact
        self.reps_display.size = 44 if compact else 52
        self.root.content.spacing = 6 if compact else 8

    def _on_timer_tick(self) -> None:
        mins = self.state.timer_seconds_remaining // 60
        secs = self.state.timer_seconds_remaining % 60
        self.timer_display.value = f"{mins:02d}:{secs:02d}"
        # Only update the timer display control when the Tracker tab is active
        if self.page and getattr(self, "is_active", True):
            try:
                self.timer_display.update()
            except Exception:
                pass

    def _format_weight(self, wt: float) -> str:
        return str(int(wt) if wt.is_integer() else round(wt, 1))

    def _open_exercise_picker(self, e) -> None:
        def on_select(_):
            self._has_selected_exercise = True
            self.update_ui()

        show_exercise_picker(
            self.page,
            self.state,
            on_select=on_select,
        )

    def _open_add_dialog(self, e) -> None:
        def on_success(_):
            self._has_selected_exercise = True
            self.update_ui()

        show_add_exercise_dialog(
            self.page,
            self.state,
            on_success=on_success,
        )

    def _on_weight_input_change(self, e) -> None:
        self.state.set_weight_from_text(e.control.value)

    def _is_log_blocked(self) -> bool:
        """Require an explicit exercise choice before recording a set."""
        return (not self._has_selected_exercise or self._is_logging or
                (self.state.timer_running and self.state.timer_seconds_remaining > 0))

    def _sync_log_btn_state(self) -> None:
        """Sync the log button appearance to match current blocked/allowed state."""
        blocked = self._is_log_blocked()
        if not self._has_selected_exercise:
            label = "SELECT AN EXERCISE"
            icon = ft.Icons.FITNESS_CENTER
        elif blocked and self.state.timer_running:
            label = "REST IN PROGRESS"
            icon = ft.Icons.TIMER
        elif blocked:
            label = "LOGGING..."
            icon = ft.Icons.HOURGLASS_BOTTOM
        else:
            label = "LOG THIS SET"
            icon = ft.Icons.CHECK_CIRCLE
        self.log_btn.disabled = blocked
        self.log_btn.content = label
        self.log_btn.icon = icon
        self.log_btn.style = ft.ButtonStyle(
            bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if blocked else ft.Colors.PRIMARY,
            color=ft.Colors.OUTLINE if blocked else ft.Colors.ON_PRIMARY,
            shape=ft.RoundedRectangleBorder(radius=10),
        )

    def _build_log_btn(self) -> ft.FilledButton:
        return ft.FilledButton(
            content="LOG THIS SET",
            icon=ft.Icons.CHECK_CIRCLE,
            expand=True,
            height=52,
            style=ft.ButtonStyle(
                bgcolor=ft.Colors.PRIMARY,
                color=ft.Colors.ON_PRIMARY,
                shape=ft.RoundedRectangleBorder(radius=10),
            ),
            on_click=self._on_log_set,
        )

    async def _on_log_set(self, e) -> None:
        # Synchronous check — bail instantly if already in-flight or timer is running
        if self._is_log_blocked():
            return
        self._is_logging = True
        self._sync_log_btn_state()
        try:
            self.log_btn.update()
        except Exception:
            pass
        try:
            success, message = await self.state.log_set()
            self.page.show_dialog(
                ft.SnackBar(
                    content=ft.Text(message),
                    show_close_icon=True,
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST if not success else None,
                )
            )
            self.page.update()
        finally:
            self._is_logging = False
            self._sync_log_btn_state()
            try:
                self.log_btn.update()
            except Exception:
                pass

    def _build_weight_pills(self) -> ft.Row:
        steps = [
            ("-5", -5.0),
            ("-2.5", -2.5),
            ("+2.5", +2.5),
            ("+5", +5.0),
        ]
        pills = []
        for label, delta in steps:
            pills.append(
                ft.OutlinedButton(
                    content=ft.Text(label, size=12, weight=ft.FontWeight.BOLD, no_wrap=True),
                    expand=True,
                    height=44,
                    tooltip=f"Adjust weight by {label} kg",
                    style=ft.ButtonStyle(
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(4, 4, 4, 4),
                    ),
                    on_click=lambda _, d=delta: asyncio.create_task(self.state.update_weight(delta=d)),
                )
            )
        return ft.Row(
            spacing=8,
            controls=pills,
        )

    def _refresh_timer_pills(self) -> None:
        presets = [30, 60, 90, 120]
        pills = []
        for sec in presets:
            is_active = (self.state.timer_running and self.state.timer_seconds_remaining == sec)
            pills.append(
                ft.OutlinedButton(
                    content=ft.Text(f"{sec}s", size=12, weight=ft.FontWeight.BOLD, no_wrap=True),
                    expand=True,
                    height=44,
                    tooltip=f"Start a {sec} second rest timer",
                    style=ft.ButtonStyle(
                        bgcolor=ft.Colors.PRIMARY_CONTAINER if is_active else None,
                        color=ft.Colors.ON_PRIMARY_CONTAINER if is_active else ft.Colors.ON_SURFACE,
                        shape=ft.RoundedRectangleBorder(radius=10),
                        padding=ft.Padding(4, 4, 4, 4),
                    ),
                    on_click=lambda _, s=sec: asyncio.create_task(self.state.set_timer_preset(s)),
                )
            )
        self.timer_pills_container.controls = pills
        self.timer_pills_container.spacing = 8

    def update_ui(self) -> None:
        if self.state.current_exercise.name != self._initial_exercise_name:
            self._has_selected_exercise = True
        # Reps & Badge
        self.reps_display.value = str(self.state.current_reps)
        self.set_badge.value = f"SET {self.state.current_set_number}"
        self.default_reps_btn.content = ft.Text(
            f"Default ({self.state.current_exercise.default_reps})",
            size=11,
        )

        # Weight input field and default button
        formatted_wt = self._format_weight(self.state.current_weight)
        if self.weight_input.value != formatted_wt:
            self.weight_input.value = formatted_wt
        formatted_default_wt = self._format_weight(self.state.current_exercise.default_weight)
        self.default_weight_btn.content = ft.Text(
            f"Default ({formatted_default_wt}kg)",
            size=11,
        )

        # Exercise Selector Card sync
        cur = self.state.current_exercise
        self.exercise_name_label.value = cur.name if self._has_selected_exercise else "Select Exercise"
        self.exercise_name_label.color = (
            ft.Colors.ON_SURFACE if self._has_selected_exercise else ft.Colors.ON_SURFACE_VARIANT
        )
        if not self._has_selected_exercise:
            self.exercise_category_label.value = "Tap to choose a movement"
        elif cur.default_weight == 0 or cur.category.lower() == "calisthenics":
            self.exercise_category_label.value = f"{cur.category} • {cur.default_reps} reps"
        else:
            formatted_default_wt = self._format_weight(cur.default_weight)
            self.exercise_category_label.value = f"{cur.category} • {cur.default_reps} reps @ {formatted_default_wt}kg"
        self.exercise_badge.visible = cur.is_custom and self._has_selected_exercise
        self.default_reps_btn.disabled = not self._has_selected_exercise
        self.default_weight_btn.disabled = not self._has_selected_exercise
        self.weight_input.disabled = not self._has_selected_exercise
        self.rep_card.disabled = not self._has_selected_exercise
        self.weight_card.disabled = not self._has_selected_exercise
        self.rep_card.opacity = 1 if self._has_selected_exercise else 0.55
        self.weight_card.opacity = 1 if self._has_selected_exercise else 0.55

        # Timer
        mins = self.state.timer_seconds_remaining // 60
        secs = self.state.timer_seconds_remaining % 60
        self.timer_display.value = f"{mins:02d}:{secs:02d}"

        if self.state.timer_running:
            self.timer_status_label.value = "Resting..."
            self.timer_toggle_btn.icon = ft.Icons.PAUSE
            self.timer_toggle_btn.tooltip = "Pause timer"
        elif self.state.timer_seconds_remaining > 0:
            self.timer_status_label.value = "Timer paused"
            self.timer_toggle_btn.icon = ft.Icons.PLAY_ARROW
            self.timer_toggle_btn.tooltip = "Resume timer"
        else:
            self.timer_status_label.value = "Rest Timer"
            self.timer_toggle_btn.icon = ft.Icons.PLAY_ARROW
        self.timer_toggle_btn.disabled = self.state.timer_seconds_remaining == 0
        self.timer_reset_btn.disabled = self.state.timer_seconds_remaining == 0

        self._refresh_timer_pills()
        self._sync_log_btn_state()

    def _build_layout(self) -> ft.Container:
        root = ft.Container(
            padding=ft.Padding(16, 8, 16, 8),
            expand=True,
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # 1. Exercise Selection Row (compact margin to eliminate top gap)
                    ft.Container(
                        content=ft.Row(
                            spacing=8,
                            alignment=ft.MainAxisAlignment.CENTER,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                self.exercise_selector_card,
                                ft.Container(
                                    content=ft.IconButton(
                                        icon=ft.Icons.ADD,
                                        icon_color=ft.Colors.PRIMARY,
                                        icon_size=22,
                                        size_constraints=ft.BoxConstraints(min_width=48, min_height=48),
                                        tooltip="Add Custom Exercise",
                                        on_click=self._open_add_dialog,
                                    ),
                                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                                    border_radius=12,
                                    padding=ft.Padding(0, 2, 0, 2),
                                ),
                            ],
                        ),
                    ),

                    # 2. Compact Rep Counter Card
                    ft.Card(
                        margin=0,
                        content=ft.Container(
                            padding=ft.Padding(16, 10, 16, 10),
                            content=ft.Column(
                                spacing=4,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    # Set Badge + Default Reset Row
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Container(
                                                content=self.set_badge,
                                                bgcolor=ft.Colors.PRIMARY_CONTAINER,
                                                padding=ft.Padding(10, 3, 10, 3),
                                                border_radius=8,
                                            ),
                                            self.default_reps_btn,
                                        ],
                                    ),
                                    # Stepper: [-] decreases by 1, Rep Number, [+] increases by 1
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=18,
                                        controls=[
                                            ft.IconButton(
                                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                                icon_size=32,
                                                size_constraints=ft.BoxConstraints(min_width=56, min_height=56),
                                                tooltip="Decrease 1 rep",
                                                on_click=lambda _: asyncio.create_task(self.state.update_reps(-1)),
                                            ),
                                            ft.Column(
                                                spacing=0,
                                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                                controls=[
                                                    self.reps_display,
                                                    ft.Text(
                                                        "REPS",
                                                        size=10,
                                                        weight=ft.FontWeight.BOLD,
                                                        color=ft.Colors.ON_SURFACE_VARIANT,
                                                    ),
                                                ],
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.ADD_CIRCLE,
                                                icon_size=32,
                                                icon_color=ft.Colors.PRIMARY,
                                                size_constraints=ft.BoxConstraints(min_width=56, min_height=56),
                                                tooltip="Increase 1 rep",
                                                on_click=lambda _: asyncio.create_task(self.state.update_reps(+1)),
                                            ),
                                        ],
                                    ),
                                ],
                            ),
                        ),
                    ),

                    # 3. Spacious Weight Stepper Card with Input Field & Pills
                    ft.Card(
                        margin=0,
                        content=ft.Container(
                            padding=ft.Padding(16, 8, 16, 8),
                            content=ft.Column(
                                spacing=4,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    # Header: Label on left, Default reset on right
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Row(
                                                spacing=4,
                                                controls=[
                                                    ft.Icon(ft.Icons.SCALE, size=15, color=ft.Colors.ON_SURFACE_VARIANT),
                                                    ft.Text("WEIGHT LIFTED", size=11, weight=ft.FontWeight.BOLD),
                                                ],
                                            ),
                                            self.default_weight_btn,
                                        ],
                                    ),
                                    # Center Stepper Row: [-] [ Input Field ] [+]
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.CENTER,
                                        spacing=14,
                                        controls=[
                                            ft.IconButton(
                                                icon=ft.Icons.REMOVE_CIRCLE_OUTLINE,
                                                icon_size=26,
                                                size_constraints=ft.BoxConstraints(min_width=48, min_height=48),
                                                tooltip="Decrease 2.5 kg",
                                                on_click=lambda _: asyncio.create_task(self.state.update_weight(-2.5)),
                                            ),
                                            self.weight_input,
                                            ft.IconButton(
                                                icon=ft.Icons.ADD_CIRCLE,
                                                icon_size=26,
                                                icon_color=ft.Colors.PRIMARY,
                                                size_constraints=ft.BoxConstraints(min_width=48, min_height=48),
                                                tooltip="Increase 2.5 kg",
                                                on_click=lambda _: asyncio.create_task(self.state.update_weight(+2.5)),
                                            ),
                                        ],
                                    ),
                                    # + and - Adjustment Pills (matches Rest Timer styling)
                                    self.weight_shortcuts,
                                ],
                            ),
                        ),
                    ),

                    # 4. Compact Rest Timer Card
                    ft.Card(
                        margin=0,
                        content=ft.Container(
                            padding=ft.Padding(16, 8, 16, 8),
                            content=ft.Column(
                                spacing=4,
                                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                controls=[
                                    # Header: Timer icon/status on left, Clock + Controls on right
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        controls=[
                                            ft.Row(
                                                spacing=4,
                                                controls=[
                                                    ft.Icon(ft.Icons.TIMER_OUTLINED, color=ft.Colors.SECONDARY, size=16),
                                                    self.timer_status_label,
                                                ],
                                            ),
                                            ft.Row(
                                                spacing=2,
                                                controls=[
                                                    self.timer_display,
                                                    self.timer_toggle_btn,
                                                    self.timer_reset_btn,
                                                ],
                                            ),
                                        ],
                                    ),
                                    # Timer Presets Row (Only the 4 pills)
                                    self.timer_pills_container,
                                ],
                            ),
                        ),
                    ),

                    # 5. Primary Action Button (Full Width)
                    ft.Container(
                        content=ft.Row(
                            controls=[self.log_btn],
                        ),
                    ),
                ],
            ),
        )
        self.rep_card = root.content.controls[1]
        self.weight_card = root.content.controls[2]
        return root
