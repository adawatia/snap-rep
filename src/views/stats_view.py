"""Stats view: Comprehensive workout statistics, volume analysis, and personal records (PRs)."""

import flet as ft
from state import AppState


class StatsView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state

        self.stats_column = ft.Column(scroll=ft.ScrollMode.AUTO, expand=True, spacing=14)
        self.root = ft.Container(padding=16, expand=True, content=self.stats_column)
        self.update_ui()

    def update_ui(self) -> None:
        cards: list[ft.Control] = []
        if not self.state.history:
            cards.append(
                ft.Container(
                    padding=40,
                    alignment=ft.Alignment.CENTER,
                    content=ft.Column(
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        spacing=12,
                        controls=[
                            ft.Icon(ft.Icons.INSIGHTS, size=54, color=ft.Colors.OUTLINE),
                            ft.Text("No Workout Statistics Yet", size=17, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Log your workout sets to track total volume, sets, reps, and unlock personal records (PRs).",
                                size=13,
                                color=ft.Colors.OUTLINE,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                )
            )
            self.stats_column.controls = cards
            return

        # 1. High-Level Aggregates
        total_sets = len(self.state.history)
        total_reps = sum(r.reps for r in self.state.history)
        total_volume = sum(round(r.reps * r.weight_kg, 2) for r in self.state.history)
        unique_days = len({r.timestamp[:10] for r in self.state.history if len(r.timestamp) >= 10})

        # 2. Executive Metric Dashboard
        cards.append(
            ft.Text("Lifetime Workout Summary", size=16, weight=ft.FontWeight.BOLD)
        )

        def build_metric_tile(icon: str, label: str, value: str, icon_color: str) -> ft.Control:
            return ft.Container(
                expand=True,
                padding=12,
                bgcolor=ft.Colors.SURFACE_CONTAINER,
                border_radius=12,
                border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                content=ft.Column(
                    spacing=4,
                    controls=[
                        ft.Row(
                            spacing=6,
                            controls=[
                                ft.Icon(icon, size=16, color=icon_color),
                                ft.Text(label, size=11, color=ft.Colors.OUTLINE, weight=ft.FontWeight.W_500),
                            ],
                        ),
                        ft.Text(value, size=16, weight=ft.FontWeight.BOLD),
                    ],
                ),
            )

        volume_display = f"{total_volume:,.1f} kg" if total_volume > 0 else "Bodyweight"
        cards.append(
            ft.Column(
                spacing=8,
                controls=[
                    ft.Row(
                        spacing=8,
                        controls=[
                            build_metric_tile(ft.Icons.FITNESS_CENTER, "Total Volume", volume_display, ft.Colors.PRIMARY),
                            build_metric_tile(ft.Icons.REPLAY, "Total Sets", f"{total_sets:,}", ft.Colors.SECONDARY),
                        ],
                    ),
                    ft.Row(
                        spacing=8,
                        controls=[
                            build_metric_tile(ft.Icons.SPEED, "Total Reps", f"{total_reps:,}", ft.Colors.TERTIARY),
                            build_metric_tile(ft.Icons.EVENT_AVAILABLE, "Active Days", f"{unique_days:,} days", ft.Colors.GREEN),
                        ],
                    ),
                ],
            )
        )

        # 3. Exercise Breakdown & Personal Records
        exercise_data: dict[str, dict] = {}
        for r in self.state.history:
            if r.exercise not in exercise_data:
                exercise_data[r.exercise] = {
                    "sets": 0,
                    "reps": 0,
                    "volume": 0.0,
                    "max_weight": 0.0,
                    "max_reps": 0,
                }
            d = exercise_data[r.exercise]
            d["sets"] += 1
            d["reps"] += r.reps
            d["volume"] += round(r.reps * r.weight_kg, 2)
            if r.weight_kg > d["max_weight"]:
                d["max_weight"] = r.weight_kg
            if r.reps > d["max_reps"]:
                d["max_reps"] = r.reps

        cards.append(
            ft.Container(
                margin=ft.Margin(0, 10, 0, 0),
                content=ft.Text("Exercise Breakdown & PRs", size=16, weight=ft.FontWeight.BOLD),
            )
        )

        for ex_name, d in sorted(exercise_data.items(), key=lambda x: x[1]["reps"], reverse=True):
            sets_count = d["sets"]
            total_reps_ex = d["reps"]
            vol_ex = d["volume"]

            # Smart PR determination: Weight PR or Rep PR
            if d["max_weight"] > 0:
                pr_label = f"PR: {d['max_weight']:g} kg"
                sub_label = f"{sets_count} sets • {total_reps_ex} reps • {vol_ex:,.1f} kg"
            else:
                pr_label = f"PR: {d['max_reps']} reps"
                sub_label = f"{sets_count} sets • {total_reps_ex} reps"

            cards.append(
                ft.Card(
                    content=ft.Container(
                        padding=14,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text(ex_name, size=15, weight=ft.FontWeight.BOLD),
                                        ft.Text(sub_label, size=12, color=ft.Colors.OUTLINE),
                                    ],
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER, size=16),
                                            ft.Text(pr_label, weight=ft.FontWeight.BOLD, size=13),
                                        ],
                                    ),
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                    padding=ft.Padding(10, 5, 10, 5),
                                    border_radius=8,
                                    border=ft.Border.all(1, ft.Colors.OUTLINE_VARIANT),
                                ),
                            ],
                        ),
                    )
                )
            )

        self.stats_column.controls = cards
