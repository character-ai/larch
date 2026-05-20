# Review Round 1

- Mode: `diff`
- Accepted findings: 3
- Rejected findings: 3
- Exonerated findings: 2
- Neutral findings: 1

## Accepted Findings

### FINDING_1: **correctness** `scripts/ship-pr.sh:1026-1030` — The new computed title is not applied when `create-pr.sh` finds an existing open PR: `create-pr.sh` returns `PR_STATUS=existing` without using the passed `--title`, and this branch only updates the PR body afterward. Concrete scenario: an open PR created before this fix still has title `Bump version to 1.0.1`; rerunning `pr-create` with `ISSUE_NUMBER=7` computes `Fixes #7: initial` and stores it in state, but GitHub keeps the old title. **Suggested fix:** On `PR_STATUS=existing`, update the title too, for example via `gh pr edit "$pr_number" --title "$title"` with the same repo args, and add a regression test for the existing-PR path.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1026-1030` — The new computed title is not applied when `create-pr.sh` finds an existing open PR: `create-pr.sh` returns `PR_STATUS=existing` without using the passed `--title`, and this branch only updates the PR body afterward. Concrete scenario: an open PR created before this fix still has title `Bump version to 1.0.1`; rerunning `pr-create` with `ISSUE_NUMBER=7` computes `Fixes #7: initial` and stores it in state, but GitHub keeps the old title. **Suggested fix:** On `PR_STATUS=existing`, update the title too, for example via `gh pr edit "$pr_number" --title "$title"` with the same repo args, and add a regression test for the existing-PR path.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/test-ship-pr.sh:883-893
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New PR-title test only hits git log HEAD fallback without origin/main; merge-base..HEAD path is untested and the fixture would break if origin/main were added at initial. Contributor adds origin/main at initial: merge-base..HEAD excludes initial; filtered subjects collapse to Bump version only; PR_TITLE becomes Fixes #7: Bump version to 1.0.1 while test expects Fixes #7: initial. Model git so merge-base succeeds and initial lies inside merge-base..HEAD (base commit on main then branch-only initial flush bump).
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** `scripts/test-ship-pr.sh:886-891` — The new regression fixture never establishes `origin/main` (see `make_repo` at `scripts/test-ship-pr.sh:241-254`, which only `git init`s a local repo), so `git merge-base HEAD origin/main` in `run_pr_create_phase` always fails and the title is taken from the `git log … HEAD` fallback (`scripts/ship-pr.sh:947-948`), not from the `merge-base..HEAD` range (`scripts/ship-pr.sh:945-946`). The assertion therefore does not prove the primary production path where `_merge_base` is non-empty; it only proves oldest-subject selection when the merge-base lookup misses. **Suggested fix:** Extend the fixture (for example add a `git remote add origin` and a `main` ref the merge-base can resolve, or materialize `refs/remotes/origin/main`) so `_merge_base` is set and the test still expects `PR_TITLE=Fixes #7: initial`.
- **Reviewer**: dyn-git-log-ordering-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr.sh:886-891` — The new regression fixture never establishes `origin/main` (see `make_repo` at `scripts/test-ship-pr.sh:241-254`, which only `git init`s a local repo), so `git merge-base HEAD origin/main` in `run_pr_create_phase` always fails and the title is taken from the `git log … HEAD` fallback (`scripts/ship-pr.sh:947-948`), not from the `merge-base..HEAD` range (`scripts/ship-pr.sh:945-946`). The assertion therefore does not prove the primary production path where `_merge_base` is non-empty; it only proves oldest-subject selection when the merge-base lookup misses. **Suggested fix:** Extend the fixture (for example add a `git remote add origin` and a `main` ref the merge-base can resolve, or materialize `refs/remotes/origin/main`) so `_merge_base` is set and the test still expects `PR_TITLE=Fixes #7: initial`.
- **Suggested revision**: Address the concern above.


