# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Adapters for common circuit inputs.

Shadow-HoTT keeps Qiskit and Cirq optional. The functions below consume real
Qiskit/Cirq objects when present, but they use duck typing instead of importing
those libraries at module import time. Unsupported operations raise ``ValueError``
so callers do not accidentally lint a partially ignored circuit.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Iterable, Sequence

from .pauli import normalize_clifford_op
from .types import Instruction


_QASM_LINE_RE = re.compile(r"^(?P<op>h|s|sdg|x|y|z|cx|cnot|cz|swap|measure)\s+(?P<body>.+?);?$", re.IGNORECASE)
_QREG_RE = re.compile(r"q\[(\d+)\]")
_CREG_RE = re.compile(r"c\[(\d+)\]")
_SINGLE_QASM_OPS = {"h": "H", "s": "S", "sdg": "SDG", "x": "X", "y": "Y", "z": "Z"}
_TWO_QASM_OPS = {"cx": "CNOT", "cnot": "CNOT", "cz": "CZ", "swap": "SWAP"}
_SINGLE_QISKIT_OPS = {"h": "H", "s": "S", "sdg": "SDG", "x": "X", "y": "Y", "z": "Z"}
_TWO_QISKIT_OPS = {"cx": "CNOT", "cnot": "CNOT", "cz": "CZ", "swap": "SWAP"}


def parse_openqasm2(source: str) -> list[Instruction]:
    """Parse a tiny supported subset of OpenQASM 2.

    Supported statements: ``h/s/sdg/x/y/z q[i];``, ``cx/cnot/cz/swap q[i],q[j];``
    and ``measure q[i] -> c[j];``. Unsupported gates raise ``ValueError``.
    """

    circuit: list[Instruction] = []
    for raw_line in source.splitlines():
        line = raw_line.split("//", 1)[0].strip()
        if not line:
            continue
        lowered = line.lower()
        if lowered.startswith(("openqasm", "include", "qreg", "creg", "barrier")):
            continue
        match = _QASM_LINE_RE.match(line)
        if not match:
            raise ValueError(f"unsupported or invalid OpenQASM line: {raw_line!r}")
        op = match.group("op").lower()
        body = match.group("body")
        qbits = [int(x) for x in _QREG_RE.findall(body)]
        if op in _SINGLE_QASM_OPS:
            if len(qbits) != 1:
                raise ValueError(f"{op} expects one qubit: {raw_line!r}")
            circuit.append(Instruction(_SINGLE_QASM_OPS[op], target=qbits[0]))
        elif op in _TWO_QASM_OPS:
            if len(qbits) != 2:
                raise ValueError(f"{op} expects two qubits: {raw_line!r}")
            if qbits[0] == qbits[1]:
                raise ValueError(f"{op} expects distinct qubits: {raw_line!r}")
            circuit.append(Instruction(_TWO_QASM_OPS[op], control=qbits[0], target=qbits[1]))
        elif op == "measure":
            if len(qbits) != 1:
                raise ValueError(f"measure expects one qubit: {raw_line!r}")
            circuit.append(Instruction("MEASURE", target=qbits[0]))
        else:  # pragma: no cover, regex prevents this
            raise ValueError(f"unsupported op: {op!r}")
    return circuit


def parse_openqasm2_file(path: str | Path) -> list[Instruction]:
    """Read and parse a supported OpenQASM 2 file."""

    return parse_openqasm2(Path(path).read_text(encoding="utf-8"))


