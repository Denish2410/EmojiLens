"""Transformation framework: specs, results, offset maps, validation, chains.

A transformation is a pure function of (text, variety, seed, params). Its output carries a
*piece map*: a list of ``(original start, original end, output text)`` pieces that tile the
original exactly once, in order. Concatenating piece texts gives the output. Piece maps compose
across chains, so every output span of a multi-step chain traces back to original offsets.
"""

from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from emojilens_core.multilingual import Variety
from emojilens_core.unicode import InvalidUnicodeError, validate_unicode

Piece = tuple[int, int, str]


@dataclass(frozen=True, slots=True)
class Param:
    name: str
    kind: str  # "float" | "int" | "choice" | "string" | "bool"
    default: Any
    description: str
    choices: tuple[str, ...] = ()
    minimum: float | None = None
    maximum: float | None = None


@dataclass(frozen=True, slots=True)
class TransformSpec:
    id: str
    version: str
    family: str
    description: str
    varieties: tuple[Variety, ...]
    params: tuple[Param, ...]
    seeded: bool
    reversible: bool


@dataclass(frozen=True, slots=True)
class Validation:
    valid: bool
    checks: dict[str, bool | None]
    notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StepResult:
    transform_id: str
    version: str
    family: str
    params: dict[str, Any]
    seed: int
    input: str
    output: str
    pieces: list[Piece]
    edits: int
    validation: Validation
    provenance: dict[str, Any] = field(default_factory=dict)


class TransformError(ValueError):
    code = "transform_error"


Impl = Callable[[str, Variety, random.Random, dict[str, Any]], tuple[list[Piece], dict[str, Any]]]
Decoder = Callable[[str, dict[str, Any]], str | None]


@dataclass(frozen=True, slots=True)
class Transform:
    spec: TransformSpec
    impl: Impl
    decoder: Decoder | None = None
    # Normalisation applied to the input before comparing a decoded round trip (e.g. lowercasing
    # for case-insensitive ciphers).
    roundtrip_key: Callable[[str], str] | None = None

    def resolve_params(self, given: dict[str, Any] | None) -> dict[str, Any]:
        given = dict(given or {})
        unknown = set(given) - {p.name for p in self.spec.params}
        if unknown:
            raise TransformError(f"Unknown parameter(s) for {self.spec.id}: {sorted(unknown)}")
        out: dict[str, Any] = {}
        for p in self.spec.params:
            v = given.get(p.name, p.default)
            if p.kind == "float":
                if not isinstance(v, (int, float)) or isinstance(v, bool):
                    raise TransformError(f"{p.name} must be a number")
                v = float(v)
            elif p.kind == "int":
                if not isinstance(v, int) or isinstance(v, bool):
                    raise TransformError(f"{p.name} must be an integer")
            elif p.kind == "bool":
                if not isinstance(v, bool):
                    raise TransformError(f"{p.name} must be a boolean")
            elif p.kind in ("choice", "string"):
                if not isinstance(v, str):
                    raise TransformError(f"{p.name} must be a string")
                if p.kind == "choice" and v not in p.choices:
                    raise TransformError(f"{p.name} must be one of {list(p.choices)}")
                if p.kind == "string":
                    validate_unicode(v)
                    if len(v) > 200:
                        raise TransformError(f"{p.name} is limited to 200 code points")
            if p.minimum is not None and isinstance(v, (int, float)) and v < p.minimum:
                raise TransformError(f"{p.name} must be >= {p.minimum}")
            if p.maximum is not None and isinstance(v, (int, float)) and v > p.maximum:
                raise TransformError(f"{p.name} must be <= {p.maximum}")
            out[p.name] = v
        return out

    def apply(
        self, text: str, variety: Variety, seed: int = 0, params: dict[str, Any] | None = None
    ) -> StepResult:
        try:
            validate_unicode(text)
        except InvalidUnicodeError as exc:
            raise TransformError(str(exc)) from exc
        resolved = self.resolve_params(params)
        rng = random.Random(f"{seed}:{self.spec.id}:{self.spec.version}")  # noqa: S311 - not crypto
        pieces, provenance = self.impl(text, variety, rng, resolved)
        output = "".join(p[2] for p in pieces)
        edits = sum(1 for s, e, t in pieces if text[s:e] != t)
        checks: dict[str, bool | None] = {
            "output_well_formed": _well_formed(output),
            "pieces_tile_original": tiles(pieces, len(text)),
            "changed": output != text,
            "round_trip": None,
        }
        notes: list[str] = []
        if self.decoder is not None:
            decoded = self.decoder(output, provenance)
            if decoded is not None:
                expected = self.roundtrip_key(text) if self.roundtrip_key else text
                checks["round_trip"] = decoded == expected
        if variety not in self.spec.varieties:
            notes.append(f"{variety.value} is not a supported variety for {self.spec.id}")
        if edits == 0 and self.spec.family != "identity":
            notes.append("no eligible positions: output equals input")
        valid = bool(checks["output_well_formed"] and checks["pieces_tile_original"]) and (
            checks["round_trip"] is not False
        )
        if self.spec.family == "identity":
            valid = valid and not checks["changed"]
        return StepResult(
            transform_id=self.spec.id,
            version=self.spec.version,
            family=self.spec.family,
            params=resolved,
            seed=seed,
            input=text,
            output=output,
            pieces=pieces,
            edits=edits,
            validation=Validation(valid=valid, checks=checks, notes=tuple(notes)),
            provenance=provenance,
        )


