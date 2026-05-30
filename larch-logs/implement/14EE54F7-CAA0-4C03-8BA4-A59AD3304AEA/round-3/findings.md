Verifying a few code references so merged findings stay accurate.
Structured aggregator output from the supplied reviewer findings (merged by behavioral risk; severity uses **important** > **latent** > **nit**).

---

### FINDING_1: CI_FIX_REBASE_PENDING retry skips post-rebase verify when BEHIND_COUNT=0
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt, dyn-rebase-dirty-state-output.txt
- **Severity**: important
- **Concern**: Post-rebase verification (`_verify_failed_jobs_locally`, lint loop, TSV guards) runs only inside `if [ "$behind" -gt 0 ]`. After a deferred rebase, the next `_stage_and_push_ci_fixes` call usually has `BEHIND_COUNT=0` while `CI_FIX_REBASE_PENDING` still routes through `git-force-push.sh`, so a pending retry can force-push without re-running failed-job or lint gates. The fix loop’s `per_job_verification_retry` path executes `:` only and does not re-enter `_stage_and_push_ci_fixes` with a push-only pending branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add a CI_FIX_REBASE_PENDING branch at loop start that calls _stage_and_push_ci_fixes with persisted ci-failed-jobs TSV; add a harness asserting force-push without a second rebase-push.
  - From cursor-specialist-correctness-output.txt: Extract and call post-rebase verify helper on pending retries even when behind=0
  - From cursor-specialist-testing-output.txt: Run verify/stage when CI_FIX_REBASE_PENDING even if behind=0; add fix-loop test with post-rebase lint fail then pass on retry
  - From cursor-specialist-security-output.txt: Require successful post-rebase verify before any push when CI_FIX_REBASE_PENDING is set, even if behind==0; otherwise stall.
  - From cursor-specialist-edge-cases-output.txt: Run post-rebase verify whenever CI_FIX_REBASE_PENDING is set, independent of behind count
  - From cursor-specialist-plan-fidelity-output.txt: Add a CI_FIX_REBASE_PENDING branch at the start of the _fix_attempt loop (and for vendor stage_rc=4) that re-calls _stage_and_push_ci_fixes with the persisted failed-jobs TSV
  - From dyn-bash-parser-quoting-output.txt: Extract post-rebase verify into a helper and call it whenever `did_rebase=true` **or** `CI_FIX_REBASE_PENDING=true`, even when `behind=0`; only skip the `run_rebase_rebump` call when already current.
  - From dyn-rebase-dirty-state-output.txt: Factor post-rebase re-verify into a helper invoked whenever `CI_FIX_REBASE_PENDING=true` or `did_rebase=true` on this call, independent of `behind`; require `effective_failed_jobs_tsv` before push; only clear the pending flag after verify passes and push succeeds.

### FINDING_2: Fork CI-fix rebump still uses origin/main instead of threaded base
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt
- **Severity**: important
- **Concern**: On `FORKED_TARGET` CI-fix with `BEHIND>0`, rebase uses `upstream/main` but `_run_rebase_rebump_from_step3` still runs `git-sync-local-main.sh` without `--base-remote/--base-ref` and the version-regression guard reads `origin/main:.claude-plugin/plugin.json`, producing wrong rebump semantics on fork workflows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass base_remote/base_ref into git-sync-local-main.sh and the plugin.json regression read in _run_rebase_rebump_from_step3; extend fork harness beyond ci-behind-count args.
  - From cursor-specialist-plan-fidelity-output.txt: Pass --base-remote/--base-ref to git-sync-local-main.sh and use ${base_remote}/${base_ref} in the version-regression guard
  - From dyn-bash-parser-quoting-output.txt: Thread `base_remote`/`base_ref` into `git-sync-local-main.sh` and the version-regression lookup (e.g. `git show "${base_remote}/${base_ref}:.claude-plugin/plugin.json"`), matching `rebase-push.sh`.

### FINDING_3: Fail-open BEHIND_COUNT=0 on git fetch/rev-list errors
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Transient `git fetch` or `rev-list` failure in `ci-behind-count.sh` emits `BEHIND_COUNT=0`; ship-pr may skip needed rebase and plain-push a fix still behind main, causing extra CI churn or pushing without integrating latest base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Keep fail-open for ci-status; optionally treat diagnostics in ship-pr push path as elevated Warnings or a conservative stall when push-time behind-check fails.
  - From cursor-specialist-security-output.txt: Fail closed on CI-fix push path or emit distinct unknown status; do not treat errors as zero behind.
  - From cursor-specialist-edge-cases-output.txt: Fail closed in CI-fix path or stall with diagnostic

