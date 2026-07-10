### [Plan Review] FINDING_2

### FINDING_2: Invariant refusal should reset full validation state
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The new invariant refusal path clears only one validation field, so a missing-assessment refusal can leave stale validation metadata behind and make the refusal environment look like a normal validation run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Mirror _emit_missing_guideline_assessment_refusal's full validation reset, especially VALIDATE_LOG_FILE, when emitting the invariant refusal.`


### [Plan Review] FINDING_3

### FINDING_3: Missing-invariant warnings can be ordered incorrectly
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The new invariant warning is built through additive prefixing, which can leave the guideline warning ahead of it when both markers are present. That breaks the required invariant-first warning order.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: `Compose both warning lines in one write, or call the guideline prefix first and the invariant prefix second so the invariant warning is rendered first.`

