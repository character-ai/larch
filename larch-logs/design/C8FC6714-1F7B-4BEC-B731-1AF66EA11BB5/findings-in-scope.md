### FINDING_1: Shared Markdown sweep omits lint-scanned Family B fences
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-sweep-completeness, Codex-dyn-sweep-completeness
- **Severity**: important
- **Concern**: The planned Markdown sweep omits `skills/shared/*.md` files that `lint-foreground-markers.sh` already scans, especially `skills/shared/external-reviewers.md` and `skills/shared/dialectic-protocol.md`, leaving existing `collect-agent-results.sh` background-plus-monitor fences stale or causing CI lint failures once the new invariant lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add these two files to the Markdown sweep (same & / PID=$! / wait pattern as research/design references) or CI will fail after the new lint rule lands
  - From Codex-Arch: Add the shared files to the plan and sweep every matching skills/shared/*.md Family B fence, not only skill-specific reference files
  - From Cursor-Edge: Add skills/shared/external-reviewers.md and skills/shared/dialectic-protocol.md to the sweep; grep skills/shared/*.md for all five writer basenames
  - From Cursor-Innovation: Add skills/shared/dialectic-protocol.md and skills/shared/external-reviewers.md to sweep; grep skills/shared/*.md for five writer basenames
  - From Cursor-Pragmatic: Add skills/shared/external-reviewers.md and skills/shared/dialectic-protocol.md to the explicit sweep list (grep skills/shared for collect-agent-results.sh + breadcrumb-monitor.sh pairs)
  - From Codex-Pragmatic: Add a skills/shared/*.md sweep to the plan, at minimum updating external-reviewers.md and dialectic-protocol.md
  - From Cursor-Requirements: Add skills/shared/external-reviewers.md to Files to modify and apply the canonical writer-& PID wait pattern to the Collection fence
  - From Cursor-dyn-sweep-completeness: Add skills/shared/external-reviewers.md to Files to modify with the same wait pattern as other collector fences
  - From Codex-dyn-sweep-completeness: Add `skills/shared/external-reviewers.md` to Files to modify and rewrite the fenced block at lines 46-68 to the canonical writer `&`, PID capture, monitor, then `wait "$PID" 2>/dev/null || true` shape

### FINDING_2: PID-capture lint window conflicts with multiline writer invocations
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The proposed lint rule measures PID capture from the first physical anchor line, but real Family B commands span multiple backslash-continued lines, so correct PID capture after command completion would be rejected or encourage invalid placement before the command has ended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Define the check relative to the merged logical command end, require the shell ampersand on that command, and add a multiline Step 8-style positive fixture
  - From Codex-Edge: Define the capture window relative to the logical command end, not the anchor start line. Extend the linter tests with a multiline ship-pr.sh fixture matching skills/implement/SKILL.md Step 8, with the ampersand on the final argv line and PID capture immediately after.
  - From Codex-Innovation: Track the logical command end after backslash continuations and require & plus PID capture within three nonblank lines after the final physical command line
  - From Codex-Requirements: Define the capture position relative to the end of the logical backslash-continued command, not the first physical anchor line, and add multi-line ship-pr.sh and collect-agent-results.sh fixtures

### FINDING_3: Next-fence wait allowance is not modeled by the current Markdown scanner
- **Reviewer(s)**: Codex-Arch, Codex-dyn-lint-regex-fidelity
- **Severity**: important
- **Concern**: The plan allows monitor or wait support in the next fenced block, but the current scanner evaluates the current fence body and only uses post-fence context for prose checks, so this requires new pending-anchor state or removal of the allowance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Prefer requiring capture, monitor, and wait in the same fence; otherwise explicitly design and test a pending-anchor lookahead path
  - From Codex-dyn-lint-regex-fidelity: Revise the Markdown scanner to carry pending Family B anchor state into the next shell fence within the 10-line window, then add a fixture with writer/PID capture in fence 1 and monitor/wait in fence 2; otherwise remove the next-fence allowance from the contract.

### FINDING_4: New regression harness is not wired into relevant-checks
- **Reviewer(s)**: Codex-Arch, Codex-Requirements
- **Severity**: important
- **Concern**: Registering a new Makefile target is insufficient for `scripts/relevant-checks.sh`, which delegates through pre-commit on changed files and would not necessarily run `test-background-monitor-wait`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a local pre-commit hook or explicit relevant-checks routing for the new harness, plus a relevant-checks test proving the intended path runs
  - From Codex-Requirements: Add .pre-commit-config.yaml wiring or fold the harness into an always-run local hook, and update docs/linting.md so make lint, CI shards, and relevant-checks have a single documented path

### FINDING_5: Fake-writer harness models the wrong process lifetime
- **Reviewer(s)**: Codex-Arch, Codex-Requirements, Codex-Edge, Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed regression harness can model a writer that exits after spawning a background child, so `wait "$writer_pid"` waits only for the short-lived shell rather than proving coupling to a still-running top-level Family B writer after an early sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Make the fake top-level writer write the sentinel early and then remain alive until a delayed marker or child wait completes; assert wrapper completion occurs after that marker
  - From Codex-Edge: Make the fake top-level writer write the done sentinel early and then remain alive in the foreground, for example printf EXIT_CODE=0 > "$LARCH_DONE_SENTINEL"; sleep 5; exit 0. Use a marker-file on writer exit rather than only elapsed-time math.
  - From Codex-Innovation: Make the fake writer write the sentinel and then remain alive itself, e.g. write sentinel then sleep 5, with a negative no-wait control
  - From Codex-Pragmatic: Make the fake writer write the done sentinel and then sleep in the foreground in the same writer process; keep a no-wait negative control and prefer marker-file completion over tight elapsed-time assertions

### FINDING_6: Canonical wrapper masks monitor infrastructure failures
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: Making `wait ... || true` the final command means a nonzero `breadcrumb-monitor` result, such as bad argv/path validation or timeout, can be overwritten by a successful reap and reported as success.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Capture monitor status before waiting, always wait/reap the writer, then exit with the monitor status, e.g. monitor_rc=0; breadcrumb-monitor ... || monitor_rc=$?; wait "$pid" 2>/dev/null || true; exit "$monitor_rc". Add a negative harness case for monitor timeout/path failure preserving non-zero wrapper status.

### FINDING_7: collect-agent-results.sh may no longer write the done sentinel
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: `collect-agent-results.sh` installs the quiet done trap, then replaces `EXIT` with a `WAIT_STDERR` cleanup trap, so monitor-based fences can hang until timeout because the expected done sentinel is not written on normal collector exit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Include collect-agent-results.sh in the implementation scope: preserve the existing quiet done trap when adding WAIT_STDERR cleanup, for example by installing cleanup before larch_quiet_append_done_trap or by composing the cleanup with the existing trap through the lib-quiet helper pattern. Add a real collect-agent-results.sh monitor smoke or unit fixture.

### FINDING_8: Shell backgrounding contract conflicts with tool run_in_background usage
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan canonizes shell `&`, `$!`, and `wait`, while live fences also use tool-level `run_in_background`, creating ambiguity about when shell backgrounding is required and risking double-backgrounding or waiting on the wrong PID.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Reconcile in §4: when shell & is required vs when tool JSON alone suffices; one worked example matching implement SKILL ship-pr block

### FINDING_9: Caller should wait on paired PID file rather than only `$!`
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Existing fences do not necessarily use shell `&`, and Family B writers already publish `LARCH_PAIRED_PID_FILE`; relying only on `$!` can be stale, unset, or point at the wrong process shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Post-monitor wait on PID read from LARCH_PAIRED_PID_FILE (reuse monitor validation); treat $! as optional when & present

### FINDING_10: Monitor-level paired-PID draining may be the more complete fix
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A fence-only wait fix leaves `breadcrumb-monitor.sh` itself returning on the done sentinel without draining the paired PID, so tool-background and sub-pipeline variants can remain inconsistent across callers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Consider post-done paired-PID drain inside breadcrumb-monitor.sh; keep caller wait as belt-and-suspenders only if needed

### FINDING_11: Shell-file lint enforcement is missing or overstated
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan claims a shell-file scan path for PID/wait enforcement, but the referenced linter behavior only covers nested unset scanning, leaving future `.sh` wrappers of Family B pairs without mechanical wait enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add scan_shell_file_for_family_b_wait mirroring fence helper or state enforcement is Markdown-only

### FINDING_12: Missing ampersand must fail lint if the invariant requires shell backgrounding
- **Reviewer(s)**: Cursor-Innovation, Codex-dyn-lint-regex-fidelity
- **Severity**: important
- **Concern**: Treating a missing `&` as warning-only conflicts with the fail-closed PID/wait invariant; lint would pass even though there is no real writer PID to wait on.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add hard fail for missing & on top-level writers or drop & requirement and wait on paired-pid file only
  - From Codex-dyn-lint-regex-fidelity: Make the `&-present-before-pid-capture` check an exit-1 lint violation, with the existing suppression mechanism for intentional exceptions, and add a negative fixture that verifies nonzero exit.

### FINDING_13: Canonical wait discards load-bearing writer exit status
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Codex-Requirements, Cursor-dyn-exit-code-discard, Codex-dyn-exit-code-discard
- **Severity**: important
- **Concern**: The proposed `wait "$PID" 2>/dev/null || true` hides Family B writer failures. For `ship-pr.sh` and other load-bearing callers, this can make the wrapper exit 0 after writer exit codes that should drive bail, stall, conflict handoff, retry, or downstream parsing decisions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Propagate wait exit code or check LARCH_STATUS_FILE after wait before continuing
  - From Codex-Innovation: Redirect writer stdout to a temp file, monitor, wait, read EXIT_CODE from LARCH_STATUS_FILE, then parse or eval the captured stdout file
  - From Codex-Pragmatic: Capture wait status or read LARCH_STATUS_FILE after the monitor, then emit or propagate a stable writer exit code; update SKILL parse instructions and tests around that contract
  - From Codex-Requirements: Revise the wrapper contract to capture monitor_rc and writer_rc; on monitor success return the writer status or update the post-block routing to read LARCH_STATUS_FILE explicitly. Add regression coverage for representative ship-pr.sh nonzero exits
  - From Cursor-dyn-exit-code-discard: Update Step 8+ prose to branch on EXIT_CODE from $LARCH_STATUS_FILE (written by lib-quiet exit trap per scripts/breadcrumb-monitor.md:97-100) before ship-pr-state key reads; do not rely on wrapper process exit once wait uses || true
  - From Codex-dyn-exit-code-discard: Do not use unconditional || true for load-bearing Family B callers. Capture monitor_rc and writer_rc, then on monitor success exit with writer_rc; on monitor infrastructure failure preserve monitor_rc or explicitly map it. Update Step 8 prose and lint/tests to require status propagation for ship-pr.sh.

### FINDING_14: Backgrounding stdout-capturing writers breaks assignment/eval contracts
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: Some Family B-like commands capture stdout through command substitution and eval it later; naively appending `&` backgrounds the assignment in a subshell or loses captured KVs, breaking downstream parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Redirect writer stdout to a temp file, monitor, wait, read EXIT_CODE from LARCH_STATUS_FILE, then parse or eval the captured stdout file
  - From Codex-Requirements: Specify a refactor for stdout-capturing writers: redirect writer stdout to a temp file, background the writer, monitor, wait, then read/eval the captured file after completion. Add a lint or harness fixture for this shape

### FINDING_15: Existing positive lint fixtures need updating for the new invariant
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: Current clean Family B lint fixtures may fail once PID capture, monitor, and wait become required, making it unclear whether new negative cases are meaningful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update every positive top-level Family B fixture to include script &, matching PID capture, monitor, and wait, or explicitly scope non-writer/nested cases

### FINDING_16: Linting docs are omitted from the plan
- **Reviewer(s)**: Codex-Innovation
- **Severity**: nit
- **Concern**: The lint invariant changes, but `docs/linting.md` is not included, leaving the canonical linting table incomplete for contributors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update docs/linting.md alongside BASH_AUTHORING.md and scripts/lint-foreground-markers.md to document the new invariant and harness target

### FINDING_17: Optional local PID capture needs lint support and fixture coverage
- **Reviewer(s)**: Cursor-dyn-lint-regex-fidelity, Codex-dyn-lint-regex-fidelity
- **Severity**: important
- **Concern**: The helper contract calls for shell-function support such as `local FAMILY_B_PID=$!`, but the proposed regex and tests may only cover plain assignments in Markdown fences.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-lint-regex-fidelity: Add `(local[[:space:]]+)?` to the PID-capture pattern in the helper spec and in `fence_has_family_b_pid_capture_and_wait`; add a harness fixture with `local VAR=$!`
  - From Codex-dyn-lint-regex-fidelity: Add a shell-script fixture using a function that launches a top-level Family B writer with `&`, captures `local FAMILY_B_PID=$!`, runs the monitor, and waits on `"$FAMILY_B_PID"`; assert clean.

### FINDING_18: Named wait forms lack positive fixture coverage
- **Reviewer(s)**: Codex-dyn-lint-regex-fidelity
- **Severity**: latent
- **Concern**: The helper spec permits `wait "$IDENT"`, `wait $IDENT`, and `wait "${IDENT}"`, but the proposed tests may only prove the canonical quoted form.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-lint-regex-fidelity: Add positive fixture coverage for the unquoted and brace-quoted wait forms, ideally table-driven alongside the canonical double-quoted case.

### FINDING_19: Identifier mismatch failure mode needs a regression fixture
- **Reviewer(s)**: Codex-dyn-lint-regex-fidelity
- **Severity**: latent
- **Concern**: The plan requires waiting on the captured PID variable, but tests do not cover a fence that captures one identifier and waits on another.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-lint-regex-fidelity: Add a negative fixture that captures `SHIP_PR_PID=$!` but waits on a different identifier after the monitor; assert exit 1 and the `wait identifier does not match captured PID variable` diagnostic.

### FINDING_20: Timeout boundedness is not preserved by unconditional post-monitor wait
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-exit-code-discard
- **Severity**: important
- **Concern**: If `breadcrumb-monitor.sh` exits nonzero on timeout or monitor failure, an unconditional `wait` on the writer can block beyond the monitor’s bounded timeout, especially when the paired PID is missing, stale, wrong, or not reaped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add an explicit nonzero-monitor branch with bounded reap semantics before returning monitor_rc, and document/test the timeout path separately from normal sentinel completion
  - From Codex-dyn-exit-code-discard: Revise the caller contract for nonzero monitor_rc: avoid an unbounded wait after monitor timeout, or add an explicit bounded post-monitor reap policy before returning monitor_rc. Also correct the plan text so it does not assert a guarantee the script does not implement.

### FINDING_21: Exit-code discard needs explicit status regression coverage
- **Reviewer(s)**: Codex-dyn-exit-code-discard
- **Severity**: latent
- **Concern**: The proposed monitor-wait harness checks timing/orphan behavior but would not catch a wrapper that still exits 0 after a writer writes the done sentinel and exits nonzero.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-exit-code-discard: Add explicit negative/status tests: fake writer exits with representative ship-pr codes 3, 4, 5, and 6 after the early sentinel, and the wrapper must return the same load-bearing code. Add a lint fixture for the Step 8 ship-pr pattern rejecting unconditional wait-status discard.
