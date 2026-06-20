### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:350-372; python/test_review_pipeline.py:694-716
- **Concern**: Plan-mode reviewer tokenization would split valid spaced labels. Scenario: Using re.split(r"[\s,]+", cell) fixes Cursor-Pragmatic Codex-Arch but regresses existing dynamic labels such as Cursor-dyn-Api Contract, so prune counts stop accruing for that reviewer.
- **Proposed resolution**: Tokenize by matching the known label set with comma/whitespace boundaries, prefer longest labels, and keep the existing spaced-label test while adding the whitespace-separated two-label case.




### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: python/design_log_publish_flow.py:150-177; python/redact.py:357-376; python/run_logs.py:1739-1785
- **Concern**: The secret count plan does not require the design copy writer and counter to use the same scrubbed text. Scenario: For an extra scrub-log family not removed by redact secrets, such as a Slack token, design log-publish writes directly under the worktree log root; _copy_tree_to_repo does not copy or scrub source==dest, so a count-only pre-pass can still commit the token or double-count it if another scrub later runs.
- **Proposed resolution**: After tmpdir path redaction, run the counted scrubber on the exact text that will be written, write that scrubbed text with the existing newline behavior, and pass only that pre-scrub count to run-log commit for those files.




### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:908-911
- **Concern**: Item 3 no-defect rationale cites `_tracked_paths_vs_ref("")` fallback but `_collect_round_stage_paths` returns `[]` when `diff_base` is empty before any fallback runs. Scenario: An implementer re-check may treat missing `diff_base` as a live drop bug and add production changes that fight pinned tests like `test_collect_round_stage_paths_without_snapshot_returns_empty`
- **Proposed resolution**: Close Item 3 with the intentional empty-return contract and existing tests; do not cite the `_tracked_paths_vs_ref` fallback as proof




### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:350-366
- **Concern**: Plan's comma-or-whitespace tokenization would split valid plan reviewer labels that contain spaces. Scenario: Existing plan-mode labels can contain spaces via the label map, for example python/test_review_pipeline.py:684-695 expects "Cursor-dyn-Api Contract" to count as one reviewer. Blind re.split(r"[\s,]+", cell) turns it into two tokens and regresses that path.
- **Proposed resolution**: Parse against known label keys first. Preserve the full comma segment as a token, and only apply whitespace splitting when it cannot break a known spaced label.




### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: blocking
- **Focus area**: security
- **Location**: python/design_log_publish_flow.py:150-174; python/redact.py:33-49
- **Concern**: Design pre-redaction plan can count scrub-log-only secret families without redacting the bytes it commits. Scenario: The plan says to preserve current redact secrets output while using redact.scrub_log_secrets for counts. scrub_log_secrets covers extra families such as Slack, Google API, Stripe, and GitLab at python/redact.py:39-49, but the current design copy writes the narrower redact secrets output. A token from an extra family could produce a nonzero count while still landing in the design log PR.
- **Proposed resolution**: Use one scrub pass for both content and count after tmpdir path redaction. Write the scrubbed text returned by redact.scrub_log_secrets, or restrict the count to exactly the families the written content redacts.




### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:364-366
- **Concern**: Item 8 proposes plan-mode `finding_reviewers` tokenization via `re.split(r"[\s,]+", cell)`. Scenario: Spaced dynamic labels are production data: `_slot_human_label` emits values like `Cursor-dyn-Api Contract`, and `test_reviewer_prune_record_plan_mode_preserves_spaced_dynamic_label` expects that cell to credit one combo. Whitespace/comma splitting turns it into `Cursor-dyn-Api` and `Contract`, so accepted/rejected/total stay 0 and rounds 3-4 can falsely prune a productive combo.
- **Proposed resolution**: Tokenize against the known `label_list` passed into `_read_classification_counts` (exact match first; comma segments; otherwise greedy longest-prefix match against known labels). Do not use blind `[\s,]+` splitting. Keep `test_reviewer_prune_record_plan_mode_preserves_spaced_dynamic_label` green and add the whitespace-separated two-reviewer case from `test-findings-classification.sh`.




### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_pipeline.py:363-366
- **Concern**: Plan's comma-or-whitespace split would regress existing plan reviewer labels that contain spaces. Scenario: The existing plan-mode label-map test uses Cursor-dyn-Api Contract as one reviewer label; re.split(r"[\s,]+", cell) would split it into Cursor-dyn-Api and Contract, so prune counts no longer accrue to that reviewer
- **Proposed resolution**: Support whitespace-separated reviewer cells without splitting known multi-word labels, for example exact known-label matching or comma splitting first with a whitespace fallback only for slug-like tokens, and keep the existing spaced-label coverage passing




### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:9-10
- **Concern**: Item 3 no-defect rationale cites `_tracked_paths_vs_ref("")` fallback, but `_collect_round_stage_paths` returns `[]` when `diff_base` is empty before any path collection. Scenario: An implementer may skip the issue-required trace/confirm step and treat Item 3 as already proven by the wrong mechanism
- **Proposed resolution**: Pin Item 3 closure to `review_and_fix.py:908-911` plus existing tests `test_collect_round_stage_paths_with_empty_baseline_returns_empty` / `test_collect_round_stage_paths_without_snapshot_returns_empty`, or require an explicit implement-time re-check before closing




### FINDING_11:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/review_and_fix.py:908-910
- **Concern**: Item 3 closes the missing-diff_base concern on a helper fallback that this branch never reaches. Scenario: When _round_diff_base returns empty, _collect_round_stage_paths returns [] before _tracked_paths_vs_ref("") can include current tracked paths, so the plan can falsely close a path-drop defect or leave the no-defect rationale unverifiable
- **Proposed resolution**: Revise Item 3 to trace the actual early-return branch; either document the missing-base snapshot contract with existing or targeted coverage, or remove the early return and collect the required paths




