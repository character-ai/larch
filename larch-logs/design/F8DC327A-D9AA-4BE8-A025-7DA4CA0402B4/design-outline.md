## Proposed Design Outline

### Goals
- Extend `stall-recovery-report.sh` with generic parameterization flags so `/design` can use it without forking.
- Record /design escalation events (MAV, autofix-exhausted) and terminal failures in `$DESIGN_TMPDIR`.
- Wire a failure-report gate into `/design` teardown (inside `render-final-summary.sh`) to file one report per run via the cross-repo filing layer.

### Non-goals
- No retry/recovery mechanism for /design failures; this is reporting only.
- No move of `stall-recovery-report.sh` out of `skills/implement/scripts/`; callers reference it by absolute path.
- No changes to `/implement` failure reporting behavior.

### Approach sketch
- Add `--profile generic` / `--artifact-prefix <prefix>` / step-vocab / phase-vocab overrides to `stall-recovery-report.sh`; design uses prefix `design-failure`.
- Add `stall-recovery-report.sh record-escalation` calls (with design-specific step/phase tokens) at MAV and autofix-exhausted sites in `SKILL.md` / `design-step-validator-autofix.sh`.
- New `design-failure-report.sh` script: checks terminal-failure markers and escalation ledger in `$DESIGN_TMPDIR`, classifies outcome, composes Tier A / Tier B report, calls `file-failure-report-cross-repo.sh`.
- Wire `design-failure-report.sh` call into `render-final-summary.sh --post-publish-only` phase before the run-summary upsert.
- Update `SECURITY.md` and `docs/` for new /design surfaces.

### Surfaces in scope
- `skills/implement/scripts/stall-recovery-report.sh` (add profile/artifact-prefix parameterization)
- `skills/implement/scripts/stall-recovery-report.md` (update subcommand docs)
- `skills/implement/scripts/test-stall-recovery-report.sh` (parameterization tests)
- `skills/design/scripts/render-final-summary.sh` (wire teardown gate)
- `skills/design/scripts/design-failure-report.sh` (new — teardown gate driver)
- `skills/design/scripts/design-failure-report.md` (new sibling)
- `skills/design/scripts/design-step-validator-autofix.sh` (add escalation recording on exhausted path)
- `skills/design/SKILL.md` (Step 3 MAV escalation recording call site)
- `SECURITY.md`, `docs/`

### Open questions
- None.
