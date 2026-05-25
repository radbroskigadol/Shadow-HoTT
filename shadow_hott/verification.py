# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Soundness checks for exact Clifford label transport."""
from __future__ import annotations

from itertools import product
from typing import Any, Dict

from .pauli import CNOT_LOCAL_TABLE, CZ_LOCAL_TABLE, pauli_word_mul, transport_single_label


def verify_transport_soundness(max_qubits: int = 3) -> Dict[str, Any]:
    """Exhaustively check implemented Clifford transport involutions/orders.

    Checks include H^2, S^4, Sdg inverse-to-S, Pauli-gate square identities,
    CNOT^2, CZ^2, and SWAP^2 on signed Pauli labels. This is a code-level
    verification harness for implemented Clifford transport, not a proof of the
    heuristic bilateral scoring layer.
    """

    if max_qubits < 1:
        raise ValueError("max_qubits must be >= 1")
    report: Dict[str, Any] = {"max_qubits": max_qubits, "checks": [], "passed": True}

    assert transport_single_label("+X", "H", target=0) == "+Z"
    assert transport_single_label("+Z", "H", target=0) == "+X"
    assert transport_single_label("+Y", "H", target=0) == "-Y"
    assert transport_single_label("+X", "S", target=0) == "+Y"
    assert transport_single_label("+Y", "S", target=0) == "-X"
    assert transport_single_label("+Z", "S", target=0) == "+Z"
    assert transport_single_label("+X", "Sdg", target=0) == "-Y"
    assert transport_single_label("+Y", "Sdg", target=0) == "+X"
    assert transport_single_label("+Y", "X", target=0) == "-Y"
    assert transport_single_label("+Z", "X", target=0) == "-Z"
    assert transport_single_label("+X", "Y", target=0) == "-X"
    assert transport_single_label("+Z", "Y", target=0) == "-Z"
    assert transport_single_label("+X", "Z", target=0) == "-X"
    assert transport_single_label("+Y", "Z", target=0) == "-Y"
    report["checks"].append("single-qubit generator image sanity checks passed")

    for n in range(1, max_qubits + 1):
        words = ["".join(w) for w in product("IXYZ", repeat=n)]
        labels = [s + w for w in words for s in "+-"]
        for t in range(n):
            for label in labels:
                l1 = transport_single_label(label, "H", target=t)
                l2 = transport_single_label(l1, "H", target=t)
                assert l2 == label, f"H^2 failed for n={n}, t={t}, label={label}"

                s1 = transport_single_label(label, "S", target=t)
                s2 = transport_single_label(s1, "S", target=t)
                s3 = transport_single_label(s2, "S", target=t)
                s4 = transport_single_label(s3, "S", target=t)
                assert s4 == label, f"S^4 failed for n={n}, t={t}, label={label}"

                sdg_inverse = transport_single_label(s1, "Sdg", target=t)
                assert sdg_inverse == label, f"Sdg did not invert S for n={n}, t={t}, label={label}"

                for op in ("X", "Y", "Z"):
                    p1 = transport_single_label(label, op, target=t)
                    p2 = transport_single_label(p1, op, target=t)
                    assert p2 == label, f"{op}^2 failed for n={n}, t={t}, label={label}"
        report["checks"].append(f"H^2, S/Sdg, S^4, and Pauli squares exhaustive on n={n} passed")

        if n >= 2:
            for c in range(n):
                for t in range(n):
                    if c == t:
                        continue
                    for label in labels:
                        l1 = transport_single_label(label, "CNOT", target=t, control=c)
                        l2 = transport_single_label(l1, "CNOT", target=t, control=c)
                        assert l2 == label, f"CNOT^2 failed for n={n}, c={c}, t={t}, label={label}"

                        cz1 = transport_single_label(label, "CZ", target=t, control=c)
                        cz2 = transport_single_label(cz1, "CZ", target=t, control=c)
                        assert cz2 == label, f"CZ^2 failed for n={n}, a={c}, b={t}, label={label}"

                        sw1 = transport_single_label(label, "SWAP", target=t, control=c)
                        sw2 = transport_single_label(sw1, "SWAP", target=t, control=c)
                        assert sw2 == label, f"SWAP^2 failed for n={n}, a={c}, b={t}, label={label}"
            report["checks"].append(f"CNOT^2, CZ^2, and SWAP^2 exhaustive on n={n} passed")

    return report
