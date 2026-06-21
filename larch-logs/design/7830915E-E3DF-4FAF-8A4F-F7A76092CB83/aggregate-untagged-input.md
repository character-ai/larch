### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:675-783
- **Concern**: run_main cannot pass targeted issue details into fate scoring via argv-only main(analyze_args). Scenario: run_main is supposed to fetch per-issue gh view data then render fate-adjusted OOS scoring, but today it only forwards analyze flags into main(); filed_issue_details is an in-memory dict and cannot cross that boundary, so the live /analyze-issues run path can render the new section without enriched comments or may skip wiring entirely
- **Proposed resolution**: Extract a shared render helper (e.g. build_report/load_issues + fate_adjusted_oos_scoring + section assembly) called by both main() and run_main; have run_main load the dump, scan logs, fetch filed_issue_details, then call the helper with that dict; keep offline analyze --json on the helper with filed_issue_details={} and no network

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan: cap-rollup expansion fallback
- **Concern**: Same-source cap-rollup fallback may pick the first N unfiled blocks when more than N exist. Scenario: Production cap-rollups often leave many same-source oos-accepted blocks (for example 8 blocks for a rollup of 3); the plan's source-key fallback orders unfiled blocks and takes up to N without an exactly-N guard, so the wrong members get fate-adjusted credit/docks
- **Proposed resolution**: Require unambiguous membership before expansion: use explicit stable-id citations or rollup excerpt mapping first; for same-source fallback only expand when the unfiled candidate count equals N, otherwise emit ambiguous_rollup_expansion; add a fixture with N=3 and 8 candidates that must not expand

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan: cap-rollup expansion / stable-id join
- **Concern**: Cap-rollup expansion does not bridge oos-accepted-main-agent stable ids to oos-accepted-review markdown. Scenario: Committed ndjson often uses oos-accepted-main-agent:OOS_1 while member blocks live under round-*/oos-accepted-review.md; strict source_key matching from the aggregate stable id skips those blocks, so rollup docking under-attributes or misses member rows
- **Proposed resolution**: Reuse oos_filer._issue_covers_stable_id (or the planned widened _stable_ids_cover) when resolving rollup members, not only stem equality; add a regression fixture with main-agent aggregate stable id and review-path markdown blocks

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/analyze_issues.py:675-783
- **Concern**: run_main targeted fetch has no contract to pass filed_issue_details into report assembly. Scenario: run_main may fetch per-issue view data that main() never receives, so combined-away docking stays unknown on live runs despite extra gh calls
- **Proposed resolution**: Extract one shared report builder used by main() and run_main(), or pass filed_issue_details via an explicit argv sidecar (for example --filed-issue-details-file) that main() reads before fate_adjusted_oos_scoring

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:688-702
- **Concern**: Plan omits wiring fate section into main() stdout join. Scenario: main() can keep printing only the seven legacy sections; fate-adjusted totals never show in analyze --json or run_main output
- **Proposed resolution**: Explicitly append fate_adjusted_oos_scoring output after reviewer_effectiveness in main()'s join list, with try/except degrade per plan failure-mode note

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:125-128
- **Concern**: Cap-rollup fallback selects first N same-source unfiled blocks when candidate count exceeds N. Scenario: Real implement logs can have many unfiled OOS blocks in one round while ndjson cites one aggregate rollup of 3; heuristic expansion can credit/dock the wrong reviewers
- **Proposed resolution**: When inferred same-source unfiled candidates exceed parsed rollup N, emit ambiguous_rollup_expansion instead of taking the first N by artifact_relpath/heading order

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/analyze_issues.py:168-174
- **Concern**: python/oos_filer.py:272-276. Scenario: [SCOPE-REDUCTION] _bare_oos_item_suffix is specified in both analyze_issues.py and oos_filer.py
- **Proposed resolution**: Two copies of suffix matching can drift on FINDING_N vs OOS_N handling Implement _bare_oos_item_suffix once in oos_filer.py and import it from analyze_issues.py; keep analyze-local cover logic only where source-key rules differ

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:754-783
- **Concern**: run_main has no contract to pass targeted filed-OOS gh view results into main(). Scenario: run_main is supposed to dedupe filed issue numbers, call _fetch_filed_oos_issue_details, then render fate-adjusted scoring; today it only chains fetch_main and main(["--json", dump, ...]). filed_issue_details never reaches fate_adjusted_oos_scoring, so live runs either skip enrichment or require duplicate fetch logic outside main()
- **Proposed resolution**: Add an explicit handoff: e.g. run_main writes a sidecar JSON map and forwards --filed-issue-details-json PATH (and --log-root) through analyze_args; main() loads issues from --json, loads the sidecar when present, and passes filed_issue_details into fate_adjusted_oos_scoring before printing the new section

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/analyze_issues.py:713-733
- **Concern**: fetch_main retry when stateReason/url are unsupported is only in Failure modes, not in the fetch_main change list. Scenario: Adding stateReason and url to the bulk gh issue list --json field list can make the entire list call fail on older gh builds; run_main aborts before any report, not just fate degradation
- **Proposed resolution**: Mandate in the fetch_main update: try the expanded --json field list once; on non-zero exit retry with the current field set (number,title,state,createdAt,closedAt,body,labels,closedByPullRequestsReferences) and record degraded stateReason/url availability for classify_oos_issue_fate

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/oos_filer.py:267-289 vs python/analyze_issues.py:221-226
- **Concern**: Plan strict filed-OOS evidence parsing can be undermined by copying oos_filer._ndjson_filed_evidence. Scenario: oos_filer._ndjson_filed_evidence falls back to _GITHUB_URL_RE.findall(body) for any GitHub issue URL in ndjson body; the plan requires explicit Filed URL / Filed as / Filed OOS issue forms only. Reusing the oos_filer helper verbatim would treat incidental issue links in disposition prose as filed OOS and inflate fate-adjusted reviewer points
- **Proposed resolution**: In _parse_oos_issues_ndjson / join path, implement the plan's explicit filed-evidence grammar only; do not call or mirror _ndjson_filed_evidence's body-wide URL fallback

### FINDING_12:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/analyze_issues.py:classify_oos_issue_fate
- **Concern**: Fate policy omits GitHub stateReason DUPLICATE. Scenario: An OOS issue closed as a duplicate (common when /issue dedupes or an operator marks duplicate) has no PR link and is not NOT_PLANNED; plan keeps provisional +1 as closed_unknown or open, so worthless filed OOS still counts toward adjusted reviewer totals
- **Proposed resolution**: Treat stateReason DUPLICATE like combined-away (dock to 0), or map it to the combined-away bucket when closedByPullRequestsReferences is empty

### FINDING_13:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/rendering.py:838-840; skills/design/references/plan-review.md:30-32; skills/shared/reviewer-templates.md:162-166
- **Concern**: OOS reviewer prompts still promise unconditional +1. Scenario: The plan updates scoring docs and the analyze report, but runtime competition notices still tell reviewers that panel-accepted OOS earns +1. Reviewers keep seeing the old incentive, so the feature does not fully stop the permanent-point incentive it targets.
- **Proposed resolution**: Update the planned prompt/template changes to say accepted OOS earns a provisional +1 subject to fate-adjusted /analyze-issues docking, and regenerate shipped agent prompt outputs if required.
