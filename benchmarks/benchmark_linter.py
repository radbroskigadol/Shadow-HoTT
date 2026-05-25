# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT
"""Benchmark the Shadow-HoTT Clifford/Pauli linter.

This benchmark intentionally measures the package's actual core task:
exact signed-Pauli label transport plus Shadow-HoTT diagnostic scoring.
It does not benchmark full quantum simulation, Born sampling, or arbitrary
non-Clifford execution, because those are outside the package scope.

Usage:
    python benchmarks/benchmark_linter.py --out benchmark_results
"""
from __future__ import annotations

import argparse
import csv
import gc
import json
import math
import os
import platform
import random
import statistics
import sys
import time
import tracemalloc
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Sequence

# Allow running from an unpacked source tree without installation.
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from shadow_hott import (  # noqa: E402
    Instruction,
    evaluate_compiler_routes,
    lint_instructions,
    lint_openqasm2,
)
from shadow_hott.adapters import instructions_to_openqasm2  # noqa: E402
from shadow_hott.certificates import build_certificate, to_jsonable  # noqa: E402

SINGLE_GATES = ("H", "S", "Sdg", "X", "Y", "Z")
TWO_GATES = ("CNOT", "CZ", "SWAP")


@dataclass(slots=True)
class BenchCase:
    name: str
    mode: str
    num_wires: int
    depth: int
    repeats: int
    median_seconds: float
    best_seconds: float
    worst_seconds: float
    instructions_per_second: float
    labels_per_step_estimate: int
    estimated_label_updates_per_second: float
    peak_tracemalloc_bytes: int
    final_signature: list[int] | None = None
    final_active_labels: int | None = None
    final_active_total_support: int | None = None
    final_nonlocal_label_count: int | None = None
    final_hardware_violation_score: int | None = None
    notes: str = ""


def _cpu_name() -> str:
    # Portable enough for Linux/macOS/Windows; best effort only.
    try:
        if Path("/proc/cpuinfo").exists():
            for line in Path("/proc/cpuinfo").read_text(errors="ignore").splitlines():
                if line.lower().startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return platform.processor() or platform.machine() or "unknown"


def environment() -> dict[str, object]:
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "processor": _cpu_name(),
        "cpu_count": os.cpu_count(),
        "implementation": platform.python_implementation(),
    }


def random_clifford_circuit(
    num_wires: int,
    depth: int,
    *,
    seed: int,
    two_qubit_probability: float = 0.45,
    measure_tail: bool = False,
) -> list[Instruction]:
    rng = random.Random(seed)
    circuit: list[Instruction] = []
    for _ in range(depth):
        if num_wires >= 2 and rng.random() < two_qubit_probability:
            a, b = rng.sample(range(num_wires), 2)
            circuit.append(Instruction(rng.choice(TWO_GATES), control=a, target=b))
        else:
            circuit.append(Instruction(rng.choice(SINGLE_GATES), target=rng.randrange(num_wires)))
    if measure_tail:
        circuit.extend(Instruction("MEASURE", target=w) for w in range(num_wires))
    return circuit


def line_hardware(num_wires: int) -> list[tuple[int, int]]:
    return [(i, i + 1) for i in range(num_wires - 1)]


def labels_per_step_estimate(num_wires: int, *, sparse: bool) -> int:
    if sparse:
        # Initial sparse active layer: +I/-I and +/-Z on each wire.
        return 2 + 2 * num_wires
    return 2 * (4**num_wires) + 2 * num_wires


def _run_once(
    circuit: Sequence[Instruction],
    *,
    num_wires: int,
    sparse: bool,
    hardware_edges: Iterable[tuple[int, int]] | None,
) -> tuple[float, dict[str, object], int]:
    gc.collect()
    tracemalloc.start()
    start = time.perf_counter()
    report = lint_instructions(
        circuit,
        num_wires=num_wires,
        sparse=sparse,
        hardware_edges=hardware_edges,
        include_trace=False,
    )
    elapsed = time.perf_counter() - start
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return elapsed, report, peak