def instructions_to_openqasm2(circuit: Sequence[Instruction], *, num_wires: int | None = None) -> str:
    """Serialize supported instructions to a minimal OpenQASM 2 string.

    Invalid or incomplete instructions raise ``ValueError`` instead of emitting
    malformed QASM such as ``q[None]``.
    """

    validated: list[Instruction] = []
    max_wire = -1
    for inst in circuit:
        op = normalize_clifford_op(inst.normalized_op())
        if op in {"H", "S", "SDG", "X", "Y", "Z", "MEASURE"}:
            if inst.target is None:
                raise ValueError(f"{op} requires target for OpenQASM serialization: {inst!r}")
            if inst.target < 0:
                raise ValueError(f"negative target wire in instruction: {inst!r}")
            max_wire = max(max_wire, inst.target)
        elif op in {"CNOT", "CZ", "SWAP"}:
            if inst.control is None or inst.target is None:
                raise ValueError(f"{op} requires two wires for OpenQASM serialization: {inst!r}")
            if inst.control < 0 or inst.target < 0:
                raise ValueError(f"negative wire in instruction: {inst!r}")
            if inst.control == inst.target:
                raise ValueError(f"{op} wires must differ: {inst!r}")
            max_wire = max(max_wire, inst.control, inst.target)
        else:
            raise ValueError(f"unsupported instruction for OpenQASM serialization: {inst!r}")
        validated.append(inst)

    inferred_wires = max_wire + 1 if max_wire >= 0 else 1
    if num_wires is None:
        num_wires = inferred_wires
    elif num_wires <= 0:
        raise ValueError("num_wires must be positive")
    elif max_wire >= num_wires:
        raise ValueError(f"num_wires={num_wires} is too small for max referenced wire {max_wire}")

    lines = ["OPENQASM 2.0;", 'include "qelib1.inc";', f"qreg q[{num_wires}];", f"creg c[{num_wires}];"]
    for inst in validated:
        op = normalize_clifford_op(inst.normalized_op())
        if op in {"H", "S", "X", "Y", "Z"}:
            lines.append(f"{op.lower()} q[{inst.target}];")
        elif op == "SDG":
            lines.append(f"sdg q[{inst.target}];")
        elif op == "CNOT":
            lines.append(f"cx q[{inst.control}],q[{inst.target}];")
        elif op == "CZ":
            lines.append(f"cz q[{inst.control}],q[{inst.target}];")
        elif op == "SWAP":
            lines.append(f"swap q[{inst.control}],q[{inst.target}];")
        elif op == "MEASURE":
            lines.append(f"measure q[{inst.target}] -> c[{inst.target}];")
    return "\n".join(lines) + "\n"


def from_qiskit(circuit: Any) -> list[Instruction]:
    """Convert a Qiskit ``QuantumCircuit``-like object into instructions.

    This supports the common Qiskit 0.x/1.x/2.x ``circuit.data`` shapes:
    ``CircuitInstruction(operation, qubits, clbits)`` and the older tuple form
    ``(operation, qargs, cargs)``. Barriers, delays, and identity gates are
    ignored; unsupported computational gates raise ``ValueError``.
    """

    data = getattr(circuit, "data", None)
    if data is None:
        raise TypeError("from_qiskit expects an object with a .data attribute")

    out: list[Instruction] = []
    for entry in data:
        operation = getattr(entry, "operation", None)
        qargs = getattr(entry, "qubits", None)
        if operation is None or qargs is None:
            try:
                operation, qargs = entry[0], entry[1]
            except Exception as exc:  # pragma: no cover - defensive shape guard
                raise TypeError(f"cannot read Qiskit instruction entry: {entry!r}") from exc
        name = _operation_name(operation)
        if name in {"barrier", "delay", "id", "iden"}:
            continue
        indices = [_qubit_index(q, owner=circuit) for q in qargs]
        if name in _SINGLE_QISKIT_OPS:
            _require_arity(name, indices, 1)
            out.append(Instruction(_SINGLE_QISKIT_OPS[name], target=indices[0]))
        elif name in _TWO_QISKIT_OPS:
            _require_arity(name, indices, 2)
            out.append(Instruction(_TWO_QISKIT_OPS[name], control=indices[0], target=indices[1]))
        elif name in {"measure", "measure_z"}:
            _require_arity(name, indices, 1)
            out.append(Instruction("MEASURE", target=indices[0]))
        else:
            raise ValueError(f"unsupported qiskit operation for Shadow-HoTT linter: {name!r}")
    return out


def from_qiskit_like(circuit: Any) -> list[Instruction]:
    """Backward-compatible alias for ``from_qiskit``."""

    return from_qiskit(circuit)


