### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/deps/SKILL.md:46-55
- **Concern**: [SCOPE-REDUCTION] Plan forbids auto-flipping dependency edges when the desired client is in-flight. Scenario: Issue scope says non-REGULAR in-flight issues cannot receive new blocked-by edges, and when reasonable the potential dependency should be expressed as the blocker via the other direction (mutable REGULAR client, in-flight blocker). Plan instead warns and skips all such edges with an explicit no-flip rule, so dependencies that could be recorded as REGULAR blocked-by in-flight are never proposed or written.
- **Proposed resolution**: Add a bounded flip path in `deps plan` / Step 3: when desired `(client, blocker)` has an in-flight client and a mutable REGULAR blocker, attempt reversed `(blocker, client)` only when prompt-side rationale shows the reversed scheduling constraint matches the evidence; otherwise keep the loud warning and skip.

### FINDING_7:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:3,129,145,153,209-210,271-274
- **Concern**: [SCOPE-REDUCTION] Plan adds stale issue closes beyond the requested REGULAR issue rewrite flow. Scenario: A /deps run can close open issues as not planned, adding a destructive mutation path not required for the exported audit skill
- **Proposed resolution**: Remove stale-close proposal, apply, docs, tests, and security paths; keep body rewrites only for stale or inaccurate REGULAR issue parts

### FINDING_8:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:65-75,108,116,136,149-151,203,258,278,286,295-297,355
- **Concern**: [SCOPE-REDUCTION] Optional --pair-cap partial-audit mode conflicts with the all-open-issues audit scope. Scenario: The feature asks to audit all currently open issues, but the plan adds a partial mode with extra approval and dependency-write state
- **Proposed resolution**: Remove --pair-cap and partial-audit branches; keep the default complete explicit-ref plus latent dependency audit