def benchmark_lint_case(
    name: str,
    *,
    num_wires: int,
    depth: int,
    sparse: bool,
    repeats: int,
    seed: int,
    hardware: str = "line",
) -> BenchCase:
    circuit = random_clifford_circuit(num_wires, depth, seed=seed)
    edges = line_hardware(num_wires) if hardware == "line" else None

    # Warmup. Kept outside timing table.
    lint_instructions(circuit[: min(10, len(circuit))], num_wires=num_wires, sparse=sparse, hardware_edges=edges)

    times: list[float] = []
    peaks: list[int] = []
    last_report: dict[str, object] | None = None
    old_gc_state = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            elapsed, report, peak = _run_once(circuit, num_wires=num_wires, sparse=sparse, hardware_edges=edges)
            times.append(elapsed)
            peaks.append(peak)
            last_report = report
    finally:
        if old_gc_state:
            gc.enable()

    assert last_report is not None
    geometry = last_report["final_geometry"]
    geom = asdict(geometry) if hasattr(geometry, "__dataclass_fields__") else dict(geometry)  # type: ignore[arg-type]
    median = statistics.median(times)
    labels = labels_per_step_estimate(num_wires, sparse=sparse)
    return BenchCase(
        name=name,
        mode="sparse" if sparse else "dense",
        num_wires=num_wires,
        depth=depth,
        repeats=repeats,
        median_seconds=median,
        best_seconds=min(times),
        worst_seconds=max(times),
        instructions_per_second=(depth / median) if median else math.inf,
        labels_per_step_estimate=labels,
        estimated_label_updates_per_second=(depth * labels / median) if median else math.inf,
        peak_tracemalloc_bytes=max(peaks),
        final_signature=list(last_report["final_signature"]),  # type: ignore[arg-type]
        final_active_labels=int(geom["active_label_count"]),
        final_active_total_support=int(geom["active_total_support"]),
        final_nonlocal_label_count=int(geom["nonlocal_label_count"]),
        final_hardware_violation_score=int(geom["hardware_violation_score"]),
    )


def benchmark_route_case(*, num_wires: int, depth: int, variants: int, repeats: int, seed: int) -> BenchCase:
    circuits = [random_clifford_circuit(num_wires, depth, seed=seed + i) for i in range(variants)]
    edges = line_hardware(num_wires)
    evaluate_compiler_routes([c[: min(10, len(c))] for c in circuits], num_wires=num_wires, sparse=True, hardware_edges=edges)
    times: list[float] = []
    peaks: list[int] = []
    last_report: dict[str, object] | None = None
    old_gc_state = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            gc.collect()
            tracemalloc.start()
            start = time.perf_counter()
            report = evaluate_compiler_routes(circuits, num_wires=num_wires, sparse=True, hardware_edges=edges)
            elapsed = time.perf_counter() - start
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            times.append(elapsed)
            peaks.append(peak)
            last_report = report
    finally:
        if old_gc_state:
            gc.enable()
    assert last_report is not None
    median = statistics.median(times)
    instructions = depth * variants
    labels = labels_per_step_estimate(num_wires, sparse=True)
    optimal = last_report["optimal_route"]
    geometry = optimal["final_geometry"]
    geom = asdict(geometry) if hasattr(geometry, "__dataclass_fields__") else dict(geometry)  # type: ignore[arg-type]
    return BenchCase(
        name=f"route_eval_{variants}x_{num_wires}w_{depth}d",
        mode="route-sparse",
        num_wires=num_wires,
        depth=instructions,
        repeats=repeats,
        median_seconds=median,
        best_seconds=min(times),
        worst_seconds=max(times),
        instructions_per_second=(instructions / median) if median else math.inf,
        labels_per_step_estimate=labels,
        estimated_label_updates_per_second=(instructions * labels / median) if median else math.inf,
        peak_tracemalloc_bytes=max(peaks),
        final_signature=list(optimal["final_signature"]),
        final_active_labels=int(geom["active_label_count"]),
        final_active_total_support=int(geom["active_total_support"]),
        final_nonlocal_label_count=int(geom["nonlocal_label_count"]),
        final_hardware_violation_score=int(geom["hardware_violation_score"]),
        notes=f"winner={optimal['circuit_id']}; selection={last_report['selection_order']}",
    )


