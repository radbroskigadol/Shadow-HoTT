# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

import json
import subprocess
import sys
from dataclasses import dataclass

import pytest

from shadow_hott import (
    Instruction,
    from_cirq,
    from_qiskit,
    lint_auto,
    lint_cirq,
    lint_instructions,
    lint_openqasm2,
    lint_qiskit,
)
from shadow_hott.certificates import to_jsonable


@dataclass
class FakeQubit:
    index: int


@dataclass
class FakeOperation:
    name: str


@dataclass
class FakeQiskitEntry:
    operation: FakeOperation
    qubits: tuple[FakeQubit, ...]


class FakeQiskitCircuit:
    num_qubits = 2

    def __init__(self):
        self.q0 = FakeQubit(0)
        self.q1 = FakeQubit(1)
        self.data = [
            FakeQiskitEntry(FakeOperation("h"), (self.q0,)),
            FakeQiskitEntry(FakeOperation("s"), (self.q1,)),
            FakeQiskitEntry(FakeOperation("cx"), (self.q0, self.q1)),
            FakeQiskitEntry(FakeOperation("measure"), (self.q0,)),
        ]

    def find_bit(self, qubit):
        return type("FoundBit", (), {"index": qubit.index})()


def test_qiskit_adapter_and_linter_duck_type():
    circuit = FakeQiskitCircuit()
    instructions = from_qiskit(circuit)
    assert instructions == [
        Instruction("H", target=0),
        Instruction("S", target=1),
        Instruction("CNOT", control=0, target=1),
        Instruction("MEASURE", target=0),
    ]
    report = lint_qiskit(circuit, hardware_edges=[(0, 1)])
    assert report["frontend"] == "qiskit"
    assert report["num_wires"] == 2
    assert report["final_signature"] == report["signature4"]
    json.dumps(to_jsonable(report))


def test_qiskit_adapter_rejects_unsupported_gate():
    circuit = FakeQiskitCircuit()
    circuit.data = [FakeQiskitEntry(FakeOperation("rx"), (circuit.q0,))]
    with pytest.raises(ValueError, match="unsupported qiskit operation"):
        from_qiskit(circuit)


@dataclass
class FakeCirqQubit:
    x: int


@dataclass
class FakeCirqGate:
    name: str


@dataclass
class FakeCirqOperation:
    gate: FakeCirqGate
    qubits: tuple[FakeCirqQubit, ...]


class FakeCirqCircuit:
    def __init__(self):
        q0 = FakeCirqQubit(0)
        q1 = FakeCirqQubit(1)
        self._ops = [
            FakeCirqOperation(FakeCirqGate("H"), (q0,)),
            FakeCirqOperation(FakeCirqGate("S"), (q1,)),
            FakeCirqOperation(FakeCirqGate("CNOT"), (q0, q1)),
            FakeCirqOperation(FakeCirqGate("measure"), (q1,)),
        ]

    def all_operations(self):
        return iter(self._ops)


def test_cirq_adapter_and_linter_duck_type():
    circuit = FakeCirqCircuit()
    instructions = from_cirq(circuit)
    assert instructions == [
        Instruction("H", target=0),
        Instruction("S", target=1),
        Instruction("CNOT", control=0, target=1),
        Instruction("MEASURE", target=1),
    ]
    report = lint_cirq(circuit, num_wires=2)
    assert report["frontend"] == "cirq"
    assert report["num_instructions"] == 4
    json.dumps(to_jsonable(report))


def test_lint_auto_dispatches_common_inputs():
    qasm = """OPENQASM 2.0;
    qreg q[2];
    creg c[2];
    h q[0];
    cx q[0],q[1];
    measure q[0] -> c[0];
    """
    assert lint_auto(qasm)["frontend"] == "openqasm2"
    assert lint_auto([Instruction("H", target=0)])["frontend"] == "instructions"
    assert lint_auto(FakeQiskitCircuit())["frontend"] == "qiskit"
    assert lint_auto(FakeCirqCircuit(), num_wires=2)["frontend"] == "cirq"


def test_lint_instructions_and_openqasm_reports_are_jsonable():
    report = lint_instructions([Instruction("H", target=0)], hardware_edges=[(0, 1)])
    assert report["frontend"] == "instructions"
    json.dumps(to_jsonable(report))

    qasm_report = lint_openqasm2("OPENQASM 2.0;\nqreg q[1];\nh q[0];\n")
    assert qasm_report["frontend"] == "openqasm2"
    json.dumps(to_jsonable(qasm_report))


def test_qiskit_adapter_extended_clifford_duck_type():
    circuit = FakeQiskitCircuit()
    circuit.data = [
        FakeQiskitEntry(FakeOperation("x"), (circuit.q0,)),
        FakeQiskitEntry(FakeOperation("y"), (circuit.q1,)),
        FakeQiskitEntry(FakeOperation("z"), (circuit.q0,)),
        FakeQiskitEntry(FakeOperation("sdg"), (circuit.q1,)),
        FakeQiskitEntry(FakeOperation("cz"), (circuit.q0, circuit.q1)),
        FakeQiskitEntry(FakeOperation("swap"), (circuit.q0, circuit.q1)),
    ]
    assert from_qiskit(circuit) == [
        Instruction("X", target=0),
        Instruction("Y", target=1),
        Instruction("Z", target=0),
        Instruction("SDG", target=1),
        Instruction("CZ", control=0, target=1),
        Instruction("SWAP", control=0, target=1),
    ]
    report = lint_qiskit(circuit, hardware_edges=[(0, 1)])
    assert report["frontend"] == "qiskit"
    assert report["num_instructions"] == 6


def test_cirq_adapter_extended_clifford_duck_type():
    q0 = FakeCirqQubit(0)
    q1 = FakeCirqQubit(1)
    circuit = type("Circuit", (), {})()
    circuit._ops = [
        FakeCirqOperation(FakeCirqGate("X"), (q0,)),
        FakeCirqOperation(FakeCirqGate("Y"), (q1,)),
        FakeCirqOperation(FakeCirqGate("Z"), (q0,)),
        FakeCirqOperation(FakeCirqGate("sdg"), (q1,)),
        FakeCirqOperation(FakeCirqGate("CZ"), (q0, q1)),
        FakeCirqOperation(FakeCirqGate("SWAP"), (q0, q1)),
    ]
    circuit.all_operations = lambda: iter(circuit._ops)
    assert from_cirq(circuit) == [
        Instruction("X", target=0),
        Instruction("Y", target=1),
        Instruction("Z", target=0),
        Instruction("SDG", target=1),
        Instruction("CZ", control=0, target=1),
        Instruction("SWAP", control=0, target=1),
    ]
    report = lint_cirq(circuit, num_wires=2)
    assert report["frontend"] == "cirq"
    assert report["num_instructions"] == 6
