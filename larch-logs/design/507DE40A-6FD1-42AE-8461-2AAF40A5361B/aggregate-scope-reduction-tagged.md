### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Reuse issue_wire named-block helpers for the triage body section instead of parallel marker grammar. Scenario: The plan adds bespoke helper-owned triage block validation and replacement in triage.py while issue_wire already owns compose_named_block, strip_named_block, parse_named_block, and malformed detection for plan and design-pause markers. A second parser will drift and complicate idempotent replace/preserve-original-body behavior.
- **Proposed resolution**: Add triage to the shared named-block surface (for example extend _ALLOWED_MARKERS with triage) and delegate valid-body edits to issue_wire helpers; keep triage.py focused on verdict orchestration and postconditions.

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Reuse issue_wire named-block helpers for the triage section. Scenario: The plan adds separate helper-owned triage marker parsing and body splice logic in triage.py while issue_wire already owns compose_named_block and parse_named_block for plan and design-pause. Parallel marker logic adds drift risk without new capability.
- **Proposed resolution**: Extend issue_wire _ALLOWED_MARKERS with triage, reuse compose_named_block and parse_named_block for insert/replace/idempotency, and keep triage.py focused on verdict orchestration and sanitation.

### FINDING_13:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: plan.txt:42-48
- **Concern**: [SCOPE-REDUCTION] 3. Dependency writes are not limited to the valid verdict path. Scenario: Already-fixed, invalid, and duplicate verdicts close the issue, but the next step can still add blocked-by edges to that closed issue.
- **Proposed resolution**: Apply dependency edges only for a verified valid verdict while the issue remains open.

### FINDING_15:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/triage.py
- **Concern**: [SCOPE-REDUCTION] Plan specifies bespoke helper-owned triage block syntax instead of reusing issue_wire named-block parse, compose, and strip with marker triage. Scenario: A second malformed-block grammar can disagree with issue_wire on plan and design-pause markers and accept or reject protected bodies differently than the rest of larch
- **Proposed resolution**: Implement triage section splice via issue_wire.parse_named_block, compose_named_block, and strip_named_block with marker triage; keep compare-and-swap mutation only in triage apply ### 1. completeness — `skills/triage/SKILL.md` / `python/larch/cli.py` The binding scope anchor requires collecting cited `larch-logs/` from unmerged PR branches using `git fetch` plus `git show`. The plan mentions a deterministic ref helper in skill prose, but `### UPDATED: python/larch/cli.py` registers only `triage apply` and `triage probe`, and the planned `python/tests/issue/test_triage.py` coverage list has no fetch/show cases. That leaves the primary evidence path unspecified in the firm Python surface and untested. **Suggested revision:** Add and register a `triage read-ref` (or equivalent) helper, invoke it from the skill for validated SHAs or `refs/pull/<n>/head`, and pin behavior in unit and structural tests. ### 2. architecture — `python/larch/issue/triage.py` [SCOPE-REDUCTION] The plan tasks `triage.py` with validating “helper-owned triage block syntax” independently. `issue_wire.py` already owns named-block grammar (`<!-- larch:{marker}:start/end -->`) and malformed tokens for `plan` and `design-pause`. Duplicating that logic adds diff and drift risk against protected-state checks. **Suggested revision:** Reuse `issue_wire` parse/compose/strip with marker `triage` for section handling; keep `updatedAt` compare-and-swap and authorization in `triage apply` only.
