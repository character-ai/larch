### FINDING_1: Degraded-response heuristic reads or publishes the extracted file in the wrong order
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: The planned degraded-response check is coupled ambiguously to the existing `jq` success path: `$EXTRACT_TMP` may already have been moved to `$OUTPUT`, or a degraded branch may conflict with the later `mv`. This can make the heuristic never fire, fire incorrectly, or break the extraction flow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After successful jq mv, use RESULT_BYTES=$(wc -c < "$OUTPUT") (or run the check before mv); drop the erroneous rm -f "$EXTRACT_TMP" on the post-mv path
  - From Codex-Arch: Restructure the successful jq extraction branch so bytes are measured before publishing, then either write CURSOR_DEGRADED_RESPONSE and skip mv, or mv the extracted result in an explicit else branch
  - From Cursor-Innovation, Cursor-Pragmatic: Insert the block inside the `jq … > "$EXTRACT_TMP" && [[ -s "$EXTRACT_TMP" ]]` branch **before** `mv`, or measure `"$OUTPUT"` only after `mv` (not both)
  - From Codex-Innovation: Compute RESULT_BYTES before mv, or compute it from $OUTPUT after mv; pin the B3 test to the exact success-path placement
  - From Cursor-Requirements: Run the byte-count/threshold check on $OUTPUT (or on $EXTRACT_TMP before mv): only promote to $OUTPUT when not degraded; document this ordering explicitly in the plan snippet
  - From Codex-Requirements: Revise the plan to replace the jq extraction branch with an explicit if degraded write sentinel else mv EXTRACT_TMP to OUTPUT structure, and keep the B3 positive and negative assertions tied to that branch


### FINDING_2: Retry-success outputs can still promote sentinel literals to OK
- **Reviewer(s)**: Codex-Arch, Codex-Edge
- **Severity**: important
- **Concern**: Always-on sentinel detection is planned only around the initial OK result path, so retry outputs containing `CURSOR_EMPTY_RESPONSE` or `CURSOR_DEGRADED_RESPONSE` can still be marked `STATUS=OK`, especially for callers that do not enable validation mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add a post-retry normalization pass over every STATUS=OK result, or factor a helper and call it both before the initial RESULTS append and before assigning retry STATUS=OK; add a retry-output fixture to Case 5b
  - From Codex-Edge: Revise the plan to factor sentinel-literal classification into a helper and call it before every STATUS=OK assignment, including the empty-output retry success path at lines 1138-1140; add a retry fixture without --validation-mode to the collector tests


### FINDING_3: Degraded-response heuristic can overwrite valid terse reviewer results
- **Reviewer(s)**: Codex-Arch, Cursor-Edge, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The byte-count versus token heuristic runs in the launcher before downstream validation can accept legitimate short outputs, so valid sentinels or compact structured results can be rewritten to `CURSOR_DEGRADED_RESPONSE`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Whitelist recognized no-findings sentinels in the launcher before applying the degraded heuristic, or narrow the heuristic to known narration-only shapes; add a high-outputTokens no-issues control test
  - From Cursor-Edge: Before writing CURSOR_DEGRADED_RESPONSE, skip when trimmed EXTRACT_TMP matches json_no_issues_found (reuse validate-research-output.sh logic), NO_ISSUES_FOUND, or a schema_version TSV header prefix; add a B3 negative control with high outputTokens plus the JSON sentinel
  - From Codex-Pragmatic: Before emitting CURSOR_DEGRADED_RESPONSE, exempt recognized valid short outputs such as JSON no-issues, NO_ISSUES_FOUND, and first-line TSV/header forms, or make the heuristic conditional on failing a caller-provided result contract
  - From Codex-Requirements: Revise the heuristic acceptance criterion to exempt recognized valid sentinel/structured starts before applying the byte/token rule, and add a high-outputTokens short-sentinel control test


