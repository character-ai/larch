### FINDING_1: Step 4 and Gate C still parse tail stdout after the bgjob launcher change
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: Step 4 post-DONE handling and Gate C routing still depend on tail-wrapper stdout, so once the wrapper becomes a thin `bgjob start` launcher the rejected-findings reporting and Gate C auto-approve path can silently break because child output moves to bgjob logs/result envs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Rebind Step 4 post-`DONE` handling in `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, and `skills/design/scripts/design-step3b-tail.md`: after `BGJOB_RC=0`, read `SKIP_APPROVE_REQUESTED_GATEC` and any framed rejected-findings body from `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` (merge env written before daemon exit) and/or the captured final `bgjob wait` `DONE` stdout; keep disk fallbacks for `resume@4b`. Update harness pins accordingly.


### FINDING_4: Step 3 Gate B still points at the legacy resume env and resume fence
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Concern**: Step 3 outcomes still read the legacy `.step3-review-result.env` and resume via `design-step3-review.sh --starting-round`, so the resumed review path can stay outside the bgjob contract and miss fresh `BGJOB_RC` state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add `skills/design/references/approval-gates.md` to UPDATED and rebind Step 3 outcomes and resume branches to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with `BGJOB_RC=0` gating.


### FINDING_5: Parallel external lanes need distinct per-lane `--step` slugs
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Concern**: Reusing one bgjob step name for parallel external lanes can overwrite the registry row and unlink the first lane's result env, so concurrent research/validation/brainstorm launches can clobber each other.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `research-phase.md`, `validation-phase.md`, and `brainstorm.md`, require unique `--step` values per parallel lane (for example `research-arch`, `research-edge`, `validation-cursor`, `design-brainstorm-framing`) with per-lane merge env truncation. Add a collision regression in `scripts/test-research-structure.sh`.


### FINDING_6: Step 8 bgjob gate conflicts with route-exit's numeric rc contract
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: Gating Step 8 route-exit on `BGJOB_RC=0` would treat valid handoff-sidecar branches as generic bgjob failures, because the existing route-exit contract still uses numeric rc values like 1, 3, 4, and 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: For Step 8, either make the bgjob child exit 0 after it safely writes current rc/json handoff sidecars and keep the real driver rc only in the sidecar, or allow numeric BGJOB_RC with valid current handoff sidecars to proceed to ship route-exit while still blocking timeout, orphaned, and missing sidecars; pin rc 3 or rc 6 route-exit coverage in test-step-8-ship.sh.


### FINDING_7: Step 8 re-entry can start a second live ship daemon
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: A fresh Step 8 bgjob start during an existing live Step 8 registry row can create a second ship driver against the same state and handoff files, because only Step 5 has the live-registry rejoin rule today.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Add the same live identity-valid registry rule for implement-step8-ship before every Step 8 bgjob start: rejoin with bgjob wait when live, clear only stale or dead rows before a fresh start, and pin this in step-8-ship.md and test-step-8-ship.sh.


