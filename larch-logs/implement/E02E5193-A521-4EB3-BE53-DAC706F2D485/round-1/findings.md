### FINDING_1: **correctness** `scripts/ship-pr.sh:1026-1030` — The new computed title is not applied when `create-pr.sh` finds an existing open PR: `create-pr.sh` returns `PR_STATUS=existing` without using the passed `--title`, and this branch only updates the PR body afterward. Concrete scenario: an open PR created before this fix still has title `Bump version to 1.0.1`; rerunning `pr-create` with `ISSUE_NUMBER=7` computes `Fixes #7: initial` and stores it in state, but GitHub keeps the old title. **Suggested fix:** On `PR_STATUS=existing`, update the title too, for example via `gh pr edit "$pr_number" --title "$title"` with the same repo args, and add a regression test for the existing-PR path.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1026-1030` — The new computed title is not applied when `create-pr.sh` finds an existing open PR: `create-pr.sh` returns `PR_STATUS=existing` without using the passed `--title`, and this branch only updates the PR body afterward. Concrete scenario: an open PR created before this fix still has title `Bump version to 1.0.1`; rerunning `pr-create` with `ISSUE_NUMBER=7` computes `Fixes #7: initial` and stores it in state, but GitHub keeps the old title. **Suggested fix:** On `PR_STATUS=existing`, update the title too, for example via `gh pr edit "$pr_number" --title "$title"` with the same repo args, and add a regression test for the existing-PR path.
- **Suggested revision**: Address the concern above.

### FINDING_2: **correctness** `scripts/test-ship-pr.sh:886-891` — The new regression fixture never establishes `origin/main` (see `make_repo` at `scripts/test-ship-pr.sh:241-254`, which only `git init`s a local repo), so `git merge-base HEAD origin/main` in `run_pr_create_phase` always fails and the title is taken from the `git log … HEAD` fallback (`scripts/ship-pr.sh:947-948`), not from the `merge-base..HEAD` range (`scripts/ship-pr.sh:945-946`). The assertion therefore does not prove the primary production path where `_merge_base` is non-empty; it only proves oldest-subject selection when the merge-base lookup misses. **Suggested fix:** Extend the fixture (for example add a `git remote add origin` and a `main` ref the merge-base can resolve, or materialize `refs/remotes/origin/main`) so `_merge_base` is set and the test still expects `PR_TITLE=Fixes #7: initial`.
- **Reviewer**: dyn-git-log-ordering-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr.sh:886-891` — The new regression fixture never establishes `origin/main` (see `make_repo` at `scripts/test-ship-pr.sh:241-254`, which only `git init`s a local repo), so `git merge-base HEAD origin/main` in `run_pr_create_phase` always fails and the title is taken from the `git log … HEAD` fallback (`scripts/ship-pr.sh:947-948`), not from the `merge-base..HEAD` range (`scripts/ship-pr.sh:945-946`). The assertion therefore does not prove the primary production path where `_merge_base` is non-empty; it only proves oldest-subject selection when the merge-base lookup misses. **Suggested fix:** Extend the fixture (for example add a `git remote add origin` and a `main` ref the merge-base can resolve, or materialize `refs/remotes/origin/main`) so `_merge_base` is set and the test still expects `PR_TITLE=Fixes #7: initial`.
- **Suggested revision**: Address the concern above.

