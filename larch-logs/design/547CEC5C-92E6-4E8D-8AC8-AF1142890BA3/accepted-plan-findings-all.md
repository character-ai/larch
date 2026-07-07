### FINDING_2: Step 3 result-env parsing still reads the legacy file
- **Reviewer(s)**: Cursor-Arch, Cursor-Requirements
- **Severity**: major
- **Concern**: The `--read-result-env` / `_step3_normalize_read_result_env` path still hardcodes `.step3-review-result.env`, even though bgjob completion truth moves to `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env`; parsing the stale file can miss `BGJOB_RC` and route the review incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Rebind normalize/read-result-env to bgjob/design-step3-review.result.env first (with controlled fallback), include BGJOB_RC in required keys, and pin the path in python/tests/review/test_plan_review.py plus skills/design/scripts/test-design-step3-review.sh."
  - From Cursor-Requirements: "Add `skills/design/references/approval-gates.md` to the plan; rebind Step 3 post-`DONE` parsing in `skills/design/SKILL.md`, `skills/design/references/plan-review.md`, and `plan_review_normalize.py` to read `$DESIGN_TMPDIR/bgjob/design-step3-review.result.env` (via `python/cli.py design read-result-env` or equivalent) with legacy-path fallback only when absent"
  - From Cursor-Requirements: "Make functional updates explicit: either repoint `--read-result-env` / `_step3_normalize_read_result_env` to the bgjob result env, or delete the branch and update `skills/design/scripts/test-design-step3-review.sh` accordingly"


### FINDING_3: Legacy Step 3 harness pins still reference notification recovery
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Concern**: `scripts/test-design-structure.sh` still enforces the old design-background-wait load and notification-recovery literals, so the Step 3 migration can fail CI or leave the legacy contract live even after the docs move.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: "Expand the test-design-structure.sh item with an explicit flip list: replace task-notification/immediate-background pins with bgjob-wait references, repoint Step 4 wait reads to bgjob-wait.md (or the new post-DONE doc), and drop or rewrite SHARED_DESIGN_WAIT_MD notification-recovery contains/not_contains rows."


### FINDING_4: Step 5 resume and re-entry path still needs bgjob ownership
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-dyn-Bgjob Process Safety
- **Severity**: major
- **Concern**: The Step 5 migration still omits the resume wrapper, the branch reference, the detach/reattach contract doc, and the live re-entry coverage, so the stall-recovery path can continue to run on the legacy direct-launch stack.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: "Add `skills/implement/scripts/step-5-resume.sh` and `skills/implement/references/step5-review-branches.md` to the firm update set, then convert the resume path to bgjob launch/wait and result-env ownership."
  - From Cursor-Pragmatic: "Add `### UPDATED: skills/implement/scripts/step-5-review.md` rebinding the contract to bgjob daemon ownership, owner-death/orphan handling, and merge-result env completion; drop detach/reattach sidecar prose"
  - From Codex-Pragmatic: "Add Step 5 re-entry behavior to the plan and harness: a live same-step bgjob must be rejoined or rejected without launching a second loop, while stale or dead rows are cleared before a fresh start."
  - From Codex-dyn-Bgjob Process Safety: "Add the resume-branch files and their wrapper test to the update set, then convert the resume fence to `bgjob start` plus chunked `bgjob wait` with `BGJOB_RC=0` gating before any step-5 re-entry."


### FINDING_9: Merge-result env freshness needs a per-run reset
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Concern**: The daemon merges any pre-existing result env, so a stale `.step*-result.env` from a prior attempt can satisfy required KVs after a new child exits `BGJOB_RC=0` without writing fresh values, causing false success or wrong routing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: "Clear or recreate each per-step merge-result env before `bgjob start`, or add a per-run generation/freshness token before merging; add a minimal stale-env regression assertion to the affected wrapper harnesses."


### FINDING_10: Completion routing still lacks the BGJOB_RC gate
- **Reviewer(s)**: Cursor-Requirements, Cursor-dyn-Bgjob Process Safety
- **Severity**: major
- **Concern**: Step 5 and Step 8 completion routing still treats `bgjob wait` exit status, `DONE`, or notification-time wrapper stdout as sufficient, even though `bgjob wait` exits 0 for `WAIT` and `DEAD`, and `DONE` can still carry `timeout` or `orphaned`; that can mis-route review and route-exit paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: "In `skills/implement/SKILL.md`, state explicitly that after the final `bgjob wait` `DONE` with `BGJOB_RC=0`, required KVs come from wait stdout and `$IMPLEMENT_TMPDIR/bgjob/<step>.result.env`, not from the start launcher or notification recovery"


### FINDING_11: Checks repair-loop still launches bare re-entry commands
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Concern**: The checks repair-loop reference still owns the Step 3, Step 5, and Step 6 post-repair re-entry launch commands, and after `NEXT_ACTION=continue` it still points the orchestrator at bare composite launchers instead of bgjob-waited re-entry paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: "Add `skills/implement/references/checks-repair-loop.md` as an UPDATED file and convert its pinned composite re-entry commands to the shared bgjob start/wait contract with required KV gates"


### FINDING_13: Step 6 in-flight detection needs liveness, not file presence
- **Reviewer(s)**: Cursor-dyn-Bgjob Process Safety
- **Severity**: major
- **Concern**: Step 6 still treats registry file presence as in-flight, so a stale dead registry row can block Step 6 forever, while any registry file can be misread as live after `DEAD`; the migration needs identity-aware liveness instead of presence checks.
- **Suggested revisions (informational for voters; coder decides)**:


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


