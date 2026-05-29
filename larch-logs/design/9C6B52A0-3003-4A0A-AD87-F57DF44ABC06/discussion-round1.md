## Decision 1: Scope of findings to address
- **Question**: Issue #3172 bundles 6 transient-retry findings. Which should the plan address, given that 2 design-log-publish.sh items appear already fixed on main?
- **Resolution**: Confirmed-open gaps only — `rebase-push.sh` `--no-push` fetch, `create-pr.sh` recovery `gh pr list` (closing the latent duplicate-PR risk too), and `merge-pr.sh` `gh pr view` / `gh pr checks`. The two `design-log-publish.sh` findings (FINDING_10 trap; FINDING_14 list/view retry) are recorded as already-resolved on main — no code change.
- **Source**: user

## Decision 2: rebase-push.sh --no-push fetch — preserve fatal-on-real-failure contract
- **Question**: Should the `--no-push` fetch tolerate failure after adding retry, or keep failing hard?
- **Resolution**: Add `with_transient_retry` around the `git fetch` so transient network failures are retried (3 attempts), then preserve the existing hard-fail contract on exhaustion: `emit_kv REBASE_ERROR "git fetch ... failed (network/auth issue)"` + `exit 3`. The `--no-push` path exists for freshness, so a genuinely failed fetch must stay fatal (per the line 192-193 comment). Default-mode fetch (line 200, `|| true`) is unchanged.
- **Source**: codebase

## Decision 3: merge-pr.sh — add with_transient_retry without removing the UNKNOWN-recovery loop
- **Question**: Does wrapping `gh pr view` / `gh pr checks` in `with_transient_retry` replace the existing `retry_pr_info_unknown_recovery` loop?
- **Resolution**: No — keep both. `with_transient_retry` handles network/auth transients (gh exits non-zero with a net signature). The existing UNKNOWN-recovery loop handles GitHub returning a valid-but-UNKNOWN `mergeStateStatus` (content uncertainty), which is orthogonal. The two layers compose. Preserve all `MERGE_RESULT=*` outcomes, exit codes, and the EXIT-trap KV contract.
- **Source**: codebase

## Decision 4: create-pr.sh — retry the recovery gh pr list; this also closes FINDING_20
- **Question**: How to fix the bare `gh pr list` in conflict recovery and the latent lost-success duplicate-PR risk?
- **Resolution**: Wrap the recovery `gh pr list` in `recover_existing_pr_after_create_conflict()` with `with_transient_retry`. Preserve the existing conflict-text URL fallback (lines 213-215) as the second tier. Because `gh pr create` is already retried, a server-side success whose client response is lost triggers an "already exists" conflict on the next attempt; a retried recovery list then reliably finds the existing PR, closing the FINDING_20 lost-success path.
- **Source**: codebase

## Decision 5: Hard constraints / non-goals
- **Question**: What must not change?
- **Resolution**: Non-goals: no unrelated retry refactors; no change to `design-log-publish.sh`; no change to `lib-net.sh` (`with_transient_retry`, `is_transient_net_signature`, `transient_envelope_predicate_none` are the canonical helpers and are reused as-is). Preserve every script's stdout `key=value` contract, exit-code table, redaction behavior, and `mktemp` fail-file cleanup. Each fix stays small (< ~30 LOC per the issue). Honor `.claude/rules`: `set -euo pipefail` posture (rebase-push.sh and merge-pr.sh intentionally use `set -uo pipefail`), Bash 3.2 portability, and gh body-file rules (no body payloads added here).
- **Source**: user + codebase
