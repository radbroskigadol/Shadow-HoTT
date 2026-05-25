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
| sparse_4w_250d | sparse | 4 | 250 | 0.118614 | 2,107.7 | 10 | 21,076.8 | 0.51 | 12 |
| sparse_16w_250d | sparse | 16 | 250 | 0.359194 | 696.0 | 34 | 23,664.1 | 1.56 | 1098 |
| sparse_64w_250d | sparse | 64 | 250 | 1.755305 | 142.4 | 130 | 18,515.3 | 7.26 | 206 |
| dense_2w_100d | dense | 2 | 100 | 0.095555 | 1,046.5 | 36 | 37,674.8 | 0.59 | 0 |
| dense_3w_100d | dense | 3 | 100 | 0.290953 | 343.7 | 134 | 46,055.6 | 2.18 | 0 |
| dense_4w_50d | dense | 4 | 50 | 0.563237 | 88.8 | 520 | 46,161.7 | 4.35 | 20 |
| route_eval_4x_16w_80d | route-sparse | 16 | 320 | 0.451542 | 708.7 | 34 | 24,095.2 | 1.02 | 44 |
| openqasm_parse_lint_12w_120d | openqasm2-sparse | 12 | 120 | 0.136411 | 879.7 | 26 | 22,872.1 | 0.63 | 402 |

## Interpretation

- Sparse mode is the intended default for larger linting runs. It transports the explicit active bilateral layer, which starts at `2 + 2n` Pauli labels for `n` wires.
- Dense mode is deliberately exponential: it materializes `2 * 4^n + 2n` labels and is useful for small-width verification/audit runs, not large circuits.
- Route evaluation multiplies lint cost by the number of route variants, then adds comparison/scoring overhead.
- OpenQASM timing includes parser overhead as well as linting, so it should be compared to direct instruction linting only as an end-to-end frontend benchmark.
- `peak_tracemalloc` measures Python allocations seen by `tracemalloc`; it is useful for comparing cases in the same environment, not for exact resident memory claims.
