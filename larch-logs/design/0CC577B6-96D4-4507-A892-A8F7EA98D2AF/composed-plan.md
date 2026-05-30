## Plan

Re-sequence the `/implement` CI-fix path in `scripts/ship-pr.sh` so a fix is
pushed already-rebased, re-bumped, and lint-clean in one shot. Reuse existing
helpers only — no new rebase / rebump / behind-count / lint-fix / push logic
(issue #3210 hard constraint). Design decisions: guard-only (no `ci-decide.sh`
rework), rotate the vendor start tier per attempt, cover both fix-push paths via
one shared helper.

### Files to modify/create

- **NEW** `scripts/ci-behind-count.sh` (+ `.md`): extract the behind-count
  computation from `ci-status.sh:177` (`git rev-list "HEAD..$BASE_TARGET"
  --count`) into one reusable script. Args `--base-remote` (default `origin`),
  `--base-ref` (default `main`), `--no-fetch`. Emits `BEHIND_COUNT=<n>` on the
  `lib-quiet.sh` contract stream. Fail-open: emit `BEHIND_COUNT=0` + a Warnings
  diagnostic on a failed `git rev-list` (never block a push on a count error).
- **UPDATED** `scripts/ci-status.sh` (+ `.md`): call `ci-behind-count.sh
  --base-remote "$BASE_REMOTE" --base-ref "$BASE_REF" --no-fetch` at line 177
  (already fetched at line 80); parse the integer. Merge detection (184-190)
  unchanged. This is the "call from both sites" half of the no-dup mandate.
- **UPDATED** `scripts/ship-pr.sh` (+ `.md`): see Approach.
- **UPDATED** `scripts/test-ship-pr.sh`; **NEW** `scripts/test-ci-behind-count.sh`
  (+ `.md`); **UPDATED** `Makefile` (register `test-ci-behind-count` `.PHONY` +
  target + a `test-harnesses-N` shard); **UPDATED** `docs/workflow-lifecycle.md`.

### Approach (`scripts/ship-pr.sh`)

New fix-push order: **commit fix → check behind (against the same base the rebase
will use) → (if behind) rebase + rebump with push deferred → re-verify failed
jobs + lint on the rebased tree → push (force-with-lease if rebased, else
plain).** This matches the issue's required order while reusing
`run_rebase_rebump` wholesale.

1. **Fork-aware deferred-push flag through the rebase reuse.** Add `defer_push`
   plus `base_remote` / `base_ref` params to `run_rebase_rebump` (2797), threaded
   into `_run_rebase_rebump_from_step3` (2676),
   `_run_rebase_rebump_verify_plain_no_push` (2663), and every `rebase-push.sh`
   call in that family so a fork rebase targets the correct base. When
   `defer_push=true`, `_run_rebase_rebump_from_step3` does sync-main + bump +
   commit-changelog but **skips** the final `git-force-push.sh` (2784) and
   returns; `REBASE_COUNT` / `ITERATION` still increment. Defaults keep the
   `ci-decide.sh` `ACTION=rebase` callers (3120/3126/3153/3157) byte-identical.
2. **Behind-check + conditional rebase + re-verify in the shared push site.** In
   `_stage_and_push_ci_fixes` (1758), add a 4th `failed_jobs_tsv` param. After
   the `git-commit.sh "Fix CI failure"` (1806-1814) and before `git-push.sh`
   (1823): resolve base (`FORKED_TARGET=true` → `upstream`/`main`, else
   `origin`/`main`; mirrors `ci_common_args` 1644-1651); compute
   `BEHIND=$(kv_value BEHIND_COUNT "$(ci-behind-count.sh --base-remote ...
   --base-ref ...)")` with numeric default `0`; if `BEHIND > 0` set
   `did_rebase=true`, run `run_rebase_rebump "$phase" defer-push "$base_remote"
   "$base_ref"`, refresh `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` from current
   `HEAD`, re-capture dirty-path snapshots, then re-verify
   (`_verify_failed_jobs_locally` + `run_checks_with_lint_fix_loop`) and stage
   the lint delta from the re-captured snapshots. Map re-verify `rc=2` →
   `exit_stall`, `rc=4` → `return 4`, other non-zero → `return 1` (never push an
   unverified tree); set `CI_FIX_REBASE_PENDING=true` only on a failed
   post-rebase verify path. Push `git-force-push.sh` when `did_rebase` or
   `CI_FIX_REBASE_PENDING`; else `git-push.sh`. Clear `CI_FIX_REBASE_PENDING`
   after a successful push.
3. **Vendor start-tier rotation.** Add `start_attempt` to `run_ci_fix_vendor`
   (1831); iterate a rotated `(cursor codex claude)` list (`offset = start_attempt
   % 3`), all tiers eligible; re-key the first-fixer-non-health shortcut
   (1907-1915) on "first iteration of this waterfall" rather than literal
   `cursor`.
4. **Thread attempt index + TSV + verify rc.** In `run_ci_fix_vendor` pass the
   `failed_jobs_tsv` into `_stage_and_push_ci_fixes` (1931) and mirror its `2`/`4`
   returns into the `verify_rc` `case` (1925-1930). In `run_evaluate_failure`
   pass `"$_fix_attempt"` to both `run_ci_fix_vendor` sites (2320, 2341) and
   `"$ci_failed_tsv"` to the per-job `_stage_and_push_ci_fixes` call (2289);
   handle its `2`/`4` returns with the existing `per_job_rc` / `vendor_rc` `case`.

