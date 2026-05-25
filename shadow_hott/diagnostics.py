# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Diagnostic metrics for Shadow-HoTT traces and states."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, List, Mapping, Sequence, Tuple

from .pauli import is_event_label, label_to_signed_word, support_weight
from .state import ShadowState
from .types import Val


@dataclass(frozen=True, slots=True)
class GeometryMetrics:
    """Label-sensitive geometry metrics for a single state."""

    active_truth_support: int
    active_falsity_support: int
    active_total_support: int
    active_label_count: int
    max_support_weight: int
    nonlocal_label_count: int
    hardware_violation_score: int


def get_signature_4(state: ShadowState) -> List[int]:
    """Return ``[count_T, count_F, count_B, count_U]``.

    In sparse mode, missing labels are counted as implicit ``U``.
    """

    counts = [0, 0, 0, 0]
    for val in state.cache.values():
        if val == Val.T:
            counts[0] += 1
        elif val == Val.F:
            counts[1] += 1
        elif val == Val.B:
            counts[2] += 1
        elif val == Val.U:
            counts[3] += 1
    explicit_count = sum(counts)
    if explicit_count > state.total_labels:
        raise RuntimeError("signature count exceeds total label count")
    counts[3] += state.total_labels - explicit_count
    return counts


def calculate_shock_profile(trace: Sequence[ShadowState]) -> List[int]:
    """L1 differences between consecutive four-valued signatures."""

    shocks: List[int] = []
    for i in range(1, len(trace)):
        sig_prev = get_signature_4(trace[i - 1])
        sig_curr = get_signature_4(trace[i])
        shocks.append(sum(abs(curr - prev) for curr, prev in zip(sig_curr, sig_prev)))
    return shocks


def cache_value_changes(prev: ShadowState, curr: ShadowState) -> int:
    """Count label-wise cache changes, not just count-vector changes."""

    labels = set(prev.cache) | set(curr.cache)
    if not prev.sparse:
        labels |= set(prev.bi)
    if not curr.sparse:
        labels |= set(curr.bi)
    return sum(prev.value(label) != curr.value(label) for label in labels)


def calculate_label_shock_profile(trace: Sequence[ShadowState]) -> List[int]:
    """Label-sensitive cache-change profile across a trace."""

    return [cache_value_changes(trace[i - 1], trace[i]) for i in range(1, len(trace))]


def active_labels(state: ShadowState) -> List[str]:
    """Return labels with non-``U`` threshold value."""

    return [label for label, val in state.cache.items() if val != Val.U]


def normalize_hardware_edges(edges: Iterable[Tuple[int, int]] | None) -> set[Tuple[int, int]] | None:
    """Normalize undirected hardware edges. ``None`` means fully connected."""

    if edges is None:
        return None
    return {tuple(sorted((a, b))) for a, b in edges}


def label_hardware_violation(label: str, hardware_edges: set[Tuple[int, int]] | None) -> int:
    """Score how much a Pauli support exceeds a hardware coupling graph.

    For support of size 0/1 there is no routing violation. For support of size
    >=2, every unsupported pair contributes one violation. This is a conservative
    structural lint metric, not a physical noise model.
    """

    if hardware_edges is None or is_event_label(label):
        return 0
    _, word = label_to_signed_word(label)
    support = [i for i, ch in enumerate(word) if ch != "I"]
    if len(support) <= 1:
        return 0
    violations = 0
    for i, a in enumerate(support):
        for b in support[i + 1 :]:
            if tuple(sorted((a, b))) not in hardware_edges:
                violations += 1
    return violations


def state_geometry_metrics(
    state: ShadowState,
    *,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
) -> GeometryMetrics:
    """Compute label-sensitive support and hardware metrics for a state."""

    edges = normalize_hardware_edges(hardware_edges)
    truth_support = 0
    falsity_support = 0
    total_support = 0
    active_count = 0
    max_weight = 0
    nonlocal_count = 0
    violation_score = 0

    for label, val in state.cache.items():
        if val == Val.U:
            continue
        weight = support_weight(label)
        active_count += 1
        max_weight = max(max_weight, weight)
        if weight > 1:
            nonlocal_count += 1
        if val in (Val.T, Val.B):
            truth_support += weight
        if val in (Val.F, Val.B):
            falsity_support += weight
        total_support += weight
        violation_score += label_hardware_violation(label, edges)

    return GeometryMetrics(
        active_truth_support=truth_support,
        active_falsity_support=falsity_support,
        active_total_support=total_support,
        active_label_count=active_count,
        max_support_weight=max_weight,
        nonlocal_label_count=nonlocal_count,
        hardware_violation_score=violation_score,
    )


def calculate_support_growth_profile(trace: Sequence[ShadowState]) -> List[int]:
    """Differences in active total support between consecutive states."""

    out: List[int] = []
    for i in range(1, len(trace)):
        prev = state_geometry_metrics(trace[i - 1]).active_total_support
        curr = state_geometry_metrics(trace[i]).active_total_support
        out.append(abs(curr - prev))
    return out


def check_determinization(state: ShadowState) -> bool:
    return state.determinized()
