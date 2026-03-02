# The Shadow HoTT Engine 

**A high-speed diagnostic and routing engine for Quantum Compilers.**

Traditional quantum simulators track wavefunctions and probability amplitudes, which scale exponentially and crash classical computers. The **Shadow Engine** takes a different approach: it abandons physics entirely. 

By mapping quantum circuits onto a 4-valued paraconsistent logic structure (True, False, Both, Neither) and utilizing $O(1)$ Heisenberg Pauli transport rules, it acts as a **lightning-fast spellchecker and diagnostic linter for quantum code**.

## 🚀 What is it good for?

1. Evaluate thousands of different circuit routing options in milliseconds. The engine tracks the "Signature Shocks" and "Total Variation" of a circuit, instantly flagging the most logically stable, hardware-safe route.
2. Inject logical errors (Gluts/Gaps) into a circuit and instantly trace how they cascade through entanglement. Ideal for Quantum Error Correction (QEC) syndrome mapping.
3. Use the engine as a pre-filter for quantum machine learning (VQA/QAOA). If a circuit generates massive "Coherence Defects," the engine rejects it in a fraction of a second, saving hours of expensive server simulation time.

## ⚙️ How it Works (The Math)

Instead of simulating complex matrices, the engine operates as a highly-optimized dictionary manipulator:
* **Clifford Transport:** Uses the Gottesman-Knill theorem to perfectly simulate $X, Z, H, S$, and $CNOT$ gates as simple string manipulations with exact phase tracking.
* **The Bilateral Twist:** Tracks continuous Truth/Falsity scores and applies a hard threshold ($\theta$) to drop observables into discrete logical buckets ($\Tv, \Fv, \Bv, \Uv$).
* **Sparse Memory Allocation:** Only tracks observables that contain active data or noise, dramatically reducing the memory footprint for NISQ-era circuits.

* # Theorem: Exact Clifford Label-Transport Soundness

## Preliminaries

**Definition 1** (Pauli group on *n* qubits).
Let *𝒫ₙ* = {*I*, *X*, *Y*, *Z*}^⊗*n* denote the *n*-qubit Pauli group (modulo global phase). Elements are tensor products *P* = *P*₁ ⊗ ··· ⊗ *Pₙ* where each *Pᵢ* ∈ {*I*, *X*, *Y*, *Z*}.

**Definition 2** (Signed Pauli observables).
The set of *signed n-qubit Pauli observables* is

> *𝒫ₙ*^± = { *σP* : *σ* ∈ {+1, −1}, *P* ∈ *𝒫ₙ* }.

Each element *σP* is Hermitian with eigenvalues ±1 (for *P* ≠ *I*^⊗*n*) and represents a physical observable. We write +*P* and −*P* for the two signs. The set *𝒫ₙ*^± is closed under negation: −(σ*P*) = (−σ)*P*.

**Definition 3** (Clifford conjugation action).
For a Clifford unitary *g*, the *conjugation action* on signed Pauli observables is

> Ad_*g*(*σP*) = *g*(*σP*)*g*† = *σ* · *gPg*†.

Since *g* is Clifford, *gPg*† = *τQ* for some *τ* ∈ {+1, −1} and *Q* ∈ *𝒫ₙ*. Thus Ad_*g*(*σP*) = (*στ*)*Q* ∈ *𝒫ₙ*^±.

**Key property.** Ad_*g* : *𝒫ₙ*^± → *𝒫ₙ*^± is a bijection (in fact a group automorphism of the signed Pauli group under multiplication).

**Definition 4** (Implemented generators).
The engine implements transport maps for the following Clifford generators acting on an *n*-wire register:

- *Hᵢ* (Hadamard on wire *i*), for 0 ≤ *i* < *n*
- *Sᵢ* (Phase gate on wire *i*), for 0 ≤ *i* < *n*
- CNOT_{*c*→*t*} (controlled-NOT with control wire *c*, target wire *t*), for 0 ≤ *c* ≠ *t* < *n*

These generate the full Clifford group on *n* qubits.

