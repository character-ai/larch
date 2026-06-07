## Proposed Design Outline

### Goals
- One uniform review-round cap of 5: `/design` Gate C SIMPLE 3 → 5 (HARD stays 5); `/implement` becomes a hard ceiling of 5 (drop degraded-round inflation, per Step 1c decision).
- Remove vestigial knobs: `--round-cap` chain into `plan-review-loop.sh` (incl. `run-step3-review.sh` argv and the design SKILL.md launch line) and the `LARCH_DESIGN_ROUND_CAP` env var.
- Remove `lib-implement-round-cap.sh` (+ sibling .md, test harness, Makefile target) — zero consumers once inflation is gone.

### Non-goals
- No bump to 7; no cap value other than 5 anywhere.
- No change to single-pass review architecture or Gate C loop semantics.
- No removal of the `DEGRADED_ROUND` marker (still consumed by `find_previous_non_degraded_round`) or of `/implement`'s live `review-and-fix.sh --round-cap` conduit.

### Approach sketch
- Flatten `run-step3-review.sh` tier `case` to a single cap of 5; drop its `--round-cap` argv and the forward to `plan-review-loop.sh`.
- `plan-review-loop.sh`: delete `--round-cap` flag, validation, `LARCH_DESIGN_ROUND_CAP` default; update usage + .md.
- `run-step5-review.sh` single mode: pass base cap 5 (delete `ROUND_CAP_INFLATED`); loop script: `effective_round_cap = base_cap` (delete entry/per-round/post-round degraded math); keep `EFFECTIVE_ROUND_CAP` envelope key (now always 5) to avoid contract churn.
- Update prose caps (SIMPLE = 5) in `approval-gates.md`, design `flags.md`, design SKILL.md, `plan-review.md`, implement SKILL.md banner fence, `docs/configuration-and-permissions.md`.

### Surfaces in scope
- `skills/design/scripts/`: `run-step3-review.sh`/`.md`, `plan-review-loop.sh`/`.md`, `test-step3-review-cap.sh`, `test-run-step3-review.sh`, `test-plan-review-loop.sh`
- `skills/design/references/`: `approval-gates.md`, `flags.md`, `plan-review.md`; `skills/design/SKILL.md`
- `scripts/`: `run-step5-review.sh`/`.md`, `lib-implement-round-cap.sh`/`.md` (delete), `test-lib-implement-round-cap.sh`/`.md` (delete), `test-run-step5-review.sh`, `test-design-structure.sh`, `test-design-multi-round-integration.sh`, `test-implement-structure.md` consumers
- `skills/implement/SKILL.md`, `skills/review-and-fix/SKILL.md`, `skills/review-and-fix/scripts/` (`review-and-fix.sh`, `review-implement-step5-loop.sh`, `test-review-and-fix.sh`)
- `Makefile`, `docs/configuration-and-permissions.md`, `docs/review-agents.md`, topology/prose counts

### Open questions
- None.