### FINDING_4: Force-push failure after rebase does not persist CI_FIX_REBASE_PENDING
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: When post-rebase verify passes and rebase completes but `git-force-push.sh` fails, the retry may use plain `git-push.sh` against a rebased HEAD and hit non-fast-forward errors because `CI_FIX_REBASE_PENDING` was not set on push failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Set CI_FIX_REBASE_PENDING=true on force-push failure when did_rebase was true before returning

### FINDING_5: Post-rebase verify exit 2/3 does not set CI_FIX_REBASE_PENDING
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Deferred rebase rewrites history; post-rebase `ci-local-unfixable` or other verify failures (including exit 3 where applicable) may return without setting `CI_FIX_REBASE_PENDING`, so the outer loop may plain-push a diverged branch, re-dispatch vendors, or rebase again instead of a controlled pending push/retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Set CI_FIX_REBASE_PENDING on post-rebase verify failures including rc=3 after defer-push rebase
  - From cursor-specialist-edge-cases-output.txt: Set pending and bail with exit 3 without vendor/redundant rebase

### FINDING_6: Dirty working tree on pending retry after aborted post-rebase verify
- **Reviewer(s)**: dyn-rebase-dirty-state-output.txt
- **Severity**: important
- **Concern**: On post-rebase verify failure (`verify_rc=4` or non-zero lint), the function sets `CI_FIX_REBASE_PENDING` and returns without committing lint/per-job deltas from the success branch, leaving an uncommitted dirty tree on the rebased HEAD. A pending retry re-enters `_stage_and_push_ci_fixes` and may run the upfront lint loop again on that dirty tree, double-applying fixes or producing a different delta than the aborted pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-dirty-state-output.txt: On failed post-rebase verify, either commit/stash the captured lint delta before returning, or on pending retry skip the upfront lint loop and re-run only the gated post-rebase verify + targeted staging path; avoid treating aborted-verify dirt as a fresh vendor baseline.

### FINDING_7: `waterfall_iter` not advanced on `wrapper_rc=2` breaks first-fixer rotation semantics
- **Reviewer(s)**: dyn-waterfall-rotation-semantics-output.txt
- **Severity**: important
- **Concern**: `waterfall_iter` increments only on the `record_failure` / `_ci_fix_rollback` path, not when a tier exits with `wrapper_rc=2` (`continue` at validation failure). With `start_attempt=0`, if cursor returns `wrapper_rc=2` and codex returns `wrapper_rc=0` with `LAUNCHER_FAILURE_CLASS=other`, the guard can still see `waterfall_iter=0`, set `BAIL_REASON=first-fixer-non-health`, and skip claude—treating codex as the first fixer though cursor already ran. Pre-#3210 behavior keyed the shortcut to `tier=cursor` only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-rotation-semantics-output.txt: Advance a per-waterfall “tiers attempted” counter for every launched tier (including `wrapper_rc=2` and the claude-unavailable `continue` at 2006–2010), e.g. increment at the end of each loop iteration except the success `break`, and gate `first-fixer-non-health` on that counter being `0` only for the tier that was actually first in the rotated order (or compare `tier` to `tiers[offset]`). Add a fix-loop harness case: cursor `exit 2`, codex `other` → codex must not set `first-fixer-non-health` and claude should still be eligible.

### FINDING_8: Plan-listed regression harness gaps for pending/rebase paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance/plan cases for `CI_FIX_REBASE_PENDING` retry, post-rebase rc=2 stall, fork defer-push rebase argv threading, and pending force-push retry are missing or incomplete in `scripts/test-ship-pr.sh`, allowing production gaps (e.g. pending retry without re-verify) to ship.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fix-loop cases for CI_FIX_REBASE_PENDING retry, rc=2 stall, and fork behind>0 rebase-push --base-remote upstream
  - From cursor-specialist-plan-fidelity-output.txt: Add fix-loop fixtures stubbing verify rc=2/4 and failed force-push with CI_FIX_REBASE_PENDING retry assertions

### FINDING_9: Post-rebase job re-verify skipped when failed_jobs TSV is empty
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: After rebase with `did_rebase=true`, if the failed-jobs TSV is empty or missing, lint-only check may proceed to force-with-lease without re-running failed CI jobs locally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Mandate _resolve_ci_failed_jobs_tsv when did_rebase=true; stall if no jobs to verify.

### FINDING_10: Pre- vs post-rebase verify exit-3 propagation diverges
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Pre-rebase verify exit 3 may kill ship-pr while post-rebase verify exit 3 in a subshell becomes return 1 and retries, diverging from planned exit-3 preservation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Align exit-3 propagation or document and test intentional subshell behavior

