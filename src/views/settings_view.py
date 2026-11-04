"""Settings view: Preferences, rest timer defaults, theme selection,
haptic feedback, data export, and app info.
Streamlined and decluttered with the dedicated Exercises tab.
"""

import asyncio
import flet as ft

from components.backup_dialog import show_backup_dialog
from components.confirm_dialog import show_confirm_dialog
from components.export_dialog import show_export_dialog
from components.restore_dialog import show_restore_dialog
from config import APP_SUBTITLE, APP_TITLE, APP_VERSION, REST_TIMER_OPTIONS
from state import AppState
from theme import resolve_theme_mode


class SettingsView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state

        # 1. Appearance / Theme
        self.theme_dropdown = ft.Dropdown(
            label="Color theme",
            label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            value=self.state.settings.get("theme_mode", "light"),
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
            fill_color=ft.Colors.SURFACE_CONTAINER,
            content_padding=ft.Padding(14, 10, 14, 10),
            dense=True,
            menu_height=220,
            expand=True,
            options=[
                ft.DropdownOption("light", "Light · Coral and cream"),
                ft.DropdownOption("dark", "Dark · Coral and navy"),
                ft.DropdownOption("system", "Use device setting"),
            ],
            on_select=self._on_theme_select,
        )

        # 2. Rest Timer Preference
        default_rest_val = str(self.state.settings.get("default_rest_timer", 60))
        self.rest_timer_dropdown = ft.Dropdown(
            label="Rest after each set",
            label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.ON_SURFACE_VARIANT),
            value=default_rest_val,
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
            fill_color=ft.Colors.SURFACE_CONTAINER,
            content_padding=ft.Padding(14, 10, 14, 10),
            dense=True,
            menu_height=260,
            expand=True,
            options=[ft.DropdownOption(str(sec), label) for sec, label in REST_TIMER_OPTIONS],
            on_select=self._on_rest_timer_select,
        )

        # 3. Haptic Feedback Switch
        self.haptic_switch = ft.Switch(
            value=self.state.settings.get("haptic_feedback", True),
            on_change=self._on_haptic_toggle,
        )

        # 4. Status summary labels
        self.history_stat_text = ft.Text("", size=12, color=ft.Colors.ON_SURFACE_VARIANT)

        self.root = self._build_layout()
        self.update_ui()

    async def _on_theme_select(self, e) -> None:
        val = self.theme_dropdown.value or "light"
        self.state.update_setting("theme_mode", val)
        self.page.theme_mode = resolve_theme_mode(val)
        self.page.update()

    async def _on_rest_timer_select(self, e) -> None:
        try:
            val = int(self.rest_timer_dropdown.value or 60)
            self.state.update_setting("default_rest_timer", val)
            await self.state.trigger_haptic("click")
        except ValueError:
            pass

    async def _on_haptic_toggle(self, e) -> None:
        self.state.update_setting("haptic_feedback", self.haptic_switch.value)
        await self.state.trigger_haptic("click")

    def _on_clear_all_history(self, e) -> None:
        async def do_clear():
            await self.state.clear_history()
            self.update_ui()
            self.page.update()

        show_confirm_dialog(
            self.page,
            title="Clear All History?",
            message="This will permanently delete all recorded workout sets from your phone.",
            confirm_text="Clear All",
            is_destructive=True,
            on_confirm=do_clear,
        )

    def update_ui(self) -> None:
        self.theme_dropdown.value = self.state.settings.get("theme_mode", "light")
        self.rest_timer_dropdown.value = str(self.state.settings.get("default_rest_timer", 60))
        self.haptic_switch.value = self.state.settings.get("haptic_feedback", True)

        total_sets = len(self.state.history)
        self.history_stat_text.value = f"{total_sets} recorded set{'s' if total_sets != 1 else ''} in history"

    def _build_layout(self) -> ft.Container:
        def action_tile(icon, title, detail, on_click, destructive=False):
            color = ft.Colors.ERROR if destructive else ft.Colors.PRIMARY
            return ft.ListTile(
                leading=ft.Icon(icon, color=color, size=22),
                title=ft.Text(title, size=14, weight=ft.FontWeight.W_600, color=color if destructive else None),
                subtitle=ft.Text(detail, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                trailing=ft.Icon(ft.Icons.CHEVRON_RIGHT, size=18, color=ft.Colors.ON_SURFACE_VARIANT),
                content_padding=ft.Padding(12, 4, 12, 4),
                min_height=64,
                on_click=on_click,
            )

        def section(title, controls):
            return ft.Column(
                spacing=8,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    ft.Text(title, size=16, weight=ft.FontWeight.BOLD),
                    ft.Container(
                        bgcolor=ft.Colors.SURFACE_CONTAINER,
                        border_radius=16,
                        padding=ft.Padding(14, 14, 14, 14),
                        content=ft.Column(
                            spacing=14,
                            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                            controls=controls,
                        ),
                    ),
                ],
            )

        return ft.Container(
            padding=ft.Padding(16, 14, 16, 24),
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=22,
                horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
                controls=[
                    section("Appearance", [
                        ft.Text("Choose how SnapRep looks on this device.", size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Row(controls=[self.theme_dropdown]),
                    ]),
                    section("Workout", [
                        ft.Row(controls=[self.rest_timer_dropdown]),
                        ft.Text("Starts automatically after you log a set.", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                        ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            vertical_alignment=ft.CrossAxisAlignment.CENTER,
                            controls=[
                                ft.Column(spacing=3, expand=True, controls=[
                                    ft.Text("Haptic feedback", size=14, weight=ft.FontWeight.W_600),
                                    ft.Text("Vibration for reps and timer alerts", size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                                ]),
                                self.haptic_switch,
                            ],
                        ),
                    ]),
                    ft.Column(spacing=8, horizontal_alignment=ft.CrossAxisAlignment.STRETCH, controls=[
                        ft.Text("Your data", size=16, weight=ft.FontWeight.BOLD),
                        self.history_stat_text,
                        ft.Container(
                            bgcolor=ft.Colors.SURFACE_CONTAINER,
                            border_radius=16,
                            content=ft.Column(spacing=0, controls=[
                                action_tile(
                                    ft.Icons.BACKUP_OUTLINED, "Back up data", "Save workouts and exercises as JSON",
                                    lambda _: asyncio.create_task(show_backup_dialog(self.page, self.state)),
                                ),
                                action_tile(
                                    ft.Icons.RESTORE, "Restore data", "Import a saved JSON backup",
                                    lambda _: asyncio.create_task(show_restore_dialog(self.page, self.state)),
                                ),
                                action_tile(
                                    ft.Icons.TABLE_CHART_OUTLINED, "Export history", "Save workout sets as CSV",
                                    lambda _: asyncio.create_task(show_export_dialog(self.page, self.state)),
                                ),
                            ]),
                        ),
                        action_tile(
                            ft.Icons.DELETE_OUTLINE, "Clear workout history", "Permanently remove recorded sets",
                            self._on_clear_all_history, destructive=True,
                        ),
                    ]),
                    ft.Text(
                        f"{APP_TITLE} v{APP_VERSION} · {APP_SUBTITLE}",
                        size=11,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            ),
        )
