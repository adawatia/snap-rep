"""Theme configuration and color palettes for SnapRep."""

import flet as ft

PALETTES = {
    "coral": "Coral & Navy",
    "catppuccin": "Catppuccin",
    "gruvbox": "Gruvbox",
    "material_you": "Material You",
}

# Published Catppuccin Latte/Mocha and Gruvbox colors, assigned to Material roles.
_SCHEMES = {
    "catppuccin": {
        "light": dict(primary="#8839EF", on_primary="#FFFFFF", primary_container="#EADAFB", on_primary_container="#4C1D95", secondary="#04A5E5", on_secondary="#1E1E2E", secondary_container="#D8F1FB", on_secondary_container="#075985", tertiary="#179299", on_tertiary="#11111B", tertiary_container="#D5F1EE", on_tertiary_container="#075C60", surface="#EFF1F5", on_surface="#4C4F69", on_surface_variant="#5C5F77", surface_container="#E6E9EF", surface_container_high="#DCE0E8", surface_container_highest="#CCD0DA", outline="#6C6F85", outline_variant="#BCC0CC"),
        "dark": dict(primary="#CBA6F7", on_primary="#35204D", primary_container="#51376B", on_primary_container="#F0DBFF", secondary="#89DCEB", on_secondary="#12343B", secondary_container="#24505A", on_secondary_container="#C8F4FB", tertiary="#94E2D5", on_tertiary="#153D37", tertiary_container="#2B584F", on_tertiary_container="#C9FAEF", surface="#1E1E2E", on_surface="#CDD6F4", on_surface_variant="#BAC2DE", surface_container="#313244", surface_container_high="#45475A", surface_container_highest="#585B70", outline="#A6ADC8", outline_variant="#6C7086"),
    },
    "gruvbox": {
        "light": dict(primary="#9D0006", on_primary="#FFFFFF", primary_container="#F2D5CC", on_primary_container="#5F0003", secondary="#076678", on_secondary="#FFFFFF", secondary_container="#D5E8E5", on_secondary_container="#06434E", tertiary="#8F3F71", on_tertiary="#FFFFFF", tertiary_container="#EDD9E4", on_tertiary_container="#582243", surface="#FBF1C7", on_surface="#3C3836", on_surface_variant="#504945", surface_container="#F2E5BC", surface_container_high="#EBDBB2", surface_container_highest="#D5C4A1", outline="#665C54", outline_variant="#BDAE93"),
        "dark": dict(primary="#FB4934", on_primary="#3C1410", primary_container="#692B25", on_primary_container="#FFDAD1", secondary="#83A598", on_secondary="#172D27", secondary_container="#355348", on_secondary_container="#D0E8DE", tertiary="#D3869B", on_tertiary="#361E27", tertiary_container="#583845", on_tertiary_container="#F6D9E1", surface="#282828", on_surface="#EBDBB2", on_surface_variant="#D5C4A1", surface_container="#3C3836", surface_container_high="#504945", surface_container_highest="#665C54", outline="#BDAE93", outline_variant="#7C6F64"),
    },
    "material_you": {
        "light": dict(primary="#6750A4", on_primary="#FFFFFF", primary_container="#EADDFF", on_primary_container="#21005D", secondary="#625B71", on_secondary="#FFFFFF", secondary_container="#E8DEF8", on_secondary_container="#1D192B", tertiary="#7D5260", on_tertiary="#FFFFFF", tertiary_container="#FFD8E4", on_tertiary_container="#31111D", surface="#FFFBFE", on_surface="#1C1B1F", on_surface_variant="#49454F", surface_container="#F3EDF7", surface_container_high="#ECE6F0", surface_container_highest="#E6E0E9", outline="#79747E", outline_variant="#CAC4D0"),
        "dark": dict(primary="#D0BCFF", on_primary="#381E72", primary_container="#4F378B", on_primary_container="#EADDFF", secondary="#CCC2DC", on_secondary="#332D41", secondary_container="#4A4458", on_secondary_container="#E8DEF8", tertiary="#EFB8C8", on_tertiary="#492532", tertiary_container="#633B48", on_tertiary_container="#FFD8E4", surface="#141218", on_surface="#E6E0E9", on_surface_variant="#CAC4D0", surface_container="#211F26", surface_container_high="#2B2930", surface_container_highest="#36343B", outline="#938F99", outline_variant="#49454F"),
    },
}


