### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/shared/reviewer-templates.md:237-240
- **Concern**: Canonical reviewer templates still cap OOS proposals with highest-materiality wording. Scenario: The plan rewrites rendering.py and the shared rubric but leaves four Out-of-Scope sections in reviewer-templates.md telling reviewers to keep only the highest-materiality OOS items, so static and generated reviewer prompts will still filter proposals under the old standard at proposal time
- **Proposed resolution**: Add ### UPDATED: skills/shared/reviewer-templates.md: replace highest-materiality / materiality-gate cap bullets with legitimacy selection; add reviewer-templates.md to the rewritten Update triggers list in oos-acceptance-rubric.md; regenerate auto-generated agents via existing generate targets and extend test_rendering.py or generate check as needed



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py:665-858
- **Concern**: FINDING_11 is scoped to file_oos.py but multi-issue splitting lives in oos_filer. Scenario: After issue-cap rolls accepted OOS into one item, _split_to_github_limit and the part loop still create additional public issues titled (part N/M) when the rollup body exceeds GitHub limits, breaking the exactly-one-[OOS]-issue requirement
- **Proposed resolution**: Promote oos_filer.py from MAY_UPDATE to UPDATED: on oversize rollup emit one summarized public body (full text stays in run logs) and file a single create-one call; retire or gate multi-part splitting for capped OOS batches; add/adjust tests in test_oos_filer.py (and test_file_oos.py only if issue-cap output changes)



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:976-991
- **Concern**: Design cap-1 rollup does not annotate every accepted source block with the filed URL. Scenario: Prepare writes oos-design-filing-order.txt with every pre-cap OOS header, but annotate maps stdout URLs by 1-based batch index only; when OOS_ISSUES_PER_RUN_CAP=1 collapses multiple accepted blocks into one issue, only the first ordered block gets - **Filed URL**:, so later blocks stay unfiled and a later Step 5b prepare can attempt to file them again
- **Proposed resolution**: Add an explicit design_oos.py annotate step: when cap produces one issue URL, stamp that URL on every source OOS block listed in the order file (or write OOS_FILE_MAP rows for each); cover multi-accepted cap-1 rollup in test_design_oos.py



### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py:665-833
- **Concern**: Prior FINDING_11 fix is incomplete because the body-size splitter remains only MAY_UPDATE even though this file owns post-cap issue splitting. Scenario: An oversized accepted OOS rollup can pass through issue_cap as one block, then _body_files_for_item splits it into multiple body files and _run_issue_batch files multiple [OOS] issues, violating the one-issue invariant
- **Proposed resolution**: Make oos_filer.py a firm update. Replace splitting with one under-limit summarized body that points to full run-log details, and test exactly one create-one call for oversized OOS



### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: security
- **Location**: python/larch/review/plan_review_tally.py:859-882
- **Concern**: Prior FINDING_7 fix is incomplete for design because rejected or neutral security OOS still appends to public oos.md. Scenario: When a design OOS or rerouted finding is security-tagged but not accepted, _record_plan_review_artifact_chunks appends it to oos_chunks. Committed design logs list oos.md, so security prose can leak publicly
- **Proposed resolution**: Route every security OOS outcome in plan_review_tally.py to a private sidecar and exclude it from oos.md, oos-accepted-design.md, and the aggregate pool. Add the matching design tally test



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/reviewer-templates.md:239-505
- **Concern**: Reviewer proposal prompts still say highest-materiality after the rubric rewrite. Scenario: The plan updates `rendering.oos_proposal_instruction()` but leaves four `### Out-of-Scope Observations` cap lines in `reviewer-templates.md` (and generated `agents/*.md` bodies) on highest-materiality wording. Static specialist and plan-fidelity renders that pull template bodies will keep filtering OOS at proposal time under the old gate, so legitimacy never reaches the ballot on those paths.
- **Proposed resolution**: Add `### UPDATED: skills/shared/reviewer-templates.md` to swap highest-materiality / materiality-gate cap text for highest-legitimacy / legitimacy auto-reject wording (mirror `rendering.py`), extend the rubric Update triggers list, and add a testing step to regenerate affected agents and run `python3 python/cli.py generate check`.



### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py:665-854
- **Concern**: FINDING_11 is incomplete on the `/implement` filing path. Scenario: The plan targets oversized rollup only in `file_oos.py`, but Step 9a.1 filing runs through `oos_filer._body_files_for_item` → `_split_to_github_limit`, which still emits `oos-body-*-partN` files and calls `issue create-one` once per part with `(part N/M)` titles. A single capped rollup can therefore create multiple public `[OOS]` issues, breaking the exactly-one-issue acceptance criterion.
- **Proposed resolution**: Promote `oos_filer.py` from `MAY_UPDATE` to firm `### UPDATED:`: when `OOS_ISSUES_PER_RUN_CAP=1`, replace multi-part splitting with one summarized public body (full detail stays in run logs), and add `test_oos_filer.py` coverage that an oversized post-cap combined payload yields exactly one `create-one` call / one sentinel URL.



### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:610-991
- **Concern**: Design annotate/order still desync after cap rollup (FINDING_8 gap). Scenario: `file_oos_prepare_main` writes `oos-design-filing-order.txt` from pre-cap headers, then `issue-cap` collapses multiple accepted blocks into one combined item. `file_oos_annotate_main` still maps `ISSUE_URL_1` back to individual `OOS_N` blocks via the stale order, so only the first source block gets `- **Filed URL**:`. Later blocks stay unfiled; a later prepare pass can try to file them again.
- **Proposed resolution**: Add a firm `### UPDATED: python/larch/design/design_oos.py` step: after successful `issue-cap`, rewrite `order_file` from capped combined headers (or, when cap yields one issue, stamp every accepted source block with the single rollup URL and record `OOS_FILE_MAP` rows for all originals). Extend `test_design_oos.py` for multi-accepted → one capped issue → all sources annotated / `skip-no-items` on rerun.



### FINDING_9:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: python/larch/review/plan_review_tally.py:882-886
- **Concern**: FINDING_7 fix is incomplete for design tally. Scenario: Plan only routes code-review security OOS to a private sidecar and says design keeps current behavior, but design tally appends non-accepted security-tagged OOS to oos.md; under the new oos.md audit/projection path, a rejected or neutral design security OOS can still reach public artifacts.
- **Proposed resolution**: Add an explicit plan step for plan_review_tally to keep every security-tagged OOS out of oos_chunks, oos_accepted_chunks, and oos_pool_chunks, preserving it only in a local security sidecar or private disposition path, and cover rejected/neutral design security OOS.



### FINDING_10:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/file_oos.py:752-761, python/larch/issue/oos_filer.py:665-704
- **Concern**: FINDING_11 fix is incomplete for single oversized OOS. Scenario: The plan covers oversized rollups, but issue_cap no-ops when one raw OOS item exceeds the GitHub body limit; /implement then splits that one item into multiple public issues, while /design can send the oversized single item to /larch:issue and fail instead of filing one unifying issue.
- **Proposed resolution**: Handle body-size overflow for any post-cap OOS item, including the one-item case, in the shared cap/summarization path; remove or neutralize oos_filer multi-part public splitting so it emits one summarized issue, and add implement plus design tests for one oversized accepted OOS.



### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:619-991
- **Concern**: Design Step 5b annotate still maps one issue URL only to the first pre-cap OOS slot after cap rollup. Scenario: The plan fixes implement rollup idempotency in oos_filer via _stable_ids_by_combined_item, but design prepare still writes oos-design-filing-order.txt from pre-cap headers while issue-cap collapses oos-combined.md to one block; annotate then writes Filed URL for order[0] only, leaving other accepted OOS_N blocks unannotated so a later prepare pass treats them as unfiled and can re-file
- **Proposed resolution**: Add an UPDATED design_oos.py step: after cap=1 rollup, stamp every source OOS block in oos-accepted-design.md with the single filed URL (or port the implement stable-id mapping); extend test_design_oos.py to assert all rollup sources carry Filed URL and skip re-file on rerun