### FINDING_11: defer-push CI-fix rebases consume REBASE_COUNT budget
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Multiple defer-push CI-fix rebases increment `REBASE_COUNT` toward the 20-cap and can stall before ci-wait fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip or separate counter for defer-push CI-fix rebases

### FINDING_12: Duplicate BEHIND_COUNT parsing between ci-status and ship-pr
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `ci-status.sh` parses `BEHIND_COUNT` with awk while ship-pr uses `kv_value`; future emit format changes could desync ci-wait gating from ship-pr push gating.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Share kv_value parsing or a tiny behind-count-parse helper used by both scripts.
  - From cursor-specialist-plan-fidelity-output.txt: Optionally use kv_value for parity with ship-pr

### FINDING_13: Large inline post-rebase block in `_stage_and_push_ci_fixes`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The rebase→reverify→stage→push sequence is hard to review and test in isolation inside one large inline block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a named helper for post-rebase reverify/stage; keep single push call site.

### FINDING_14: #3175 anti-polling work bundled with #3210 on same branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unrelated hook/AGENTS changes ship in the same branch as CI-fix sequencing, forcing reviewers to validate out-of-scope surface to approve #3210.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split commits/PR sections or document explicit scope boundaries in PR summary.

### FINDING_15: run-logs.md update cited in plan but absent on branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance cites a run-logs doc update; branch omits it, so the run-logs contract may be stale relative to new CI-fix push sequencing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add run-logs note or remove criterion from issue

### FINDING_16: Inconsistent CI_FIX_REBASE_PENDING mutation style
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Push/verify paths mix direct `CI_FIX_REBASE_PENDING=` assignment with calls to an undefined `_ci_fix_rebase_pending_set` helper in some revisions, complicating review and risking runtime errors if helper calls land without a definition.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Unify through one setter once defined

### FINDING_17: `ci_fix_push_force_when_behind` does not assert post-rebase job re-verify
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness exercises force-push when behind but not `_verify_failed_jobs_locally` ordering before force-push when a TSV exists after deferred rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ci-failed-jobs/gh stubs and assert verify ordering before force-push

### FINDING_18: No harness for fetch-failure fail-open in ci-behind-count
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Fetch failure always yields `BEHIND_COUNT=0` without regression coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub git fetch failure; assert BEHIND_COUNT=0 and diagnostic stderr

### FINDING_19: ci-status harness does not assert ci-behind-count delegation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Refactor could restore duplicated rev-list logic in `ci-status.sh` without failing `test-ci-status`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert ci-behind-count.sh is invoked or match child git argv in stub log

### FINDING_20: Vendor rotation test omits `start_attempt>0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Mis-rotation on retry attempts could ship undetected because harness only covers offset 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add harness with _fix_attempt=1 asserting first tier is codex

### FINDING_21: Weak charset validation on ci-behind-count base CLI args
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Pathological `base_remote`/`base_ref` strings reach git without the validation used in `run_rebase_rebump`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Share _validate_rebase_base_remote_ref or disallow .. and unsafe ref characters.

