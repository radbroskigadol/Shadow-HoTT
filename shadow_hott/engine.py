# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Circuit execution engine."""
from __future__ import annotations

from typing import Optional, Sequence

from .pauli import (
    distinguished_pauli_label,
    normalize_clifford_op,
    transport_CNOT,
    transport_CZ,
    transport_H,
    transport_S,
    transport_Sdg,
    transport_SWAP,
    transport_X,
    transport_Y,
    transport_Z,
    validate_two_wires,
    validate_wire,
)
from .state import ShadowState, finalize_measurement_state, reset_event_labels
from .types import Instruction, Val


def apply_gate(
    state: ShadowState,
    gate_type: str,
    target_wire: int,
    control_wire: Optional[int] = None,
) -> ShadowState:
    """Apply one supported Clifford gate to a ``ShadowState``."""

    gate = normalize_clifford_op(gate_type)
    new_state = state.copy()
    new_state.carrier = gate
    new_state.provenance += 1

    if gate == "H":
        validate_wire(new_state.num_wires, target_wire)
        new_state.bi = transport_H(new_state.bi, target_wire)
    elif gate == "S":
        validate_wire(new_state.num_wires, target_wire)
        new_state.bi = transport_S(new_state.bi, target_wire)
    elif gate == "SDG":
        validate_wire(new_state.num_wires, target_wire)
        new_state.bi = transport_Sdg(new_state.bi, target_wire)
    elif gate == "X":
        validate_wire(new_state.num_wires, target_wire)
        new_state.bi = transport_X(new_state.bi, target_wire)
    elif gate == "Y":
        validate_wire(new_state.num_wires, target_wire)
        new_state.bi = transport_Y(new_state.bi, target_wire)
    elif gate == "Z":
        validate_wire(new_state.num_wires, target_wire)
        new_state.bi = transport_Z(new_state.bi, target_wire)
    elif gate == "CNOT":
        if control_wire is None:
            raise ValueError("CNOT requires control_wire")
        validate_two_wires(new_state.num_wires, control_wire, target_wire)
        new_state.bi = transport_CNOT(new_state.bi, control_wire, target_wire)
    elif gate == "CZ":
        if control_wire is None:
            raise ValueError("CZ requires control_wire")
        validate_two_wires(new_state.num_wires, control_wire, target_wire)
        new_state.bi = transport_CZ(new_state.bi, control_wire, target_wire)
    elif gate == "SWAP":
        if control_wire is None:
            raise ValueError("SWAP requires control_wire")
        validate_two_wires(new_state.num_wires, control_wire, target_wire)
        new_state.bi = transport_SWAP(new_state.bi, control_wire, target_wire)
    else:
        raise ValueError(f"unsupported gate_type: {gate_type!r}")

    new_state.bi = reset_event_labels(new_state.bi)
    new_state._prune_bi()
    new_state.refresh_cache()
    return new_state


def apply_measurement(state: ShadowState, wire: int, *, forced_outcome: int | None = None) -> ShadowState:
    """Apply the deterministic Z-basis measurement proxy.

    If ``forced_outcome`` is supplied, it must be ``0`` or ``1``. Otherwise the
    outcome is selected from the distinguished ±Z labels, with ambiguous ties
    deterministically broken toward ``0``.
    """

    validate_wire(state.num_wires, wire)
    if forced_outcome is not None:
        return finalize_measurement_state(state, wire, forced_outcome)

    pos_z_label = distinguished_pauli_label(state.num_wires, wire, "Z", sign="+")
    neg_z_label = distinguished_pauli_label(state.num_wires, wire, "Z", sign="-")
    val_pos = state.value(pos_z_label)
    val_neg = state.value(neg_z_label)
    pos_designated = val_pos in (Val.T, Val.B)
    neg_designated = val_neg in (Val.T, Val.B)

    if pos_designated and not neg_designated:
        outcome = 0
    elif neg_designated and not pos_designated:
        outcome = 1
    else:
        outcome = 0
    return finalize_measurement_state(state, wire, outcome)


def infer_num_wires(circuit: Sequence[Instruction]) -> int:
    """Infer circuit width from instruction wire references."""

    max_wire = -1
    for inst in circuit:
        if inst.target is not None:
            max_wire = max(max_wire, inst.target)
        if inst.control is not None:
            max_wire = max(max_wire, inst.control)
    return max_wire + 1 if max_wire >= 0 else 1


def execute_circuit(
    circuit: Sequence[Instruction],
    num_wires: Optional[int] = None,
    *,
    theta: float = 0.5,
    sparse: bool = False,
    epsilon: float = 0.0,
    initial_state: ShadowState | None = None,
) -> list[ShadowState]:
    """Execute a supported circuit and return the full shadow trace."""

    if initial_state is not None:
        if num_wires is not None and num_wires != initial_state.num_wires:
            raise ValueError("num_wires conflicts with initial_state.num_wires")
        state = initial_state.copy()
    else:
        if num_wires is None:
            num_wires = infer_num_wires(circuit)
        state = ShadowState(num_wires, theta=theta, sparse=sparse, epsilon=epsilon)

    trace = [state]
    for inst in circuit:
        op = normalize_clifford_op(inst.normalized_op())
        if op in {"H", "S", "SDG", "X", "Y", "Z"}:
            if inst.target is None:
                raise ValueError(f"{op} requires target")
            state = apply_gate(state, op, target_wire=inst.target)
        elif op == "CNOT":
            if inst.control is None or inst.target is None:
                raise ValueError("CNOT requires control and target")
            state = apply_gate(state, "CNOT", target_wire=inst.target, control_wire=inst.control)
        elif op == "CZ":
            if inst.control is None or inst.target is None:
                raise ValueError("CZ requires two wires")
            state = apply_gate(state, "CZ", target_wire=inst.target, control_wire=inst.control)
        elif op == "SWAP":
            if inst.control is None or inst.target is None:
                raise ValueError("SWAP requires two wires")
            state = apply_gate(state, "SWAP", target_wire=inst.target, control_wire=inst.control)
        elif op == "MEASURE":
            if inst.target is None:
                raise ValueError("MEASURE requires target")
            state = apply_measurement(state, inst.target)
        else:
            raise ValueError(f"unsupported instruction op: {inst.op!r}")
        trace.append(state)
    return trace
