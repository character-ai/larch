### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-clarify.sh:189-200
- **Concern**: Route-state read failure must not always call `_stage_failed_clarify`. Scenario: Bash only stages `failed-clarify` on fetch-phase route-state failure; publish writes `CLARIFY_PUBLISH_STATUS=route-state-read-failed` and exits without staging. The plan groups route-state with fetch staging and never splits by phase.
- **Proposed resolution**: A publish run with missing `REPO` and unreadable `.design-step0-route-state.env` could spuriously stage terminal failed-clarify state.

### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py (proposed publish path); skills/design/scripts/design-clarify.sh:295-312
- **Concern**: Publish path does not explicitly require REQUEST_ID before side effects. Scenario: A malformed .design-clarify-request.env can reach plan write or log publish before clarify_comment_post rejects the bad id, regressing the current fail-closed ordering
- **Proposed resolution**: Add an early positive-integer REQUEST_ID validation immediately after request-state load and before artifact redaction, plan write, log publish, response post, or label removal

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-clarify.sh:167-206
- **Concern**: Thin wrapper drops argv validation before pause-save. Scenario: Current driver rejects missing/invalid --issue and --phase before pause-save; the wrapper plan pause branch can run with empty ISSUE or skip phase checks, changing exit codes and pause-save inputs versus today
- **Proposed resolution**: Keep current ordering: parse and validate --phase and --issue (and --claude-pid when present) before the .pause-requested branch; only then exec design pause-save or delegate to python/cli.py design clarify