### FINDING_4: Anchored require-result pattern still scans the whole file
- **Reviewer(s)**: Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The planned `--require-result-pattern` check uses `grep -Eq`, so anchors apply per line rather than to the first meaningful content. Reviewer output with prose first and a valid TSV or JSON sentinel later can still pass the gate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Revise the plan to change dispatch-with-waterfall.sh's --require-result-pattern check to validate only the first non-blank line, or add a stricter helper there; then pass the plan-review pattern to that helper
  - From Codex-Innovation: Change dispatch-with-waterfall to match only the first nonblank line, or add a --require-first-line-pattern gate; add a regression where leading prose plus a valid TSV header must fail the gate
  - From Codex-Pragmatic: Check only the first nonblank line or prefix before accepting the pattern, and add a regression where narration precedes an otherwise valid TSV header
  - From Codex-Requirements: Revise dispatch-with-waterfall.sh to check the first nonblank line or first non-whitespace content explicitly, then add a regression where preamble plus TSV header falls back


### FINDING_5: Degraded-response contract docs are incomplete
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: nit
- **Concern**: The plan changes launcher and validator behavior around `CURSOR_DEGRADED_RESPONSE`, but sibling script and operator-facing docs may still document only the older `CURSOR_EMPTY_RESPONSE` behavior or old Cursor mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Update the validator contract docs and external reviewer validation docs alongside the script header and tests
  - From Codex-Pragmatic: Update the sibling contract docs alongside the script/test changes so the shipped plugin docs match the new --mode ask and degraded-response behavior


### FINDING_6: Dispatch-plan-review test does not assert require-result-pattern forwarding
- **Reviewer(s)**: Codex-Requirements
- **Severity**: latent
- **Concern**: The plan adds `--require-result-pattern` to the plan-review dispatcher, but the existing harness may not prove that the flag and exact pattern are passed through to `dispatch-with-waterfall.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Extend test-dispatch-plan-review-panel.sh so the stub captures --require-result-pattern and asserts the exact plan-review pattern is present


### FINDING_7: Collector sentinel pseudocode uses variables unavailable at the proposed insertion point
- **Reviewer(s)**: Cursor-dyn-collector-sentinel-vars, Codex-dyn-collector-sentinel-vars
- **Severity**: important
- **Concern**: The collector plan snippet appears intended for the first-pass result loop but references variables and indexes from later result-iteration code. Under `set -u`, this can abort the collector, target the wrong file, skip appending the current reviewer, or overwrite the wrong result entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-collector-sentinel-vars: Insert a new always-on pass after §3 retry (before §3.5 at ~1160) that parses each RESULTS[j] entry into REVIEWER_FILE/ENTRY_TOOL like §3.5, or rewrite the snippet to use $OUTPUT/$TOOL inside the i-loop
  - From Codex-dyn-collector-sentinel-vars: Rewrite the insertion to use $OUTPUT and $TOOL in the first-pass loop, or move the logic into a later RESULTS iteration where REVIEWER_FILE and ENTRY_TOOL are actually extracted from each entry.
  - From Codex-dyn-collector-sentinel-vars: Do not use RESULTS[j]= or continue in the first-pass insertion. Set STATUS=CURSOR_EMPTY_RESPONSE and FAILURE_REASON, then fall through to the existing RESULTS+= line, or append explicitly with RESULTS+=("REVIEWER_FILE=$OUTPUT|TOOL=$TOOL|STATUS=CURSOR_EMPTY_RESPONSE|EXIT_CODE=0|FAILURE_REASON=...").


### FINDING_8: Required test harness files are missing from the plan scope
- **Reviewer(s)**: Cursor-dyn-test-scope-completeness, Codex-dyn-test-scope-completeness
- **Severity**: important
- **Concern**: The acceptance criteria require collector and validator regression tests, but the corresponding harness files are missing from the files-to-modify scope. Implementers following the scoped list can miss required tests, duplicate an existing case ID, or overwrite an unrelated validation case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-test-scope-completeness: Add both test harness files to Files to modify/create, scout-plan-scope-files.txt, and explicit implementation bullets mirroring AC 8-9
  - From Codex-dyn-test-scope-completeness: Add an UPDATED subsection for scripts/test-collect-agent-bash32.sh describing Case 5b fixtures for CURSOR_EMPTY_RESPONSE and CURSOR_DEGRADED_RESPONSE without --substantive-validation --validation-mode.
  - From Codex-dyn-test-scope-completeness: Add an UPDATED subsection for scripts/test-validate-research-output.sh and use a non-conflicting case id, such as 19h, updating the top-of-file case catalog accordingly.

