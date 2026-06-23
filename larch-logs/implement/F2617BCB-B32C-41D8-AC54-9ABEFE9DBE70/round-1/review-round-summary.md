# Review Round 1

- Mode: `diff`
- 2 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: _fit_to_github_limit measures characters, not UTF-8 bytes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_fit_to_github_limit` in `python/oos_filer.py` (lines 564–568) uses Python `len()` and a local `_GITHUB_BODY_LIMIT = 65535` instead of UTF-8 byte sizing against `config.GITHUB_ISSUE_BODY_MAX_BYTES` (65536). A body with many multibyte characters can pass the character check yet exceed GitHub’s byte limit when encoded, causing `gh issue create` to fail with no truncation. The hardcoded 65535 also drifts from the shared config constant used elsewhere (e.g. `report_tokens_issue.py`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Truncation silently drops oversized OOS source bodies
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_fit_to_github_limit` (lines 564–580) truncates oversized accepted-OOS bodies instead of preserving every source observation under GitHub limits. Tail content is lost while downstream logic (e.g. lines 640–690) may still record all source stable IDs as filed, so retries skip the lost content. Current tests pin truncation as success rather than full preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


