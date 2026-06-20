### FINDING_1: Tier-2 salvage missing schema_version pollution guard
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The planned tier-2 no-issues salvage path does not include the `schema_version` pollution guard that the plan adds to the Cursor normalizer. In a Codex path (no Cursor postprocess), output with narration, a non-record JSON line containing `schema_version`, and one trailing `{"no_issues_found": true}` line can yield zero normalized records and `len(sentinel_indexes)==1`, so `validate_structured_reviewer_output` salvages a clean pass and drops a partial finding attempt. The plan's Cursor path blocks this via `_review_cursor_has_structured_findings`, but the shared validator does not.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: In validate_structured_reviewer_output, before tier-2 salvage, reject when any non-blank line parses as a JSON object with a schema_version key (mirror the Cursor guard in python/agents.py); add a test in python/test_research_eval.py for prose + invalid schema_version JSON line + lone sentinel returning exit 5 or preserving failure semantics


### FINDING_2: Joined-body salvage bypasses singleton-sentinel rule
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The planned joined-body no-issues salvage can bypass the singleton-sentinel rule. `_json_no_issues` uses `raw_decode` and ignores trailing content, so the proposed tier-1 check can accept two sentinel lines before the planned `len(sentinel_indexes) == 1` check runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Use a strict whole-body JSON helper for structured joined-body salvage, or count standalone sentinels before accepting tier 1