Guard-only reconciliation: `ci-decide.sh` / `run_ci_phase` routing untouched.
After the post-fix rebase the next `ci-wait` poll sees `BEHIND_COUNT=0`, so
`ci-decide.sh` returns `wait`/`evaluate_failure` — the next-poll `ACTION=rebase`
is a natural no-op fallback (no double-rebase).

### Edge cases

- Not behind → no rebase, plain push (unchanged).
- Fork target → base `upstream/main` threaded into both behind-check and
  `run_rebase_rebump`; `run_rebase_rebump` did **not** previously support a
  non-`origin` base (the fork `ACTION=rebase` branch at 3142-3151 is separate) —
  this plan adds that plumbing.
- Rebase conflict → reuses `run_rebase_rebump`'s vendor conflict-resolution and
  `exit_stall`.
- Lint delta after rebase → staged from re-captured post-rebase snapshots.
- `HAS_BUMP=false` → `_run_rebase_rebump_from_step3` already skips the rebump.

### Failure modes

1. Re-verify fails after a deferred rebase (unpushed local rebase): set
   `CI_FIX_REBASE_PENDING` only on the failed verify path so the retry push uses
   force-with-lease (no non-fast-forward rejection); `exit 3` before re-verify
   never leaves the flag set without a verify gate.
2. False `first-fixer-non-health` bail (#3134 class): refresh
   `LAST_STAGE_AND_PUSH_PRE_REFRESH_HEAD` after the rebase.
3. Double-rebase regression: post-fix path leaves the branch current; next poll
   sees `BEHIND_COUNT=0`. Covered by a regression test.

### Testing strategy

- `scripts/test-ci-behind-count.sh` (new): behind/ahead/equal, `--no-fetch`,
  fork base, fail-open on bad ref.
- `scripts/test-ship-pr.sh --section fix-loop` (extend): behind>0 deferred-push +
  re-verify + force-with-lease; behind=0 plain push; re-verify-failure →
  `CI_FIX_REBASE_PENDING` + retry force-with-lease; `BEHIND_COUNT` parsed via
  `kv_value`; fork base threaded; HEAD-snapshot refresh suppresses the false
  no-commit bail; post-rebase `rc=2`→`exit_stall`, `rc=4`→retry; start-tier
  rotation; no second rebase when already current.
- `scripts/test-ci-status.sh` stays green after delegation.
- `bash scripts/relevant-checks.sh` (lint/shellcheck/bash32) on touched scripts;
  `make test-harness-shards-coverage` after the Makefile edit.

## Acceptance

- [ ] The CI-fix post-fix path performs a behind-count check (via the shared
  `ci-behind-count.sh`, not an open-coded `git rev-list`) and conditionally
  rebases onto the correct base — `origin/main`, or `upstream/main` for
  `FORKED_TARGET` — **before** the fix push.
- [ ] `BEHIND` is parsed from the helper's `BEHIND_COUNT=<n>` line via
  `kv_value` (not assigned the raw helper output), with a numeric default of `0`.
- [ ] The rebase reuses `run_rebase_rebump` (rebump + changelog) rather than a
  parallel code path; `git-force-push.sh` (force-with-lease) is used after a
  rebase, plain `git-push.sh` otherwise.
- [ ] After a rebase, failed jobs and lint are re-verified on the rebased tree
  **before** pushing, reusing `_verify_failed_jobs_locally` /
  `run_checks_with_lint_fix_loop`, with post-rebase stage paths re-captured.
- [ ] Post-rebase verify return codes are propagated: `rc=2`→`exit_stall`,
  `rc=4`→retry, `exit 3` preserved; an unverified tree is never pushed.
- [ ] `CI_FIX_REBASE_PENDING` is set only on a failed post-rebase verify path,
  forces force-with-lease on a retry push, and is cleared after a successful push.
- [ ] No false `first-fixer-non-health` bail after a deferred rebase (the
  pre-push HEAD snapshot is refreshed).
- [ ] Fixer re-spawn rotates the waterfall start tier per `_max_fix` attempt with
  all tiers eligible; `_max_fix` / exit-3 `ci-local-unfixable` /
  `first-fixer-non-health` (keyed on first iteration) semantics are preserved.
- [ ] No double-rebase regression with the `ci-decide.sh` `ACTION=rebase` path on
  the following iteration.
- [ ] No duplicated rebase / rebump / lint-fix / behind-count / push logic —
  `ci-behind-count.sh` is extracted and called from both `ci-status.sh` and
  `ship-pr.sh`; shared steps are factored into single helpers.
- [ ] Regression harness updated: `scripts/test-ship-pr.sh` fix-loop cases + new
  `scripts/test-ci-behind-count.sh`; `Makefile` shard registered
  (`make test-harness-shards-coverage` green); `scripts/test-ci-status.sh` green.
- [ ] Docs updated: `docs/workflow-lifecycle.md` and the touched script `.md`
  siblings.
- [ ] `bash scripts/relevant-checks.sh` passes on all touched scripts.

diff_lines: 810
