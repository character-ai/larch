### FINDING_2: Harness `contains` checks do not verify refusal-template first line
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan asks for `contains` assertions on the `**❌ /implement preflight: admission blocked` refusal template in the `admission-blockers`, `admission-missing-designed`, `admission-report`, and `admission-error` cases. A `contains` check can pass if stdout gains any line before the refusal template but still includes the expected template later, so the new acceptance criterion for exact refusal-template behavior remains weakly verifiable. The `managed-prefix` case already asserts the refusal first line; the four untested branches do not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Use a minimal first-line comparison for the four new cases, for example compare sed -n 1p of stdout to the expected template, and keep the existing context contains checks unchanged


### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:20-25
- **Concern**: [SCOPE-REDUCTION] relevant-checks path list qualifies scripts/test-implement-preflight.md with "if the harness contract doc is edited in this change" under Match these paths. Scenario: The implementer may omit scripts/test-implement-preflight.md from the case pattern while still editing scripts/test-implement-preflight.sh; doc-only harness contract edits would then skip the offline harness
- **Proposed resolution**: Always include scripts/test-implement-preflight.md in the case block alongside the other three paths, mirroring scripts/implement-finalize.sh routing; keep optional wording only for whether to edit Coverage prose in scripts/test-implement-preflight.md


### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/relevant-checks.sh:305-307
- **Concern**: [SCOPE-REDUCTION] Route for scripts/test-implement-preflight.md is conditional on editing the doc in this PR. Scenario: The feature is to wire future implement-preflight surface edits. If the prose file is not edited now and the route is omitted, future harness contract doc edits still miss test-implement-preflight.
- **Proposed resolution**: Make scripts/test-implement-preflight.md unconditional in the relevant-checks case pattern. Keep the prose file edit itself optional.




### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:31-43
- **Concern**: [SCOPE-REDUCTION] SECURITY.md edit exceeds approved outline and conflicts with keep-the-rest-intact. Scenario: Outline goal is only merge compatibility; plan adds an admission-suppression bullet and says keep the rest of SECURITY.md:245 intact, leaving exactly three Preflight gates and The bypass does not suppress the admission gate while SKILL.md documents four emergency bypasses including missing-designed-prefix admission carve-out
- **Proposed resolution**: Limit SECURITY.md to replacing the mutually exclusive with --merge clause per outline; drop the new admission-suppression bullet unless the same edit also updates the downgrade list to four gates (add missing-designed-prefix admission check) and removes the stale does-not-suppress-the-admission-gate sentence




### FINDING_1: SECURITY.md preserves false emergency/merge exclusivity consequence
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: A minimal word swap on the mutual-exclusion phrase in `SECURITY.md:245` can leave the downstream consequence clause intact ("so a downgraded run cannot flow into automated merge paths"), so the security policy still claims emergency runs cannot reach automated merge even though `skills/implement/SKILL.md` documents `--emergency` and `--merge` as compatible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Delete the entire stale clause, including so a downgraded run cannot flow into automated merge paths, when stating compatibility. Replace it with one sentence that emergency and merge may be combined and that downgrade warnings and trust-boundary caveats still apply. Drop or narrow Keep the rest of the paragraph intact so it does not preserve the obsolete consequence.



