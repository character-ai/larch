### FINDING_1: Design Step 3 must restore `p`/`progress` without disambiguation or wait-contract violations
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: During `/design` Step 3 immediate-background plan-review wait, `p` or `progress` must again show the yellow phase progress snapshot and end the turn. It must not open an `AskUserQuestion` pause/wait/cancel menu (Example 2). The fix must not break the immediate-background wait contract by parsing tmpdir early, polling reviewers, or consuming `.step3-review-result.env`, reviewer dirs, or terminal sentinels before the `<task-notification>`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Route exact `p` or `progress` (case per prior contract) to read the phase progress status artifact, emit yellow contents, and end the turn; do not treat as pause/cancel/stray-keystroke prompt
  - From Cursor-Innovation: Keep Step 3 background wait unchanged; progress prompt is a read-only side path that does not consume `.step3-review-result.env`, reviewer dirs, or terminal sentinels before notification

---

### FINDING_2: Implement ship-pr/review must restore status-only `p`/`progress` with no narration
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Concern**: In `/implement` during ship-pr or review background fences, `p`/`progress` must again print only the harness progress status file in the existing yellow channel and yield/end the turn. Example 1 shows forbidden behavior: full recap, unrelated file `Read`, step-advance prose, and context pollution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: On `p`/`progress` during ship-pr or review fences: read only the harness progress status file, print it in the existing yellow progress channel, yield/end turn; forbid plan peek, tally narration, or background-fence advancement

---

### FINDING_3: Pin authoritative progress status file paths and freshness rules
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The plan must document one authoritative progress status file per covered phase (design plan-review wait, implement review, ship-pr), how wrappers update it, and that the progress prompt reads that file only. Ambiguous paths or stale-file fallback risk wrong snapshots or silent no-op.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Document one status file per covered phase (design plan-review wait, implement review, ship-pr), how it is updated by wrappers, and that progress prompt reads that file only (no substitute logs or stdout scraping)

---

### FINDING_4: Subprocess regression test must scrub `LARCH_QUIET_DISABLE` from child env
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The planned subprocess test in `python/test_progress_report.py` must not inherit `LARCH_QUIET_DISABLE=1` from conftest autouse via `os.environ.copy()`. That makes `quiet_init` a no-op and can let the test pass even when `report_main` still calls `quiet_init`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Build env with os.environ.copy(), then env.pop(config.ENV_LARCH_QUIET_DISABLE, None) (same as python/test_design_lifecycle.py:1971-1974); set LARCH_QUIET_ACTIVE=1 and a foreign LARCH_QUIET_PID; assert stdout has the report and the quiet log does not

---

### FINDING_5: Plan testing strategy must include `make lint`
- **Reviewer(s)**: Cursor-Requirements Phase2, Codex-Requirements
- **Severity**: important
- **Concern**: The plan's Run list (`plan.txt` ~85–90) lists only `make py-lint` and `make py-test`. `AGENTS.md` requires `make lint` after any change, so the plan is incomplete for repository-wide validation before shipping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements Phase2: Add make lint to the Run list; keep make py-lint and make py-test.
  - From Codex-Requirements: Add make lint to the Run list before make py-lint and make py-test

---

### FINDING_6: Plan artifact was unreadable; scope audit could not validate change list
- **Reviewer(s)**: Cursor-dyn-Scope Audit
- **Severity**: blocking
- **Concern**: Without read access to `plan.txt` and the repo, the sibling-command audit boundary, quiet-contract scope, and per-file change list could not be validated in this review slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-Scope Audit: Re-run plan review after read access to <TMPDIR>/plan.txt and the repo is restored

---

**Merge notes (diagnostic)**

| Raw ID | Disposition |
|--------|-------------|
| FINDING_3 + FINDING_7 | Merged → FINDING_1 (same surface: `skills/design/SKILL.md` Step 3 `p`/`progress`; complementary restore + constraint) |
| FINDING_4 | Kept → FINDING_2 (distinct surface: `skills/implement/SKILL.md` ship-pr/review) |
| FINDING_6 | Kept → FINDING_3 (documentation surface; separate fix from skill behavior) |
| FINDING_9 | Kept → FINDING_4 |
| FINDING_12 + FINDING_13 | Merged → FINDING_5 (identical concern and fix) |
| FINDING_16 | Kept → FINDING_6 (process/meta; not subsumed by feature findings) |