### FINDING_22: Anti-poll hook splits Bash operators without quote awareness
- **Reviewer(s)**: dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: `bash_line_task_output_poll_token` splits on literal `;`, `&&`, and `||` without respecting quotes, fracturing segments inside quoted strings and weakening detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parser-quoting-output.txt: Either document this as best-effort and add harness cases for quoted-operator edge cases, or replace the splitter with a quote-aware scanner (even a small state machine over `'"`\`).

### FINDING_23: Anti-poll hook narrow read-verb / path coverage
- **Reviewer(s)**: dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: Only `cat|tail|head|less|more` and a narrow `sed -n` pattern count; paths via `$var`, `read`, `awk`, `python`, etc. are false negatives (e.g. `TASK=tasks/foo.output; cat "$TASK"`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parser-quoting-output.txt: Expand verb coverage conservatively and/or resolve simple `"$VAR"` expansions when the assignment appears earlier in the same line; at minimum document unsupported shapes in `scripts/hook-anti-read-poll.md`.

### FINDING_24: Anti-poll hook tracks only first qualifying segment per invocation
- **Reviewer(s)**: dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: `bash_line_task_output_poll_token` returns the first matching segment and `extract_bash_task_output_poll_token` only considers the first line, so `cat tasks/A.output; cat tasks/B.output` under-counts alternating reads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parser-quoting-output.txt: Either scan all segments (and optionally all lines) and increment counters per distinct `tasks/<id>.output` token, or document that only the leftmost qualifying segment per Bash invocation is tracked.

---

### OOS_1: [OUT_OF_SCOPE] Uncommitted `_ci_fix_rebase_pending_set` calls without definition
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt, dyn-rebase-dirty-state-output.txt
- **Severity**: important
- **Concern**: Working-tree / uncommitted edits call `_ci_fix_rebase_pending_set` at `scripts/ship-pr.sh:1886,1956,1962` (or equivalent) but no such function exists in the repo; successful push paths would log “command not found” and may leave `CI_FIX_REBASE_PENDING` stuck true, skewing later push routing in the same process.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Define _ci_fix_rebase_pending_set (or use direct assignment) at all three call sites
  - From cursor-specialist-testing-output.txt: Define _ci_fix_rebase_pending_set or inline assignments; add a harness asserting the flag clears after successful force-push
  - From cursor-specialist-edge-cases-output.txt: Define the helper or assign CI_FIX_REBASE_PENDING directly; add regression coverage for clear-on-success
  - From cursor-specialist-plan-fidelity-output.txt: Define the helper or keep direct CI_FIX_REBASE_PENDING assignment
  - From dyn-bash-parser-quoting-output.txt: Uncommitted edits to `scripts/ship-pr.sh` (not in commit `1e8effa87`) call `_ci_fix_rebase_pending_set` at `scripts/ship-pr.sh:1886,1956,1962` but no such function is defined anywhere in the repo; those paths would fail at runtime until replaced with `CI_FIX_REBASE_PENDING=…` assignments or a real helper.
  - From dyn-rebase-dirty-state-output.txt: Either define `_ci_fix_rebase_pending_set` (if persistence was intended) or replace all three calls with direct `CI_FIX_REBASE_PENDING=true/false` assignments matching the diff’s original `CI_FIX_REBASE_PENDING=false` at push success.

### OOS_2: [OUT_OF_SCOPE] Deliberate fail-open BEHIND_COUNT=0 (pre-existing / plan tradeoff)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: `ci-behind-count.sh` fail-open to `BEHIND_COUNT=0` on fetch/rev-list errors is an accepted design tradeoff; transient failures can skip needed rebase before push.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Pre-existing design tradeoff; monitor if needed
  - From cursor-specialist-testing-output.txt: Document operational risk; optional metric/alert on fail-open warnings
  - From dyn-bash-parser-quoting-output.txt: `scripts/ci-behind-count.sh` fail-open to `BEHIND_COUNT=0` on fetch/`rev-list` errors is deliberate; it can skip a needed rebase under transient git failures (accepted tradeoff per plan).

### OOS_3: [OUT_OF_SCOPE] #3175 hook/doc work bundled with #3210
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt
- **Severity**: latent
- **Concern**: Anti-polling hook expansion (`hook-anti-read-poll.sh`, `AGENTS.md`, `orchestrator-never.md`, etc.) ships on the same branch as #3210 CI-fix work, increasing review/merge surface and conflicting with single-feature PR policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Track as separate change or split PR if policy requires single-feature diffs
  - From cursor-specialist-plan-fidelity-output.txt: Track/review under its own issue
  - From dyn-bash-parser-quoting-output.txt: Branch also bundles unrelated `#3175` hook/doc work (`scripts/hook-anti-read-poll.sh`, `AGENTS.md`, `skills/shared/orchestrator-never.md`) via commit `2fc05d968`; the `#3210` core is commit `1e8effa87` (13 files).

### OOS_4: [OUT_OF_SCOPE] `git-force-push.sh` hardcodes `origin`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Fork/upstream rebase may not align force-push remote with rebase base; pre-existing limitation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pre-existing; thread base remote into git-force-push when fixing fork paths.

### OOS_5: [OUT_OF_SCOPE] nosession bucket shares poll counters across sessions
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Missing session metadata causes false shared reminders in `hook-anti-read-poll.md` nosession bucket.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Documented limitation; optional stricter session binding later.

### OOS_6: [OUT_OF_SCOPE] Pre-push vendor verify failure without CI_FIX_REBASE_PENDING
- **Reviewer(s)**: dyn-rebase-dirty-state-output.txt
- **Severity**: latent
- **Concern**: When `run_ci_fix_vendor` returns `4` from pre-push `_verify_failed_jobs_locally` (before `_stage_and_push_ci_fixes`), `CI_FIX_REBASE_PENDING` is not set; outer retries may re-dispatch with prior uncommitted verify deltas preserved by `_ci_fix_rollback`. Adjacent to scout scope, not introduced by deferred-rebase path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-dirty-state-output.txt: **risk-integration** `scripts/ship-pr.sh:2061-2066,2508-2511` — When `run_ci_fix_vendor` returns `4` from pre-push `_verify_failed_jobs_locally` (before `_stage_and_push_ci_fixes`), `CI_FIX_REBASE_PENDING` is not set; the next outer attempt can call `run_ci_fix_vendor` again with a new baseline that includes the prior attempt’s uncommitted verify deltas, and `_ci_fix_rollback` (1733–1777) will preserve those paths across tier failures. That is adjacent to the scout prompt but not introduced by the deferred-rebase path (which correctly avoids re-entering the vendor waterfall while pending).

### OOS_7: [OUT_OF_SCOPE] Harness passes without asserting re-verify on pending retry
- **Reviewer(s)**: dyn-rebase-dirty-state-output.txt
- **Severity**: latent
- **Concern**: `ci_fix_no_double_rebase_pending_retry` asserts no second rebase when `BEHIND_COUNT=0` on retry but does not assert `_verify_failed_jobs_locally` runs on the pending retry, so the harness can pass while the production gap remains.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-rebase-dirty-state-output.txt: **architecture** `scripts/test-ship-pr.sh:5261-5367` — `ci_fix_no_double_rebase_pending_retry` asserts no second rebase when `BEHIND_COUNT=0` on retry, but does not assert that `_verify_failed_jobs_locally` runs on the pending retry; the harness can pass while the production gap above remains.

### OOS_8: [OUT_OF_SCOPE] Intentional conservative anti-poll warnings under short-circuit
- **Reviewer(s)**: dyn-bash-parser-quoting-output.txt
- **Severity**: nit
- **Concern**: Conservative Bash warnings (e.g. `test -f x || cat tasks/….output`) may fire even when short-circuiting would skip the read; matches warn-on-suspicious-syntax posture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-parser-quoting-output.txt: Intentional conservative Bash warnings (e.g. `test -f x || cat tasks/….output`, `echo 'waiting' || cat …` in `scripts/test-hook-anti-read-poll.sh`) may fire even when short-circuiting would skip the read; that matches a “warn on suspicious syntax” posture rather than exact shell semantics.

### OOS_9: [OUT_OF_SCOPE] `start_attempt` timing — no bug found
- **Reviewer(s)**: dyn-waterfall-rotation-semantics-output.txt
- **Severity**: nit
- **Concern**: Reviewer reports `start_attempt` passed as current `$_fix_attempt` before end-of-iteration increment matches intended rotation; no timing bug found.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-rotation-semantics-output.txt: **correctness** `scripts/ship-pr.sh:2511,2532,2555` — `start_attempt` is passed as the current `$_fix_attempt` before the end-of-iteration increment at 2555, so the first outer retry uses `0` (cursor-first) and the second uses `1` (codex-first), matching `ci_fix_vendor_rotation_start_attempt`; no timing bug found there.

### OOS_10: [OUT_OF_SCOPE] Stale `ship-pr.md` waterfall paragraph vs rotation invariant
- **Reviewer(s)**: dyn-waterfall-rotation-semantics-output.txt
- **Severity**: nit
- **Concern**: Recovery waterfall paragraph still describes first-fixer shortcut as “when the **first** tier (`cursor`) fails…”, conflicting with Invariants text for rotated first tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-rotation-semantics-output.txt: **code-quality** `scripts/ship-pr.md:108` vs `scripts/ship-pr.md:140-142` — The Recovery waterfall paragraph still describes the shortcut as “when the **first** tier (`cursor`) fails…”, while the Invariants section documents rotation and “first tier of the rotated list”; the stale paragraph conflicts with the implementation intent and the newer invariant text.

---

**Merge notes (for voters, not part of machine output):**

- Input items **8, 15, 29, 52** (undefined `_ci_fix_rebase_pending_set` on committed paths) were folded into **OOS_1** where reviewers tagged uncommitted/WIP state; the committed tree in this workspace uses direct `CI_FIX_REBASE_PENDING=` assignment and has no `_ci_fix_rebase_pending_set` symbol.
- **FINDING_4** (push failure pending) complements **FINDING_1** but stays separate because the fix differs (set flag on push failure vs re-run verify on retry).
- Reviewer-only “no bug” observations (**57**) are captured as **OOS_9** for traceability; voters may treat as informational.
- Slots that only said “Address the concern above” are omitted per aggregator rules; substantive fix text is taken from each reviewer’s concern or explicit suggested-fix paragraphs.