def benchmark_qasm_case(*, num_wires: int, depth: int, repeats: int, seed: int) -> BenchCase:
    circuit = random_clifford_circuit(num_wires, depth, seed=seed)
    qasm = instructions_to_openqasm2(circuit, num_wires=num_wires)
    edges = line_hardware(num_wires)
    lint_openqasm2(qasm, num_wires=num_wires, sparse=True, hardware_edges=edges)
    times: list[float] = []
    peaks: list[int] = []
    last_report: dict[str, object] | None = None
    old_gc_state = gc.isenabled()
    gc.disable()
    try:
        for _ in range(repeats):
            gc.collect()
            tracemalloc.start()
            start = time.perf_counter()
            report = lint_openqasm2(qasm, num_wires=num_wires, sparse=True, hardware_edges=edges)
            elapsed = time.perf_counter() - start
            _, peak = tracemalloc.get_traced_memory()
            tracemalloc.stop()
            times.append(elapsed)
            peaks.append(peak)
            last_report = report
    finally:
        if old_gc_state:
            gc.enable()
    assert last_report is not None
    geometry = last_report["final_geometry"]
    geom = asdict(geometry) if hasattr(geometry, "__dataclass_fields__") else dict(geometry)  # type: ignore[arg-type]
    median = statistics.median(times)
    labels = labels_per_step_estimate(num_wires, sparse=True)
    return BenchCase(
        name=f"openqasm_parse_lint_{num_wires}w_{depth}d",
        mode="openqasm2-sparse",
        num_wires=num_wires,
        depth=depth,
        repeats=repeats,
        median_seconds=median,
        best_seconds=min(times),
        worst_seconds=max(times),
        instructions_per_second=(depth / median) if median else math.inf,
        labels_per_step_estimate=labels,
        estimated_label_updates_per_second=(depth * labels / median) if median else math.inf,
        peak_tracemalloc_bytes=max(peaks),
        final_signature=list(last_report["final_signature"]),  # type: ignore[arg-type]
        final_active_labels=int(geom["active_label_count"]),
        final_active_total_support=int(geom["active_total_support"]),
        final_nonlocal_label_count=int(geom["nonlocal_label_count"]),
        final_hardware_violation_score=int(geom["hardware_violation_score"]),
        notes="includes OpenQASM text parse time",
    )


