### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:2046-2109
- **Concern**: [SCOPE-REDUCTION] `RoundCommitResult` dataclass migration is heavier than the bug requires. Scenario: The plan adds a new return type, explicit field-access branching, and multiple test monkeypatch migrations solely to distinguish `stale-index-lock` from generic commit failure. A `tuple[str, str]` return `(sha, failure_reason)` or parsing `coder-commit.log` in `apply_findings_with_coder` preserves today's string API for success paths and avoids the dataclass-truthiness trap without touching every `_stage_and_commit_round` monkeypatch
- **Proposed resolution**: Return `(sha, failure_reason)` from `_stage_and_commit_round`; branch on `failure_reason == "stale-index-lock"` before cleanup; keep success `sha` as `str`
