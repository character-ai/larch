### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:531-547
- **Concern**: Step 4 and Gate C still parse tail wrapper stdout after bgjob launcher change. Scenario: `design-step3b-tail.sh` is converted to a thin `bgjob start` launcher whose harness-visible stdout is only `BGJOB_STATUS=STARTED`. Step 4 still re-emits `---LARCH-REJECTED-*---` from wrapper output, and Step 4b still parses `SKIP_APPROVE_REQUESTED_GATEC` and Gate C preview/digest from tail wrapper stdout (`approval-gates.md` also requires same-turn tail stdout). Child output lands in the bgjob stdout log, so rejected-findings reporting and Gate C auto-approve routing can silently break.
- **Proposed resolution**: Rebind Step 4 post-`DONE` handling in `skills/design/SKILL.md`, `skills/design/references/approval-gates.md`, and `skills/design/scripts/design-step3b-tail.md`: after `BGJOB_RC=0`, read `SKIP_APPROVE_REQUESTED_GATEC` and any framed rejected-findings body from `$DESIGN_TMPDIR/bgjob/design-step4-tail.result.env` (merge env written before daemon exit) and/or the captured final `bgjob wait` `DONE` stdout; keep disk fallbacks for `resume@4b`. Update harness pins accordingly.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/shared/design-background-wait.md:37-50
- **Concern**: Step 3 post-DONE reviewer-table sequence has no migrated normative home. Scenario: `design-background-wait.md` owns the Step 3 post-`DONE` contract (emit `$DESIGN_TMPDIR/reviewer-status-table.txt`, then parse loop routing). The plan removes `design-background-wait.md` loads from migrated `/design` call sites but does not relocate that sequence to `bgjob-wait.md`, `skills/design/SKILL.md`, or `plan-review.md`, and `test-design-structure.sh` still pins the old post-notification load contract. After migration, Step 3 can route from the bgjob result env without ever printing the compact reviewer table.
- **Proposed resolution**: Add a Step 3 post-`DONE` section to `skills/shared/bgjob-wait.md` (or inline in `skills/design/SKILL.md`): after final `bgjob wait` returns `DONE` with `BGJOB_RC=0` and `.completed/step-3-terminal` is present, Read and emit `reviewer-status-table.txt`, then parse `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` (legacy fallback only when absent). Replace the harness `check_context` pins that still require loading `Step 3 post-notification sequence` from `design-background-wait.md`.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md (Testing strategy)
- **Concern**: Final validation omits the committed run-log half of acceptance criterion 6. Scenario: Issue AC 6 requires both zero `<task-notification>` transcript entries and no notification-recovery turns in the committed run log. The plan's final validation bullet checks only the session transcript, so a regression that still writes notification-recovery turns to `larch-logs/` can pass manual QA.
- **Proposed resolution**: Extend the Testing strategy / final-validation bullet to assert the committed run log also has no notification-recovery turns for migrated steps, matching issue AC 6.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:91-95
- **Concern**: Plan omits this live Gate B authority; Step 3 outcomes still read `.step3-review-result.env` and resume via `design-step3-review.sh --starting-round`, leaving the legacy post-review path outside the bgjob contract.. Scenario: A resumed Step 3 review can keep routing off the stale legacy env and old resume fence, so Gate B may miss fresh `BGJOB_RC` state or re-enter the wrong branch after this migration.
- **Proposed resolution**: Add `skills/design/references/approval-gates.md` to UPDATED and rebind Step 3 outcomes and resume branches to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with `BGJOB_RC=0` gating.

### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/shared/bgjob-wait.md
- **Concern**: Step 3 post-DONE reviewer-table and loop-routing contract has no migration target. Scenario: The plan removes `design-background-wait.md` loads from `skills/design/SKILL.md` and repoints harness pins away from that file, but `bgjob-wait.md` only documents generic start/wait/DONE rules. The compact reviewer-status-table Read plus result-env routing sequence still lives only in `design-background-wait.md` §Step 3 post-notification sequence. After migration, Step 3 can finish with `BGJOB_RC=0` yet skip the table and mis-route on stale legacy paths.
- **Proposed resolution**: Add a Step 3 post-DONE section to `skills/shared/bgjob-wait.md` (or an explicit `skills/design/references/plan-review.md` anchor): after final `DONE` with `BGJOB_RC=0`, Read `$DESIGN_TMPDIR/reviewer-status-table.txt` once, then parse `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with legacy fallback; require `.completed/step-3` before Step 3b. Pin the new load target in `scripts/test-design-structure.sh`.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md
- **Concern**: Parallel external lanes lack distinct per-lane `--step` slugs. Scenario: bgjob registry keys are `{run_id}-{step}` and result envs are `$TMPDIR/bgjob/<step>.result.env` for one tmpdir run_id. Research launches four Codex lanes in one wave; validation runs Cursor and Codex in parallel; brainstorm can launch framing and scope together. Reusing one step name makes the second `bgjob start` overwrite the registry row and unlink the first lane's result env on daemon start.
- **Proposed resolution**: In `research-phase.md`, `validation-phase.md`, and `brainstorm.md`, require unique `--step` values per parallel lane (for example `research-arch`, `research-edge`, `validation-cursor`, `design-brainstorm-framing`) with per-lane merge env truncation. Add a collision regression in `scripts/test-research-structure.sh`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md (Testing strategy)
- **Concern**: Final validation omits the committed run-log half of acceptance criterion 6. Scenario: Binding acceptance criterion 6 requires zero notification-recovery turns in the committed run log, not only zero `<task-notification>` entries in the session transcript. The plan's final validation bullet checks transcript entries only, so a run can pass manual QA while still logging notification-recovery turns.
- **Proposed resolution**: Extend the Testing strategy final-validation step to assert no notification-recovery turns in the committed `/design` and `/implement` run logs, matching acceptance criterion 6.

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:17-23
- **Concern**: Step 8 bgjob gate conflicts with route-exit's numeric rc contract. Scenario: The plan gates Step 8 route-exit on BGJOB_RC=0, but route-exit currently maps driver rc 1, 3, 4, and 6 from the handoff sidecars; a valid ci-fix, reship, stall, or operator branch would be treated as generic bgjob failure instead of preserving ship route-exit consumption.
- **Proposed resolution**: For Step 8, either make the bgjob child exit 0 after it safely writes current rc/json handoff sidecars and keep the real driver rc only in the sidecar, or allow numeric BGJOB_RC with valid current handoff sidecars to proceed to ship route-exit while still blocking timeout, orphaned, and missing sidecars; pin rc 3 or rc 6 route-exit coverage in test-step-8-ship.sh.

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:626-636
- **Concern**: Step 8 re-entry can start a second live ship daemon. Scenario: The plan converts every Step 8 re-entry or relaunch to bgjob start, but only Step 5 gets a live-registry rejoin rule; after an unexpected turn end with implement-step8-ship still live and no handoff yet, a fresh step-8-ship.sh launch can overwrite the registry and run a second ship driver against the same state and handoff files.
- **Proposed resolution**: Add the same live identity-valid registry rule for implement-step8-ship before every Step 8 bgjob start: rejoin with bgjob wait when live, clear only stale or dead rows before a fresh start, and pin this in step-8-ship.md and test-step-8-ship.sh.

### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/shared/bgjob-wait.md
- **Concern**: Step 3 post-DONE orchestration has no migrated normative home. Scenario: The plan repoints `skills/design/SKILL.md` and harnesses from `design-background-wait.md` to `bgjob-wait.md`, but `bgjob-wait.md` only covers start/wait/DONE gating. It omits the Step 3 post-DONE reviewer-status table emit and `NEXT_ACTION` loop-routing sequence still defined in `design-background-wait.md` §Step 3 post-notification sequence. After migration, Step 3 can return `BGJOB_RC=0` with no contract for printing `reviewer-status-table.txt` or parsing loop envelopes.
- **Proposed resolution**: Add a design-specific post-DONE section to `skills/shared/bgjob-wait.md` (or `skills/design/references/plan-review.md`) that preserves the reviewer-table Read/emit rules and result-env routing after final `bgjob wait` `DONE` with `BGJOB_RC=0`, rebinding reads to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` with legacy fallback; pin it in `scripts/test-design-structure.sh`.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:Testing strategy
- **Concern**: Final validation omits committed run-log acceptance criterion. Scenario: Issue AC6 requires zero `<task-notification>` entries and no notification-recovery turns in the committed run log. The plan's final validation bullet checks only the session transcript. A run could pass manual validation while still logging notification-recovery turns, leaving AC6 unverified.
- **Proposed resolution**: Restore the AC6 run-log half explicitly in Testing strategy / final validation: inspect the committed `larch-logs` run log (or session transcript export) for notification-recovery turns, not just absence of `<task-notification>` in the live transcript.
