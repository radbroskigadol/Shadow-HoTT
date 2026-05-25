# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Core public types for Shadow-HoTT."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Val(Enum):
    """Four-valued threshold class for a bilateral truth/falsity score."""

    T = "True_Only"
    F = "False_Only"
    B = "Both_Glut"
    U = "Neither_Gap"


@dataclass(frozen=True, slots=True)
class Instruction:
    """A minimal circuit instruction.

    Supported operations are ``H``, ``S``, ``Sdg``, ``X``, ``Y``, ``Z``,
    ``CNOT``/``CX``, ``CZ``, ``SWAP``, ``MEASURE``, ``M``, and
    ``MEASURE_Z``. The engine intentionally covers Clifford label transport, not
    arbitrary unitary simulation.
    """

    op: str
    target: Optional[int] = None
    control: Optional[int] = None

    def normalized_op(self) -> str:
        return self.op.upper()
