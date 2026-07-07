## Proposed Design Outline

### Goals
- Add two new mechanical plan-size signals to the existing plan-size detector: firm-heading count (`NEW:`/`UPDATED:`/`REWRITTEN:`, excluding `MAY_UPDATE:`) and distinct top-level surfaces touched.
- Block an oversized single plan from finalizing unless the operator decomposes it (existing panel) or records `oversize_override: operator` in the plan block.
- Ship the issue's initial thresholds in `python/larch/core/config.py` with calibration rationale, and document the signals in `docs/issue-anchored-plan.md`.

### Non-goals
- No changes to `/implement` gating or the one-shot implementer contract (companion issue owns that).
- No inline per-part `larch:plan` generation; part issues are `/design`'d independently to earn their reviewed plan blocks.
- No full run-log recalibration study; ship the proposed constants with documented rationale.

### Approach sketch
- Extend the plan-size detector (`plan check-size` implementation) to also emit `FIRM_HEADINGS` and `SURFACES_TOUCHED`; add thresholds (firm headings > 25, distinct surfaces > 4) to `python/larch/core/config.py`.
- Feed the new signals into the existing Step 2b.5 hard-trigger; add an interactive **Override** option that writes `oversize_override: operator` into the plan block's final metadata block adjacent to `diff_lines:`.
- Add a Step 5c finalization guard that refuses to write a single `larch:plan` block for an oversized plan lacking the override record (the "cannot reach /implement" guarantee).
- Reuse the decompose panel unchanged for the Split path (parts already get native blocked-by edges + per-part inventories).

### Surfaces in scope
- `python/larch/…` plan-quality detector + `python/larch/core/config.py`
- `skills/design/SKILL.md` (Step 2b.5, Step 5c), `references/step2b5-rc-handling.md`, `scripts/check-plan-size.md`
- `docs/issue-anchored-plan.md`
- Python tests for the detector, thresholds, and the finalization guard

### Open questions
- Whether the Step 5c finalization guard is required in addition to the extended Step 2b.5 hard-block, or whether hardening 2b.5 alone is sufficient — to be settled in plan review.
