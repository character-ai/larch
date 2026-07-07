## Decision 1: Decomposition depth for oversized-plan parts
- **Question**: When /design blocks an oversized plan and the operator decomposes it, how complete must each part issue be at decomposition time?
- **Resolution**: Boundaries + inventory only. Reuse the existing decompose panel (Step 2b.5 Split-path): file serial part issues with native blocked-by edges, per-part firm-heading inventory, and per-part acceptance criteria. Each part earns its own reviewed `larch:plan` block by being /design'd independently later. Do NOT generate reviewed per-part `larch:plan` blocks inline during decomposition.
- **Source**: user

## Decision 2: Oversize override surface
- **Question**: How should the operator record the `oversize_override: operator` escape hatch that lets an oversized plan finalize as a single issue?
- **Resolution**: Interactive prompt only. Add an Override option to the oversized-plan block prompt; selecting it writes `oversize_override: operator` into the finalized plan block. No new CLI flag.
- **Source**: user

## Decision 3: Threshold values
- **Question**: How should the numeric thresholds be set in this change?
- **Resolution**: Ship the issue's proposed initial constants in `python/larch/core/config.py` with calibration rationale anchored to the #6514 incident: firm headings > 25, distinct top-level surfaces > 4. Keep the existing diff thresholds (`diff_added > 2000` new-style / `diff_lines > 1500` legacy). A full run-log recalibration study is out of scope (future work).
- **Source**: user

## Decision 4: Reuse existing size-check and decompose machinery (no parallel system)
- **Question**: Should the guardrail extend the existing Step 2b.5 check-size + decompose Split-path, or build a new parallel finalization subsystem?
- **Resolution**: Extend existing machinery. The new firm-heading-count and distinct-surfaces signals are added to the existing plan-size detector (today it measures only plan-body lines and diff size). Reuse the existing decompose panel unchanged for part filing. Add a finalization guard so an oversized single plan cannot write its `larch:plan` block without an `oversize_override: operator` record.
- **Source**: codebase (check-plan-size.md, decompose-panel.md) + issue proposal item 4

## Decision 5: Non-goals (hard boundaries, not to be touched)
- **Question**: What is explicitly out of scope?
- **Resolution**: No changes to /implement gating or the one-shot implementer contract (companion issue owns that). No auto-splitting without operator visibility — decomposition output still goes through the normal panel + approval surfaces. No full threshold recalibration study.
- **Source**: issue Non-goals

## Decision 6: Hard constraints that must not break
- **Question**: What contracts must be preserved?
- **Resolution**: Preserve the `larch:plan` wire format and the clarify round-trip per docs/issue-anchored-plan.md. Preserve the existing plan grammar trailer contract (`diff_lines:` final line + optional `diff_added:`/`diff_deleted:`/`mechanical_churn:` metadata block); `oversize_override: operator` is recorded adjacent to `diff_lines:`. Preserve /implement preflight admission and plan materialization on part issues (each part carries its own valid `larch:plan` block earned via its own /design run). `make py-lint`, `make py-test`, and affected test-harness shards must pass.
- **Source**: issue Acceptance criteria + codebase
