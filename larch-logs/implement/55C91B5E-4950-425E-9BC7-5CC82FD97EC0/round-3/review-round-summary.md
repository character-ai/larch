# Review Round 3

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: step-5-resume treats COMMITTED=true as success with non-empty porcelain
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Resume handoff treats `COMMITTED=true` as success while porcelain may remain non-empty after a pathspec-only commit. A review fix in `b.py` may not be collected while `a.py` commits; the wrapper exits 0; Step 8 hits a dirty-tree stall. The handoff should fail closed when porcelain is non-empty after handoff unless all remaining dirty paths are expected.
- **Suggested revisions (informational for voters; coder decides)**:


### FINDING_2: Step 7 lacks fail-closed handling for commit-fixes --stage-all failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 7 invokes `commit-fixes --stage-all` without fail-closed dirty-tree handling when the helper exits non-zero, unlike Step 5 resume. Self-review fixes may lack a snapshot; `commit_fixes` can return no review-delta paths with a dirty tree; the run advances to Step 8 and stalls. The orchestrator should parse `COMMITTED`/`ERROR`, probe porcelain, and stall with a durable bail when porcelain stays dirty after a failed or partial commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Mirror step-5-resume fail-closed semantics at Step 7: parse COMMITTED/ERROR/exit code, probe porcelain, stall with a durable bail token and skip to Step 16 when commit fails on a non-empty tree.


### FINDING_3: Missing lint_applied_ever gate allows no-changes-pass commit without applied lint
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Post-loop lint commit lacks a `lint_applied_ever` gate. A `no-changes` lint pass can still commit via `_lint_fix_delta_paths` without any lint iteration having been applied. Lint returns `no-changes`; an external working-tree change after snapshot occurs; recheck passes; paths get committed under the lint-fix reason.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track lint_applied_ever per plan or isolate no-changes recovery as explicit separate path.


### FINDING_14: commit-fixes --stage-all can stage unrelated dirty files via round path recomputation
- **Reviewer(s)**: codex-generic-output.txt, dyn-delta-scope-output.txt
- **Severity**: important
- **Concern**: `_collect_review_fix_stage_paths` (used by `commit-fixes --stage-all` in Step 5 resume and Step 7) calls `_collect_round_stage_paths(..., since_committed=True)`, which recomputes against the current working tree and can include unrelated tracked or untracked deltas. `_collect_round_stage_paths` lists paths with `git diff --name-only <post-coder-head>` but passes that same post-commit SHA into `_path_matches_pre_coder_snapshot`; patches were captured against `pre-coder-head.txt`, so unchanged pre-existing dirty tracked files still differ from the later commit, fail the snapshot check, and get staged and committed via pathspec. That violates the review-delta-only contract and recreates the #4712 dirty-tree class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: For `--stage-all`, use a dedicated post-coder or pre-handoff snapshot and collect only paths that diverged from that snapshot during the handoff, or reuse persisted round stage files instead of recomputing broad current-tree deltas from old round snapshots.
  - From dyn-delta-scope-output.txt: Keep `post-coder-head` only as the diff-listing base for `since_committed=True`, but always compare snapshots against the stored `pre-coder-head.txt` (add a `snapshot_head` argument to `_round_coder_delta_paths`, or read it inside `_path_matches_pre_coder_snapshot`). Add a regression test: pre-dirty `unrelated.py` at pre-coder snapshot, coder commits only `fixed.py`, main-agent handoff `--stage-all` must not stage `unrelated.py`.


