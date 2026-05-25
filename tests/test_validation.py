# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

import pytest

from shadow_hott import Instruction, ShadowState, instructions_to_openqasm2


def test_rejects_invalid_user_labels():
    state = ShadowState(1, sparse=True)
    with pytest.raises(ValueError):
        state.inject_truth("bad")
    with pytest.raises(ValueError):
        state.inject_truth("+XX")
    with pytest.raises(IndexError):
        state.inject_truth("EV:5:0")
    with pytest.raises(ValueError):
        state.inject_truth("EV:0:2")


def test_openqasm_serializer_rejects_incomplete_instructions():
    with pytest.raises(ValueError):
        instructions_to_openqasm2([Instruction("H")])
    with pytest.raises(ValueError):
        instructions_to_openqasm2([Instruction("CNOT", target=1)])
    with pytest.raises(ValueError):
        instructions_to_openqasm2([Instruction("CNOT", control=0, target=0)])
    with pytest.raises(ValueError):
        instructions_to_openqasm2([Instruction("H", target=2)], num_wires=2)
