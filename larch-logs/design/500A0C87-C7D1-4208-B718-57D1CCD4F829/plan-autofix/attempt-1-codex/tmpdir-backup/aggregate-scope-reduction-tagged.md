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
