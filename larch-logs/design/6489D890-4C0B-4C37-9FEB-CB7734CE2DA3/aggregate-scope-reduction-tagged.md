### FINDING_1:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/bug/SKILL.md:32-40
- **Concern**: [SCOPE-REDUCTION] Plan adds `--urgent` parsing but does not require stripping it before Step 1 validation. Scenario: `/bug --urgent` alone is non-empty to the current trim check, so the run can continue and file `[BUG] (URGENT) Bug report` with no real operator description
- **Proposed resolution**: Add an explicit Step 0/1 rule: strip all leading `--urgent` tokens first, then run empty-input and security triage on the remaining description text

### FINDING_1:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: security
- **Location**: plan.txt:40-44
- **Concern**: [SCOPE-REDUCTION] Optional committed code-flow-diagram.failure.log expands the run-log surface beyond the required durable tail. Scenario: A verbose diagram subprocess failure would commit a new full stdout/stderr-derived artifact under larch-logs even though the committed execution-issues tail already satisfies post-run diagnosis; this increases redaction and docs/run-logs.md contract burden
- **Proposed resolution**: Remove the run-dir copy and copy-specific test; keep the tmpdir failure log plus committed execution-issues DIAGRAM_REASON/tail. If the artifact stays, add it to docs/run-logs.md
