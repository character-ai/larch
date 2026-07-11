### [Plan Review] FINDING_1

### FINDING_1: RESUME_HINT is not bound to `none` for `operator-action`
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The proposed postmerge guard returns `operator-action` / `none`, but `classify()` unconditionally recomputes the resume hint afterward. Because `operator-action` is not in the early non-resumable set and `postmerge-flush` sanitizes to `unknown`, the postmerge path can still fall through to `step8-shippr`, preserving the spurious reship behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In the expected-postmerge branch set hint="none" directly and skip _resume_hint_for(), or add operator-action to the early none return set in _resume_hint_for(). Document the chosen approach in the _classify.py plan section.
  - From Cursor-Requirements: In _classify.py, add operator-action to the _resume_hint_for() early none set and/or bind hint=none when MATCHED_CLASSIFIER_PATTERN=postmerge-flush-expected instead of discarding the guard hint; add a regression asserting RESUME_HINT=none for the positive fixture.


