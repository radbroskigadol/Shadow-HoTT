# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Shadow-HoTT: exact Clifford signed-Pauli transport plus bilateral diagnostics."""
from __future__ import annotations

from .adapters import (
    from_cirq,
    from_cirq_like,
    from_qiskit,
    from_qiskit_like,
    instructions_to_openqasm2,
    parse_openqasm2,
    parse_openqasm2_file,
)
from .certificates import PACKAGE_VERSION, build_certificate, dump_json_report
from .diagnostics import (
    GeometryMetrics,
    calculate_label_shock_profile,
    calculate_shock_profile,
    calculate_support_growth_profile,
    check_determinization,
    get_signature_4,
    state_geometry_metrics,
)
from .engine import apply_gate, apply_measurement, execute_circuit, infer_num_wires
from .pauli import (
    CNOT_LOCAL_TABLE,
    CZ_LOCAL_TABLE,
    distinguished_pauli_label,
    label_to_signed_word,
    normalize_clifford_op,
    pauli_word_mul,
    signed_word_to_label,
    support_weight,
    transport_single_label,
)
from .lint import lint_auto, lint_cirq, lint_instructions, lint_openqasm2, lint_qiskit
from .routes import evaluate_compiler_routes, theta_sweep_report
from .state import ShadowState
from .types import Instruction, Val
from .verification import verify_transport_soundness

__version__ = PACKAGE_VERSION

__all__ = [
    "CNOT_LOCAL_TABLE",
    "CZ_LOCAL_TABLE",
    "GeometryMetrics",
    "Instruction",
    "ShadowState",
    "Val",
    "apply_gate",
    "apply_measurement",
    "build_certificate",
    "calculate_label_shock_profile",
    "calculate_shock_profile",
    "calculate_support_growth_profile",
    "check_determinization",
    "distinguished_pauli_label",
    "dump_json_report",
    "evaluate_compiler_routes",
    "execute_circuit",
    "from_cirq",
    "from_cirq_like",
    "from_qiskit",
    "from_qiskit_like",
    "get_signature_4",
    "infer_num_wires",
    "instructions_to_openqasm2",
    "label_to_signed_word",
    "normalize_clifford_op",
    "lint_auto",
    "lint_cirq",
    "lint_instructions",
    "lint_openqasm2",
    "lint_qiskit",
    "parse_openqasm2",
    "parse_openqasm2_file",
    "pauli_word_mul",
    "signed_word_to_label",
    "state_geometry_metrics",
    "support_weight",
    "theta_sweep_report",
    "transport_single_label",
    "verify_transport_soundness",
]
