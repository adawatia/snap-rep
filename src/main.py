"""SnapRep - Flet Android Application
Main entry point orchestrating state, themes, services, and modular views.
"""

import json
import flet as ft

try:
    from snaprep_dynamic_color import SnaprepDynamicColor
except ImportError:  # Local web previews can run before the native extension is installed.
    SnaprepDynamicColor = None

from config import APP_TITLE
from components.quick_tour import is_first_launch, show_quick_tour
from state import AppState
from storage import AppStorage
from theme import get_palette_themes, resolve_theme_mode
from views import ExercisesView, HistoryView, SettingsView, StatsView, TrackerView, WeightView


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
    first_launch = is_first_launch(storage)
    state = AppState(storage=storage)
    state.haptic = haptic
    state.clipboard = clipboard
    state.file_picker = file_picker

    # Theme Configuration
    dynamic_schemes = None
    last_palette = state.settings.get("theme_palette", "coral")

    def apply_theme():
        page.theme, page.dark_theme = get_palette_themes(
            state.settings.get("theme_palette", "coral"), dynamic_schemes
        )
        page.theme_mode = resolve_theme_mode(state.settings.get("theme_mode", "light"))

    apply_theme()

    dynamic_color = None
    dynamic_color_ready = True
    settings_view = None
    if (
        SnaprepDynamicColor is not None
        and not getattr(page, "web", False)
        and getattr(page, "platform", None) == ft.PagePlatform.ANDROID
    ):
        def on_dynamic_schemes(e):
            nonlocal dynamic_schemes
            payload = json.loads(e.data) if isinstance(e.data, str) else e.data
            dynamic_schemes = {
                "light": payload["light"], "dark": payload["dark"]
            } if payload and payload.get("available") else None
            if state.settings.get("theme_palette") == "material_you":
                apply_theme()
                if settings_view is not None:
                    settings_view.update_ui()
                page.update()

        dynamic_color = SnaprepDynamicColor(on_schemes=on_dynamic_schemes)
        page.services.append(dynamic_color)

    async def refresh_dynamic_color():
        nonlocal dynamic_color_ready
        if dynamic_color is None or not dynamic_color_ready:
            return
        try:
            await dynamic_color.refresh()
        except RuntimeError:
            # The preview host may not have the packaged Flutter extension.
            dynamic_color_ready = False

    # Initialize Views
    tracker_view = TrackerView(page, state)
    history_view = HistoryView(page, state)
    exercises_view = ExercisesView(page, state)
    stats_view = StatsView(page, state)
    weight_view = WeightView(page, state)
    settings_view = SettingsView(page, state, dynamic_schemes=lambda: dynamic_schemes)

    view_instances = [tracker_view, history_view, exercises_view, stats_view, weight_view]
    for index, view in enumerate(view_instances):
        view.root.key = f"tab-{index}"

    # Navigation & State Change Observer
    current_tab_index = 0
    tab_titles = ["Tracker", "History", "Exercises", "Stats", "Weight"]

    def on_state_changed():
        nonlocal last_palette
        palette = state.settings.get("theme_palette", "coral")
        apply_theme()
        if palette == "material_you" and palette != last_palette and dynamic_color and dynamic_color_ready and hasattr(page, "run_task"):
            page.run_task(refresh_dynamic_color)
        last_palette = palette
        active_view = settings_view if page.route == "/settings" else view_instances[current_tab_index]
        active_view.update_ui()
        page.update()

    state.subscribe(on_state_changed)

    tab_transition = ft.AnimatedSwitcher(
        content=view_instances[current_tab_index].root,
        expand=True,
        duration=180,
        reverse_duration=120,
        transition=ft.AnimatedSwitcherTransition.FADE,
        switch_in_curve=ft.AnimationCurve.EASE_OUT,
        switch_out_curve=ft.AnimationCurve.EASE_IN,
    )
    content_area = ft.Container(
        content=tab_transition,
        expand=True,
        padding=0,
    )

    def on_nav_change(e):
        nonlocal current_tab_index
        selected = e.control.selected_index
        if selected is None or not 0 <= selected < len(view_instances) or selected == current_tab_index:
            return
        current_tab_index = selected
        root_appbar.title = ft.Text(tab_titles[current_tab_index], weight=ft.FontWeight.BOLD, size=20)
        # Sync active tab to optimize background rendering
        tracker_view.is_active = (current_tab_index == 0)
        tab_transition.content = view_instances[current_tab_index].root
        view_instances[current_tab_index].update_ui()
        page.update()

    def on_page_resize(e):
        tracker_view.update_viewport_layout(getattr(e, "height", None) or getattr(page, "height", None))
        if current_tab_index == 0:
            page.update()

    page.on_resize = on_page_resize

    async def on_lifecycle(e):
        if e.state in (ft.AppLifecycleState.RESUME, ft.AppLifecycleState.RESTART):
            await refresh_dynamic_color()

    page.on_app_lifecycle_state_change = on_lifecycle

    navigation_bar = ft.NavigationBar(
        selected_index=0,
        on_change=on_nav_change,
        animation_duration=180,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        indicator_color=ft.Colors.SECONDARY_CONTAINER,
        elevation=0,
        destinations=[
            ft.NavigationBarDestination(icon=ft.Icons.FITNESS_CENTER_OUTLINED, selected_icon=ft.Icons.FITNESS_CENTER, label="Tracker"),
            ft.NavigationBarDestination(icon=ft.Icons.CALENDAR_MONTH_OUTLINED, selected_icon=ft.Icons.CALENDAR_MONTH, label="History"),
            ft.NavigationBarDestination(icon=ft.Icons.FORMAT_LIST_BULLETED, label="Exercises"),
            ft.NavigationBarDestination(icon=ft.Icons.INSIGHTS_OUTLINED, selected_icon=ft.Icons.INSIGHTS, label="Stats"),
            ft.NavigationBarDestination(icon=ft.Icons.MONITOR_WEIGHT_OUTLINED, selected_icon=ft.Icons.MONITOR_WEIGHT, label="Weight"),
        ],
    )

    root_appbar = ft.AppBar(
        automatically_imply_leading=False,
        title=ft.Text("Tracker", weight=ft.FontWeight.BOLD, size=20),
        center_title=False,
        bgcolor=ft.Colors.SURFACE_CONTAINER,
        actions=[ft.IconButton(icon=ft.Icons.SETTINGS_OUTLINED, tooltip="Settings",
                               on_click=lambda _: page.navigate("/settings"))],
    )

    root_view = ft.View(
        route="/", padding=0,
        controls=[ft.SafeArea(expand=True, content=content_area)],
        appbar=root_appbar, navigation_bar=navigation_bar,
    )
    settings_route = ft.View(
        route="/settings", padding=0,
        controls=[ft.SafeArea(expand=True, content=settings_view.root)],
        appbar=ft.AppBar(title=ft.Text("Settings", weight=ft.FontWeight.BOLD, size=20),
                         bgcolor=ft.Colors.SURFACE_CONTAINER),
    )

    def on_route_change(e=None):
        page.views = [root_view]
        if page.route == "/settings":
            settings_view.update_ui()
            page.views.append(settings_route)
        page.update()

    async def on_view_pop(e):
        await page.push_route("/")

    page.on_route_change = on_route_change
    page.on_view_pop = on_view_pop
    on_route_change()
    if dynamic_color and hasattr(page, "run_task"):
        page.run_task(refresh_dynamic_color)
    if first_launch and not state.settings.get("quick_tour_seen", False):
        show_quick_tour(page, state)


# App entry point - container refresh update
if __name__ == "__main__":
    ft.run(main)
