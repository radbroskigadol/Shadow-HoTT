# Changelog

## 0.2.5

- Added a dependency-free benchmark suite under `benchmarks/benchmark_linter.py`.
- Added measured benchmark outputs in `benchmark_results/` and a top-level `BENCHMARK_REPORT.md`.
- Documented sparse-vs-dense scaling: sparse mode is the large-circuit linter path, while dense mode is exponential and intended for small verification/audit runs.

## 0.2.4

- Added exact signed-Pauli transport for `X`, `Y`, `Z`, `Sdg`, `CZ`, and `SWAP`.
- Added OpenQASM 2 parse/export support for `x`, `y`, `z`, `sdg`, `cz`, and `swap`.
- Extended duck-typed Qiskit and Cirq adapters for the same Clifford gate set.
- Extended the transport verification harness to check `Sdg` as inverse-S, Pauli-gate squares, `CZ^2`, and `SWAP^2`.
- Updated documentation, examples, and certificates to reflect the expanded Clifford linter scope.

## 0.2.3

- Added high-level `lint_instructions`, `lint_openqasm2`, `lint_qiskit`, `lint_cirq`, and `lint_auto` entry points.
- Added real duck-typed Qiskit `QuantumCircuit` conversion using modern `CircuitInstruction` shape and `find_bit` when available.
- Added real duck-typed Cirq `Circuit` conversion using `all_operations()` when available.
- Added `shadow-hott lint-qasm` CLI command with repeatable `--hardware-edge` options.
- Added frontend/CLI tests for Qiskit-like, Cirq-like, OpenQASM, auto dispatch, and JSON report conversion.


## 0.2.2

- Added MIT + CC BY 4.0 split licensing with explicit attribution notice.
- Added SPDX MIT headers to Python source and test files.
- Fixed pyproject metadata for newer setuptools license-expression handling.

## 0.2.1

- Added validation for user-injected labels so invalid or wrong-width labels cannot corrupt signatures.
- Added OpenQASM serialization validation so incomplete instructions fail cleanly instead of emitting malformed q[None] output.


## 0.2.1

- Repackaged the flat prototype into an installable Python package.
- Added exact transport modules for signed Pauli labels.
- Added state, execution, diagnostics, route scoring, adapters, certificates, CLI, tests, and CI.
- Added label-sensitive and hardware-aware route metrics.
- Added explicit claim discipline distinguishing theorem-backed transport from heuristic diagnostics.


---

© 2026 David Betzer. Documentation/exposition licensed under CC BY 4.0. Please attribute as: “Shadow-HoTT by David Betzer.”
