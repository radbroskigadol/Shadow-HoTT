# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

from shadow_hott import Instruction, evaluate_compiler_routes, execute_circuit, verify_transport_soundness

circuit_a = [
    Instruction("H", target=0),
    Instruction("S", target=0),
    Instruction("Sdg", target=0),
    Instruction("CZ", control=0, target=1),
    Instruction("SWAP", control=0, target=1),
    Instruction("CNOT", control=0, target=1),
    Instruction("MEASURE", target=0),
    Instruction("MEASURE", target=1),
]

circuit_b = [
    Instruction("S", target=1),
    Instruction("H", target=1),
    Instruction("CNOT", control=1, target=0),
    Instruction("MEASURE", target=1),
    Instruction("MEASURE", target=0),
]

trace = execute_circuit(circuit_a, num_wires=2, sparse=True)
print("final signature:", trace[-1].signature4())

routes = evaluate_compiler_routes([circuit_a, circuit_b], num_wires=2, sparse=True, hardware_edges=[(0, 1)])
print("winner:", routes["optimal_route"]["circuit_id"])
print("selection order:", routes["selection_order"])

print(verify_transport_soundness(max_qubits=2))
