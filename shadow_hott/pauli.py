# Copyright (c) 2026 David Betzer
# SPDX-License-Identifier: MIT

"""Exact signed-Pauli label algebra and Clifford transport primitives."""
from __future__ import annotations

from itertools import product
from typing import Dict, Iterable, List, Mapping, Tuple

Score = List[float]
BilateralLayer = Dict[str, Score]

_SINGLE_MUL: Dict[Tuple[str, str], Tuple[complex, str]] = {
    ("I", "I"): (1, "I"),
    ("I", "X"): (1, "X"),
    ("I", "Y"): (1, "Y"),
    ("I", "Z"): (1, "Z"),
    ("X", "I"): (1, "X"),
    ("X", "X"): (1, "I"),
    ("X", "Y"): (1j, "Z"),
    ("X", "Z"): (-1j, "Y"),
    ("Y", "I"): (1, "Y"),
    ("Y", "X"): (-1j, "Z"),
    ("Y", "Y"): (1, "I"),
    ("Y", "Z"): (1j, "X"),
    ("Z", "I"): (1, "Z"),
    ("Z", "X"): (1j, "Y"),
    ("Z", "Y"): (-1j, "X"),
    ("Z", "Z"): (1, "I"),
}

# Local single-wire Clifford conjugation maps. Values are (local_sign, new_char).
_SINGLE_WIRE_TRANSPORT: Dict[str, Dict[str, Tuple[int, str]]] = {
    # H X H = Z, H Y H = -Y, H Z H = X
    "H": {"I": (+1, "I"), "X": (+1, "Z"), "Y": (-1, "Y"), "Z": (+1, "X")},
    # S P S†
    "S": {"I": (+1, "I"), "X": (+1, "Y"), "Y": (-1, "X"), "Z": (+1, "Z")},
    # S† P S, inverse of S transport.
    "SDG": {"I": (+1, "I"), "X": (-1, "Y"), "Y": (+1, "X"), "Z": (+1, "Z")},
    # Pauli gates, interpreted up to global phase as conjugation by the Pauli.
    "X": {"I": (+1, "I"), "X": (+1, "X"), "Y": (-1, "Y"), "Z": (-1, "Z")},
    "Y": {"I": (+1, "I"), "X": (-1, "X"), "Y": (+1, "Y"), "Z": (-1, "Z")},
    "Z": {"I": (+1, "I"), "X": (-1, "X"), "Y": (-1, "Y"), "Z": (+1, "Z")},
}

_SDG_ALIASES = {"SDG", "S†", "S_DAG", "S-DAG", "SINV", "S^-1", "SADJ", "SADG"}
_CNOT_ALIASES = {"CNOT", "CX"}


def normalize_clifford_op(op: str) -> str:
    """Normalize supported Clifford operation names used by the engine/adapters."""

    opu = op.strip().upper()
    if opu in _SDG_ALIASES:
        return "SDG"
    if opu in _CNOT_ALIASES:
        return "CNOT"
    if opu in {"MEASURE", "M", "MEASURE_Z"}:
        return "MEASURE"
    return opu


def pauli_words(num_wires: int) -> Iterable[str]:
    """Yield all unsigned Pauli words of width ``num_wires``."""

    if num_wires <= 0:
        raise ValueError("num_wires must be positive")
    for word_tuple in product("IXYZ", repeat=num_wires):
        yield "".join(word_tuple)


def signed_pauli_labels(num_wires: int) -> Iterable[str]:
    """Yield every signed Pauli label, using ``+XYZ`` / ``-XYZ`` syntax."""

    for word in pauli_words(num_wires):
        yield f"+{word}"
        yield f"-{word}"


def is_event_label(label: str) -> bool:
    return label.startswith("EV:")


def label_to_signed_word(label: str) -> Tuple[int, str]:
    """Parse a signed label into ``(+/-1, word)``."""

    if not label or label[0] not in "+-":
        raise ValueError(f"not a signed Pauli label: {label!r}")
    word = label[1:]
    if not word or any(ch not in "IXYZ" for ch in word):
        raise ValueError(f"invalid Pauli word in label: {label!r}")
    sign = +1 if label[0] == "+" else -1
    return sign, word


def signed_word_to_label(sign: int, word: str) -> str:
    """Render ``(+/-1, word)`` as a signed label."""

    if sign not in (+1, -1):
        raise ValueError("sign must be +1 or -1")
    if not word or any(ch not in "IXYZ" for ch in word):
        raise ValueError(f"invalid Pauli word: {word!r}")
    return ("+" if sign == +1 else "-") + word


def distinguished_pauli_label(num_wires: int, wire: int, pauli: str, sign: str = "+") -> str:
    """Build labels such as ``+ZI`` or ``-IX``."""

    if sign not in {"+", "-"}:
        raise ValueError("sign must be '+' or '-'")
    if pauli not in {"X", "Y", "Z"}:
        raise ValueError("pauli must be one of X, Y, Z")
    validate_wire(num_wires, wire)
    chars = ["I"] * num_wires
    chars[wire] = pauli
    return sign + "".join(chars)


