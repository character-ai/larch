## Goal
Implement issue #5000: [IMPLEMENTING] Audit Python dataclass use and make all frozen=True that can be made frozen.

## Implementation Plan
Enacts guideline **G-Py-1** (pass composite data as frozen dataclasses) from #4659.

## Goal

Convert existing `@dataclass` definitions to `@dataclass(frozen=True)` wherever the data is not legitimately mutated after construction.

## Current state (at filing)

Dataclasses are widely used in `python/`, but `frozen=True` appears in only roughly a fifth of files. Most composite types are mutable by default.

## Why

Immutability prevents accidental cross-boundary mutation; frozen instances are hashable and safe to share; named fields stay refactor-safe.

## Approach

- Inventory `@dataclass` sites in `python/`.
- Make frozen where construction-then-read is the actual usage.
- Where freezing only blocks one or two reassignments, prefer `dataclasses.replace()` over staying mutable.
- Leave mutable (with a one-line reason) where a field is genuinely reassigned by design.

## Carve-outs (stay mutable)

Accumulators/builders; objects whose fields are reassigned in place; interop shims that must match an external mutable shape.

## Note

Not lint-enforceable as a blanket rule (frozen-ness is a per-type design choice), so this is an audit plus the ongoing G-Py-1 guideline, not a new linter.

## Related

#4659 (G-Py-1).

## Acceptance

Dataclasses that can be frozen are frozen; remaining mutable ones carry a one-line reason; `make py-lint` and `make py-test` green.

## Test plan
(no test plan section in plan-file)