### FINDING_7:
- **Reviewer(s)**: Cursor-Arch Phase2
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:62-66
- **Concern**: [SCOPE-REDUCTION] Sibling audit can expand the PR beyond the broken p/progress hook path. Scenario: The implementer may change unrelated cli.py commands that also combine quiet_init with stdout, even though the issue only requires restoring progress report capture and the plan already identifies python/progress_report.py as the fix
- **Proposed resolution**: Delete the sibling audit and inline-fix instruction. Keep this PR to python/progress_report.py and the focused regression test; file any unrelated stdout findings separately if discovered.

### FINDING_8:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:62-66
- **Concern**: [SCOPE-REDUCTION] Plan allows inline fixes to unrelated quiet_init callers discovered by the sibling audit. Scenario: The issue scope is the p/progress hook path. Fixing other CLI commands would expand the PR beyond the minimum-change repair, even if another similar bug exists.
- **Proposed resolution**: Make the sibling audit read-only for this PR. Keep only python/progress_report.py and python/test_progress_report.py inline. Record any unrelated matching commands as out-of-scope follow-up items.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: hooks/hooks.json
- **Concern**: [SCOPE-REDUCTION] Prefer one shared interception surface over duplicated per-skill orchestrator prose. Scenario: A plan that only patches design and implement SKILL.md duplicates detection logic and will drift again on the next wait-state edit
- **Proposed resolution**: Centralize `^p$`/`^progress$` handling (hook or shared progress-reporting contract) that any long-running phase calls; skills only document the contract, not reimplement parsing

### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:62-66; scripts/hook-progress-report.sh:32
- **Concern**: [SCOPE-REDUCTION] Plan permits inline fixes to sibling CLI commands outside the progress hook path. Scenario: The reported bug flows only through scripts/hook-progress-report.sh invoking python/cli.py progress report --cwd. Fixing other quiet_init plus stdout commands would expand the PR beyond the progress-report regression.
- **Proposed resolution**: Delete the inline sibling-fix allowance. Keep any audit read-only, and record non-progress matches as out of scope.

### FINDING_11:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:62-66
- **Concern**: [SCOPE-REDUCTION] The sibling audit allows unrelated inline fixes beyond the progress-report bug. Scenario: An implementer could change other quiet_init callers and break unrelated CLI stdout or quiet-routing contracts while fixing a one-command hook regression
- **Proposed resolution**: Remove the sibling-audit inline-fix step. Limit code changes to python/progress_report.py and python/test_progress_report.py. If another command appears broken, file it out of scope.

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements Phase2
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:62-66
- **Concern**: [SCOPE-REDUCTION] Sibling audit authorizes inline fixes outside the progress-report bug. Scenario: The issue scope is restoring typed p/progress reports. If the audit changes another cli.py-registered command, the PR ships unrelated behavior and test surface not required for this bug.
- **Proposed resolution**: Keep the audit read-only or delete it; file any non-progress command defect as out of scope unless it directly blocks progress report.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:62-66
- **Concern**: [SCOPE-REDUCTION] Sibling audit allows unrelated inline fixes. Scenario: The issue scope is the progress prompt path, but the plan permits modifying other cli.py-registered commands if another captured-stdout bug is found
- **Proposed resolution**: Make the sibling audit verification-only, and file any non-progress command defect out of scope instead of fixing it in this PR

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-Stdout Contract
- **Severity**: important
- **Focus area**: architecture
- **Location**: <TMPDIR>/plan.txt:62-66
- **Concern**: [SCOPE-REDUCTION] The plan authorizes fixing sibling quiet_init plus stdout commands inline.. Scenario: The progress hook bug is fixed by removing quiet_init from progress_report.report_main and adding the focused subprocess regression. If the audit finds another command and changes it here, the PR broadens beyond the hook-captured progress report contract.
- **Proposed resolution**: Remove the sibling-audit/fix paragraph, or change it to file any non-progress-report discovery as out of scope without code changes.
