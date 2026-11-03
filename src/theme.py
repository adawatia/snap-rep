"""Theme configuration and color palettes for SnapRep."""

import flet as ft

# Modern Athletic Indigo & Obsidian Dark Tokens
COLOR_PRIMARY = "#6366F1"         # Electric Indigo (matches brand icon)
COLOR_ON_PRIMARY = "#FFFFFF"
COLOR_PRIMARY_CONTAINER = "#312E81"
COLOR_ON_PRIMARY_CONTAINER = "#E0E7FF"

COLOR_SECONDARY = "#38BDF8"       # Crisp Sky / Cyan Accent
COLOR_ON_SECONDARY = "#082F49"
COLOR_SECONDARY_CONTAINER = "#0C4A6E"
COLOR_ON_SECONDARY_CONTAINER = "#BAE6FD"

COLOR_TERTIARY = "#F59E0B"        # Warm Amber (for PR stars / badges)
COLOR_ON_TERTIARY = "#451A03"
COLOR_TERTIARY_CONTAINER = "#78350F"
COLOR_ON_TERTIARY_CONTAINER = "#FEF3C7"

COLOR_SURFACE_DARK = "#0B0F17"    # Deep Obsidian Slate
COLOR_CONTAINER_DARK = "#161D29"  # Elevated Slate Card
COLOR_CONTAINER_HIGH_DARK = "#222D3D"
COLOR_CONTAINER_HIGHEST_DARK = "#2D3B4E"
COLOR_ON_SURFACE_DARK = "#F8FAFC" # Crisp White (high-contrast WCAG AAA)
COLOR_ON_SURFACE_VARIANT_DARK = "#CBD5E1" # Highly legible secondary text
COLOR_OUTLINE_DARK = "#94A3B8"    # Clear visible borders
COLOR_OUTLINE_VARIANT_DARK = "#475569"

# Light Theme Tokens
COLOR_PRIMARY_LIGHT = "#4F46E5"   # Athletic Indigo (consistent brand)
COLOR_ON_PRIMARY_LIGHT = "#FFFFFF"
COLOR_PRIMARY_CONTAINER_LIGHT = "#E0E7FF"
COLOR_ON_PRIMARY_CONTAINER_LIGHT = "#1E1B4B"

COLOR_SECONDARY_LIGHT = "#0284C7" # Sky Blue
COLOR_ON_SECONDARY_LIGHT = "#FFFFFF"
COLOR_SECONDARY_CONTAINER_LIGHT = "#E0F2FE"
COLOR_ON_SECONDARY_CONTAINER_LIGHT = "#0369A1"

COLOR_TERTIARY_LIGHT = "#D97706"  # Amber
COLOR_SURFACE_LIGHT = "#F8FAFC"
COLOR_CONTAINER_LIGHT = "#FFFFFF"
COLOR_CONTAINER_HIGH_LIGHT = "#F1F5F9"
COLOR_CONTAINER_HIGHEST_LIGHT = "#E2E8F0"
COLOR_ON_SURFACE_LIGHT = "#0F172A" # High-contrast deep slate text
COLOR_ON_SURFACE_VARIANT_LIGHT = "#475569" # Legible secondary text
COLOR_OUTLINE_LIGHT = "#64748B"
COLOR_OUTLINE_VARIANT_LIGHT = "#CBD5E1"


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
            on_surface=COLOR_ON_SURFACE_DARK,
            on_surface_variant=COLOR_ON_SURFACE_VARIANT_DARK,
            surface_container=COLOR_CONTAINER_DARK,
            surface_container_high=COLOR_CONTAINER_HIGH_DARK,
            surface_container_highest=COLOR_CONTAINER_HIGHEST_DARK,
            outline=COLOR_OUTLINE_DARK,
            outline_variant=COLOR_OUTLINE_VARIANT_DARK,
        ),
        card_bgcolor=COLOR_CONTAINER_DARK,
        scaffold_bgcolor=COLOR_SURFACE_DARK,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=COLOR_PRIMARY,
            thickness=4,
            radius=8,
            thumb_visibility=False,
            track_visibility=False,
            interactive=True,
        ),
    )


def get_light_theme() -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(
            primary=COLOR_PRIMARY_LIGHT,
            on_primary=COLOR_ON_PRIMARY_LIGHT,
            primary_container=COLOR_PRIMARY_CONTAINER_LIGHT,
            on_primary_container=COLOR_ON_PRIMARY_CONTAINER_LIGHT,
            secondary=COLOR_SECONDARY_LIGHT,
            on_secondary=COLOR_ON_SECONDARY_LIGHT,
            secondary_container=COLOR_SECONDARY_CONTAINER_LIGHT,
            on_secondary_container=COLOR_ON_SECONDARY_CONTAINER_LIGHT,
            tertiary=COLOR_TERTIARY_LIGHT,
            surface=COLOR_SURFACE_LIGHT,
            on_surface=COLOR_ON_SURFACE_LIGHT,
            on_surface_variant=COLOR_ON_SURFACE_VARIANT_LIGHT,
            surface_container=COLOR_CONTAINER_LIGHT,
            surface_container_high=COLOR_CONTAINER_HIGH_LIGHT,
            surface_container_highest=COLOR_CONTAINER_HIGHEST_LIGHT,
            outline=COLOR_OUTLINE_LIGHT,
            outline_variant=COLOR_OUTLINE_VARIANT_LIGHT,
        ),
        card_bgcolor=COLOR_CONTAINER_LIGHT,
        scaffold_bgcolor=COLOR_SURFACE_LIGHT,
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=COLOR_PRIMARY_LIGHT,
            thickness=4,
            radius=8,
            thumb_visibility=False,
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
