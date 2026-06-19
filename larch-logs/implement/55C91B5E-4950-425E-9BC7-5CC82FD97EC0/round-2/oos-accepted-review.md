### OOS_1: correctness: python/review_and_fix.py:1522-1542
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] MAV inline fixes skip rounds without full pre-coder snapshot so --stage-all returns no paths Step 5 main-agent-vote-required: orchestrator edits foo.py; resume --ready-to-commit gets ERROR=no review delta paths and stalls while porcelain is dirty Capture a handoff snapshot before MAV inline edits or derive stage paths from porcelain plus review artifacts when snapshots are missing
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/review_and_fix.py:489-514,465-480
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] since_committed diffs from post-coder-head include files already committed by later lint-fix commits Lint-fix commits linted.py after post-coder-head; --stage-all pathspec includes linted.py; commit --only can fail while manual.py stays dirty Diff from current HEAD or intersect collected paths with porcelain or wt-vs-HEAD deltas only
- **Suggested revision**: Address the concern above.


### OOS_3: correctness: python/review_and_fix.py:1267-1278
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Missing lint_applied_ever guard allows post-loop commit on no-changes-pass when delta helper returns paths Dirty baseline plus no-changes lint exit could commit without an applied lint iteration if wt diverges unexpectedly Track lint_applied_ever and skip _commit_lint_fix_delta_paths when false per plan
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] correctness: python/review_and_fix.py:528-541
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Self-review fallback stages all tracked and untracked paths when round snapshots are absent Self-review run with unrelated dirty files can stage more than review deltas Restrict fallback to paths referenced in self-review-accepted.md or porcelain intersection
- **Suggested revision**: Address the concern above.


### OOS_5: risk-integration: python/review_and_fix.py:530-543
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] _collect_self_review_stage_paths stages all tracked and untracked porcelain paths when self-review-accepted.md exists. In --self-review mode there are no round pre-coder snapshots, so Step 7 commit-fixes --stage-all always uses this fallback and can commit unrelated pre-existing dirty files into the review-fixes commit. Capture a pre-self-review baseline snapshot and stage only paths that diverge from it (or diff against merge-base); fail closed if unrelated porcelain remains.
- **Suggested revision**: Address the concern above.


### OOS_6: [OUT_OF_SCOPE] risk-integration: python/review_and_fix.py:530-543
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Self-review fallback stages all tracked/untracked porcelain, not snapshot-bounded review deltas. --self-review run with unrelated pre-dirty files could stage hunks outside review scope at Step 7 --stage-all. Only relevant for --self-review; standard review-loop path uses round snapshots. Narrow fallback if self-review + dirty-tree becomes a supported path.
- **Suggested revision**: Address the concern above.


### OOS_7: **risk-integration** `python/review_and_fix.py:530-543,1522-1541` — `_collect_self_review_stage_paths` falls back to every tracked and untracked path from `_capture_round_tracked_paths()` / `_capture_round_untracked_paths()` when no `round-*` dir has a full pre-coder snapshot. In `--self-review` runs (no external coder rounds), `commit-fixes --stage-all` at Step 5 resume or Step 7 can stage and commit unrelated pre-existing dirty files, not just self-review deltas. The branch test encodes this broad behavior rather than narrowing it. **Suggested fix:** Capture a self-review baseline snapshot (tracked paths plus per-path wt/index patches) when `self-review-accepted.md` is written, and have `_collect_self_review_stage_paths` return only paths that diverge from that snapshot, mirroring the lint-fix and pre-coder machinery.
- **Reviewer**: dyn-delta-scope-output.txt
- **Concern**: - **risk-integration** `python/review_and_fix.py:530-543,1522-1541` — `_collect_self_review_stage_paths` falls back to every tracked and untracked path from `_capture_round_tracked_paths()` / `_capture_round_untracked_paths()` when no `round-*` dir has a full pre-coder snapshot. In `--self-review` runs (no external coder rounds), `commit-fixes --stage-all` at Step 5 resume or Step 7 can stage and commit unrelated pre-existing dirty files, not just self-review deltas. The branch test encodes this broad behavior rather than narrowing it. **Suggested fix:** Capture a self-review baseline snapshot (tracked paths plus per-path wt/index patches) when `self-review-accepted.md` is written, and have `_collect_self_review_stage_paths` return only paths that diverge from that snapshot, mirroring the lint-fix and pre-coder machinery.
- **Suggested revision**: Address the concern above.


### OOS_8: **risk-integration** `python/review_and_fix.py:1267-1320` — `_lint_loop_successful_break` runs on `no-changes-pass` without a `lint_applied_ever` guard (the plan required one). When lint returns `no-changes` but checks pass on a dirty baseline, snapshot-diverged paths can still be committed even though no lint iteration reported `applied`. That can commit working-tree edits that were not produced by the lint-fix loop. **Suggested fix:** Track `lint_applied_ever` across the loop and skip `_commit_lint_fix_delta_paths` unless at least one `applied` iteration occurred, matching the plan contract and leaving non-lint dirty paths for resume handoff or Step 7.
- **Reviewer**: dyn-delta-scope-output.txt
- **Concern**: - **risk-integration** `python/review_and_fix.py:1267-1320` — `_lint_loop_successful_break` runs on `no-changes-pass` without a `lint_applied_ever` guard (the plan required one). When lint returns `no-changes` but checks pass on a dirty baseline, snapshot-diverged paths can still be committed even though no lint iteration reported `applied`. That can commit working-tree edits that were not produced by the lint-fix loop. **Suggested fix:** Track `lint_applied_ever` across the loop and skip `_commit_lint_fix_delta_paths` unless at least one `applied` iteration occurred, matching the plan contract and leaving non-lint dirty paths for resume handoff or Step 7.
- **Suggested revision**: Address the concern above.