**Definition 5** (Engine transport map).
For each implemented generator *g*, the engine computes a map

> *τ̂_g* : *𝒫ₙ*^± → *𝒫ₙ*^±

by the following procedure. Given input label *σP* = *σ*(*P*₁ ⊗ ··· ⊗ *Pₙ*):

**(a) For *g* = *Hᵢ*:** Set *σ*′ = *σ*, *Q_j* = *P_j* for *j* ≠ *i*, and apply the local rule at wire *i*:

| *Pᵢ* | *Qᵢ* | sign factor |
|------|------|-------------|
| *I*  | *I*  | +1          |
| *X*  | *Z*  | +1          |
| *Y*  | *Y*  | −1          |
| *Z*  | *X*  | +1          |

Output: (*σ*′ · sign_factor) · (*Q*₁ ⊗ ··· ⊗ *Qₙ*).

**(b) For *g* = *Sᵢ*:** Set *σ*′ = *σ*, *Q_j* = *P_j* for *j* ≠ *i*, and apply:

| *Pᵢ* | *Qᵢ* | sign factor |
|------|------|-------------|
| *I*  | *I*  | +1          |
| *X*  | *Y*  | +1          |
| *Y*  | *X*  | −1          |
| *Z*  | *Z*  | +1          |

Output: (*σ*′ · sign_factor) · (*Q*₁ ⊗ ··· ⊗ *Qₙ*).

**(c) For *g* = CNOT_{*c*→*t*}:** Set *Q_j* = *P_j* for *j* ∉ {*c*, *t*}. The local action on the (*c*, *t*) pair is determined by a precomputed table *T*_CNOT derived as follows.

*Generator images* (standard CNOT conjugation on the 2-qubit Pauli generators):

| Input (*Pc*, *Pt*) | Output (sign, *Qc*, *Qt*) |
|---------------------|---------------------------|
| (*X*, *I*)          | (+1, *X*, *X*)            |
| (*Z*, *I*)          | (+1, *Z*, *I*)            |
| (*I*, *X*)          | (+1, *I*, *X*)            |
| (*I*, *Z*)          | (+1, *Z*, *Z*)            |

*Closure rule.* For arbitrary (*Pc*, *Pt*), decompose as (*Pc*, *I*) · (*I*, *Pt*) and compute the image by multiplying the generator images using the Pauli product rule, reducing the resulting phase to {±1}. Formally:

> Let (*s*₁, *W*₁) = image(*Pc*, *I*) and (*s*₂, *W*₂) = image(*I*, *Pt*).
> Compute *W*₁ · *W*₂ = *φ* · *W* where *φ* ∈ {±1, ±*i*} and *W* is a 2-qubit Pauli word.
> Then *T*_CNOT(*Pc*, *Pt*) = (*s*₁ · *s*₂ · Re(*φ*), *W*[0], *W*[1]).

The phase *φ* reduces to {±1} (see Lemma 1 below). Output: (*σ* · local_sign) · (*Q*₁ ⊗ ··· ⊗ *Qₙ*).

---

## Lemma 1 (Hermiticity-Guaranteed Phase Reduction)

**Statement.** Let *g* be a Clifford unitary and *P* ∈ *𝒫ₙ* a Hermitian Pauli operator. Then *gPg*† = *τQ* with *τ* ∈ {+1, −1} and *Q* ∈ *𝒫ₙ*.

**Proof.** Since *P* is Hermitian, (*gPg*†)† = *gP*†*g*† = *gPg*†, so *gPg*† is Hermitian. Since *g* is Clifford, *gPg*† = *φQ* for some phase *φ* and Pauli *Q*. Hermiticity of *φQ* requires *φ*̄*Q*† = *φQ*. Since *Q* is Hermitian (*Q*† = *Q*), this gives *φ*̄ = *φ*, i.e. *φ* ∈ ℝ. Since *φ* is also a root of unity in {±1, ±*i*} (the Pauli phase group), we have *φ* ∈ {±1, ±*i*} ∩ ℝ = {±1}. ∎

