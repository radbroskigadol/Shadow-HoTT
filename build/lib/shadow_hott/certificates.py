# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Versioned certificate/report helpers."""
from __future__ import annotations

import json
import platform
import sys
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from .verification import verify_transport_soundness

PACKAGE_VERSION = "0.2.5"
TRANSPORT_TABLE_VERSION = "clifford-h-s-sdg-pauli-cnot-cz-swap-v2"
SCORING_VERSION = "bilateral-threshold-label-support-v2"


def build_certificate(*, max_qubits_verified: int = 3, extra: Mapping[str, Any] | None = None) -> dict[str, Any]:
    """Build a reproducibility certificate for a run or release."""

    cert: dict[str, Any] = {
        "package": "shadow-hott",
        "package_version": PACKAGE_VERSION,
        "transport_table_version": TRANSPORT_TABLE_VERSION,
        "scoring_version": SCORING_VERSION,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version,
        "platform": platform.platform(),
        "transport_soundness": verify_transport_soundness(max_qubits=max_qubits_verified),
        "scope": {
            "exact": ["signed Pauli label transport for H, S, Sdg, X, Y, Z, CNOT/CX, CZ, SWAP"],
            "heuristic": [
                "bilateral truth/falsity scoring",
                "threshold cache",
                "deterministic measurement proxy",
                "route diagnostics",
            ],
            "not_claimed": [
                "Born-rule quantum sampling",
                "full stabilizer measurement update",
                "arbitrary non-Clifford simulation",
            ],
        },
    }
    if extra:
        cert["extra"] = dict(extra)
    return cert


def to_jsonable(value: Any) -> Any:
    """Convert report values, dataclasses, and states to JSON-friendly objects."""

    from .state import ShadowState

    if isinstance(value, ShadowState):
        return {
            "num_wires": value.num_wires,
            "theta": value.theta,
            "sparse": value.sparse,
            "carrier": value.carrier,
            "provenance": value.provenance,
            "signature4": value.signature4(),
            "last_measurements": value.last_measurements,
        }
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [to_jsonable(v) for v in value]
    return value


def dump_json_report(report: Any, path: str | Path) -> None:
    """Write a JSON report with stable indentation."""

    Path(path).write_text(json.dumps(to_jsonable(report), indent=2, sort_keys=True), encoding="utf-8")
