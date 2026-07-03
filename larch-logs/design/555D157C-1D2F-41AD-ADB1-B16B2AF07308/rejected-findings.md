### [Plan Review] FINDING_2

### FINDING_2: Keep the scout-sidecar substring
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The plan does not pin the `optional best-effort` phrase that tests expect in both generated implementer prompts. Compressing the intro prose can remove it and break `test_generated_implementers_include_scout_sidecar` after a successful regeneration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add optional best-effort to the immutable prose list (or cite test_generated_implementers_include_scout_sidecar in Testing strategy / Failure modes)
  - From Cursor-Innovation: When tightening intro bullets in `_implementer_text()`, keep the substring `optional best-effort` (or explicitly add updating that test to the plan if the wording is intentionally changed)


