# Shadow-HoTT audit fix report

This package fixes the structural/code issues identified in the audit of the public `radbroskigadol/Shadow-HoTT` repository.

## Fixed

1. **Broken package layout**
   - Replaced the extensionless `Q-Path` flat file with a real `shadow_hott/` package.
   - Added `pyproject.toml` and package metadata.
   - Added `py.typed`.

2. **README/API mismatch**
   - Removed the stale `from shadow_engine import ...` usage pattern.
   - Added tested imports from `shadow_hott`.

3. **Collapsed/invalid raw source formatting risk**
   - Rewrote all source files as formatted Python modules.
   - Verified importability, pytest execution, and CLI execution.

4. **Exact math separated from heuristic semantics**
   - `pauli.py`: exact signed Pauli algebra and Clifford transport.
   - `state.py`: bilateral truth/falsity state and threshold cache.
   - `engine.py`: circuit execution and measurement proxy.
   - `diagnostics.py`: state/trace metrics.
   - `routes.py`: route evaluation.
   - `verification.py`: exact transport soundness checks.

5. **Weak count-only route metric**
   - Retained legacy signature shock for compatibility.
   - Added label-wise cache shock.
   - Added support-growth metrics.
   - Added active support totals, nonlocal label count, and hardware-coupling violation score.
   - Route selection now uses a composite score instead of signature shock alone.

6. **Measurement claim calibration**
   - Measurement is documented and implemented as a deterministic diagnostic collapse proxy.
   - The docs explicitly state it is not Born sampling and not a full stabilizer update.

7. **No clean error-injection API**
   - Added `inject_glut`, `inject_gap`, `inject_truth`, and `inject_falsity` on `ShadowState`.

8. **No adapters**
   - Added dependency-free OpenQASM 2 subset parser/exporter.
   - Added first-class lint helpers and best-effort Qiskit-like/Cirq-like conversion hooks without hard dependencies.

9. **No reproducibility/certificate layer**
   - Added `build_certificate` and `dump_json_report`.
   - Certificate includes package version, transport-table version, scoring version, platform, Python version, transport checks, and claim-scope boundaries.

10. **No formal test suite**
    - Added pytest tests for Pauli transport, engine execution, sparse/dense equivalence, route metrics, adapters, frontend linting, CLI linting, and certificate serialization.
    - Current local result: `30 passed`.

11. **No CI**
    - Added `.github/workflows/tests.yml` for Python 3.10, 3.11, and 3.12.

## Verified locally

```text
python -m pytest -q
30 passed

python -m pip install -e . --no-build-isolation
Successfully installed shadow-hott-0.2.4

shadow-hott verify
passed

shadow-hott lint-qasm examples/example.qasm --hardware-edge 0,1 --out /tmp/lint-report-v024-installed.json
passed
```

## v0.2.4 extended Clifford linter update

The exact transport layer now covers `H`, `S`, `Sdg`, `X`, `Y`, `Z`, `CNOT`/`CX`, `CZ`, and `SWAP`. OpenQASM, Qiskit-like, and Cirq-like frontends were extended to parse/convert those gates. The certificate scope and verification harness were updated accordingly.

## Remaining external steps

These are not code defects in the package itself, but should be handled before public release:

- License files are now included: MIT for code, CC BY 4.0 for docs/exposition.
- Decide whether the package name should stay `shadow-hott` or be changed for naming or trademark reasons.
- Add downstream-user-specific Qiskit/Cirq adapters if their runtime requires exact native objects rather than lightweight conversion hooks.
- Add benchmark comparisons against chosen stabilizer/tableau baselines in the target environment.
- Add Lean/mathlib integration only when you are ready to connect the formal-proof layer.


---

© 2026 David Betzer. Documentation/exposition licensed under CC BY 4.0. Please attribute as: “Shadow-HoTT by David Betzer.”
