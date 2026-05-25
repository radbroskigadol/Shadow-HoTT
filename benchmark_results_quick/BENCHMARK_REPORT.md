# Shadow-HoTT benchmark report

This benchmark measures the linter's actual core path: signed-Pauli Clifford transport plus Shadow-HoTT diagnostic scoring. It is not a benchmark of full quantum simulation.

## Environment

- **python:** `3.13.5 (main, Jun 25 2025, 18:55:22) [GCC 14.2.0]`
- **platform:** `Linux-4.4.0-x86_64-with-glibc2.41`
- **machine:** `x86_64`
- **processor:** `unknown`
- **cpu_count:** `56`
- **implementation:** `CPython`

## Results

| case | mode | wires | instr. | median s | instr/s | labels/step est. | est. label updates/s | peak tracemalloc MiB | final hw violations |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sparse_4w_250d | sparse | 4 | 250 | 0.124404 | 2,009.6 | 10 | 20,095.8 | 0.51 | 12 |
| sparse_16w_250d | sparse | 16 | 250 | 0.362650 | 689.4 | 34 | 23,438.6 | 1.56 | 1098 |
| sparse_64w_250d | sparse | 64 | 250 | 1.791733 | 139.5 | 130 | 18,138.9 | 7.26 | 206 |
| dense_2w_100d | dense | 2 | 100 | 0.086415 | 1,157.2 | 36 | 41,659.6 | 0.59 | 0 |
| dense_3w_100d | dense | 3 | 100 | 0.277166 | 360.8 | 134 | 48,346.6 | 2.18 | 0 |
| dense_4w_50d | dense | 4 | 50 | 0.552761 | 90.5 | 520 | 47,036.6 | 4.35 | 20 |
| route_eval_4x_16w_80d | route-sparse | 16 | 320 | 0.449754 | 711.5 | 34 | 24,191.0 | 1.02 | 44 |
| openqasm_parse_lint_12w_120d | openqasm2-sparse | 12 | 120 | 0.138970 | 863.5 | 26 | 22,450.9 | 0.63 | 402 |

## Interpretation

- Sparse mode is the intended default for larger linting runs. It transports the explicit active bilateral layer, which starts at `2 + 2n` Pauli labels for `n` wires.
- Dense mode is deliberately exponential: it materializes `2 * 4^n + 2n` labels and is useful for small-width verification/audit runs, not large circuits.
- Route evaluation multiplies lint cost by the number of route variants, then adds comparison/scoring overhead.
- OpenQASM timing includes parser overhead as well as linting, so it should be compared to direct instruction linting only as an end-to-end frontend benchmark.
- `peak_tracemalloc` measures Python allocations seen by `tracemalloc`; it is useful for comparing cases in the same environment, not for exact resident memory claims.