def write_csv(cases: Sequence[BenchCase], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rows = [asdict(c) for c in cases]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def write_markdown(cases: Sequence[BenchCase], env: dict[str, object], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines: list[str] = []
    lines.append("# Shadow-HoTT benchmark report\n")
    lines.append("This benchmark measures the linter's actual core path: signed-Pauli Clifford transport plus Shadow-HoTT diagnostic scoring. It is not a benchmark of full quantum simulation.\n")
    lines.append("## Environment\n")
    for k, v in env.items():
        lines.append(f"- **{k}:** `{v}`")
    lines.append("\n## Results\n")
    lines.append("| case | mode | wires | instr. | median s | instr/s | labels/step est. | est. label updates/s | peak tracemalloc MiB | final hw violations |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|")
    for c in cases:
        lines.append(
            "| {name} | {mode} | {w} | {d} | {sec:.6f} | {ips:,.1f} | {labels:,} | {lps:,.1f} | {mib:.2f} | {hw} |".format(
                name=c.name,
                mode=c.mode,
                w=c.num_wires,
                d=c.depth,
                sec=c.median_seconds,
                ips=c.instructions_per_second,
                labels=c.labels_per_step_estimate,
                lps=c.estimated_label_updates_per_second,
                mib=c.peak_tracemalloc_bytes / (1024 * 1024),
                hw=c.final_hardware_violation_score,
            )
        )
    lines.append("\n## Interpretation\n")
    lines.append("- Sparse mode is the intended default for larger linting runs. It transports the explicit active bilateral layer, which starts at `2 + 2n` Pauli labels for `n` wires.")
    lines.append("- Dense mode is deliberately exponential: it materializes `2 * 4^n + 2n` labels and is useful for small-width verification/audit runs, not large circuits.")
    lines.append("- Route evaluation multiplies lint cost by the number of route variants, then adds comparison/scoring overhead.")
    lines.append("- OpenQASM timing includes parser overhead as well as linting, so it should be compared to direct instruction linting only as an end-to-end frontend benchmark.")
    lines.append("- `peak_tracemalloc` measures Python allocations seen by `tracemalloc`; it is useful for comparing cases in the same environment, not for exact resident memory claims.")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", default="benchmark_results", help="output directory")
    parser.add_argument("--repeats", type=int, default=3, help="timed repeats per case")
    parser.add_argument("--seed", type=int, default=1729, help="base RNG seed")
    parser.add_argument("--include-dense", action="store_true", default=True, help="include small dense-mode cases")
    parser.add_argument("--full", action="store_true", help="run a longer benchmark sweep; default is the CI-safe benchmark")
    parser.add_argument("--quick", action="store_true", help="alias for the default CI-safe benchmark")
    args = parser.parse_args(argv)

    out_dir = Path(args.out)
    repeats = max(1, args.repeats)
    cases: list[BenchCase] = []

    if args.full:
        sparse_cfgs = [(4, 1000), (8, 1000), (16, 1000), (32, 1000), (64, 1000)]
        # Dense cases are intentionally capped. Full-trace dense linting is exponential.
        dense_cfgs = [(2, 250), (3, 250), (4, 200), (5, 80)] if args.include_dense else []
    else:
        # CI-safe default. Use --full for a larger local sweep.
        sparse_cfgs = [(4, 250), (16, 250), (64, 250)]
        dense_cfgs = [(2, 100), (3, 100), (4, 50)] if args.include_dense else []

    for idx, (n, d) in enumerate(sparse_cfgs):
        cases.append(
            benchmark_lint_case(
                f"sparse_{n}w_{d}d",
                num_wires=n,
                depth=d,
                sparse=True,
                repeats=repeats,
                seed=args.seed + idx,
            )
        )
    for idx, (n, d) in enumerate(dense_cfgs):
        cases.append(
            benchmark_lint_case(
                f"dense_{n}w_{d}d",
                num_wires=n,
                depth=d,
                sparse=False,
                repeats=repeats,
                seed=args.seed + 100 + idx,
            )
        )

    route_depth = 250 if args.full else 80
    route = benchmark_route_case(num_wires=16, depth=route_depth, variants=4, repeats=repeats, seed=args.seed + 1000)
    cases.append(route)
    qasm_depth = 500 if args.full else 120
    qasm = benchmark_qasm_case(num_wires=12, depth=qasm_depth, repeats=repeats, seed=args.seed + 2000)
    cases.append(qasm)

    env = environment()
    payload = {
        "environment": env,
        "certificate": to_jsonable(build_certificate(max_qubits_verified=3, extra={"benchmark_seed": args.seed})),
        "cases": [asdict(c) for c in cases],
    }
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "benchmark_results.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    write_csv(cases, out_dir / "benchmark_results.csv")
    write_markdown(cases, env, out_dir / "BENCHMARK_REPORT.md")
    print(f"wrote {out_dir / 'benchmark_results.json'}")
    print(f"wrote {out_dir / 'benchmark_results.csv'}")
    print(f"wrote {out_dir / 'BENCHMARK_REPORT.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