**Corollary.** The `_phase_to_real_sign` function in the engine never raises its error branch when called on the result of Clifford conjugation of a Hermitian Pauli.

---

## Theorem (Exact Clifford Label-Transport Soundness)

**Statement.** Let *n* ≥ 1. For each implemented generator *g* ∈ {*Hᵢ*, *Sᵢ*, CNOT_{*c*→*t*}}, the engine transport map *τ̂_g* : *𝒫ₙ*^± → *𝒫ₙ*^± satisfies

> *τ̂_g* = Ad_*g*

i.e. for all *σP* ∈ *𝒫ₙ*^±:

> *τ̂_g*(*σP*) = *g*(*σP*)*g*†.

Equivalently: the engine's label transport agrees exactly with Clifford conjugation on the full set of signed Hermitian Pauli observables for all implemented generators, on registers of any width *n* ≥ 1.

**Proof.**

We prove the claim for each generator family. The argument has a common structure: (i) verify the local conjugation identities that define the transport, (ii) show that locality + the tensor product structure of *𝒫ₙ* imply global correctness.

**Structural lemma.** Each implemented generator *g* acts nontrivially on at most 2 wires. For any *P* = *P*₁ ⊗ ··· ⊗ *Pₙ*, we have

> *gPg*† = *P*₁ ⊗ ··· ⊗ (*g*_local · *P*_local · *g*_local†) ⊗ ··· ⊗ *Pₙ*

where *P*_local and *g*_local act on the affected wire(s). The engine applies the local rule only at the affected wire(s) and copies all other tensor factors unchanged, matching this tensor product structure exactly.

Therefore, it suffices to verify the local conjugation tables.

---

**Case 1: *g* = *Hᵢ***

The standard Hadamard conjugation identities on a single qubit are:

> *HXH* = *Z*, *HZH* = *X*, *HYH* = −*Y*, *HIH* = *I*

These are verified by direct matrix computation (or are standard textbook results). The engine's local rule table at wire *i* (Definition 5a) reproduces these four identities exactly, including the sign factor −1 for *Y*. Combined with the structural lemma, *τ̂_Hᵢ* = Ad_{*Hᵢ*} on all of *𝒫ₙ*^±.

**Involution check.** Since *H*² = *I*, we must have Ad_{*H*}² = id, hence (*τ̂_H*)² = id. This is verified exhaustively by the code for all labels up to *n* = 3 (and is immediate from the table: *X* ↔ *Z* is an involution, and *Y* ↦ −*Y* ↦ *Y* is an involution). ∎ (Case 1)

---

**Case 2: *g* = *Sᵢ***

The standard phase gate conjugation identities on a single qubit are:

> *SXS*† = *Y*, *SYS*† = −*X*, *SZS*† = *Z*, *SIS*† = *I*

Verification: *SXS*† = |0⟩⟨0|*X* + *i*|1⟩⟨1|*X* multiplied by *S*† gives *Y* (routine matrix check). Similarly for *Y* and *Z*. The engine's local rule table (Definition 5b) reproduces these identities exactly.

**Order check.** Since *S*⁴ = *I*, we need Ad_*S*⁴ = id. From the table: *X* → *Y* → −*X* → −*Y* → *X*, confirming order 4. This is verified exhaustively by the code for all labels up to *n* = 3. ∎ (Case 2)

---

**Case 3: *g* = CNOT_{*c*→*t*}**

This case requires more care because CNOT acts on two wires simultaneously.

**Step 1: Generator images are correct.**

The standard CNOT conjugation on 2-qubit Pauli generators is:

| Observable | CNOT · (·) · CNOT† | Source |
|------------|---------------------|--------|
| *X_c* ⊗ *I_t* | *X_c* ⊗ *X_t* | Standard: CNOT propagates *X* forward |
| *I_c* ⊗ *X_t* | *I_c* ⊗ *X_t* | Target *X* is fixed |
| *Z_c* ⊗ *I_t* | *Z_c* ⊗ *I_t* | Control *Z* is fixed |
| *I_c* ⊗ *Z_t* | *Z_c* ⊗ *Z_t* | Standard: CNOT propagates *Z* backward |

