# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""High-level lint entry points for supported circuit front ends.

The low-level engine works on ``Instruction`` objects. This module provides the
public convenience layer expected by users: lint internal instructions, OpenQASM
2 text, Qiskit ``QuantumCircuit`` instances, and Cirq ``Circuit``/operation
iterables without making Qiskit or Cirq mandatory install dependencies.
"""
from __future__ import annotations

from typing import Any, Iterable, Sequence, Tuple

from .adapters import from_cirq, from_qiskit, parse_openqasm2
from .diagnostics import (
    calculate_label_shock_profile,
    calculate_shock_profile,
    calculate_support_growth_profile,
    check_determinization,
    get_signature_4,
    state_geometry_metrics,
)
from .engine import execute_circuit, infer_num_wires
from .state import ShadowState
from .types import Instruction


def lint_instructions(
    circuit: Sequence[Instruction],
    *,
    num_wires: int | None = None,
    theta: float = 0.5,
    sparse: bool = True,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
    include_trace: bool = False,
) -> dict[str, Any]:
    """Run the Shadow-HoTT linter on already-normalized instructions.

    Returns a JSON-serializable report except for ``final_state`` and optional
    ``trace`` entries, which are deliberately kept as Python objects for callers
    that want to inspect the state. Use ``certificates.to_jsonable`` before JSON
    dumping if those objects are included.
    """

    normalized = list(circuit)
    if num_wires is None:
        num_wires = infer_num_wires(normalized)
    trace = execute_circuit(
        normalized,
        num_wires=num_wires,
        theta=theta,
        sparse=sparse,
        epsilon=epsilon,
    )
    final_state = trace[-1]
    report: dict[str, Any] = {
        "frontend": "instructions",
        "num_wires": num_wires,
        "num_instructions": len(normalized),
        "theta": theta,
        "sparse": sparse,
        "epsilon": epsilon,
        "final_signature": get_signature_4(final_state),
        "signature4": get_signature_4(final_state),
        "is_determinized": check_determinization(final_state),
        "shock_profile": calculate_shock_profile(trace),
        "label_shock_profile": calculate_label_shock_profile(trace),
        "support_growth_profile": calculate_support_growth_profile(trace),
        "final_geometry": state_geometry_metrics(final_state, hardware_edges=hardware_edges),
        "hardware_edges": list(hardware_edges) if hardware_edges is not None else None,
        "final_state": final_state,
    }
    if include_trace:
        report["trace"] = trace
    return report


def lint_openqasm2(
    source: str,
    *,
    num_wires: int | None = None,
    theta: float = 0.5,
    sparse: bool = True,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
    include_trace: bool = False,
) -> dict[str, Any]:
    """Parse a supported OpenQASM 2 subset and lint it."""

    circuit = parse_openqasm2(source)
    report = lint_instructions(
        circuit,
        num_wires=num_wires,
        theta=theta,
        sparse=sparse,
        epsilon=epsilon,
        hardware_edges=hardware_edges,
        include_trace=include_trace,
    )
    report["frontend"] = "openqasm2"
    return report


def lint_qiskit(
    circuit: Any,
    *,
    num_wires: int | None = None,
    theta: float = 0.5,
    sparse: bool = True,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
    include_trace: bool = False,
) -> dict[str, Any]:
    """Convert a Qiskit ``QuantumCircuit``-like object and lint it."""

    instructions = from_qiskit(circuit)
    if num_wires is None and hasattr(circuit, "num_qubits"):
        num_wires = int(getattr(circuit, "num_qubits"))
    report = lint_instructions(
        instructions,
        num_wires=num_wires,
        theta=theta,
        sparse=sparse,
        epsilon=epsilon,
        hardware_edges=hardware_edges,
        include_trace=include_trace,
    )
    report["frontend"] = "qiskit"
    return report


def lint_cirq(
    circuit_or_operations: Any,
    *,
    num_wires: int | None = None,
    theta: float = 0.5,
    sparse: bool = True,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
    include_trace: bool = False,
) -> dict[str, Any]:
    """Convert a Cirq ``Circuit`` or operation iterable and lint it."""

    instructions = from_cirq(circuit_or_operations)
    report = lint_instructions(
        instructions,
        num_wires=num_wires,
        theta=theta,
        sparse=sparse,
        epsilon=epsilon,
        hardware_edges=hardware_edges,
        include_trace=include_trace,
    )
    report["frontend"] = "cirq"
    return report


def lint_auto(
    circuit: Any,
    *,
    num_wires: int | None = None,
    theta: float = 0.5,
    sparse: bool = True,
    epsilon: float = 0.0,
    hardware_edges: Iterable[Tuple[int, int]] | None = None,
    include_trace: bool = False,
) -> dict[str, Any]:
    """Best-effort linter dispatch for common circuit representations.

    Dispatch order:
    1. OpenQASM text strings;
    2. sequences of ``Instruction``;
    3. Qiskit-like objects with ``data``;
    4. Cirq-like objects with ``all_operations`` or operation iterables.
    """

    common_kwargs = dict(
        num_wires=num_wires,
        theta=theta,
        sparse=sparse,
        epsilon=epsilon,
        hardware_edges=hardware_edges,
        include_trace=include_trace,
    )
    if isinstance(circuit, str):
        return lint_openqasm2(circuit, **common_kwargs)
    if isinstance(circuit, Sequence) and all(isinstance(x, Instruction) for x in circuit):
        return lint_instructions(circuit, **common_kwargs)
    if hasattr(circuit, "data"):
        return lint_qiskit(circuit, **common_kwargs)
    if hasattr(circuit, "all_operations"):
        return lint_cirq(circuit, **common_kwargs)
    try:
        seq = list(circuit)
    except TypeError as exc:
        raise TypeError(f"cannot auto-lint object of type {type(circuit).__name__}") from exc
    if all(isinstance(x, Instruction) for x in seq):
        return lint_instructions(seq, **common_kwargs)
    return lint_cirq(seq, **common_kwargs)
