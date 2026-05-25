# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Route evaluation and threshold-sweep reporting."""
from __future__ import annotations

from typing import Any, Iterable, Sequence, Tuple

from .diagnostics import (
    calculate_label_shock_profile,
    calculate_shock_profile,
    calculate_support_growth_profile,
    check_determinization,
    get_signature_4,
    state_geometry_metrics,
)
from .engine import execute_circuit
from .state import ShadowState
from .types import Instruction


def _report_for_trace(
    idx: int,
    trace: list[ShadowState],
    *,
    theta: float,
    sparse: bool,
    hardware_edges: Iterable[Tuple[int, int]] | None,
) -> dict[str, Any]:
    signature_shock = calculate_shock_profile(trace)
    label_shock = calculate_label_shock_profile(trace)
    support_growth = calculate_support_growth_profile(trace)
    final_signature = get_signature_4(trace[-1])
    denom = sum(final_signature)
    final_geometry = state_geometry_metrics(trace[-1], hardware_edges=hardware_edges)

    total_signature_variation = sum(signature_shock)
    total_label_variation = sum(label_shock)
    total_support_growth = sum(support_growth)
    glut_density = (final_signature[2] / denom) if denom else 0.0
    gap_density = (final_signature[3] / denom) if denom else 0.0

    # Composite tuple is exposed so callers can inspect/change ordering.
    composite_score = (
        final_geometry.hardware_violation_score,
        total_label_variation,
        total_support_growth,
        total_signature_variation,
        glut_density,
        gap_density,
        idx,
    )

    return {
        "circuit_id": idx,
        "theta": theta,
        "sparse": sparse,
        "total_variation": total_signature_variation,  # legacy-compatible name
        "total_signature_variation": total_signature_variation,
        "total_label_variation": total_label_variation,
        "total_support_growth": total_support_growth,
        "glut_density": glut_density,
        "gap_density": gap_density,
        "is_determinized": check_determinization(trace[-1]),
        "final_signature": final_signature,
        "shock_profile": signature_shock,
        "label_shock_profile": label_shock,
        "support_growth_profile": support_growth,
        "final_geometry": final_geometry,
        "hardware_violation_score": final_geometry.hardware_violation_score,
        "composite_score": composite_score,
        "final_state": trace[-1],
    }


def evaluate_compiler_routes(
    circuit_variants: Sequence[Sequence[Instruction]],
    *,
    num_wires: int | None = None,
    theta: float = 0.5,
    sparse: bool = False,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Evaluate circuit variants using signature, label, support, and hardware metrics.

    The legacy count-vector shock is retained, but route selection no longer uses
    only that weak metric. Selection prioritizes hardware graph violations, then
    label-wise cache movement, support growth, signature variation, glut density,
    gap density, and finally circuit id.
    """

    if not circuit_variants:
        raise ValueError("at least one circuit variant is required")

    reports: list[dict[str, Any]] = []
    for idx, circuit in enumerate(circuit_variants):
        trace = execute_circuit(
            circuit,
            num_wires=num_wires,
            theta=theta,
            sparse=sparse,
            epsilon=epsilon,
        )
        reports.append(
            _report_for_trace(
                idx,
                trace,
                theta=theta,
                sparse=sparse,
                hardware_edges=hardware_edges,
            )
        )

    optimal_route = min(reports, key=lambda x: x["composite_score"])
    return {
        "optimal_route": optimal_route,
        "all_reports": reports,
        "selection_order": [
            "hardware_violation_score",
            "total_label_variation",
            "total_support_growth",
            "total_signature_variation",
            "glut_density",
            "gap_density",
            "circuit_id",
        ],
    }


def theta_sweep_report(
    circuit_variants: Sequence[Sequence[Instruction]],
    thetas: Iterable[float],
    *,
    num_wires: int | None = None,
    sparse: bool = False,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Run route evaluation across a threshold sweep."""

    theta_results: list[dict[str, Any]] = []
    winner_sequence: list[tuple[float, int]] = []
    theta_list = list(thetas)
    if not theta_list:
        raise ValueError("thetas must contain at least one value")

    for theta in theta_list:
        res = evaluate_compiler_routes(
            circuit_variants,
            num_wires=num_wires,
            theta=theta,
            sparse=sparse,
            epsilon=epsilon,
            hardware_edges=hardware_edges,
        )
        winner_id = res["optimal_route"]["circuit_id"]
        theta_results.append(
            {
                "theta": theta,
                "winner_id": winner_id,
                "optimal_route": res["optimal_route"],
                "all_reports": res["all_reports"],
            }
        )
        winner_sequence.append((theta, winner_id))

    winner_hist: dict[int, int] = {}
    for _, winner_id in winner_sequence:
        winner_hist[winner_id] = winner_hist.get(winner_id, 0) + 1

    transitions: list[dict[str, Any]] = []
    for i in range(1, len(winner_sequence)):
        theta_prev, winner_prev = winner_sequence[i - 1]
        theta_curr, winner_curr = winner_sequence[i]
        if winner_prev != winner_curr:
            transitions.append(
                {
                    "from_theta": theta_prev,
                    "to_theta": theta_curr,
                    "from_winner": winner_prev,
                    "to_winner": winner_curr,
                }
            )

    modal_winner = max(winner_hist.items(), key=lambda kv: (kv[1], -kv[0]))[0]
    stability_fraction = winner_hist[modal_winner] / len(winner_sequence)

    return {
        "theta_results": theta_results,
        "winner_sequence": winner_sequence,
        "winner_histogram": winner_hist,
        "winner_transitions": transitions,
        "modal_winner": modal_winner,
        "stability_fraction": stability_fraction,
        "num_theta_points": len(winner_sequence),
    }
