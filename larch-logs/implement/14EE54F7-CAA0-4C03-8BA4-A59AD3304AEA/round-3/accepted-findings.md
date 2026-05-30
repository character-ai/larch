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


### FINDING_11: defer-push CI-fix rebases consume REBASE_COUNT budget
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Multiple defer-push CI-fix rebases increment `REBASE_COUNT` toward the 20-cap and can stall before ci-wait fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip or separate counter for defer-push CI-fix rebases


### FINDING_17: `ci_fix_push_force_when_behind` does not assert post-rebase job re-verify
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness exercises force-push when behind but not `_verify_failed_jobs_locally` ordering before force-push when a TSV exists after deferred rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add ci-failed-jobs/gh stubs and assert verify ordering before force-push


### FINDING_19: ci-status harness does not assert ci-behind-count delegation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Refactor could restore duplicated rev-list logic in `ci-status.sh` without failing `test-ci-status`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert ci-behind-count.sh is invoked or match child git argv in stub log


### FINDING_2: Fork CI-fix rebump still uses origin/main instead of threaded base
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-parser-quoting-output.txt
- **Severity**: important
- **Concern**: On `FORKED_TARGET` CI-fix with `BEHIND>0`, rebase uses `upstream/main` but `_run_rebase_rebump_from_step3` still runs `git-sync-local-main.sh` without `--base-remote/--base-ref` and the version-regression guard reads `origin/main:.claude-plugin/plugin.json`, producing wrong rebump semantics on fork workflows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pass base_remote/base_ref into git-sync-local-main.sh and the plugin.json regression read in _run_rebase_rebump_from_step3; extend fork harness beyond ci-behind-count args.
  - From cursor-specialist-plan-fidelity-output.txt: Pass --base-remote/--base-ref to git-sync-local-main.sh and use ${base_remote}/${base_ref} in the version-regression guard
  - From dyn-bash-parser-quoting-output.txt: Thread `base_remote`/`base_ref` into `git-sync-local-main.sh` and the version-regression lookup (e.g. `git show "${base_remote}/${base_ref}:.claude-plugin/plugin.json"`), matching `rebase-push.sh`.


### FINDING_20: Vendor rotation test omits `start_attempt>0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Mis-rotation on retry attempts could ship undetected because harness only covers offset 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add harness with _fix_attempt=1 asserting first tier is codex


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


