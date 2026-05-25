# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

import json
from pathlib import Path

from shadow_hott.cli import main


def test_cli_lint_qasm_writes_report(tmp_path):
    qasm = tmp_path / "demo.qasm"
    out = tmp_path / "report.json"
    qasm.write_text("OPENQASM 2.0;\nqreg q[2];\ncreg c[2];\nh q[0];\ncx q[0],q[1];\n", encoding="utf-8")
    assert main(["lint-qasm", str(qasm), "--hardware-edge", "0,1", "--out", str(out)]) == 0
    payload = json.loads(out.read_text(encoding="utf-8"))
    assert payload["frontend"] == "openqasm2"
    assert payload["num_wires"] == 2
