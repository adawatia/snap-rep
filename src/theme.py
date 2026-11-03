"""Theme configuration and color palettes for SnapRep."""

import flet as ft

# High-Performance Athletic Color Tokens
COLOR_PRIMARY = "#CCFF00"         # Neon Volt / Electric Lime
COLOR_ON_PRIMARY = "#0E1300"
COLOR_PRIMARY_CONTAINER = "#223300"
COLOR_ON_PRIMARY_CONTAINER = "#D9FF33"

COLOR_SECONDARY = "#00E5FF"       # Electric Cyan
COLOR_ON_SECONDARY = "#001F24"
COLOR_SECONDARY_CONTAINER = "#00363D"
COLOR_ON_SECONDARY_CONTAINER = "#80F2FF"

COLOR_TERTIARY = "#FF8400"        # Sunset Amber
COLOR_ON_TERTIARY = "#261000"
COLOR_TERTIARY_CONTAINER = "#4A2300"
COLOR_ON_TERTIARY_CONTAINER = "#FFB87A"

COLOR_SURFACE_DARK = "#0E1217"
COLOR_CONTAINER_DARK = "#161B22"
COLOR_CONTAINER_HIGH_DARK = "#1E252F"
COLOR_CONTAINER_HIGHEST_DARK = "#28323F"
COLOR_OUTLINE_DARK = "#4B5563"

# Light Theme Tokens
COLOR_PRIMARY_LIGHT = "#059669"   # Athletic Emerald
COLOR_SECONDARY_LIGHT = "#0284C7" # Sky Blue
COLOR_TERTIARY_LIGHT = "#D97706"
COLOR_SURFACE_LIGHT = "#F8FAFC"
COLOR_CONTAINER_LIGHT = "#FFFFFF"
COLOR_CONTAINER_HIGH_LIGHT = "#F1F5F9"
COLOR_CONTAINER_HIGHEST_LIGHT = "#E2E8F0"
COLOR_OUTLINE_LIGHT = "#94A3B8"


def get_dark_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=COLOR_PRIMARY,
            on_primary=COLOR_ON_PRIMARY,
            primary_container=COLOR_PRIMARY_CONTAINER,
            on_primary_container=COLOR_ON_PRIMARY_CONTAINER,
            secondary=COLOR_SECONDARY,
            on_secondary=COLOR_ON_SECONDARY,
            secondary_container=COLOR_SECONDARY_CONTAINER,
            on_secondary_container=COLOR_ON_SECONDARY_CONTAINER,
            tertiary=COLOR_TERTIARY,
            on_tertiary=COLOR_ON_TERTIARY,
            tertiary_container=COLOR_TERTIARY_CONTAINER,
            on_tertiary_container=COLOR_ON_TERTIARY_CONTAINER,
            surface=COLOR_SURFACE_DARK,
            surface_container=COLOR_CONTAINER_DARK,
            surface_container_high=COLOR_CONTAINER_HIGH_DARK,
            surface_container_highest=COLOR_CONTAINER_HIGHEST_DARK,
            outline=COLOR_OUTLINE_DARK,
        ),
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=COLOR_PRIMARY,
            thickness=4,
            radius=8,
            thumb_visibility=False,  # Adaptive: only visible during scrolling
            track_visibility=False,
            interactive=True,
        ),
    )


def get_light_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=COLOR_PRIMARY_LIGHT,
            on_primary="#FFFFFF",
            primary_container="#D1FAE5",
            on_primary_container="#065F46",
            secondary=COLOR_SECONDARY_LIGHT,
            on_secondary="#FFFFFF",
            secondary_container="#E0F2FE",
            on_secondary_container="#0369A1",
            tertiary=COLOR_TERTIARY_LIGHT,
            surface=COLOR_SURFACE_LIGHT,
            surface_container=COLOR_CONTAINER_LIGHT,
            surface_container_high=COLOR_CONTAINER_HIGH_LIGHT,
            surface_container_highest=COLOR_CONTAINER_HIGHEST_LIGHT,
            outline=COLOR_OUTLINE_LIGHT,
        ),
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=COLOR_PRIMARY_LIGHT,
            thickness=4,
            radius=8,
            thumb_visibility=False,  # Adaptive: only visible during scrolling
            track_visibility=False,
            interactive=True,
        ),
    )


def resolve_theme_mode(mode_name: str) -> ft.ThemeMode:
    clean = (mode_name or "").lower().strip()
    if clean == "light":
        return ft.ThemeMode.LIGHT
    elif clean == "dark":
        return ft.ThemeMode.DARK
    return ft.ThemeMode.SYSTEM
