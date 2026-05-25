# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Shadow state, threshold cache, mutation helpers, and injection API."""
from __future__ import annotations

from typing import Dict, List, Optional

from .pauli import (
    BilateralLayer,
    distinguished_pauli_label,
    is_event_label,
    label_to_signed_word,
    pauli_labels_touching_wire,
    signed_pauli_labels,
    validate_wire,
)
from .types import Val


class ShadowState:
    """Bilateral score state for the Shadow-HoTT diagnostic engine.

    ``bi`` maps labels to continuous ``[truth_score, falsity_score]`` pairs.
    ``cache`` stores the thresholded four-valued classification. In sparse mode,
    missing bilateral labels mean ``[0, 0]`` and missing cache entries mean ``U``.
    """

    def __init__(
        self,
        num_wires: int,
        theta: float = 0.5,
        *,
        sparse: bool = False,
        epsilon: float = 0.0,
    ) -> None:
        if num_wires <= 0:
            raise ValueError("num_wires must be positive")
        if not (0.0 <= theta <= 1.0):
            raise ValueError("theta must be in [0, 1]")
        if epsilon < 0:
            raise ValueError("epsilon must be nonnegative")

        self.num_wires = num_wires
        self.theta = theta
        self.sparse = sparse
        self.epsilon = epsilon
        self.carrier: Optional[str] = None
        self.provenance: int = 0
        self.last_measurements: Dict[int, int] = {}
        self.total_pauli_labels = 2 * (4**self.num_wires)
        self.total_event_labels = 2 * self.num_wires
        self.total_labels = self.total_pauli_labels + self.total_event_labels
        self.bi: BilateralLayer = self._initialize_bilateral_layer()
        self.cache: Dict[str, Val] = {}
        self.refresh_cache()

    def copy(self) -> "ShadowState":
        new_state = ShadowState(
            self.num_wires,
            theta=self.theta,
            sparse=self.sparse,
            epsilon=self.epsilon,
        )
        new_state.carrier = self.carrier
        new_state.provenance = self.provenance
        new_state.last_measurements = dict(self.last_measurements)
        new_state.bi = {k: [v[0], v[1]] for k, v in self.bi.items()}
        new_state.cache = dict(self.cache)
        return new_state

    def score(self, label: str) -> List[float]:
        """Return an explicit or implicit bilateral score for ``label``."""

        return [self.bi.get(label, [0.0, 0.0])[0], self.bi.get(label, [0.0, 0.0])[1]]

    def validate_label(self, label: str) -> None:
        """Validate that a user-supplied label belongs to this state.

        Pauli labels must have the same width as ``num_wires``. Event labels
        must use ``EV:<wire>:<0-or-1>`` and refer to an existing wire.
        """

        if is_event_label(label):
            parts = label.split(":")
            if len(parts) != 3 or parts[0] != "EV":
                raise ValueError(f"invalid event label: {label!r}")
            try:
                wire = int(parts[1])
                outcome = int(parts[2])
            except ValueError as exc:
                raise ValueError(f"invalid event label: {label!r}") from exc
            validate_wire(self.num_wires, wire)
            if outcome not in (0, 1):
                raise ValueError(f"event label outcome must be 0 or 1: {label!r}")
            return

        _, word = label_to_signed_word(label)
        if len(word) != self.num_wires:
            raise ValueError(
                f"Pauli label width {len(word)} does not match state width {self.num_wires}: {label!r}"
            )

    def set_score(self, label: str, truth: float, falsity: float, *, refresh: bool = True) -> None:
        """Set a bilateral score, respecting sparse-mode zero pruning."""

        self.validate_label(label)
        self._maybe_store_score(label, truth, falsity)
        self._prune_bi()
        if refresh:
            self.refresh_cache()

    def inject_glut(self, label: str, strength: float = 1.0) -> None:
        """Force a label into a both-designated/glut profile."""

        self.set_score(label, strength, strength)

    def inject_gap(self, label: str) -> None:
        """Force a label into a neither/gap profile."""

        self.set_score(label, 0.0, 0.0)

    def inject_truth(self, label: str, strength: float = 1.0) -> None:
        """Force a label into a true-only profile."""

        self.set_score(label, strength, 0.0)

    def inject_falsity(self, label: str, strength: float = 1.0) -> None:
        """Force a label into a false-only profile."""

        self.set_score(label, 0.0, strength)

    def _is_zero_pair(self, a: float, b: float) -> bool:
        return abs(a) <= self.epsilon and abs(b) <= self.epsilon

    def _maybe_store_score(self, label: str, a: float, b: float) -> None:
        if self.sparse and self._is_zero_pair(a, b):
            self.bi.pop(label, None)
        else:
            self.bi[label] = [float(a), float(b)]

    def _initialize_bilateral_layer(self) -> BilateralLayer:
        bi: BilateralLayer = {}
        if not self.sparse:
            for label in signed_pauli_labels(self.num_wires):
                bi[label] = [0.0, 0.0]
            for w in range(self.num_wires):
                bi[f"EV:{w}:0"] = [0.0, 0.0]
                bi[f"EV:{w}:1"] = [0.0, 0.0]

        id_word = "I" * self.num_wires
        bi[f"+{id_word}"] = [1.0, 0.0]
        bi[f"-{id_word}"] = [0.0, 1.0]

        for w in range(self.num_wires):
            bi[distinguished_pauli_label(self.num_wires, w, "Z", "+")] = [1.0, 0.0]
            bi[distinguished_pauli_label(self.num_wires, w, "Z", "-")] = [0.0, 1.0]
            if not self.sparse:
                for p in ("X", "Y"):
                    bi[distinguished_pauli_label(self.num_wires, w, p, "+")] = [0.0, 0.0]
                    bi[distinguished_pauli_label(self.num_wires, w, p, "-")] = [0.0, 0.0]
        return bi

    def _prune_bi(self) -> None:
        if not self.sparse:
            return
        for label in [k for k, (a, b) in self.bi.items() if self._is_zero_pair(a, b)]:
            del self.bi[label]

    def refresh_cache(self, theta: float | None = None) -> None:
        """Recompute the thresholded four-valued cache."""

        if theta is None:
            theta = self.theta
        if not (0.0 <= theta <= 1.0):
            raise ValueError("theta must be in [0, 1]")
        self.cache = {}
        for obs, scores in self.bi.items():
            a, b = scores
            if a >= theta and b < theta:
                self.cache[obs] = Val.T
            elif a < theta and b >= theta:
                self.cache[obs] = Val.F
            elif a >= theta and b >= theta:
                self.cache[obs] = Val.B
            elif not self.sparse:
                self.cache[obs] = Val.U
        if self.sparse:
            self.cache = {k: v for k, v in self.cache.items() if v != Val.U}

    def value(self, label: str) -> Val:
        """Return threshold cache value, interpreting sparse missing entries as U."""

        return self.cache.get(label, Val.U)

    def signature4(self) -> List[int]:
        from .diagnostics import get_signature_4

        return get_signature_4(self)

    def determinized(self) -> bool:
        t, f, b, u = self.signature4()
        return b == 0 and u == 0

    def __repr__(self) -> str:
        return (
            f"ShadowState(num_wires={self.num_wires}, theta={self.theta}, "
            f"sparse={self.sparse}, carrier={self.carrier!r}, "
            f"provenance={self.provenance}, signature4={self.signature4()})"
        )