### FINDING_12:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py:665-857
- **Concern**: FINDING_11 body-size split still lives only under a weak MAY_UPDATE on oos_filer. Scenario: The accepted one-public-issue rule is broken in oos_filer._split_to_github_limit and _run_issue_batch, which still emit multiple create-one calls with (part N/M) titles; listing FINDING_11 mainly on file_oos.py and MAY_UPDATE oos_filer leaves the actual multi-issue path unchanged
- **Proposed resolution**: Promote python/larch/issue/oos_filer.py to UPDATED: replace multi-part public filing with one summarized [OOS] payload and run-log retention; add test_oos_filer.py coverage for oversized rollup yielding exactly one create-one call



### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:976-991
- **Concern**: Design annotate still maps ISSUE_URL_N by capped-batch index while oos-design-filing-order.txt lists every pre-cap OOS_N header. Scenario: FINDING_8 remains open: with OOS_ISSUES_PER_RUN_CAP=1, multiple vote-accepted design OOS roll into one public issue but annotate stamps only the first order entry; later accepted blocks stay without - **Filed URL**:, re-enter prepare as unfiled, and break re-run dedup
- **Proposed resolution**: Add a firm ### UPDATED: python/larch/design/design_oos.py step: when prepare/issue-cap collapses to one ISSUE_URL, annotate every order-listed accepted source block (or all still-unfiled accepts) with that URL and emit OOS_FILE_MAP rows per source; extend python/tests/design/test_design_oos.py with a capped multi-OOS annotate case asserting every original block is marked filed



### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/shared/reviewer-templates.md:239,317,413,505
- **Concern**: Proposal-time OOS selection text still says highest-materiality outside rendering.py. Scenario: FINDING_1 remains open: the plan rewrites oos_proposal_instruction() in rendering.py but omits reviewer-templates.md and the hand-maintained agents/reviewer-*.md plus agents/pre-rendered/*-body.txt chain that render specialist loads first; reviewers still cap or rank OOS by backlog materiality before voting
- **Proposed resolution**: Add ### UPDATED: skills/shared/reviewer-templates.md (replace four highest-materiality OOS-cap lines with legitimacy wording), update hand-maintained agents/reviewer-*.md matching lines or regenerate via python3 python/cli.py generate pre-rendered-reviewer-prompts, regenerate committed agents/code-reviewer.md (and other generator-owned agents) from templates, and extend python/test_rendering.py or generate check so proposal prompts cannot drift back to materiality



### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/issue/oos_filer.py:1068-1077
- **Concern**: Security sidecar still blocks non-security OOS filing. Scenario: After voting, one security OOS routes to security-oos-observations.md while a separate non-security OOS is accepted. oos file returns security_sidecar_present before reading accepted files, so Step 9a.1 files no unifying issue for the accepted non-security item.
- **Proposed resolution**: Make oos_filer.py a firm UPDATED file. File accepted non-security blocks while keeping security blocks private and keeping the checkpoint blocked until private disposition, or explicitly rerun oos file after the sidecar is cleared. Add a mixed security plus non-security test.



### FINDING_16:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/issue/oos_filer.py:665-704,809-815
- **Concern**: Oversized OOS fix is optional in the file that actually splits public issues. Scenario: Updating file_oos.py alone cannot preserve the one-issue invariant because _split_to_github_limit still creates multiple body files and _run_issue_batch calls issue create-one for each part. An oversized accepted OOS can still create multiple public [OOS] issues.
- **Proposed resolution**: Promote oos_filer.py from MAY_UPDATE to UPDATED. Replace body splitting with one summarized or truncated public body plus run-log details, and cover the oversized path in test_oos_filer.py.



