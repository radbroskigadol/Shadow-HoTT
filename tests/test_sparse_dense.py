# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

from shadow_hott import Instruction, execute_circuit


def test_sparse_dense_same_final_signature_for_simple_circuit():
    circuit = [
        Instruction("H", target=0),
        Instruction("S", target=0),
        Instruction("CNOT", control=0, target=1),
        Instruction("MEASURE", target=0),
        Instruction("MEASURE", target=1),
    ]
    dense = execute_circuit(circuit, num_wires=2, sparse=False)[-1]
    sparse = execute_circuit(circuit, num_wires=2, sparse=True)[-1]
    assert dense.signature4() == sparse.signature4()
