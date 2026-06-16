## Goal
Implement issue #4524: [IMPLEMENTING] [BUG] /design log-publish enables gh pr merge --auto, so log PRs never merge under….

## Implementation Plan
## Summary

`/design` Step 5c opens automated `chore(larch-logs): design run <UUID>` PRs and enables **GitHub-native auto-merge** (`gh pr merge --auto --squash`). GitHub auto-merge honors all branch-ruleset gates, and this repo's active **"Code review"** ruleset on `refs/heads/main` requires an approving review plus a code-owner review. Automated log PRs never get reviewed, so auto-merge never fires and the PRs pile up open and `BLOCKED`. An `--admin` bypass merge path already exists in the codebase (`design_log_ship.py`) but is not wired into the live `/design` flow.

## Original report

Three open `chore(larch-logs)` PRs (#4510, #4511, #4513) were never merged, even though `/design` is supposed to merge its own log PRs with `--admin`. All three were `mergeable=MERGEABLE` with **all required CI checks SUCCESS**, but `mergeStateStatus=BLOCKED` and `reviewDecision=REVIEW_REQUIRED`. They had to be merged manually with `gh pr merge --admin --squash --delete-branch`. The request was to merge them, then investigate why `/design` did not merge them with `--admin` as expected, confirm whether the root cause is still in `main`, check for an existing issue, and file a bug if none exists.

## Reproduction scenario

1. Run `/design` to completion on a branch into `main` (any design run that reaches Step 5c log publish).
2. Observe the resulting `chore(larch-logs): design run <UUID>` PR.
3. Wait for all required CI checks to go green.
4. Observe the PR stays **open** with `mergeStateStatus=BLOCKED` and `reviewDecision=REVIEW_REQUIRED`:
   - `gh pr view <n> --json mergeable,mergeStateStatus,reviewDecision` → `MERGEABLE` / `BLOCKED` / `REVIEW_REQUIRED`.
   - `gh pr view <n> --json autoMergeRequest` → auto-merge **enabled** (`enabledAt` matches PR creation) but never fired.
5. The PR never merges on its own; only `gh pr merge <n> --admin --squash --delete-branch` completes it.

## Expected behavior

`/design`-authored log PRs merge automatically (squash) once required CI checks pass, without manual intervention, using an `--admin` bypass that does not depend on a human/code-owner review the automated PR will never receive.

## Observed behavior

Log PRs are created and have GitHub-native auto-merge enabled, but auto-merge waits on the required-review gate that an unreviewed automated PR can never satisfy. The PRs accumulate as open, `BLOCKED` PRs until an operator admin-merges them manually.

## Root cause analysis

`python/design_log_publish_flow.py::_publish_design_logs` enables GitHub-native auto-merge:

```python
# Enqueue GitHub-native auto-merge (non-blocking) so the log PR squashes
# in once required checks pass, without stalling the /design orchestrator
# on CI. ...
if pr_number:
    merge = _run(["gh", "pr", "merge", "--auto", "--squash", pr_number, *repo_args], cwd=repo_root)
```

GitHub-native auto-merge (`--auto`) merges only when **all** branch-protection / ruleset conditions are met, including required reviews. The repo (`character-ai/larch`) has an **active ruleset "Code review"** (id `14887924`) scoped to `refs/heads/main` with a `pull_request` rule: `required_approving_review_count: 1` and `require_code_owner_review: true`. (Classic branch protection returns HTTP 404 "Branch not protected"; the requirement comes from the ruleset, not classic protection.) Automated log PRs never receive a review, so the auto-merge queue condition is never satisfied and the PR sits open indefinitely.

The intended `--admin` bypass **already exists but is orphaned**: `python/design_log_ship.py::run_design_log_ci_merge` (CLI verb `ship design-log`, registered at `python/cli.py:219`) waits for required checks to go green, then runs `gh pr merge --admin --squash --delete-branch` with transient retry — bypassing the review gate. Nothing in the live `/design` flow invokes it. Step 5c (`skills/design/references/approval-gates.md:201`) and `skills/design/scripts/design-clarify.sh:355` call only `python/cli.py design log-publish` (the `--auto` path). `ship design-log` is referenced only in `python/README.md`.

**This is a bash→Python port regression.** Per the documented Code Flow in #4257, the predecessor bash flow (`scripts/design-log-publish.sh`, since retired) waited for required CI and then invoked `python/cli.py ship design-log` — the admin-merge path. The #4404 Python port (`design_log_publish_flow.py`) replaced that admin-merge step with GitHub-native `--auto` and left `ship design-log` orphaned. #4257 explicitly documents admin merge as the sanctioned design — "`--admin` bypasses the review gate only; CI still gates the merge ... the sanctioned path and is **not** to be removed" — so the current `--auto` behavior also violates that documented intent.

**Regression origin:** the `--auto` block was added in commit `25c51bf7f` (PR #4404, "Fix non-unique run-1 log dirs (#4397) and design log-publish not committing (#4395)", 2026-06-15). The stated intent was a non-blocking merge "without stalling the /design orchestrator on CI." That goal is reasonable, but `--auto` also waits on the required review, which an automated PR never gets — so the PRs never merge.

**Confirmed present in `main`:** yes. `python/design_log_publish_flow.py:167` on a clean `main` still uses `gh pr merge --auto --squash`.

## Evidence

- `gh pr view 4510|4511|4513 --json mergeable,mergeStateStatus,reviewDecision` → `MERGEABLE` / `BLOCKED` / `REVIEW_REQUIRED` with all ~37 required checks `SUCCESS`.
- `gh pr view 4510 --json autoMergeRequest` → `enabledAt` 2026-06-16T12:53:41Z, `mergeMethod: SQUASH`, never fired (same pattern on 4511/4513).
- `gh api repos/{owner}/{repo}/branches/main/protection` → HTTP 404 "Branch not protected" (so review requirement is ruleset-sourced, not classic protection).
- `gh api repos/{owner}/{repo}/rulesets/14887924` → name "Code review", `enforcement: active`, `conditions.ref_name.include: ["refs/heads/main"]`, rule `pull_request` with `required_approving_review_count: 1`, `require_code_owner_review: true`.
- `git log -L 162,170:python/design_log_publish_flow.py` → the `--auto` block was introduced by commit `25c51bf7f` (#4404).
- Grep confirms `ship design-log` / `design_log_ship` is invoked nowhere in `skills/` or `scripts/`; only `python/cli.py:219` (registration) and `python/README.md` reference it.
- Manual `gh pr merge <n> --admin --squash --delete-branch` merged all three PRs immediately (rc=0), confirming `--admin` bypasses the gate that `--auto` cannot.
- #4257 (CLOSED/DONE) documents the sanctioned design ("merged with `--admin` ... not to be removed") and its Code Flow diagram shows the predecessor bash flow calling `python/cli.py ship design-log` (admin merge) after the CI wait — confirming the Python port dropped that step. #4257 was scoped to stale-base conflicts and "not about the merge mechanism," so it is distinct from this bug.

## Affected files

- `python/design_log_publish_flow.py` — primary fix locus; line ~166-169 enables `--auto` merge that cannot satisfy the required-review ruleset for unreviewed automated PRs.
- `python/design_log_ship.py` — contains the correct `--admin` wait-then-merge path (`run_design_log_ci_merge`); currently orphaned.
- `python/cli.py` — line 219 registers the `ship design-log` verb that maps to the admin path.
- `skills/design/references/approval-gates.md` (Step 5c) and `skills/design/scripts/design-clarify.sh` (~line 355) — the live callers that invoke only `design log-publish` (the `--auto` path).
- `python/README.md` — documents `ship design-log`; only reference to the admin path outside `cli.py`.

## Suggested fix(es)

Preferred (code-side, self-contained, testable): route the log PR through the existing admin merge path (`design_log_ship.run_design_log_ci_merge` / `ship design-log`), which waits for required checks then `gh pr merge --admin --squash --delete-branch`. To preserve the #4404 non-blocking goal (do not stall the `/design` orchestrator on CI), run that wait-then-admin-merge **detached/in the background** rather than enqueuing `--auto`.

Note: a naive inline swap of `--auto` for `--admin` is **insufficient** — `--admin` without a check-wait tries to merge immediately and fails before checks are green. The existing waiter (`run_design_log_ci_merge`) already solves the wait-then-admin-merge sequencing.

Alternative (repo-config, complementary): exempt `larch-logs/**` branches from the "Code review" ruleset, or add a bypass actor for those branches, so `--auto` can complete once checks pass. The code-side fix is preferred because it is self-contained and does not depend on org/repo ruleset administration.

## Open questions

- Should the design-log merge stay strictly non-blocking (detached admin-merge waiter) to preserve #4404's intent, or is a brief synchronous wait-then-admin-merge acceptable at Step 5c?
- Should the orphaned `ship design-log` verb become the canonical entry the publish flow calls, or should the admin-merge logic be inlined into `design_log_publish_flow.py`?
- Are there older accumulated `chore(larch-logs)` PRs (beyond #4510/#4511/#4513) that also need cleanup, and should the fix include a one-time sweep?

## Test plan
(no test plan section in plan-file)
