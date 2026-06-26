## Goal
Implement issue #5460: [IMPLEMENTING] [BUG] Review diff base uses local main instead of origin/main (mid-run contamination).

## Implementation Plan
## Summary

The Step 5 code-review diff (and the wider review-and-fix pipeline diff) is computed against the **local `main`** ref instead of the remote-tracking **`origin/main`**. When other PRs merge during a run and the feature branch rebases onto the advanced `origin/main`, the now-stale local `main` makes the merge-base resolve to an old commit. As a result, commits that were merged to `origin/main` by *other* PRs during the run appear in the review diff as if they were this branch's local changes. Reviewers then review — and the review fix-coder edits — already-merged, out-of-scope code, contaminating the branch with unrelated changes filed under the wrong issue. The trigger is benign concurrent merges, so this is intermittent and easy to miss.

## Original report

`/implement`'s review process ended up treating another already-merged PR's code (now on `main`) as a locally-made change in the branch under review, and the review fix-coder then "fixed" that inherited code, contaminating a docs-only branch with unrelated Python edits.

Confirmed root cause (by code read):

- `python/review_dispatch.py:307` — `gather_branch_context()` runs `git merge-base HEAD main` (literal local `main`), then computes the review diff / file-list / commit-log as `git diff <merge_base>...HEAD` (lines 307–314).
- `python/review_pipeline.py:252` calls `agent gather-branch-context --output-dir ...` and passes **no** base-remote / base-ref args, so the hardcoded `main` is always used.
- This diverges from larch's own convention: `python/ci.py` and `python/push.py` resolve the base via `--base-remote` (default `origin`) + `--base-ref` (default `main`) → `origin/main` (and `upstream/main` for forked mode), validated by `git.validate_base_remote_ref`.

## Reproduction scenario