### FINDING_3: **security** `scripts/ship-pr.sh:951-952` — `issue_num` from `read_state ISSUE_NUMBER` is concatenated into the PR title and later persisted as `PR_TITLE` without checking that it is a plain GitHub issue id (for example digits-only). That does not bypass the quoting chain into `gh`, but a malformed or hand-edited state value yields a misleading `Fixes #…` title and weakens the guarantee that the prefix refers to a real issue the way operators expect. The new test in `scripts/test-ship-pr.sh:132-140` only covers a numeric issue and does not exercise rejection or stripping of invalid values. **Suggested fix:** Before applying the prefix, require a safe pattern (for example `case "$issue_num" in ''|*[!0-9]*) ;; *) title="Fixes #${issue_num}: ${title}";; esac`) or reuse a single small validator shared with other `ISSUE_NUMBER` uses, and optionally add a regression test for a non-numeric value so the prefix is skipped and a warning is logged.
- **Reviewer**: dyn-issue-num-injection-output.txt
- **Concern**: - **security** `scripts/ship-pr.sh:951-952` — `issue_num` from `read_state ISSUE_NUMBER` is concatenated into the PR title and later persisted as `PR_TITLE` without checking that it is a plain GitHub issue id (for example digits-only). That does not bypass the quoting chain into `gh`, but a malformed or hand-edited state value yields a misleading `Fixes #…` title and weakens the guarantee that the prefix refers to a real issue the way operators expect. The new test in `scripts/test-ship-pr.sh:132-140` only covers a numeric issue and does not exercise rejection or stripping of invalid values. **Suggested fix:** Before applying the prefix, require a safe pattern (for example `case "$issue_num" in ''|*[!0-9]*) ;; *) title="Fixes #${issue_num}: ${title}";; esac`) or reuse a single small validator shared with other `ISSUE_NUMBER` uses, and optionally add a regression test for a non-numeric value so the prefix is skipped and a warning is logged.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] The same unvalidated `ISSUE_NUMBER` was already interpolated into the PR body as `Closes #$(read_state ISSUE_NUMBER)` in `scripts/ship-pr.sh` (around lines 915–916) and passed to `tracking-issue-write.sh --issue "$issue"` in `rename_done_best_effort` (around lines 1067–1077); this change widens where that value appears (title and `PR_TITLE`) but does not introduce the trust boundary itself.
- **Reviewer**: dyn-issue-num-injection-output.txt
- **Concern**: - The same unvalidated `ISSUE_NUMBER` was already interpolated into the PR body as `Closes #$(read_state ISSUE_NUMBER)` in `scripts/ship-pr.sh` (around lines 915–916) and passed to `tracking-issue-write.sh --issue "$issue"` in `rename_done_best_effort` (around lines 1067–1077); this change widens where that value appears (title and `PR_TITLE`) but does not introduce the trust boundary itself.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] `state_set` still writes arbitrary string values into the state file via `awk -v v="$value"` (`scripts/ship-pr.sh:526-540`), including newlines in values such as `PR_TITLE`; that predates this diff and is unchanged by it.
- **Reviewer**: dyn-issue-num-injection-output.txt
- **Concern**: - `state_set` still writes arbitrary string values into the state file via `awk -v v="$value"` (`scripts/ship-pr.sh:526-540`), including newlines in values such as `PR_TITLE`; that predates this diff and is unchanged by it.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh:946-948
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] git log filtered by grep -v still has pipefail/grep-empty edge cases when no subject survives the filter. All subjects match the flush skip pattern so grep exits 1; behavior depends on pipefail and assignment rules as before this change. Only worth addressing if tightening ship-pr error handling globally; unchanged by this diff aside from tail vs head.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: scripts/test-ship-pr.sh:151-152
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] create-pr stub always prints PR_TITLE=Title Misleading when reading stub output vs state file None required for this PR
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/ship-pr.sh:946-948
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] tail -1 on git log pipeline drains entire filtered history Large merge-base..HEAD (or long HEAD fallback) forces a full log scan on each pr-create instead of stopping at the first eligible line Use git log --reverse with the same grep filter and head -1 to select the oldest non-flush subject without reading the whole list
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/test-ship-pr.sh:886-892
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Title test only hits merge-base-failure fallback path Regression in the _merge_base..HEAD branch would not be caught by this test Add origin/main (or equivalent) so the merge-base branch runs in the harness
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: scripts/test-ship-pr.sh:883-893
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] New PR-title test only hits git log HEAD fallback without origin/main; merge-base..HEAD path is untested and the fixture would break if origin/main were added at initial. Contributor adds origin/main at initial: merge-base..HEAD excludes initial; filtered subjects collapse to Bump version only; PR_TITLE becomes Fixes #7: Bump version to 1.0.1 while test expects Fixes #7: initial. Model git so merge-base succeeds and initial lies inside merge-base..HEAD (base commit on main then branch-only initial flush bump).
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-ship-pr.sh:886-890
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] PR title test relies on write_state default ISSUE_NUMBER=7 instead of pinning the value in the scenario. If the default ISSUE_NUMBER in write_state changes, the test could still pass PR_TITLE=Fixes #7: initial while no longer documenting issue-driven prefixing. Set ISSUE_NUMBER explicitly in this test (or assert create-pr --title) so the scenario encodes its own contract.
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/ship-pr.sh:951-952
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] ISSUE_NUMBER is interpolated into the PR title without validation or trimming after read_state. Whitespace-only or non-numeric ISSUE_NUMBER (e.g. corrupted state) yields a title like Fixes # : … or Fixes #abc: …; GitHub may not link the issue and operators get a misleading PR title while the flow still succeeds. Trim whitespace and require an all-digit ISSUE_NUMBER before applying the Fixes # prefix; otherwise leave title unchanged or stall loudly.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-ship-pr.sh:885-894
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New PR title test never exercises merge-base..HEAD branch of run_pr_create_phase If a future edit broke only the non-empty _merge_base path (typo different rev-list pipeline split) CI could still pass while production repos with origin/main broke Add origin/main (or equivalent) to the fixture so merge-base succeeds and expectations stay Fixes #7: initial
- **Suggested revision**: Address the concern above.