def from_cirq(circuit_or_operations: Any) -> list[Instruction]:
    """Convert a Cirq ``Circuit`` or operation iterable into instructions.

    Cirq is optional. The adapter checks ``all_operations()`` when present, then
    falls back to treating the input as an iterable of operation-like objects.
    Supported operations are H, S, Sdg, X, Y, Z, CNOT/CX, CZ, SWAP, and measurement.
    """

    if hasattr(circuit_or_operations, "all_operations"):
        operations = list(circuit_or_operations.all_operations())
    else:
        operations = list(circuit_or_operations)

    out: list[Instruction] = []
    for op_obj in operations:
        # Some callers pass Moments; flatten one level if a moment-like object
        # exposes an operations list but is not itself a gate operation.
        if not hasattr(op_obj, "qubits") and hasattr(op_obj, "operations"):
            out.extend(from_cirq(getattr(op_obj, "operations")))
            continue
        gate = getattr(op_obj, "gate", op_obj)
        name = _cirq_gate_name(gate)
        qubits = list(getattr(op_obj, "qubits", []))
        indices = [_qubit_index(q) for q in qubits]
        if name in _SINGLE_QISKIT_OPS:
            _require_arity(name, indices, 1)
            out.append(Instruction(_SINGLE_QISKIT_OPS[name], target=indices[0]))
        elif name in _TWO_QISKIT_OPS:
            _require_arity(name, indices, 2)
            out.append(Instruction(_TWO_QISKIT_OPS[name], control=indices[0], target=indices[1]))
        elif name == "measure":
            _require_arity(name, indices, 1)
            out.append(Instruction("MEASURE", target=indices[0]))
        else:
            raise ValueError(f"unsupported cirq operation for Shadow-HoTT linter: {name!r}")
    return out


def from_cirq_like(operations: Iterable[Any]) -> list[Instruction]:
    """Backward-compatible alias for ``from_cirq``."""

    return from_cirq(operations)


def _operation_name(operation: Any) -> str:
    name = getattr(operation, "name", None)
    if name is None:
        name = getattr(operation, "_name", None)
    if name is None:
        name = operation.__class__.__name__
    return str(name).lower()


def _near(value: Any, target: float) -> bool:
    try:
        return abs(float(value) - target) < 1e-12
    except Exception:
        return False


def _cirq_gate_name(gate: Any) -> str:
    text = str(gate).strip().lower()
    cls = gate.__class__.__name__.lower()
    explicit_name = getattr(gate, "name", None)
    if explicit_name is not None:
        explicit = str(explicit_name).lower()
        if explicit in {"h", "s", "sdg", "x", "y", "z", "cnot", "cx", "cz", "swap", "measure"}:
            return explicit

    exponent = getattr(gate, "exponent", None)

    # Common Cirq string/class forms. Fractional non-Clifford powers are not accepted.
    if text in {"h", "cirq.h"} or cls == "hpowgate":
        return "h"
    if text in {"s", "cirq.s"}:
        return "s"
    if text in {"sdg", "s**-1", "cirq.s**-1"}:
        return "sdg"
    if text in {"x", "cirq.x"} or (cls == "xpowgate" and (exponent is None or _near(exponent, 1.0))):
        return "x"
    if text in {"y", "cirq.y"} or (cls == "ypowgate" and (exponent is None or _near(exponent, 1.0))):
        return "y"
    if text in {"z", "cirq.z"} or (cls == "zpowgate" and (exponent is None or _near(exponent, 1.0))):
        return "z"
    if cls == "zpowgate":
        if exponent is not None and _near(exponent, 0.5):
            return "s"
        if exponent is not None and _near(exponent, -0.5):
            return "sdg"
    if text in {"cnot", "cx", "cirq.cnot"} or cls == "cnotpowgate":
        return "cnot"
    if text in {"cz", "cirq.cz"} or cls == "czpowgate":
        return "cz"
    if text in {"swap", "cirq.swap"} or cls == "swappowgate":
        return "swap"
    if "measurement" in cls or text.startswith("measure") or "measure" in text:
        return "measure"
    return text or cls


def _qubit_index(qubit: Any, *, owner: Any | None = None) -> int:
    if owner is not None and hasattr(owner, "find_bit"):
        try:
            found = owner.find_bit(qubit)
            return int(getattr(found, "index", found[0]))
        except Exception:
            pass
    for attr in ("_index", "index", "x"):
        if hasattr(qubit, attr):
            value = getattr(qubit, attr)
            if callable(value):
                value = value()
            return int(value)
    text = str(qubit)
    match = re.search(r"(\d+)(?!.*\d)", text)
    if match:
        return int(match.group(1))
    raise ValueError(f"cannot infer qubit index from {qubit!r}")


def _require_arity(name: str, indices: Sequence[int], expected: int) -> None:
    if len(indices) != expected:
        raise ValueError(f"{name!r} expects {expected} qubit(s), got {len(indices)}")
