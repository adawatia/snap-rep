"""Stats view: Breakdown of workout volume and personal records (PRs)."""

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
                        spacing=10,
                        controls=[
                            ft.Icon(ft.Icons.INSIGHTS, size=48, color=ft.Colors.OUTLINE),
                            ft.Text("No workout statistics yet.", size=16, color=ft.Colors.OUTLINE),
                            ft.Text("Log workout sets to see personal stats and PRs.", size=13, color=ft.Colors.OUTLINE),
                        ],
                    ),
                )
            )
            self.stats_column.controls = cards
            return

        # Aggregate stats
        exercise_counts: dict[str, int] = {}
        exercise_sets: dict[str, int] = {}
        exercise_prs: dict[str, int] = {}

        for r in self.state.history:
            exercise_counts[r.exercise] = exercise_counts.get(r.exercise, 0) + r.reps
            exercise_sets[r.exercise] = exercise_sets.get(r.exercise, 0) + 1
            if r.exercise not in exercise_prs or r.reps > exercise_prs[r.exercise]:
                exercise_prs[r.exercise] = r.reps

        cards.append(
            ft.Text("Exercise Breakdown & PRs", size=16, weight=ft.FontWeight.BOLD)
        )

        for ex_name, total_reps in sorted(exercise_counts.items(), key=lambda x: x[1], reverse=True):
            pr = exercise_prs.get(ex_name, 0)
            sets_count = exercise_sets.get(ex_name, 0)

            cards.append(
                ft.Card(
                    content=ft.Container(
                        padding=16,
                        content=ft.Row(
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                            controls=[
                                ft.Column(
                                    spacing=4,
                                    controls=[
                                        ft.Text(ex_name, size=15, weight=ft.FontWeight.BOLD),
                                        ft.Text(f"{sets_count} sets • {total_reps} total reps", size=12, color=ft.Colors.OUTLINE),
                                    ],
                                ),
                                ft.Container(
                                    content=ft.Row(
                                        spacing=4,
                                        controls=[
                                            ft.Icon(ft.Icons.STAR, color=ft.Colors.AMBER, size=18),
                                            ft.Text(f"PR: {pr} reps", weight=ft.FontWeight.BOLD, size=14),
                                        ],
                                    ),
                                    bgcolor=ft.Colors.SURFACE_CONTAINER_HIGH,
                                    padding=ft.Padding(8, 4, 8, 4),
                                    border_radius=8,
                                ),
                            ],
                        ),
                    )
                )
            )

        self.stats_column.controls = cards
