## Decision 1: Resume scope
- **Question**: Should pause/resume work across Claude sessions (machine reboots, new shells) or only within the same Claude session?
- **Resolution**: Cross-session (full restore). All state must live on GitHub (issue body and/or comments) so resume works from any machine even if `$DESIGN_TMPDIR` is gone.
- **Source**: user

## Decision 2: Pause trigger model
- **Question**: What triggers a pause?
- **Resolution**: User presses Escape or Ctrl-C at any point in the flow and explicitly asks to pause. This is a user-initiated signal during an in-flight run, not an automatic crash-recovery mechanism.
- **Source**: user

## Decision 3: Pause granularity
- **Question**: Where in /design must pause/resume work?
- **Resolution**: Anywhere — including mid-sketch and mid-plan-reviewer. Not restricted to checkpoint boundaries between numbered steps.
- **Source**: user

## Decision 4: Generalization scope
- **Question**: Should the design intentionally generalize so /implement and /review can reuse it?
- **Resolution**: /design first, with a shared helper primitive (under `scripts/`) that /implement and /review can later adopt. Build it generic from the start; do not ship adopter code in this feature.
- **Source**: user

## Decision 5: In-flight external reviewer handling
- **Question**: When pause fires while a Cursor/Codex external is still running, what happens to that reviewer?
- **Resolution**: Abandon — kill the launcher, discard partial output, and re-launch fresh on resume. Wasted tokens are accepted in exchange for simpler state machine.
- **Source**: user

## Decision 6: Resume invocation grammar
- **Question**: How does the user trigger a resume?
- **Resolution**: Auto-detect — plain `/design <N>` resumes when paused-state markers exist in the issue body. No explicit `--resume` flag required. Mirrors `/implement`'s `parent-issue.md` auto-resume pattern.
- **Source**: user

## Decision 7: Pause/resume cycles
- **Question**: Should /design allow unbounded pause → resume → pause → resume cycles?
- **Resolution**: Unbounded. Each resume can be paused again. The paused-state marker is re-entrant and updated on each pause.
- **Source**: user

## Decision 8: Concurrent issue-body edits between pause and resume
- **Question**: If the issue body is edited between pause and resume, what should /design do?
- **Resolution**: Warn but continue — the paused-state marker wins and clobbers conflicting edits.
- **Source**: user

## Decision 9: Rollout posture
- **Question**: Should pause/resume ship as a feature-flagged opt-in initially, or always-on?
- **Resolution**: Always-on once landed. Pause is a passive primitive; users who never signal pause see zero change.
- **Source**: user

## Decisions resolved from codebase

### Codebase finding 1: existing partial infrastructure
- `skills/design/scripts/design-driver.sh` already supports `--resume-from STEP` for ACTION-sequence replay (EMIT_PLAN, VALIDATE_PLAN_COMMANDS, FINALIZE, TALLY). This is action-replay, not session-level pause/resume.
- `/implement` has `parent-issue.md` sentinel + `ship-pr-state.sh` for `PHASE` resume in `ship-pr.sh`. The shared helper from Decision 4 should generalize the parent-issue.md pattern.
- `plan-block-write.sh` writes `larch:plan` markers to issue body. The same body-marker mechanism is the natural home for a `larch:design-pause` block.

### Codebase finding 2: tracking-issue title invariants
- Title states `[DESIGNING]` (Step 0b sub-step 5.5) → `[DESIGNED]` (Step 5c after Gate C approval). Paused state must use a distinct token (e.g., `[DESIGN PAUSED]` or stay at `[DESIGNING]` with marker block) so /implement's admission gate (`implement-admission.sh`) does not adopt a paused issue as `[DESIGNED]`.

### Codebase finding 3: single-runner invariant
- `AGENTS.md` mandates only one `/design` per repo at a time. Paused state must be detectable so a second `/design` invocation on the same paused issue auto-resumes the same paused state rather than starting a parallel run.

Decisions resolved: 9 user + 3 codebase = 12 total.
