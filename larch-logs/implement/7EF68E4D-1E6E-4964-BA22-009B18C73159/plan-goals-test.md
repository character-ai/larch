## Goal
Implement issue #7484: [IMPLEMENTING] contract-unification [MIGRATION] Port design Step 3.5 settle in-process.

## Implementation Plan
#### Problem

`design-step35-settle.sh` is a 342-line wrapper that still owns application logic, dedup routing, phase writes, child-result parsing, dialectic cleanup, and settle action dispatch. `review/plan_review.py` shells back into it, despite the Python migration rule favoring in-process calls.

#### Goal

Create a typed settle request and result in Python. Call the existing post-plan, dedup, phase, and dialectic owners directly. Preserve the current `SETTLE_NEXT_ACTION`, `SETTLE_EXIT_RC`, and diagnostic contract for every site. Repoint all skill callers and remove the Bash wrapper and its direct harness after parity coverage lands.

#### Required implementation

- Port the full behavior of `skills/design/scripts/design-step35-settle.sh`; do not leave `review/plan_review.py::step35_settle` as a shell delegate.
- Model `site`, optional round number, design tmpdir, session identity, and relevant result paths in a frozen request. Accept only `gate-a`, `gate-b`, `discussion-round2`, and `gate-c`.
- Preserve site mapping: Gate B uses its Gate B post-plan path; Gate A and discussion round 2 use the existing discussion-round2 mapping; Gate C retains its clean-return and reassessment route.
- Preserve post-rewrite dedup, apply-ready markers, phase writes, dialectic stale clearing order, `POSTPLAN_RC` cardinality checks, child return-code cross-check, and `settle-next-action` dispatch.
- Emit exactly one anchored `SETTLE_NEXT_ACTION` and `SETTLE_EXIT_RC` on paths that currently do so. Preserve warning versus hard-error channels and all action names consumed by `settle-rc-dispatch.md`.
- Replace shell self-reentry with direct function calls through injected runners or typed call boundaries. Do not invoke `python/cli.py` as a subprocess from Python.
- Repoint all SKILL and reference consumers, delete the wrapper/reference and Bash-only harness, and update migration manifests without a shim.

#### Verification

Build table-driven parity fixtures from the old wrapper before deletion. Cover every site, missing/invalid round, dedup revise/fail, postplan rc `0` and nonzero, missing/duplicate `POSTPLAN_RC`, child-rc mismatch, dialectic cleanup warning, and every settle action. Run plan-review, Gate A/B/C, design lifecycle, structure, and migration checks.

#### Dependencies, size, acceptance

Blocked by the small design wrapper migration to avoid concurrent edits to `plan_review.py`, launcher mappings, structure tests, and design references. Expected change: 900-1,350 lines. Golden parity must cover gate-a, gate-b, discussion-round2, gate-c, invalid sites, missing rounds, child failures, and malformed result envelopes.

## Test plan
(no test plan section in plan-file)
