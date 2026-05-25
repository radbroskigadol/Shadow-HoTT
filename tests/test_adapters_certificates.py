# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

import json

from shadow_hott import Instruction, build_certificate, instructions_to_openqasm2, parse_openqasm2
from shadow_hott.certificates import to_jsonable


def test_openqasm_roundtrip_subset():
    circuit = [Instruction("H", target=0), Instruction("S", target=1), Instruction("CNOT", control=0, target=1), Instruction("MEASURE", target=0)]
    qasm = instructions_to_openqasm2(circuit, num_wires=2)
    parsed = parse_openqasm2(qasm)
    assert parsed == circuit


def test_certificate_jsonable():
    cert = build_certificate(max_qubits_verified=1)
    payload = to_jsonable(cert)
    text = json.dumps(payload)
    assert "shadow-hott" in text
    assert payload["scope"]["not_claimed"]


def test_openqasm_roundtrip_extended_clifford_subset():
    circuit = [
        Instruction("X", target=0),
        Instruction("Y", target=1),
        Instruction("Z", target=0),
        Instruction("SDG", target=1),
        Instruction("CZ", control=0, target=1),
        Instruction("SWAP", control=0, target=1),
        Instruction("MEASURE", target=1),
    ]
    qasm = instructions_to_openqasm2(circuit, num_wires=2)
    parsed = parse_openqasm2(qasm)
    assert parsed == circuit
