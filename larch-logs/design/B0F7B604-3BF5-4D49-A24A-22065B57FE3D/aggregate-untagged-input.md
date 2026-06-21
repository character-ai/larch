### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Plan must restore `p`/`progress` during Step 3 immediate-background wait without AskUserQuestion disambiguation. Scenario: Issue Example 2 shows `p` opening pause/wait/cancel menu while plan-review runs; binding scope requires yellow status-file snapshot only, no step advance
- **Proposed resolution**: Route exact `p` or `progress` (case per prior contract) to read the phase progress status artifact, emit yellow contents, and end the turn; do not treat as pause/cancel/stray-keystroke prompt

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Plan must restore ship-pr/review progress check without orchestrator narration or extra reads. Scenario: Issue Example 1 shows a full recap, unrelated file Read, and step-advance prose; scope requires status-file-only display with no extra turns and no context pollution
- **Proposed resolution**: On `p`/`progress` during ship-pr or review fences: read only the harness progress status file, print it in the existing yellow progress channel, yield/end turn; forbid plan peek, tally narration, or background-fence advancement

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/progress-reporting.md
- **Concern**: Plan must pin the authoritative progress status file path and freshness rules per phase. Scenario: Issue cites files that review and ship-pr already create; ambiguous path or stale-file fallback invites wrong snapshots or silent no-op
- **Proposed resolution**: Document one status file per covered phase (design plan-review wait, implement review, ship-pr), how it is updated by wrappers, and that progress prompt reads that file only (no substitute logs or stdout scraping)

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md
- **Concern**: Design fix must not violate immediate-background wait contract while handling `p`. Scenario: Handling `p` by parsing tmpdir early or polling reviewers reintroduces the cost/context pollution the issue forbids
- **Proposed resolution**: Keep Step 3 background wait unchanged; progress prompt is a read-only side path that does not consume `.step3-review-result.env`, reviewer dirs, or terminal sentinels before notification

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/test_progress_report.py
- **Concern**: Planned subprocess test must scrub LARCH_QUIET_DISABLE from the child env. Scenario: conftest autouse sets LARCH_QUIET_DISABLE=1 on os.environ; a subprocess built with os.environ.copy() inherits it, quiet_init becomes a no-op, and the test passes even if report_main still calls quiet_init
- **Proposed resolution**: Build env with os.environ.copy(), then env.pop(config.ENV_LARCH_QUIET_DISABLE, None) (same as python/test_design_lifecycle.py:1971-1974); set LARCH_QUIET_ACTIVE=1 and a foreign LARCH_QUIET_PID; assert stdout has the report and the quiet log does not

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements Phase2
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:85-90; AGENTS.md:17-20
- **Concern**: Testing strategy omits required make lint validation. Scenario: AGENTS.md requires make lint after any change. The proposed Python changes list make py-lint and make py-test only, so the plan is silent on the repository-wide gate required before shipping.
- **Proposed resolution**: Add make lint to the Run list; keep make py-lint and make py-test.

### FINDING_13:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: code-quality
- **Location**: <TMPDIR>/plan.txt:85-90
- **Concern**: Required repo validation omits make lint. Scenario: The plan changes Python files but lists only make py-lint and make py-test, missing the repository-required make lint after any change
- **Proposed resolution**: Add make lint to the Run list before make py-lint and make py-test

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-Scope Audit
- **Severity**: blocking
- **Focus area**: risk-integration
- **Location**: plan.txt
- **Concern**: Plan artifact unreadable in this review slot. Scenario: Without plan.txt and repo reads the sibling-command audit boundary quiet-contract scope and per-file change list cannot be validated
- **Proposed resolution**: Re-run plan review after read access to <TMPDIR>/plan.txt and the repo is restored
