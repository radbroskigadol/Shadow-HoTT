# The Shadow HoTT Engine 

**A high-speed diagnostic and routing engine for Quantum Compilers.**

Traditional quantum simulators track wavefunctions and probability amplitudes, which scale exponentially and crash classical computers. The **Shadow Engine** takes a different approach: it abandons physics entirely. 

By mapping quantum circuits onto a 4-valued paraconsistent logic structure (True, False, Both, Neither) and utilizing $O(1)$ Heisenberg Pauli transport rules, it acts as a **lightning-fast spellchecker and diagnostic linter for quantum code**.

## 🚀 What is it good for?

1. **The "Google Maps" for Quantum Compilers:** Evaluate thousands of different circuit routing options in milliseconds. The engine tracks the "Signature Shocks" and "Total Variation" of a circuit, instantly flagging the most logically stable, hardware-safe route.
2. **Error Propagation Tracking:** Inject logical errors (Gluts/Gaps) into a circuit and instantly trace how they cascade through entanglement. Ideal for Quantum Error Correction (QEC) syndrome mapping.
3. **Fast-Failing Bad Algorithms:** Use the engine as a pre-filter for quantum machine learning (VQA/QAOA). If a circuit generates massive "Coherence Defects," the engine rejects it in a fraction of a second, saving hours of expensive server simulation time.

## ⚙️ How it Works (The Math)

Instead of simulating complex matrices, the engine operates as a highly-optimized dictionary manipulator:
* **Clifford Transport:** Uses the Gottesman-Knill theorem to perfectly simulate $X, Z, H, S$, and $CNOT$ gates as simple string manipulations with exact phase tracking.
* **The Bilateral Twist:** Tracks continuous Truth/Falsity scores and applies a hard threshold ($\theta$) to drop observables into discrete logical buckets ($\Tv, \Fv, \Bv, \Uv$).
* **Sparse Memory Allocation:** Only tracks observables that contain active data or noise, dramatically reducing the memory footprint for NISQ-era circuits.

## 💻 Quick Start

```python
from shadow_engine import ShadowState, Instruction, execute_circuit, evaluate_compiler_routes

# 1. Define your circuit variants
circuit_a = [
    Instruction("H", target=0),
    Instruction("CNOT", control=0, target=1),
    Instruction("MEASURE", target=0)
]

circuit_b = [
    Instruction("H", target=1),
    Instruction("CNOT", control=1, target=0),
    Instruction("MEASURE", target=1)
]

# 2. Run the high-speed route evaluation
result = evaluate_compiler_routes([circuit_a, circuit_b], num_wires=2, sparse=True)

# 3. Get the optimal compiler route based on Logical Variation
print(f"Optimal Route: Circuit {result['optimal_route']['circuit_id']}")
print(f"Total Logical Shock: {result['optimal_route']['total_variation']}")
