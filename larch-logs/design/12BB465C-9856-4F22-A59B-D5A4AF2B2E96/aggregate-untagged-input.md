### FINDING_2:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/research_eval.py:48-59
- **Concern**: Tier-2 no-issues salvage lacks the schema_version pollution guard that the plan adds to the Cursor normalizer. Scenario: Codex output (no Cursor postprocess) with narration, a non-record JSON line containing schema_version, and one trailing {"no_issues_found": true} line yields zero normalized records and len(sentinel_indexes)==1, so validate_structured_reviewer_output salvages a clean pass and drops the partial finding attempt; the plan's Cursor path blocks this via _review_cursor_has_structured_findings but the shared validator does not
- **Proposed resolution**: In validate_structured_reviewer_output, before tier-2 salvage, reject when any non-blank line parses as a JSON object with a schema_version key (mirror the Cursor guard in python/agents.py); add a test in python/test_research_eval.py for prose + invalid schema_version JSON line + lone sentinel returning exit 5 or preserving failure semantics

### FINDING_3:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/research_eval.py:44-58,138-150
- **Concern**: Joined-body no-issues salvage bypasses the singleton-sentinel rule. Scenario: _json_no_issues uses raw_decode and ignores trailing content, so the proposed tier-1 check accepts two sentinel lines before the planned len(sentinel_indexes) == 1 check runs
- **Proposed resolution**: Use a strict whole-body JSON helper for structured joined-body salvage, or count standalone sentinels before accepting tier 1
