## Proposed Design Outline

### Goals
- Close the 3 confirmed-open transient-retry gaps so one transient network/auth blip no longer hard-fails a freshness rebase, misses an existing PR during conflict recovery, or stalls a merge with a false `ci_not_ready`.
- Reuse the canonical `with_transient_retry` helper from `lib-net.sh` uniformly — match the retry pattern already present elsewhere in each touched script.

### Non-goals
- No changes to `design-log-publish.sh` (trap + list/view retry already landed in #2581) or `lib-net.sh`.
- Do not replace `merge-pr.sh`'s existing UNKNOWN-recovery loop; layer retry under it. No unrelated retry refactors.
- No change to any script's stdout `key=value` contract, exit-code table, or redaction behavior.

### Approach sketch
- `rebase-push.sh`: wrap the `--no-push` `git fetch` (~line 195) in `with_transient_retry`; on exhaustion keep the existing `REBASE_ERROR` + `exit 3` fatal contract (freshness must stay fatal-on-real-failure).
- `create-pr.sh`: wrap the recovery `gh pr list` in `recover_existing_pr_after_create_conflict()` (~line 201) in `with_transient_retry`; keep the conflict-text URL fallback. This also closes the lost-success duplicate-PR path (FINDING_20).
- `merge-pr.sh`: route `gh pr view` (`refresh_pr_info`) and `gh pr checks` (`refresh_ci_state`, both JSON and text fallback) through `with_transient_retry`, parsing `_WTR_OUT` into the existing variables.

### Surfaces in scope
- `scripts/rebase-push.sh`, `scripts/create-pr.sh`, `scripts/merge-pr.sh`
- Sibling contracts `scripts/rebase-push.md`, `scripts/create-pr.md`, `scripts/merge-pr.md` (note retry coverage).
- Tests: extend `scripts/test-create-pr.sh` and `scripts/test-merge-pr.sh`; add a minimal `scripts/test-rebase-push.sh` (none exists) or verify rebase-push manually.

### Open questions
- None.
