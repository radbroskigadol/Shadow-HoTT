# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

from shadow_hott import Instruction, evaluate_compiler_routes, state_geometry_metrics, theta_sweep_report


def test_route_report_contains_new_label_sensitive_metrics():
    c0 = [Instruction("H", target=0), Instruction("CNOT", control=0, target=1)]
    c1 = [Instruction("S", target=0), Instruction("CNOT", control=0, target=1)]
    result = evaluate_compiler_routes([c0, c1], num_wires=2, sparse=True, hardware_edges=[(0, 1)])
    assert "optimal_route" in result
    report = result["all_reports"][0]
    assert "total_label_variation" in report
    assert "total_support_growth" in report
    assert "hardware_violation_score" in report
    assert result["selection_order"][0] == "hardware_violation_score"


def test_theta_sweep():
    circuits = [[Instruction("H", target=0)], [Instruction("S", target=0)]]
    sweep = theta_sweep_report(circuits, [0.25, 0.5, 0.75], num_wires=1, sparse=True)
    assert sweep["num_theta_points"] == 3
    assert len(sweep["winner_sequence"]) == 3


def test_hardware_violation_detects_nonlocal_support():
    from shadow_hott import ShadowState

    state = ShadowState(3, sparse=True)
    state.inject_truth("+XXX")
    metrics = state_geometry_metrics(state, hardware_edges=[(0, 1)])
    assert metrics.hardware_violation_score >= 1