def validate_wire(num_wires: int, wire: int) -> None:
    if wire < 0 or wire >= num_wires:
        raise IndexError(f"wire {wire} out of range for {num_wires} wires")


def validate_two_wires(num_wires: int, control: int, target: int) -> None:
    validate_wire(num_wires, control)
    validate_wire(num_wires, target)
    if control == target:
        raise ValueError("control and target wires must differ")


def pauli_word_mul(word1: str, word2: str) -> Tuple[complex, str]:
    """Multiply two equal-width Pauli words, returning ``(phase, word)``."""

    if len(word1) != len(word2):
        raise ValueError("Pauli words must have the same length")
    phase: complex = 1
    out: List[str] = []
    for a, b in zip(word1, word2):
        ph, ch = _SINGLE_MUL[(a, b)]
        phase *= ph
        out.append(ch)
    return phase, "".join(out)


def phase_to_real_sign(phase: complex) -> int:
    """Reduce a Clifford-conjugation phase to a real sign.

    Clifford conjugation of a Hermitian Pauli observable always returns another
    Hermitian signed Pauli, so this function should only see phases ``+1`` or
    ``-1`` in valid transport-table construction.
    """

    if abs(phase - 1) < 1e-9:
        return +1
    if abs(phase + 1) < 1e-9:
        return -1
    raise ValueError(f"expected real phase +/-1, got {phase!r}")


def _pair_table_from_generator_images(
    gen_img: Mapping[Tuple[str, str], Tuple[int, str]],
) -> Dict[Tuple[str, str], Tuple[int, str, str]]:
    """Generate a two-site Clifford table from images of local generators."""

    table: Dict[Tuple[str, str], Tuple[int, str, str]] = {}
    for pc in "IXYZ":
        for pt in "IXYZ":
            s1, w1 = gen_img[(pc, "I")]
            s2, w2 = gen_img[("I", pt)]
            ph, word = pauli_word_mul(w1, w2)
            sign = s1 * s2 * phase_to_real_sign(ph)
            table[(pc, pt)] = (sign, word[0], word[1])
    return table


def _generate_cnot_local_pair_table() -> Dict[Tuple[str, str], Tuple[int, str, str]]:
    """Generate the exact CNOT(control -> target) two-site transport table."""

    # Images of (Pc, I) and (I, Pt) under CNOT conjugation. The Y rows are
    # derived so the table can be generated uniformly for all local pairs.
    gen_img: Dict[Tuple[str, str], Tuple[int, str]] = {
        ("I", "I"): (+1, "II"),
        ("X", "I"): (+1, "XX"),
        ("Y", "I"): (+1, "YX"),
        ("Z", "I"): (+1, "ZI"),
        ("I", "X"): (+1, "IX"),
        ("I", "Y"): (+1, "ZY"),
        ("I", "Z"): (+1, "ZZ"),
    }
    return _pair_table_from_generator_images(gen_img)


def _generate_cz_local_pair_table() -> Dict[Tuple[str, str], Tuple[int, str, str]]:
    """Generate the exact CZ two-site transport table."""

    # CZ images: Xc -> Xc Zt, Zc -> Zc, Xt -> Zc Xt, Zt -> Zt.
    gen_img: Dict[Tuple[str, str], Tuple[int, str]] = {
        ("I", "I"): (+1, "II"),
        ("X", "I"): (+1, "XZ"),
        ("Y", "I"): (+1, "YZ"),
        ("Z", "I"): (+1, "ZI"),
        ("I", "X"): (+1, "ZX"),
        ("I", "Y"): (+1, "ZY"),
        ("I", "Z"): (+1, "IZ"),
    }
    return _pair_table_from_generator_images(gen_img)


CNOT_LOCAL_TABLE: Dict[Tuple[str, str], Tuple[int, str, str]] = _generate_cnot_local_pair_table()
CZ_LOCAL_TABLE: Dict[Tuple[str, str], Tuple[int, str, str]] = _generate_cz_local_pair_table()


def _copy_event_or_parse(label: str, scores: Score) -> Tuple[bool, int, str, Score]:
    if is_event_label(label):
        return True, +1, "", [scores[0], scores[1]]
    sign, word = label_to_signed_word(label)
    return False, sign, word, [scores[0], scores[1]]


def _transport_single_wire(bi: BilateralLayer, target_wire: int, op: str) -> BilateralLayer:
    opn = normalize_clifford_op(op)
    mapping = _SINGLE_WIRE_TRANSPORT[opn]
    out: BilateralLayer = {}
    for label, scores in bi.items():
        is_event, sign, word, new_scores = _copy_event_or_parse(label, scores)
        if is_event:
            out[label] = new_scores
            continue
        validate_wire(len(word), target_wire)
        chars = list(word)
        local_sign, new_ch = mapping[chars[target_wire]]
        sign *= local_sign
        chars[target_wire] = new_ch
        out[signed_word_to_label(sign, "".join(chars))] = new_scores
    return out


def transport_H(bi: BilateralLayer, target_wire: int) -> BilateralLayer:
    """Exact conjugation by H on ``target_wire``: X<->Z and Y->-Y."""

    return _transport_single_wire(bi, target_wire, "H")


