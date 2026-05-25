# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

import pytest

from shadow_hott import (
    CNOT_LOCAL_TABLE,
    pauli_word_mul,
    transport_single_label,
    verify_transport_soundness,
)
from shadow_hott.pauli import phase_to_real_sign


def test_single_qubit_generator_images():
    assert transport_single_label("+X", "H", target=0) == "+Z"
    assert transport_single_label("+Z", "H", target=0) == "+X"
    assert transport_single_label("+Y", "H", target=0) == "-Y"
    assert transport_single_label("+X", "S", target=0) == "+Y"
    assert transport_single_label("+Y", "S", target=0) == "-X"
    assert transport_single_label("+Z", "S", target=0) == "+Z"


def test_cnot_generator_images():
    assert transport_single_label("+XI", "CNOT", target=1, control=0) == "+XX"
    assert transport_single_label("+ZI", "CNOT", target=1, control=0) == "+ZI"
    assert transport_single_label("+IX", "CNOT", target=1, control=0) == "+IX"
    assert transport_single_label("+IZ", "CNOT", target=1, control=0) == "+ZZ"


def test_transport_soundness_harness():
    report = verify_transport_soundness(max_qubits=2)
    assert report["passed"] is True
    assert report["checks"]


def test_phase_to_real_sign_rejects_imaginary_phase():
    with pytest.raises(ValueError):
        phase_to_real_sign(1j)


def test_pauli_word_mul_known_phase():
    phase, word = pauli_word_mul("X", "Y")
    assert phase == 1j
    assert word == "Z"


def test_added_single_qubit_clifford_images():
    assert transport_single_label("+X", "Sdg", target=0) == "-Y"
    assert transport_single_label("+Y", "Sdg", target=0) == "+X"
    assert transport_single_label("+Z", "Sdg", target=0) == "+Z"
    assert transport_single_label("+Y", "X", target=0) == "-Y"
    assert transport_single_label("+Z", "X", target=0) == "-Z"
    assert transport_single_label("+X", "Y", target=0) == "-X"
    assert transport_single_label("+Z", "Y", target=0) == "-Z"
    assert transport_single_label("+X", "Z", target=0) == "-X"
    assert transport_single_label("+Y", "Z", target=0) == "-Y"


def test_cz_and_swap_generator_images():
    assert transport_single_label("+XI", "CZ", target=1, control=0) == "+XZ"
    assert transport_single_label("+IX", "CZ", target=1, control=0) == "+ZX"
    assert transport_single_label("+ZI", "CZ", target=1, control=0) == "+ZI"
    assert transport_single_label("+IZ", "CZ", target=1, control=0) == "+IZ"
    assert transport_single_label("+XI", "SWAP", target=1, control=0) == "+IX"
    assert transport_single_label("+IZ", "SWAP", target=1, control=0) == "+ZI"