These are standard textbook results (e.g. Nielsen & Chuang, §10.5.2). The engine's `gen_img` dictionary encodes these four identities (plus the identity case and the *Y* cases derived below).

**Step 2: Closure under multiplication is sound.**

Any 2-qubit Pauli *P_c* ⊗ *P_t* can be written as (*P_c* ⊗ *I*) · (*I* ⊗ *P_t*). Since Clifford conjugation is a group homomorphism:

> Ad_CNOT(*P_c* ⊗ *P_t*) = Ad_CNOT(*P_c* ⊗ *I*) · Ad_CNOT(*I* ⊗ *P_t*)

The engine computes exactly this product. The multiplication of two 2-qubit Pauli words produces a phase *φ* ∈ {±1, ±*i*} (from the Pauli commutation relations) and a Pauli word.

By Lemma 1, the composite Ad_CNOT(*P_c* ⊗ *P_t*) must be a *real-signed* Pauli (since the input is Hermitian and CNOT is Clifford). Therefore the phase *φ* arising from the product must combine with the generator image signs to yield a net real sign in {±1}. The engine's `_phase_to_real_sign` correctly extracts this sign.

**Step 3: The full table is correct.**

By Steps 1–2, the precomputed table *T*_CNOT computes Ad_CNOT exactly on all 16 pairs (*P_c*, *P_t*) ∈ {*I*, *X*, *Y*, *Z*}². The structural lemma extends this to the full *n*-wire register.

**Involution check.** Since CNOT² = *I*, we need (*τ̂*_CNOT)² = id. This is verified exhaustively by the code for all labels on 2- and 3-qubit registers. ∎ (Case 3)

---

**Conclusion.** For each implemented generator *g* ∈ {*Hᵢ*, *Sᵢ*, CNOT_{*c*→*t*}}, the engine transport *τ̂_g* agrees with Ad_*g* on all of *𝒫ₙ*^± for arbitrary *n* ≥ 1. ∎

---

## Corollary (Compositional Soundness)

**Statement.** For any circuit *C* = *g_k* ∘ ··· ∘ *g*₁ composed of implemented generators, the composed engine transport

> *τ̂_C* = *τ̂_{g_k}* ∘ ··· ∘ *τ̂_{g₁}*

satisfies *τ̂_C* = Ad_*C* = Ad_{*g_k*} ∘ ··· ∘ Ad_{*g₁*}.

**Proof.** Immediate from the theorem and the fact that Ad is a group homomorphism: Ad_{*g_k* ··· *g*₁} = Ad_{*g_k*} ∘ ··· ∘ Ad_{*g*₁}. Since each factor *τ̂_{gⱼ}* = Ad_{*gⱼ*}, the composition agrees. ∎

**Remark.** This corollary is what justifies the engine's sequential gate-by-gate transport: soundness of each step implies soundness of the whole trace. Note that this applies to the *transport* (label relabeling) component only. The bilateral scoring layer and thresholding into {T, F, B, U} are separate semantic operations not covered by this theorem.

---

## Scope and Limitations

1. **Generator coverage.** The theorem covers {*H*, *S*, CNOT}, which generate the full Clifford group. It does not cover non-Clifford gates (e.g. *T*, parametric rotations), for which Pauli conjugation does not close within *𝒫ₙ*^±.

2. **Transport vs. full semantics.** The theorem guarantees that the *relabeling of Pauli observables* is algebraically exact. It says nothing about the correctness of the bilateral scoring layer, the thresholding map, the measurement model, or the diagnostic metrics. These are separate claims requiring separate arguments.

3. **Computational verification.** The `verify_transport_soundness` harness provides exhaustive computational verification of the involution/order properties (*H*² = *I*, *S*⁴ = *I*, CNOT² = *I*) on all signed Pauli labels for registers up to a configurable number of qubits. This constitutes a concrete executable certificate complementing the mathematical proof.

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
