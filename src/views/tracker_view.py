"""Tracker view: Exercise selector, rep counter, weight input with adjustment pills, rest timer, and log button.
Arranged compactly to fit on mobile screens without vertical scroll.
"""

import asyncio
import flet as ft

from components.add_exercise_dialog import show_add_exercise_dialog
from state import AppState


class TrackerView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state

        # Reps display
        self.reps_display = ft.Text(
            str(self.state.current_reps),
            size=50,
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
            color=ft.Colors.OUTLINE,
        )
        self.timer_toggle_btn = ft.IconButton(
            icon=ft.Icons.PLAY_ARROW,
            icon_size=18,
            tooltip="Pause / Resume",
            on_click=lambda _: asyncio.create_task(self.state.toggle_timer()),
        )
        self.timer_pills_container = ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=[],
        )

        # Exercise dropdown
        self.exercise_dropdown = ft.Dropdown(
            options=self._build_exercise_options(),
            value=self.state.current_exercise.name,
            label="Select Exercise",
            label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
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
            content_padding=ft.Padding(14, 8, 14, 8),
            menu_height=300,
            dense=True,
            on_select=self._on_exercise_select,
            expand=True,
        )

        self._refresh_timer_pills()
        self._is_logging: bool = False  # synchronous in-flight guard
        self.log_btn = self._build_log_btn()
        self.root = self._build_layout()
        self.state.subscribe_timer(self._on_timer_tick)

    def _on_timer_tick(self) -> None:
        mins = self.state.timer_seconds_remaining // 60
        secs = self.state.timer_seconds_remaining % 60
        self.timer_display.value = f"{mins:02d}:{secs:02d}"
        # Also keep the log button state in sync during timer ticks
        self._sync_log_btn_state()
        if self.page:
            try:
                self.timer_display.update()
                self.log_btn.update()
            except Exception:
                pass

    def _format_weight(self, wt: float) -> str:
        return str(int(wt) if wt.is_integer() else round(wt, 1))

    def _build_exercise_options(self) -> list[ft.DropdownOption]:
        return [
            ft.DropdownOption(
                key=ex.name,
                text=f"{ex.name} • {ex.category}" + (" (Custom)" if ex.is_custom else ""),
            )
            for ex in self.state.exercises
        ]

    async def _on_exercise_select(self, e) -> None:
        if self.exercise_dropdown.value:
            await self.state.select_exercise(self.exercise_dropdown.value)
            self.page.update()

    def _open_add_dialog(self, e) -> None:
        show_add_exercise_dialog(
            self.page,
            self.state,
            on_success=lambda _: self.update_ui(),
        )

    def _on_weight_input_change(self, e) -> None:
        self.state.set_weight_from_text(e.control.value)

    def _is_log_blocked(self) -> bool:
        """Returns True when logging should be blocked (timer running OR already logging)."""
        return self._is_logging or (self.state.timer_running and self.state.timer_seconds_remaining > 0)

    def _sync_log_btn_state(self) -> None:
        """Sync the log button appearance to match current blocked/allowed state."""
        blocked = self._is_log_blocked()
        if blocked and self.state.timer_running:
            label = f"REST {self.state.timer_seconds_remaining}s (LOCKED)"
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
            height=48,
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
            ("-5kg", -5.0),
            ("-2.5kg", -2.5),
            ("+2.5kg", +2.5),
            ("+5kg", +5.0),
        ]
        pills = []
        for label, delta in steps:
            pills.append(
                ft.Container(
                    content=ft.Text(
                        label,
                        size=12,
                        weight=ft.FontWeight.BOLD,
                    ),
                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=ft.Padding(16, 6, 16, 6),
                    border_radius=8,
                    on_click=lambda _, d=delta: asyncio.create_task(self.state.update_weight(delta=d)),
                )
            )
        return ft.Row(
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
            controls=pills,
        )

    def _refresh_timer_pills(self) -> None:
        presets = [30, 60, 90, 120]
        pills = []
        for sec in presets:
            is_active = (self.state.timer_running and self.state.timer_seconds_remaining == sec)
            pills.append(
                ft.Container(
                    content=ft.Text(
                        f"{sec}s",
                        size=12,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_PRIMARY_CONTAINER if is_active else None,
                    ),
                    bgcolor=ft.Colors.PRIMARY_CONTAINER if is_active else ft.Colors.SURFACE_CONTAINER_HIGHEST,
                    padding=ft.Padding(16, 6, 16, 6),
                    border_radius=8,
                    on_click=lambda _, s=sec: asyncio.create_task(self.state.set_timer_preset(s)),
                )
            )
        self.timer_pills_container.controls = pills

    def update_ui(self) -> None:
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

        # Dropdown
        self.exercise_dropdown.options = self._build_exercise_options()
        self.exercise_dropdown.value = self.state.current_exercise.name

        # Timer
        mins = self.state.timer_seconds_remaining // 60
        secs = self.state.timer_seconds_remaining % 60
        self.timer_display.value = f"{mins:02d}:{secs:02d}"

        if self.state.timer_running:
            self.timer_status_label.value = "Resting..."
            self.timer_toggle_btn.icon = ft.Icons.PAUSE
        elif self.state.timer_seconds_remaining > 0:
            self.timer_status_label.value = "Timer paused"
            self.timer_toggle_btn.icon = ft.Icons.PLAY_ARROW
        else:
            self.timer_status_label.value = "Rest Timer"
            self.timer_toggle_btn.icon = ft.Icons.PLAY_ARROW

        self._refresh_timer_pills()
        self._sync_log_btn_state()

    def _build_layout(self) -> ft.Container:
        return ft.Container(
            padding=ft.Padding(14, 8, 14, 8),
            content=ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                controls=[
                    # 1. Exercise Selection Row (spaced down to prevent cropping under AppBar)
                    ft.Container(
                        margin=ft.Margin(0, 6, 0, 2),
                        content=ft.Row(
                            spacing=6,
                            alignment=ft.MainAxisAlignment.CENTER,
                            controls=[
                                self.exercise_dropdown,
                                ft.IconButton(
                                    icon=ft.Icons.ADD_CIRCLE_OUTLINE,
                                    icon_color=ft.Colors.PRIMARY,
                                    icon_size=26,
                                    tooltip="Add Custom Exercise",
                                    on_click=self._open_add_dialog,
                                ),
                            ],
                        ),
                    ),

                    # 2. Compact Rep Counter Card
                    ft.Card(
                        content=ft.Container(
                            padding=ft.Padding(12, 8, 12, 8),
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
                                                icon_size=40,
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
                                                        color=ft.Colors.OUTLINE,
                                                    ),
                                                ],
                                            ),
                                            ft.IconButton(
                                                icon=ft.Icons.ADD_CIRCLE,
                                                icon_size=40,
                                                icon_color=ft.Colors.PRIMARY,
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
                        content=ft.Container(
                            padding=ft.Padding(12, 8, 12, 8),
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
                                                    ft.Icon(ft.Icons.FITNESS_CENTER, size=15, color=ft.Colors.OUTLINE),
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
                                                icon_size=32,
                                                tooltip="Decrease 2.5 kg",
                                                on_click=lambda _: asyncio.create_task(self.state.update_weight(-2.5)),
                                            ),
                                            self.weight_input,
                                            ft.IconButton(
                                                icon=ft.Icons.ADD_CIRCLE,
                                                icon_size=32,
                                                icon_color=ft.Colors.PRIMARY,
                                                tooltip="Increase 2.5 kg",
                                                on_click=lambda _: asyncio.create_task(self.state.update_weight(+2.5)),
                                            ),
                                        ],
                                    ),
                                    # + and - Adjustment Pills (matches Rest Timer styling)
                                    self._build_weight_pills(),
                                ],
                            ),
                        ),
                    ),

                    # 4. Compact Rest Timer Card
                    ft.Card(
                        content=ft.Container(
                            padding=ft.Padding(12, 8, 12, 8),
                            content=ft.Column(
                                spacing=6,
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
                                                    ft.IconButton(
                                                        icon=ft.Icons.STOP,
                                                        icon_size=18,
                                                        icon_color=ft.Colors.ERROR,
                                                        tooltip="Reset Timer",
                                                        on_click=lambda _: asyncio.create_task(self.state.reset_timer()),
                                                    ),
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
                        padding=ft.Padding(0, 2, 0, 0),
                        content=ft.Row(
                            controls=[self.log_btn],
                        ),
                    ),
                ],
            ),
        )