def transport_S(bi: BilateralLayer, target_wire: int) -> BilateralLayer:
    """Exact conjugation by S on ``target_wire``: X->Y, Y->-X, Z->Z."""

    return _transport_single_wire(bi, target_wire, "S")


def transport_Sdg(bi: BilateralLayer, target_wire: int) -> BilateralLayer:
    """Exact conjugation by S† on ``target_wire``: X->-Y, Y->X, Z->Z."""

    return _transport_single_wire(bi, target_wire, "SDG")


def transport_X(bi: BilateralLayer, target_wire: int) -> BilateralLayer:
    """Exact conjugation by X on ``target_wire``: Y->-Y, Z->-Z."""

    return _transport_single_wire(bi, target_wire, "X")


def transport_Y(bi: BilateralLayer, target_wire: int) -> BilateralLayer:
    """Exact conjugation by Y on ``target_wire``: X->-X, Z->-Z."""

    return _transport_single_wire(bi, target_wire, "Y")


def transport_Z(bi: BilateralLayer, target_wire: int) -> BilateralLayer:
    """Exact conjugation by Z on ``target_wire``: X->-X, Y->-Y."""

    return _transport_single_wire(bi, target_wire, "Z")


def _transport_pair_with_table(
    bi: BilateralLayer,
    first_wire: int,
    second_wire: int,
    table: Mapping[Tuple[str, str], Tuple[int, str, str]],
) -> BilateralLayer:
    out: BilateralLayer = {}
    for label, scores in bi.items():
        is_event, sign, word, new_scores = _copy_event_or_parse(label, scores)
        if is_event:
            out[label] = new_scores
            continue
        validate_two_wires(len(word), first_wire, second_wire)
        chars = list(word)
        p_first = chars[first_wire]
        p_second = chars[second_wire]
        local_sign, new_first, new_second = table[(p_first, p_second)]
        sign *= local_sign
        chars[first_wire] = new_first
        chars[second_wire] = new_second
        out[signed_word_to_label(sign, "".join(chars))] = new_scores
    return out


def transport_CNOT(bi: BilateralLayer, control_wire: int, target_wire: int) -> BilateralLayer:
    """Exact signed Pauli-label transport under CNOT(control -> target)."""

    return _transport_pair_with_table(bi, control_wire, target_wire, CNOT_LOCAL_TABLE)


def transport_CZ(bi: BilateralLayer, wire_a: int, wire_b: int) -> BilateralLayer:
    """Exact signed Pauli-label transport under CZ(wire_a, wire_b)."""

    return _transport_pair_with_table(bi, wire_a, wire_b, CZ_LOCAL_TABLE)


def transport_SWAP(bi: BilateralLayer, wire_a: int, wire_b: int) -> BilateralLayer:
    """Exact signed Pauli-label transport under SWAP(wire_a, wire_b)."""

    out: BilateralLayer = {}
    for label, scores in bi.items():
        is_event, sign, word, new_scores = _copy_event_or_parse(label, scores)
        if is_event:
            out[label] = new_scores
            continue
        validate_two_wires(len(word), wire_a, wire_b)
        chars = list(word)
        chars[wire_a], chars[wire_b] = chars[wire_b], chars[wire_a]
        out[signed_word_to_label(sign, "".join(chars))] = new_scores
    return out


def transport_single_label(label: str, op: str, target: int, control: int | None = None) -> str:
    """Apply one exact Clifford transport to a single signed Pauli label."""

    bi = {label: [1.0, 0.0]}
    opu = normalize_clifford_op(op)
    if opu in _SINGLE_WIRE_TRANSPORT:
        out = _transport_single_wire(bi, target, opu)
    elif opu == "CNOT":
        if control is None:
            raise ValueError("CNOT requires control")
        out = transport_CNOT(bi, control, target)
    elif opu == "CZ":
        if control is None:
            raise ValueError("CZ requires both wires; pass one as control and one as target")
        out = transport_CZ(bi, control, target)
    elif opu == "SWAP":
        if control is None:
            raise ValueError("SWAP requires both wires; pass one as control and one as target")
        out = transport_SWAP(bi, control, target)
    else:
        raise ValueError(f"unsupported transport op: {op!r}")
    if len(out) != 1:
        raise RuntimeError("transport on a singleton label should produce one label")
    return next(iter(out.keys()))


def support_weight(label: str) -> int:
    """Count non-identity support of a signed Pauli label. Event labels weigh 0."""

    if is_event_label(label):
        return 0
    _, word = label_to_signed_word(label)
    return sum(ch != "I" for ch in word)


def pauli_labels_touching_wire(labels: Iterable[str], wire: int, chars: set[str]) -> List[str]:
    """Return labels whose Pauli word has one of ``chars`` at ``wire``."""

    out: List[str] = []
    for label in labels:
        if is_event_label(label):
            continue
        _, word = label_to_signed_word(label)
        validate_wire(len(word), wire)
        if word[wire] in chars:
            out.append(label)
    return out