1. Start an `/implement` run on a branch cut from local `main` at commit `A`.
2. While the run is in progress (before Step 5 review), have one or more other PRs merge to the remote, advancing `origin/main` from `A` to `B` (where `B` touches files unrelated to this branch's scope, e.g. `python/checks.py`).
3. A rebase checkpoint (`push checkpoint-probe`) fetches and rebases the feature branch onto `origin/main` = `B`. Local `main` stays at `A`.
4. Step 5 review runs `git merge-base HEAD main` → resolves to `A` (stale local `main`), not `B`.
5. The review diff `git diff A...HEAD` now includes everything merged between `A` and `B` (the other PRs' changes) as if they were this branch's local edits.

Observed live: a docs-only run for issue #5393 (branch touched only `skills/design/SKILL.md` + `skills/design/references/plan-review.md`). Local `main` was at `c8caa1e30` (#5447); `origin/main` had advanced to `4f89087bd` (#5453). Commit `0c0c077b1` (issue #5440, PR #5451) modified `python/checks.py` in that window. Step 5 reviewers saw that already-merged `checks.py` code in the diff, accepted a finding about it, and the fix-coder added ~58 lines to `python/checks.py` + ~114 lines to `python/test_checks.py` on the docs-only branch. The contamination was detected and stripped manually before merge.

## Expected behavior

The review diff should contain **only** the feature branch's own changes relative to the branch's true merge target — `origin/main` (default) or `upstream/main` (forked mode) — even when `origin/main` advances during the run. Commits merged to the base by other PRs should never appear in the review diff as local changes.

## Observed behavior

The review diff is computed against stale local `main`, so commits already merged to `origin/main` (inherited into the branch via a mid-run rebase) appear as this branch's local changes. Reviewers review them, the panel can accept findings about them, and the fix-coder edits them — landing unrelated, out-of-scope changes on the branch.

## Root cause analysis

Confirmed. `python/review_dispatch.py:307` hardcodes the local `main` ref in `git merge-base HEAD main`. In a normal run local `main` == `origin/main`, so the diff is correct. The defect surfaces only when `origin/main` advances mid-run (concurrent merges) while local `main` stays behind and the branch is rebased onto the advanced `origin/main`: the merge-base then resolves against the stale local `main`, widening the diff to include the concurrently-merged upstream commits. The wider review-and-fix pipeline inherits this base because `python/review_pipeline.py:252` invokes `gather-branch-context` without threading any base ref, unlike `ci.py`/`push.py` which take `--base-remote`/`--base-ref`.

Secondary (inference, not yet exploited as a separate failure): `python/review_and_fix.py:2154` `apply_findings_with_coder` applies accepted findings to whatever files are present in the review diff, with no validation that those files are actually in this branch's scope. So once an inherited file enters the diff, the coder will edit it with no guard.

## Evidence

- `python/review_dispatch.py:307` (read): `merge = subprocess.run(["git", "merge-base", "HEAD", "main"], ...)` followed by `git diff <merge_base>...HEAD` on lines 312–314.
- `python/review_pipeline.py:252` (grep): `_run_python_cli(["agent", "gather-branch-context", "--output-dir", str(output_dir)], ...)` — no base ref passed.
- `python/ci.py` and `python/push.py` (grep): both default `--base-remote=origin`, `--base-ref=main`, validated by `git.validate_base_remote_ref` — the existing convention `gather_branch_context` should follow.
- `python/review_and_fix.py:2154` (grep): `def apply_findings_with_coder(...)` — applies findings to diff files without a base-scope guard.
- `python/test_review_dispatch.py:154` `test_gather_branch_context_outputs_and_excludes_larch_logs` (grep): only exercises a local-only repo; no coverage for `origin/main` ahead of local `main` + rebase.
- Live incident: run `066CD6A6-9F8B-4989-8049-1F7349950C4D` for issue #5393; local `main` `c8caa1e30` (#5447) vs `origin/main` `4f89087bd` (#5453); inherited commit `0c0c077b1` (#5440 / PR #5451) touching `python/checks.py`.

## Affected files

- `python/review_dispatch.py` — `gather_branch_context()` line 307; the literal `main` base ref is the bug.
- `python/review_pipeline.py` — line 252 calls `gather-branch-context` without base-remote/base-ref; needs to thread them through.
- `python/review_and_fix.py` — `apply_findings_with_coder` (line 2154) edits any diff file without a base-scope guard (defense-in-depth).
- `python/test_review_dispatch.py` — `test_gather_branch_context_*` (line 154) has no concurrent-advance / rebase coverage.

## Suggested fix(es)

- Resolve the review base to the remote-tracking ref: `git merge-base HEAD origin/main` (default), or `{base_remote}/{base_ref}` to also fix forked mode (`upstream/main`).
- `git fetch` the base remote/ref before computing the merge-base so it reflects current remote state.
- Thread `--base-remote` / `--base-ref` from `python/review_pipeline.py` into `gather-branch-context`, mirroring `ci.py` / `push.py`, and reuse `git.validate_base_remote_ref`.
- Add a regression test in `python/test_review_dispatch.py` for the concurrent-advance + rebase scenario (local `main` behind `origin/main`; assert the inherited upstream commits are excluded from the diff/file-list).
- Optional defense-in-depth: in `python/review_and_fix.py`, skip applying findings to files already reachable from the base ref (not introduced by this branch).

## Open questions

- Forked mode: should the review base use `upstream/main` via the same `--base-remote`/`--base-ref` plumbing, and is `upstream` always the correct remote for the review base in fork runs?
- Should `gather-branch-context` `git fetch` the base remote itself, or rely on the most recent rebase-checkpoint fetch to have already updated the remote-tracking ref?
- Is the optional coder base-scope guard in `review_and_fix.py` worth adding in the same change, or tracked separately?

## Related issues

- **#1694** ("[DONE] Use merge-base diff as default for reviewer launches instead of full branch history") **introduced** the `git diff $(git merge-base HEAD main)...HEAD` pattern in the predecessor `scripts/gather-branch-context.sh` (now `python/review_dispatch.py`). Its Risk note considered interactive rebase but not the stale-local-`main`-vs-advanced-`origin/main` case. This bug is a defect in what #1694 shipped: it standardized on the local `main` ref where `origin/main` was intended.
- **#2266** ("Review panel scope-fit gate — panel must reject findings unrelated to the PR's diff or plan") is a related downstream mitigation. It does **not** catch this bug: the inherited already-merged code is genuinely *in* the mis-computed diff, so a scope-fit gate keyed on diff membership treats it as in-scope.

## Test plan
(no test plan section in plan-file)
