### FINDING_1: Session-env keys must be exported to `os.environ` before in-process Step 2 helpers
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The shared wrapper must export rehydrated session keys into `os.environ` before calling in-process `postplan_emit_main` or `pause_save_main`. `plan_quality.py` and `design_postplan.py` read `ISSUE_NUMBER`, `DESIGN_TMPDIR`, and `CLAUDE_PLUGIN_ROOT` from `os.environ` (and subprocess env copies). A local-only overlay without `os.environ` export breaks pause-save (`ISSUE_NUMBER` empty), plan-validate repo-root resolution, and token sidecar subprocesses even when `session-env.sh` was parsed correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After allowlisted session-env parse, write merged defaults into os.environ (same effective surface as Bash source) before any in-process postplan_emit_main or pause_save_main call; add pytest that sets keys only in session-env file and asserts postplan pause arm sees ISSUE_NUMBER.


### FINDING_6: Step 2a timing mark must stay best-effort when plugin root is empty
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The Step 2a plan makes plugin-root validation fatal before the best-effort timing mark. Bash Step 2a repairs sentinels and exits successfully on the non-pause path even when the timing command cannot run because `CLAUDE_PLUGIN_ROOT` is empty. Fatal validation before timing would regress that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Keep pause-save root validation fatal, but make the non-pause timing mark best-effort: skip timing or ignore root-validation failure before timing while returning success after sentinel repair.


### FINDING_7: Postplan rc 10 inline-retry plan condition is inverted
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The postplan rc 10 inline-retry condition is inverted in the parenthetical. The plan says fallback is not already used while pointing at `.step2b-postplan-fallback-used=true`; implementing that literal condition skips the required first inline retry or repeats the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Change the condition text to .step2b-postplan-fallback-used is absent or not true, matching the Bash != true check.


### FINDING_8: Validator autofix plan must pin required in-process delegation
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The validator autofix plan does not pin the required in-process delegation. The issue asks for an in-process port, but "Call existing plan auto-fix-commands" can be implemented as a subprocess back into `cli.py`, leaving the wrapper body only partially ported.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: State that plan validator-autofix calls auto_fix_plan_commands_main(...) directly, captures its stdout and rc in-process, and add the planned pytest assertion for that direct delegation.


### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/design_lifecycle.py:design step2b-drafter
- **Concern**: [SCOPE-REDUCTION] Fatal in-process postplan should not sys.exit with raw emit rc 2. Scenario: Bash delegates via exec to design-step2b-postplan.sh which maps postplan_emit rc 2 to wrapper exit 1 (design-step2b-postplan.sh:230-232). Plan says drafter exits with the fatal postplan rc (plan.txt:108), so emit rc 2 would yield process exit 2 and change orchestrator/harness expectations vs today.
- **Proposed resolution**: Reuse the postplan wrapper fatal mapping: on emit rc 1 or 2 exit the drafter fence with 1 after diagnostics; reserve returning raw emit rc for the standalone design step2b-postplan CLI only if needed.


