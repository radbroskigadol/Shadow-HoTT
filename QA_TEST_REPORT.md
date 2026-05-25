# Shadow-HoTT QA test report

Package version tested: `0.2.4`

## Result

All package tests and smoke checks passed after extending the supported Clifford linter gate set.

## Checks performed

```text
python -m pytest -q
30 passed

python -m compileall -q shadow_hott examples tests
passed

python -m pip install -e . --no-build-isolation
passed

python examples/basic_usage.py
passed after editable install

shadow-hott verify
passed

shadow-hott certificate --max-qubits 2 --out /tmp/shadow_hott_cert.json
passed

shadow-hott lint-qasm examples/example.qasm --hardware-edge 0,1 --out /tmp/lint-report-v024-installed.json
passed

python -m pip wheel . --no-build-isolation -w /tmp/shadow_hott_wheel_v024
passed

independent NumPy matrix sanity check for H, S, Sdg, X, Y, Z, CNOT, CZ, SWAP
passed
```

## Regression coverage retained and extended

- Invalid user labels are rejected instead of being silently inserted into state.
- Wrong-width Pauli labels are rejected.
- Invalid event labels are rejected.
- OpenQASM export rejects incomplete instructions instead of emitting malformed `q[None]` output.
- OpenQASM export rejects too-small `num_wires` values.
- OpenQASM import/export round-trips the extended Clifford subset.
- Qiskit-like and Cirq-like adapter tests cover `X`, `Y`, `Z`, `Sdg`, `CZ`, and `SWAP`.

---

© 2026 David Betzer. Documentation/exposition licensed under CC BY 4.0. Please attribute as: “Shadow-HoTT by David Betzer.”