def _well_formed(s: str) -> bool:
    try:
        validate_unicode(s)
    except InvalidUnicodeError:
        return False
    return True


def tiles(pieces: Sequence[Piece], n: int) -> bool:
    pos = 0
    for s, e, _ in pieces:
        if s != pos or e < s:
            return False
        pos = e
    return pos == n


def compose(first: Sequence[Piece], second: Sequence[Piece]) -> list[Piece]:
    """Compose ``first`` (original -> mid) with ``second`` (mid -> output).

    Groups are cut only at mid positions that are boundaries of both maps. Each group maps the
    union of its ``first`` original spans to the concatenation of its ``second`` outputs.
    """
    mid_len = sum(len(t) for _, _, t in first)
    a_bounds = {0}
    pos = 0
    for _, _, t in first:
        pos += len(t)
        a_bounds.add(pos)
    b_bounds = {0} | {e for _, e, _ in second}
    common = sorted(a_bounds & b_bounds | {mid_len})
    if len(common) == 1:  # empty mid text
        return [(first[0][0], first[-1][1], "".join(t for _, _, t in second))] if first else []

    def group_of(p: int, at_end: bool) -> int:
        # Index g such that common[g] <= p < common[g+1]; positions at the very end go last.
        for g in range(len(common) - 1):
            if common[g] <= p < common[g + 1]:
                return g
        return len(common) - 2 if at_end or p == mid_len else 0

    n_groups = len(common) - 1
    orig: list[list[int]] = [[] for _ in range(n_groups)]
    outs: list[list[str]] = [[] for _ in range(n_groups)]
    pos = 0
    for s, e, t in first:
        g = group_of(pos, pos == mid_len)
        orig[g] += [s, e]
        pos += len(t)
    for s, _e, t in second:
        outs[group_of(s, s == mid_len)].append(t)
    out: list[Piece] = []
    for g in range(n_groups):
        if orig[g]:
            out.append((min(orig[g]), max(orig[g]), "".join(outs[g])))
        elif outs[g] and out:
            ps, pe, pt = out[-1]
            out[-1] = (ps, pe, pt + "".join(outs[g]))
    return out


@dataclass(frozen=True, slots=True)
class ChainStep:
    transform_id: str
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ChainResult:
    original: str
    output: str
    variety: Variety
    seed: int
    steps: list[StepResult]
    pieces: list[Piece]
    chain_hash: str
    valid: bool


def canonical_chain(steps: Sequence[StepResult], seed: int, variety: Variety) -> str:
    return json.dumps(
        {
            "seed": seed,
            "variety": variety.value,
            "steps": [
                {"id": s.transform_id, "version": s.version, "params": s.params} for s in steps
            ],
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    )


def run_chain(
    registry: dict[str, Transform],
    text: str,
    variety: Variety,
    chain: Sequence[ChainStep],
    seed: int = 0,
) -> ChainResult:
    if not chain:
        raise TransformError("A chain needs at least one step.")
    if len(chain) > 8:
        raise TransformError("Chains are limited to 8 steps.")
    steps: list[StepResult] = []
    current = text
    pieces: list[Piece] | None = None
    for i, step in enumerate(chain):
        t = registry.get(step.transform_id)
        if t is None:
            raise TransformError(f"Unknown transformation '{step.transform_id}'.")
        # Each step gets a distinct derived seed so repeated steps differ but stay reproducible.
        result = t.apply(current, variety, seed=seed * 1000 + i, params=step.params)
        steps.append(result)
        pieces = result.pieces if pieces is None else compose(pieces, result.pieces)
        current = result.output
    assert pieces is not None
    chain_hash = hashlib.sha256(canonical_chain(steps, seed, variety).encode()).hexdigest()
    return ChainResult(
        original=text,
        output=current,
        variety=variety,
        seed=seed,
        steps=steps,
        pieces=pieces,
        chain_hash=chain_hash,
        valid=all(s.validation.valid for s in steps) and tiles(pieces, len(text)),
    )