def reset_event_labels(bi: BilateralLayer) -> BilateralLayer:
    """Reset all explicit event labels to zero; sparse pruning is done by state."""

    out = {k: [v[0], v[1]] for k, v in bi.items()}
    for k in list(out.keys()):
        if is_event_label(k):
            out[k] = [0.0, 0.0]
    return out


def finalize_measurement_state(state: ShadowState, wire: int, outcome: int) -> ShadowState:
    """Apply deterministic Z-measurement collapse proxy.

    This is a diagnostic collapse operator over the bilateral label field. It is
    not Born sampling and not a full stabilizer-measurement update.
    """

    validate_wire(state.num_wires, wire)
    if outcome not in (0, 1):
        raise ValueError("outcome must be 0 or 1")

    new_state = state.copy()
    new_state.carrier = f"MEASURE_Z[{wire}]={outcome}"
    new_state.provenance += 1
    new_state.last_measurements[wire] = outcome
    new_state.bi = reset_event_labels(new_state.bi)

    ev0 = f"EV:{wire}:0"
    ev1 = f"EV:{wire}:1"
    if outcome == 0:
        new_state._maybe_store_score(ev0, 1.0, 0.0)
        new_state._maybe_store_score(ev1, 0.0, 1.0)
    else:
        new_state._maybe_store_score(ev0, 0.0, 1.0)
        new_state._maybe_store_score(ev1, 1.0, 0.0)

    pos_z = distinguished_pauli_label(new_state.num_wires, wire, "Z", "+")
    neg_z = distinguished_pauli_label(new_state.num_wires, wire, "Z", "-")
    if outcome == 0:
        new_state._maybe_store_score(pos_z, 1.0, 0.0)
        new_state._maybe_store_score(neg_z, 0.0, 1.0)
    else:
        new_state._maybe_store_score(pos_z, 0.0, 1.0)
        new_state._maybe_store_score(neg_z, 1.0, 0.0)

    for p in ("X", "Y"):
        new_state._maybe_store_score(distinguished_pauli_label(new_state.num_wires, wire, p, "+"), 0.0, 0.0)
        new_state._maybe_store_score(distinguished_pauli_label(new_state.num_wires, wire, p, "-"), 0.0, 0.0)

    for label in pauli_labels_touching_wire(list(new_state.bi.keys()), wire, {"X", "Y"}):
        new_state._maybe_store_score(label, 0.0, 0.0)

    new_state._prune_bi()
    new_state.refresh_cache()
    return new_state
