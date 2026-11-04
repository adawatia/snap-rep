"""SnapRep - Flet Android Application
Main entry point orchestrating state, themes, services, and modular views.
"""

import flet as ft

from config import APP_TITLE
from state import AppState
from storage import AppStorage
from theme import get_dark_theme, get_light_theme, resolve_theme_mode
from views import ExercisesView, HistoryView, SettingsView, StatsView, TrackerView


async def main(page: ft.Page):
    page.title = APP_TITLE
    page.padding = 0

    # Initialize Services
    haptic = ft.HapticFeedback()
    clipboard = ft.Clipboard()
    file_picker = ft.FilePicker()
    page.services.extend([haptic, clipboard, file_picker])

    # Initialize State
    storage = AppStorage()
    state = AppState(storage=storage)
    state.haptic = haptic
    state.clipboard = clipboard
    state.file_picker = file_picker

    # Theme Configuration
    page.dark_theme = get_dark_theme()
    page.theme = get_light_theme()
    page.theme_mode = resolve_theme_mode(state.settings.get("theme_mode", "light"))

    # Initialize Views
    tracker_view = TrackerView(page, state)
    history_view = HistoryView(page, state)
    exercises_view = ExercisesView(page, state)
    stats_view = StatsView(page, state)
    settings_view = SettingsView(page, state)

    view_instances = [tracker_view, history_view, exercises_view, stats_view, settings_view]

    # Navigation & State Change Observer
    current_tab_index = 0
    tab_titles = ["Tracker", "History", "Exercises", "Stats", "Settings"]

    def on_state_changed():
        active_view = view_instances[current_tab_index]
        active_view.update_ui()
        page.update()

    state.subscribe(on_state_changed)

    content_area = ft.Container(
        content=view_instances[current_tab_index].root,
        expand=True,
        padding=0,
    )

    def on_nav_change(e):
        nonlocal current_tab_index
        current_tab_index = e.control.selected_index
        page.appbar.title = ft.Text(tab_titles[current_tab_index], weight=ft.FontWeight.BOLD, size=20)
        # Sync active tab to optimize background rendering
        tracker_view.is_active = (current_tab_index == 0)
        content_area.content = view_instances[current_tab_index].root
        view_instances[current_tab_index].update_ui()
        page.update()

    def on_page_resize(e):
        tracker_view.update_viewport_layout(e.height)
        if current_tab_index == 0:
            page.update()

    page.on_resize = on_page_resize

    page.navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        indicator_color=ft.Colors.SECONDARY_CONTAINER,
        elevation=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.FITNESS_CENTER, label="Tracker"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH, label="History"),
            ft.NavigationBarDestination(icon=ft.Icons.FORMAT_LIST_BULLETED, label="Exercises"),
            ft.NavigationBarDestination(icon=ft.Icons.INSIGHTS, label="Stats"),
            ft.NavigationBarDestination(icon=ft.Icons.SETTINGS, label="Settings"),
        ],
    )

    page.appbar = ft.AppBar(
        automatically_imply_leading=False,
        title=ft.Text("Tracker", weight=ft.FontWeight.BOLD, size=20),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
    )

    # Initial Mount with Android SafeArea
    page.add(
        ft.SafeArea(
            expand=True,
            content=content_area,
        )
    )


# App entry point - container refresh update
if __name__ == "__main__":
    ft.run(main)
