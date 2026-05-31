### FINDING_11: staged-carryover-orchestrator skips carryover warning assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Warning breadcrumb regression on staged carryover would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add grep for pre-existing dirty path carried over breadcrumb.


### FINDING_12: Unstaged carryover + git add/restore misclassified as outside-manifest dirt (fail-closed)
- **Reviewer(s)**: dyn-flag-removal-completeness-output.txt
- **Severity**: latent
- **Concern**: `path_is_pre_coder_carryover` classifies carryover using only `git diff "$pre_head" -- "$path"` (worktree vs `pre-coder-head`), while `capture_round_tracked_paths` also lists index-only dirt via `git diff --cached`. If pre-dispatch carryover was **unstaged** (non-empty snapshot) and the coder later runs the common `git add <path>` + `git restore --worktree` pattern—leaving the original staged blob in the index but a clean worktree—the worktree diff becomes empty, `cmp` no longer matches the snapshot, the path is treated as new outside-manifest dirt, and the round still fails closed with “dirty paths outside coder delta” even though the index content is unchanged carryover. The new `outside-manifest-break-carryover` harness deliberately exercises this shape; production coders can hit it without mutating carryover content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flag-removal-completeness-output.txt: When deciding carryover, treat a path as unchanged if either the worktree diff or the cached diff vs `pre_head` matches the snapshot (or snapshot both at dispatch with `git diff "$pre_head"` / `git diff "$pre_head" --cached` and compare both on the post-dispatch path), so index-only residue that still matches the pre-coder snapshot is not misclassified.


### FINDING_5: Index-only coder changes misclassified as unchanged carryover (fail-open)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `path_is_pre_coder_carryover` uses worktree-only `git diff` vs snapshot; index-only coder mutations on index-only pre-dirt can be misclassified as unchanged carryover. Pre-dispatch `other.txt` dirty only in index (empty snapshot); coder `git add other.txt` with new content but worktree still matches `pre_head`; round exits `applied` while mutated index content for `other.txt` remains staged outside the manifest commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Compare index and worktree consistently in the predicate and snapshot (e.g. include `git diff --cached` in snapshot and cmp), if index-only coder changes must fail closed.
  - From cursor-specialist-edge-cases-output.txt: Snapshot and compare combined worktree+cached diff vs `pre_head` (or compare trees); add index-mutation regression in test-review-and-fix.sh.


### FINDING_6: Missing post-follow-up failure breadcrumb in docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan-required post-follow-up failure breadcrumb missing from documented breadcrumb list. Operator reads review-and-fix.md and does not see the string emitted at review-and-fix.sh:609 for persistent non-carryover residue after follow-up.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add bullet: ⚠ review-and-fix: round N left tracked changes uncommitted after follow-up.