def _make_theme(colors: dict) -> ft.Theme:
    return ft.Theme(
        color_scheme=ft.ColorScheme(**colors),
        card_bgcolor=colors["surface_container"],
        scaffold_bgcolor=colors["surface"],
        scrollbar_theme=ft.ScrollbarTheme(
            thumb_color=colors["primary"], thickness=4, radius=8,
            thumb_visibility=False, track_visibility=False, interactive=True,
        ),
    )


def get_palette_themes(palette: str, dynamic_schemes: dict | None = None) -> tuple[ft.Theme, ft.Theme]:
    """Return light and dark themes, using Material fallback when OS colors are absent."""
    if palette not in PALETTES or palette == "coral":
        return get_light_theme(), get_dark_theme()
    light = _SCHEMES[palette]["light"]
    dark = _SCHEMES[palette]["dark"]
    if palette == "material_you" and dynamic_schemes:
        light = {**light, **dynamic_schemes.get("light", {})}
        dark = {**dark, **dynamic_schemes.get("dark", {})}
    return _make_theme(light), _make_theme(dark)

# Warm coral actions over layered deep navy surfaces.
COLOR_PRIMARY = "#FF907E"
COLOR_ON_PRIMARY = "#3D1915"
COLOR_PRIMARY_CONTAINER = "#65352F"
COLOR_ON_PRIMARY_CONTAINER = "#FFE0D8"

COLOR_SECONDARY = "#B5CFD8"
COLOR_ON_SECONDARY = "#173642"
COLOR_SECONDARY_CONTAINER = "#2C4B59"
COLOR_ON_SECONDARY_CONTAINER = "#D5EBF0"

COLOR_TERTIARY = "#F0BE78"
COLOR_ON_TERTIARY = "#49300D"
COLOR_TERTIARY_CONTAINER = "#634B2A"
COLOR_ON_TERTIARY_CONTAINER = "#FFE2B7"

COLOR_SURFACE_DARK = "#0D1B28"
COLOR_CONTAINER_DARK = "#172838"
COLOR_CONTAINER_HIGH_DARK = "#203446"
COLOR_CONTAINER_HIGHEST_DARK = "#2A4152"
COLOR_ON_SURFACE_DARK = "#F3F6F7"
COLOR_ON_SURFACE_VARIANT_DARK = "#C2D0D7"
COLOR_OUTLINE_DARK = "#A1B4BE"
COLOR_OUTLINE_VARIANT_DARK = "#496170"

# Warm off-white canvas with navy text and a deeper coral action color.
COLOR_PRIMARY_LIGHT = "#AA3934"
COLOR_ON_PRIMARY_LIGHT = "#FFFFFF"
COLOR_PRIMARY_CONTAINER_LIGHT = "#FCE4DC"
COLOR_ON_PRIMARY_CONTAINER_LIGHT = "#732B27"

COLOR_SECONDARY_LIGHT = "#375D6E"
COLOR_ON_SECONDARY_LIGHT = "#FFFFFF"
COLOR_SECONDARY_CONTAINER_LIGHT = "#DCEBF0"
COLOR_ON_SECONDARY_CONTAINER_LIGHT = "#244957"

COLOR_TERTIARY_LIGHT = "#8B541D"
COLOR_ON_TERTIARY_LIGHT = "#FFFFFF"
COLOR_TERTIARY_CONTAINER_LIGHT = "#F6E5CB"
COLOR_ON_TERTIARY_CONTAINER_LIGHT = "#603B14"
COLOR_SURFACE_LIGHT = "#F8F5F1"
COLOR_CONTAINER_LIGHT = "#FFFCF8"
COLOR_CONTAINER_HIGH_LIGHT = "#F4EEE8"
COLOR_CONTAINER_HIGHEST_LIGHT = "#EDE5DD"
COLOR_ON_SURFACE_LIGHT = "#192B38"
COLOR_ON_SURFACE_VARIANT_LIGHT = "#4B606B"
COLOR_OUTLINE_LIGHT = "#637783"
COLOR_OUTLINE_VARIANT_LIGHT = "#CEC8C2"


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
            on_tertiary=COLOR_ON_TERTIARY_LIGHT,
            tertiary_container=COLOR_TERTIARY_CONTAINER_LIGHT,
            on_tertiary_container=COLOR_ON_TERTIARY_CONTAINER_LIGHT,
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
