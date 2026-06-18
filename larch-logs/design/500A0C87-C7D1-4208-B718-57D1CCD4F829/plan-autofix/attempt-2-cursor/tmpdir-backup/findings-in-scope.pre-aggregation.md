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

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py (proposed publish redaction); python/redact.py:417-445
- **Concern**: [SCOPE-REDUCTION] Publish redaction switches from secrets-only redaction to full path redaction. Scenario: The current shell uses python/cli.py redact secrets, which preserves tmpdir and operator paths; redact.redact() also rewrites paths and can change the published plan block during a parity port
- **Proposed resolution**: Use redact.redact_secrets_only() or the exact redact secrets equivalent, while keeping the empty-output and truncation-sentinel checks

### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py:79-81
- **Concern**: [SCOPE-REDUCTION] Publish redaction calls redact.redact() instead of the bash parity surface redact secrets / redact_secrets_only(). Scenario: Bash pipes the plan through python/cli.py redact secrets (secrets-only). redact() also strips session tmpdir literals, so ported publish can rewrite plan paths/content differently and change the larch:plan block written to the issue
- **Proposed resolution**: Use redact_secrets_only() (or subprocess python/cli.py redact secrets) and keep the existing empty-file / non-zero exit checks only

### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-clarify.sh:167-206
- **Concern**: Thin wrapper drops argv validation before pause-save. Scenario: Current driver rejects missing/invalid --issue and --phase before pause-save; the wrapper plan pause branch can run with empty ISSUE or skip phase checks, changing exit codes and pause-save inputs versus today
- **Proposed resolution**: Keep current ordering: parse and validate --phase and --issue (and --claude-pid when present) before the .pause-requested branch; only then exec design pause-save or delegate to python/cli.py design clarify

### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/clarify.py:planned publish redaction; python/redact.py:319-334
- **Concern**: [SCOPE-REDUCTION] Redaction plan switches from secrets-only parity to broader tmpdir redaction and new truncation-fail behavior. Scenario: Current design-clarify.sh uses python/cli.py redact secrets, which maps to redact_secrets_only and preserves tmpdir/operator paths. The planned redact.redact() rewrites those paths, and the new truncation-sentinel failure can reject a clarify plan the existing phase would publish. This is a behavior change in a parity port.
- **Proposed resolution**: Use redact.redact_secrets_only() for the plan block, and keep the existing redact command semantics unless a separate issue explicitly changes clarify redaction policy.

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-clarify.sh:189-205
- **Concern**: [SCOPE-REDUCTION] Wrapper owns pause-save before the Python route-state fallback. Scenario: The current script loads .design-step0-route-state.env before pause-save, so pause gets the resolved REPO when source-env lacks it. The planned wrapper pause branch runs before the Python driver can load route state, so a clarify pause can omit --repo and fall back to gh repo resolution against the wrong or unavailable repo.
- **Proposed resolution**: Remove the wrapper pause short-circuit and delegate to python/cli.py design clarify so the Python driver loads route state before pause-save, or load the same route-state fallback in the wrapper before invoking pause-save.

