### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design plan Approach step 2
- **Concern**: Approach step 2 bundles `generate pre-rendered-reviewer-prompts` with template regeneration before hand-maintained agent sync. Scenario: `generate_pre_rendered_reviewer_prompts_main` copies every `agents/reviewer-*.md` body; running it after only template/generated updates leaves five hand-maintained specialists and their `agents/pre-rendered/*-body.txt` files on `highest-materiality`, so Item 1 ships incomplete
- **Proposed resolution**: In Approach and Testing strategy, require this order: edit `reviewer-templates.md`, regenerate the four template-owned agents, manually sync the five hand-maintained `agents/reviewer-*.md` files, then run `python3 python/cli.py generate pre-rendered-reviewer-prompts` and `generate check`



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:977-1001
- **Concern**: Cap-1 rollup path is not specified to replace the existing per-slot stdout-index loop. Scenario: `file_oos_annotate_main` always rebuilds `map_lines` at line 981 and only maps slot 1 when stdout has `ISSUE_1_URL`; a cap-1 pre-pass that stamps `accepted` but still falls through would rewrite `oos-issues-created.md` with a single `OOS_FILE_MAP` row, breaking sentinel idempotency and reopening re-file on prepare rerun
- **Proposed resolution**: Branch before `map_lines: list[str] = []`: on cap-1 rollup, stamp every non-failed order id, append one `OOS_FILE_MAP` row per original, write sentinel, and skip the per-slot loop; keep the current loop for all other cases



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/report/review_phase_detail.py:106-130
- **Concern**: Plan calls for a new classification TSV reader instead of reusing the existing voting parser. Scenario: `rejected_analysis._join_run_findings` already reads `round-*/findings-classification.tsv` through `voting.classification_tsv_schema_supported` and `classification_row_panel_inputs`; a bespoke parser can mis-handle code-review header variants and skip footer fallback when the TSV is malformed
- **Proposed resolution**: In `review_phase_detail.py`, load the sibling `findings-classification.tsv` once per round, build a `finding_id -> voting_result` map via the existing `voting` helpers when schema-supported, and fall back to `_vote_result` only when the TSV is absent or unusable



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:760-838
- **Concern**: Cap-1 rollup priority mapping can collapse duplicate issue URLs onto the last slot.. Scenario: If the label-only retry path has to rebuild priority labels from `oos-issues-created.md` instead of `oos-issue.stdout.txt`, a rollup that mixes high-risk and non-high-risk originals can lose the shared issue's `oos-correctness` label because the later slot overwrites the earlier one.
- **Proposed resolution**: Aggregate priority per URL with OR semantics across all matching originals, or persist the rolled-up priority alongside the sentinel rows, and add a cap-1 label-only retry regression test.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/report/review_phase_detail.py:106-130
- **Concern**: TSV-first rejected-OOS audit omits classification schema gate before trusting rows. Scenario: A round-*/findings-classification.tsv with a missing or drifted header can be parsed as usable and misclassify accepted OOS blocks as audit candidates or drop rows, instead of falling back to the legacy footer parser the plan promises
- **Proposed resolution**: Gate each per-round TSV with voting.classification_tsv_schema_supported(text, panel_kind="code-review") (same contract as rejected_analysis._join_run_findings); when unsupported or unreadable, treat the file as absent and use footer parsing per block



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:927-997
- **Concern**: Cap-1 rollup annotate does not bind the existing post-cap block and stdout slot helpers the file already owns. Scenario: Implementing "one parseable OOS block" via raw heading counts or ISSUE_n line counts can mis-detect rollup vs ambiguous stdout (e.g., one combined block but two URL slots) and either skip the fix or stamp wrong originals
- **Proposed resolution**: In file_oos_annotate_main, branch on len(_parse_post_cap_combined_blocks(combined))==1, len(_parse_order(order_file))>1, and exactly one non-failed URL from _parse_issue_stdout_slots(stdout); add a regression where two stdout URL slots with one combined block leaves conservative per-index behavior



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: python/tests/report/test_review_phase_detail.py:166-260
- **Concern**: TSV-first audit tests omit neutral voting_result coverage. Scenario: Plan requires neutral outcomes to remain audit candidates via TSV, but listed tests only cover rejected and accepted; a TSV-only lookup can regress neutral rows when footers are absent or malformed
- **Proposed resolution**: Add a fixture where findings-classification.tsv has voting_result=neutral for OOS_N with no usable Vote tally footer and assert the candidate still appears in render_rejected_oos_audit_section output



### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:56-86
- **Concern**: `generate pre-rendered-reviewer-prompts` also rewrites `agents/pre-rendered/.manifest`, but the file list only names the body txt files.. Scenario: A PR that updates the bodies without the manifest will leave checked-in pre-rendered prompts incomplete and make `python3 python/cli.py generate check` fail.
- **Proposed resolution**: Add `agents/pre-rendered/.manifest` to the UPDATED list and regenerate it with the pre-rendered bodies.



### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:141-146
- **Concern**: The TSV-first audit tests never cover a `voting_result=neutral` row.. Scenario: An implementation that only honors `rejected` TSV outcomes would still pass the planned tests, but the new audit path would silently drop neutral OOS candidates.
- **Proposed resolution**: Add a TSV-first neutral-row case, ideally with a missing or malformed footer, and assert the candidate still renders.



