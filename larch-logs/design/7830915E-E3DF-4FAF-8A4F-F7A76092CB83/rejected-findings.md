### [Plan Review] FINDING_6

### FINDING_6: Reusing oos_filer filed-evidence helper would violate plan's strict grammar
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `oos_filer._ndjson_filed_evidence` falls back to `_GITHUB_URL_RE.findall(body)` for any GitHub issue URL in ndjson body. The plan requires explicit `Filed URL` / `Filed as` / `Filed OOS issue` forms only. Reusing that helper verbatim would treat incidental issue links in disposition prose as filed OOS and inflate fate-adjusted reviewer points.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In _parse_oos_issues_ndjson / join path, implement the plan's explicit filed-evidence grammar only; do not call or mirror _ndjson_filed_evidence's body-wide URL fallback


### [Plan Review] FINDING_7

### FINDING_7: Fate policy omits GitHub stateReason DUPLICATE
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: An OOS issue closed as a duplicate (common when `/issue` dedupes or an operator marks duplicate) has no PR link and is not `NOT_PLANNED`. Under the plan it keeps provisional +1 as `closed_unknown` or open, so worthless filed OOS still counts toward adjusted reviewer totals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Treat stateReason DUPLICATE like combined-away (dock to 0), or map it to the combined-away bucket when closedByPullRequestsReferences is empty


### [Plan Review] FINDING_8

### FINDING_8: OOS reviewer prompts still promise unconditional +1
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Concern**: The plan updates scoring docs and the analyze report, but runtime competition notices in reviewer prompts/templates still tell reviewers that panel-accepted OOS earns +1 unconditionally. Reviewers keep seeing the old incentive, so the feature does not fully stop the permanent-point incentive it targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Generic: Update the planned prompt/template changes to say accepted OOS earns a provisional +1 subject to fate-adjusted /analyze-issues docking, and regenerate shipped agent prompt outputs if required.


### [Plan Review] FINDING_9

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:168 and python/oos_filer.py:274-276
- **Concern**: [SCOPE-REDUCTION] _bare_oos_item_suffix is listed as a new helper in both analyze_issues.py and oos_filer.py. Scenario: oos_filer already has _bare_oos_suffix (OOS-only); the plan adds a widened suffix helper in two inventories without requiring a single import path, inviting divergent regex behavior between filing joins and analyze joins
- **Proposed resolution**: Define the widened matcher once in oos_filer.py (extend or replace _bare_oos_suffix), import it from analyze_issues.py, and drop the duplicate entry from the analyze_issues helper list


