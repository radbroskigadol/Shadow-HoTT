# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

import pytest

from shadow_hott import Instruction, ShadowState, Val, apply_gate, apply_measurement, execute_circuit
from shadow_hott.pauli import distinguished_pauli_label


def test_basic_trace_execution():
    circuit = [Instruction("H", target=0), Instruction("S", target=0), Instruction("MEASURE", target=0)]
    trace = execute_circuit(circuit, num_wires=1)
    assert len(trace) == 4
    assert trace[-1].last_measurements[0] in {0, 1}


def test_h_transports_active_y_score():
    state = ShadowState(1)
    state.set_score("+Y", 1.0, 0.0)
    out = apply_gate(state, "H", target_wire=0)
    assert out.bi["-Y"] == [1.0, 0.0]


def test_measurement_writes_event_labels():
    state = ShadowState(1, sparse=True)
    measured = apply_measurement(state, 0, forced_outcome=1)
    assert measured.last_measurements[0] == 1
    assert measured.value("EV:0:1") == Val.T
    assert measured.value("EV:0:0") == Val.F


def test_injection_api_glut_and_gap():
    state = ShadowState(1, sparse=True)
    state.inject_glut("+X")
    assert state.value("+X") == Val.B
    state.inject_gap("+X")
    assert state.value("+X") == Val.U


def test_invalid_wire_errors():
    with pytest.raises(IndexError):
        execute_circuit([Instruction("H", target=2)], num_wires=1)
    with pytest.raises(ValueError):
        execute_circuit([Instruction("CNOT", control=0, target=0)], num_wires=1)


def test_execute_added_clifford_gates():
    circuit = [
        Instruction("X", target=0),
        Instruction("Y", target=1),
        Instruction("Z", target=0),
        Instruction("Sdg", target=1),
        Instruction("CZ", control=0, target=1),
        Instruction("SWAP", control=0, target=1),
    ]
    trace = execute_circuit(circuit, num_wires=2, sparse=True)
    assert len(trace) == len(circuit) + 1
    assert trace[-1].carrier == "SWAP"
