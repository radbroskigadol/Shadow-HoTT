# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Command line interface for quick smoke checks and QASM linting."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable, Tuple

from .adapters import parse_openqasm2
from .certificates import build_certificate, dump_json_report, to_jsonable
from .engine import execute_circuit
from .lint import lint_openqasm2
from .verification import verify_transport_soundness


def _parse_edge(text: str) -> Tuple[int, int]:
    pieces = text.replace(":", ",").split(",")
    if len(pieces) != 2:
        raise argparse.ArgumentTypeError("edge must look like 0,1 or 0:1")
    try:
        a, b = int(pieces[0]), int(pieces[1])
    except ValueError as exc:
        raise argparse.ArgumentTypeError("edge endpoints must be integers") from exc
    if a < 0 or b < 0 or a == b:
        raise argparse.ArgumentTypeError("edge endpoints must be nonnegative and distinct")
    return (a, b)


def _qasm_report(path: str, *, theta: float, sparse: bool, hardware_edges: Iterable[Tuple[int, int]] | None) -> dict:
    source = Path(path).read_text(encoding="utf-8")
    return lint_openqasm2(source, theta=theta, sparse=sparse, hardware_edges=hardware_edges)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="shadow-hott")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("verify", help="run Clifford transport soundness checks")

    cert = sub.add_parser("certificate", help="write a reproducibility certificate")
    cert.add_argument("--out", required=True)
    cert.add_argument("--max-qubits", type=int, default=3)

    run = sub.add_parser("run-qasm", help="run a supported OpenQASM 2 file and emit the final state report")
    run.add_argument("path")
    run.add_argument("--theta", type=float, default=0.5)
    run.add_argument("--sparse", action="store_true")
    run.add_argument("--out")

    lint = sub.add_parser("lint-qasm", help="lint a supported OpenQASM 2 file with Shadow-HoTT diagnostics")
    lint.add_argument("path")
    lint.add_argument("--theta", type=float, default=0.5)
    lint.add_argument("--dense", action="store_true", help="use dense state mode instead of sparse mode")
    lint.add_argument("--hardware-edge", action="append", type=_parse_edge, default=None, help="allowed hardware edge, e.g. 0,1; repeatable")
    lint.add_argument("--out")

    args = parser.parse_args(argv)
    if args.cmd == "verify":
        print(json.dumps(verify_transport_soundness(), indent=2))
        return 0
    if args.cmd == "certificate":
        dump_json_report(build_certificate(max_qubits_verified=args.max_qubits), args.out)
        print(args.out)
        return 0
    if args.cmd == "run-qasm":
        source = Path(args.path).read_text(encoding="utf-8")
        circuit = parse_openqasm2(source)
        trace = execute_circuit(circuit, theta=args.theta, sparse=args.sparse)
        report = {"steps": len(trace) - 1, "final_state": trace[-1], "signature4": trace[-1].signature4()}
        if args.out:
            dump_json_report(report, args.out)
            print(args.out)
        else:
            print(json.dumps(to_jsonable(report), indent=2))
        return 0
    if args.cmd == "lint-qasm":
        report = _qasm_report(args.path, theta=args.theta, sparse=not args.dense, hardware_edges=args.hardware_edge)
        if args.out:
            dump_json_report(report, args.out)
            print(args.out)
        else:
            print(json.dumps(to_jsonable(report), indent=2))
        return 0
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
