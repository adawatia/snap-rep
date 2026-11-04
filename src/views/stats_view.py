"""Workout totals and per-exercise personal records."""

import flet as ft

from state import AppState


class StatsView:
    def __init__(self, page: ft.Page, state: AppState):
        self.page = page
        self.state = state
        self.stats_column = ft.Column(
            scroll=ft.ScrollMode.ADAPTIVE,
            expand=True,
            spacing=20,
            horizontal_alignment=ft.CrossAxisAlignment.STRETCH,
        )
        self.root = ft.Container(
            padding=ft.Padding(16, 14, 16, 24),
            expand=True,
            content=self.stats_column,
        )
        self.update_ui()

    @staticmethod
    def _metric(label: str, value: str) -> ft.Control:
        return ft.Column(
            spacing=3,
            expand=True,
            controls=[
                ft.Text(label, size=11, color=ft.Colors.ON_SURFACE_VARIANT),
                ft.Text(value, size=18, weight=ft.FontWeight.BOLD),
            ],
        )

    def update_ui(self) -> None:
        records = self.state.history
        if not records:
            self.stats_column.controls = [
                ft.Container(
                    padding=ft.Padding(28, 36, 28, 36),
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=16,
                    content=ft.Column(
                        spacing=12,
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        controls=[
                            ft.Icon(ft.Icons.INSIGHTS, size=40, color=ft.Colors.PRIMARY),
                            ft.Text("Your progress starts here", size=18, weight=ft.FontWeight.BOLD),
                            ft.Text(
                                "Log a set in Tracker to see your totals and personal records.",
                                size=13,
                                color=ft.Colors.ON_SURFACE_VARIANT,
                                text_align=ft.TextAlign.CENTER,
                            ),
                        ],
                    ),
                )
            ]
            return

        total_sets = len(records)
        total_reps = sum(record.reps for record in records)
        total_volume = sum(record.reps * record.weight_kg for record in records)
        active_days = len({record.timestamp[:10] for record in records if len(record.timestamp) >= 10})

        exercise_data: dict[str, dict] = {}
        for record in records:
            data = exercise_data.setdefault(record.exercise, {
                "sets": 0, "reps": 0, "volume": 0.0, "max_weight": 0.0, "max_reps": 0,
            })
            data["sets"] += 1
            data["reps"] += record.reps
            data["volume"] += record.reps * record.weight_kg
            data["max_weight"] = max(data["max_weight"], record.weight_kg)
            data["max_reps"] = max(data["max_reps"], record.reps)

        summary = ft.Container(
            bgcolor=ft.Colors.PRIMARY_CONTAINER,
            border_radius=16,
            padding=ft.Padding(20, 18, 20, 20),
            content=ft.Column(
                spacing=4,
                controls=[
                    ft.Text("Total volume", size=13, color=ft.Colors.ON_PRIMARY_CONTAINER),
                    ft.Text(
                        f"{total_volume:,.0f} kg",
                        size=34,
                        weight=ft.FontWeight.BOLD,
                        color=ft.Colors.ON_PRIMARY_CONTAINER,
                    ),
                    ft.Text(
                        "Weight × reps across all logged sets",
                        size=11,
                        color=ft.Colors.ON_PRIMARY_CONTAINER,
                    ),
                ],
            ),
        )
        totals = ft.Container(
            bgcolor=ft.Colors.SURFACE_CONTAINER,
            border_radius=16,
            padding=ft.Padding(16, 16, 16, 16),
            content=ft.Row(
                spacing=12,
                controls=[
                    self._metric("Sets", f"{total_sets:,}"),
                    self._metric("Reps", f"{total_reps:,}"),
                    self._metric("Active days", f"{active_days:,}"),
                ],
            ),
        )
        controls: list[ft.Control] = [summary, totals]
        controls.append(
            ft.Column(
                spacing=3,
                controls=[
                    ft.Text("By exercise", size=18, weight=ft.FontWeight.BOLD),
                    ft.Text(
                        f"{len(exercise_data)} exercise{'s' if len(exercise_data) != 1 else ''} · sorted by reps",
                        size=12,
                        color=ft.Colors.ON_SURFACE_VARIANT,
                    ),
                ],
            )
        )

        peak_reps = max(1, max(data["reps"] for data in exercise_data.values()))
        for name, data in sorted(exercise_data.items(), key=lambda item: (-item[1]["reps"], item[0].lower())):
            best = (
                f"Best {data['max_weight']:g} kg"
                if data["max_weight"] > 0 else f"Best {data['max_reps']} reps"
            )
            details = f"{data['sets']} sets · {data['reps']} reps"
            if data["volume"] > 0:
                details += f" · {data['volume']:,.0f} kg volume"
            controls.append(
                ft.Container(
                    bgcolor=ft.Colors.SURFACE_CONTAINER,
                    border_radius=12,
                    padding=ft.Padding(16, 14, 16, 14),
                    content=ft.Column(
                        spacing=10,
                        controls=[
                            ft.Row(
                                spacing=10,
                                controls=[
                                    ft.Container(
                                        expand=True,
                                        content=ft.Text(name, size=15, weight=ft.FontWeight.BOLD, max_lines=2),
                                    ),
                                    ft.Container(
                                        bgcolor=ft.Colors.TERTIARY_CONTAINER,
                                        border_radius=8,
                                        padding=ft.Padding(8, 5, 8, 5),
                                        content=ft.Text(
                                            best, size=11, weight=ft.FontWeight.BOLD,
                                            color=ft.Colors.ON_TERTIARY_CONTAINER,
                                        ),
                                    ),
                                ],
                            ),
                            ft.Text(details, size=12, color=ft.Colors.ON_SURFACE_VARIANT),
                            ft.ProgressBar(
                                value=data["reps"] / peak_reps,
                                bar_height=5,
                                border_radius=3,
                                color=ft.Colors.PRIMARY,
                                bgcolor=ft.Colors.SURFACE_CONTAINER_HIGHEST,
                                semantics_label=f"{name} reps relative to the most logged exercise",
                            ),
                        ],
                    ),
                )
            )

        self.stats_column.controls = controls
