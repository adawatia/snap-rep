"""Settings view: Preferences, rest timer defaults, theme selection,
haptic feedback, data export, and app info.
Streamlined and decluttered with the dedicated Exercises tab.
"""

import asyncio
import flet as ft

from components.export_dialog import show_export_dialog
from config import APP_SUBTITLE, APP_TITLE, APP_VERSION, REST_TIMER_OPTIONS
from state import AppState
from theme import resolve_theme_mode


class SettingsView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state

        # 1. Appearance / Theme
        self.theme_dropdown = ft.Dropdown(
            label="Theme Mode",
            label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
            value=self.state.settings.get("theme_mode", "dark"),
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
            options=[
                ft.DropdownOption("dark", "Dark Mode (Stealth & Neon Volt)"),
                ft.DropdownOption("light", "Light Mode (Athletic Emerald)"),
                ft.DropdownOption("system", "Follow System Theme"),
            ],
            on_select=self._on_theme_select,
        )

        # 2. Rest Timer Preference
        default_rest_val = str(self.state.settings.get("default_rest_timer", 60))
        self.rest_timer_dropdown = ft.Dropdown(
            label="Default Rest Timer",
            label_style=ft.TextStyle(size=11, weight=ft.FontWeight.BOLD, color=ft.Colors.OUTLINE),
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
            options=[ft.DropdownOption(str(sec), label) for sec, label in REST_TIMER_OPTIONS],
            on_select=self._on_rest_timer_select,
        )

        # 3. Haptic Feedback Switch
        self.haptic_switch = ft.Switch(
            value=self.state.settings.get("haptic_feedback", True),
            on_change=self._on_haptic_toggle,
        )

        # 4. Status summary labels
        self.history_stat_text = ft.Text("", size=12, color=ft.Colors.OUTLINE)
        self.exercises_stat_text = ft.Text("", size=12, color=ft.Colors.OUTLINE)

        self.root = self._build_layout()
        self.update_ui()

    async def _on_theme_select(self, e) -> None:
        val = self.theme_dropdown.value or "dark"
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

    def update_ui(self) -> None:
        self.theme_dropdown.value = self.state.settings.get("theme_mode", "dark")
        self.rest_timer_dropdown.value = str(self.state.settings.get("default_rest_timer", 60))
        self.haptic_switch.value = self.state.settings.get("haptic_feedback", True)

        total_sets = len(self.state.history)
        self.history_stat_text.value = f"{total_sets} recorded set{'s' if total_sets != 1 else ''} in history"

        total_ex = len(self.state.exercises)
        custom_ex = sum(1 for e in self.state.exercises if e.is_custom)
        self.exercises_stat_text.value = (
            f"{total_ex} exercises ({custom_ex} custom) configured in your library."
        )

    def _build_layout(self) -> ft.Container:
        return ft.Container(
            padding=16,
            expand=True,
            content=ft.Column(
                scroll=ft.ScrollMode.ADAPTIVE,
                spacing=16,
                controls=[
                    # Page Title
                    ft.Text("Settings", size=22, weight=ft.FontWeight.BOLD),

                    # 1. Appearance Card
                    ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=10,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.PALETTE_OUTLINED, color=ft.Colors.PRIMARY, size=20),
                                            ft.Text("Appearance", size=15, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    self.theme_dropdown,
                                ],
                            ),
                        )
                    ),

                    # 2. Workout & Rest Timer Preferences Card
                    ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=14,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.TIMER_OUTLINED, color=ft.Colors.SECONDARY, size=20),
                                            ft.Text("Workout & Rest Timer", size=15, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    ft.Column(
                                        spacing=4,
                                        controls=[
                                            self.rest_timer_dropdown,
                                            ft.Text(
                                                "Auto-initiates this rest period immediately after logging a set.",
                                                size=11,
                                                color=ft.Colors.OUTLINE,
                                            ),
                                        ],
                                    ),
                                    ft.Row(
                                        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                                        vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                        controls=[
                                            ft.Column(
                                                spacing=2,
                                                expand=True,
                                                controls=[
                                                    ft.Text("Haptic Feedback", weight=ft.FontWeight.BOLD, size=14),
                                                    ft.Text(
                                                        "Tactile vibrations on counter steppers & timer completion.",
                                                        size=11,
                                                        color=ft.Colors.OUTLINE,
                                                    ),
                                                ],
                                            ),
                                            self.haptic_switch,
                                        ],
                                    ),
                                ],
                            ),
                        )
                    ),

                    # 3. Exercise Library Management Shortcut Card
                    ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=8,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.FORMAT_LIST_BULLETED, color=ft.Colors.TERTIARY, size=20),
                                            ft.Text("Exercise Library", size=15, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    self.exercises_stat_text,
                                    ft.Text(
                                        "Manage your exercises, customize default reps/weights, and add custom movements in the Exercises tab.",
                                        size=12,
                                        color=ft.Colors.OUTLINE,
                                    ),
                                ],
                            ),
                        )
                    ),

                    # 4. Data Management & Export Card
                    ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=10,
                                controls=[
                                    ft.Row(
                                        spacing=8,
                                        controls=[
                                            ft.Icon(ft.Icons.STORAGE_OUTLINED, color=ft.Colors.PRIMARY, size=20),
                                            ft.Text("Data Management", size=15, weight=ft.FontWeight.BOLD),
                                        ],
                                    ),
                                    self.history_stat_text,
                                    ft.Button(
                                        content=ft.Row(
                                            spacing=8,
                                            controls=[
                                                ft.Icon(ft.Icons.DOWNLOAD, size=18),
                                                ft.Text("Export History to CSV", weight=ft.FontWeight.BOLD),
                                            ],
                                        ),
                                        on_click=lambda _: asyncio.create_task(
                                            show_export_dialog(self.page, self.state)
                                        ),
                                    ),
                                    ft.Text(
                                        "Exports your complete workout set history with timestamps and volumes.",
                                        size=11,
                                        color=ft.Colors.OUTLINE,
                                    ),
                                ],
                            ),
                        )
                    ),

                    # 5. App Info Card
                    ft.Card(
                        content=ft.Container(
                            padding=16,
                            content=ft.Column(
                                spacing=4,
                                controls=[
                                    ft.Row(
                                        spacing=6,
                                        controls=[
                                            ft.Icon(ft.Icons.FITNESS_CENTER, size=16, color=ft.Colors.PRIMARY),
                                            ft.Text(f"{APP_TITLE} v{APP_VERSION}", weight=ft.FontWeight.BOLD, size=14),
                                        ],
                                    ),
                                    ft.Text(
                                        f"{APP_SUBTITLE} Built with Flet & Material 3 for Android.",
                                        size=12,
                                        color=ft.Colors.OUTLINE,
                                    ),
                                ],
                            ),
                        )
                    ),
                ],
            ),
        )
