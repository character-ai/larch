Reviewing the cited code paths to normalize overlapping findings accurately.
Structured aggregator output from the supplied reviewer findings (merged by behavioral risk; severity uses **important** > **latent** > **nit**).

### FINDING_1: Post-rebase retry with `CI_FIX_REBASE_PENDING` can skip re-verify and force-push an unverified tree
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Post-rebase `_verify_failed_jobs_locally` (or lint) can fail with `verify_rc` 4/1, setting `CI_FIX_REBASE_PENDING=true` and returning without push. On the next `_stage_and_push_ci_fixes` call, `ci-behind-count` may report `BEHIND_COUNT=0`, so the `behind > 0` block (deferred rebase + post-rebase re-verify) is skipped while `CI_FIX_REBASE_PENDING` still selects `git-force-push.sh`, publishing a rebased local tree that was not re-verified on retry. Related gap: `CI_FIX_REBASE_PENDING` / `did_rebase` may not survive a failed force-push across retries (plain `git-push` on retry → non-FF rejection).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Post-rebase verify failure re-dispatches full vendor waterfall instead of push-only retry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: After a successful deferred rebase, post-rebase verify can return 4; the outer `_max_fix` loop may run `run_ci_fix_vendor` again (Cursor/Codex/Claude) on an already-rebased, unpushed tree instead of retrying `_stage_and_push_ci_fixes` (or a push-only helper) with `CI_FIX_REBASE_PENDING`. Vendor rotation should apply to pre-rebase verify failures, not post-rebase push/verify retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: Fork CI-fix rebump/classify still keyed to `origin/main` while rebase uses `upstream/main`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: For `FORKED_TARGET`, deferred rebase/rebump threads `base_remote=upstream` / `base_ref=main`, but bump prep (`git-sync-local-main.sh`), `classify-bump` merge-base, and version-regression guards may still use `origin/main`. When upstream is ahead of fork `main`, rebump can mis-classify or apply wrong version correction vs the actual rebase base.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Planned #3210 fix-loop regression coverage largely missing
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance/plan cases for `CI_FIX_REBASE_PENDING` retry, post-rebase verify `rc` 2/4, fork upstream base threading, HEAD refresh after rebase, and double-rebase noop are largely unguarded in `scripts/test-ship-pr.sh`; regressions on these edge paths may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Fix-loop rotation test does not prove `start_attempt > 0` tier rotation
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harness may pass when `tail -1` is `codex` on the first outer attempt (`_fix_attempt=0`), which matches the normal cursor→codex waterfall without exercising `_fix_attempt % 3` start-tier rotation; a broken rotation on the second outer attempt could ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Fix-loop integration tests stub `ci-behind-count.sh`; real fetch/fail-open path under-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `#3210` ship-pr integration cases may stub `ci-behind-count.sh` while the real helper is only exercised in isolation (e.g. `--no-fetch`). `kv_value` parsing or fetch/fail-open behavior on the post-fix push path may not fail CI if regressed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: `ci-behind-count` fail-open `BEHIND_COUNT=0` vs `ci-status` pending on fetch failure
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: On fetch/rev-list errors, `ci-behind-count` can emit `BEHIND_COUNT=0` (fail-open) while `ci-status` treats fetch failure as pending. During CI-fix push, a transient count failure may skip pre-push rebase and plain-push a fix not validated against current main, diverging from `ci-wait` retry semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: `CI_FIX_REBASE_PENDING` is not persisted across `ship-pr` resume
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `CI_FIX_REBASE_PENDING` is a shell global (line ~60), not written to the state file. Resuming `ship-pr` after a failed post-rebase verify may lose the pending flag, leading to inconsistent plain-push vs force-push behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: Empty `failed_jobs_tsv` can skip post-rebase job re-verify when `behind > 0`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `behind > 0`, post-rebase `_verify_failed_jobs_locally` runs only if `failed_jobs_tsv` is non-empty; a vendor path with no TSV may rebase and push without re-running failed job make targets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Behind>0 harness omits post-rebase job re-verify assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Existing behind>0 fix-loop case may not supply a failed-jobs TSV or assert `_verify_failed_jobs_locally` before push on the rebased tree, so regressions in post-rebase job verification go undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: `ci-status` parses `BEHIND_COUNT` with `awk` instead of `kv_value`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Parsing diverges from `ship-pr.sh` contract-stream handling; extra lines or format changes could desync poll vs push interpretations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: `_stage_and_push_ci_fixes` grew into a multi-phase god function
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The CI-fix push pipeline (stage, behind rebase, re-verify, push) is hard to review and extend safely under ongoing #3132 refactor pressure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_13: Vendor rotation only on outer `_fix_attempt`, not after in-call verify failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Waterfall rotation may not match acceptance wording for trying a different fixer before bail when inner post-rebase verify fails once; outer-retry semantics may need documentation or an in-call waterfall retry before return.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_14: `_verify_failed_jobs_locally` exit 3 in post-rebase path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Exit 3 (`ci-local-unfixable`) may terminate `ship-pr` instead of mapping to stall/retry behavior expected on the post-rebase verify path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Behind>0 test omits `base-remote` / `base-ref` assertions
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Fix-loop harness may not assert `--base-remote` / `--base-ref` in `rebase-push-args.txt`, so fork/default base threading regressions could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_16: `test-ci-status` still asserts raw `git rev-list` instead of `ci-behind-count` delegation
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Refactoring `ci-status` to delegate behind-count to `ci-behind-count.sh` could break the contract without failing ship-pr #3210 tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Branch mixes #3210 ship-pr with #3217 anti-poll hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unrelated hook/polling/docs changes bundled with #3210 increase review/revert surface and can distract from or block ship-pr regression focus.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Fork `ACTION=rebase` still bypasses `run_rebase_rebump`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Two fork rebase behaviors may coexist after the CI-fix path enhancement (`ci-wait` / `ci-decide` fork rebase vs new post-fix rebump); fork `ACTION=rebase` should eventually unify under `run_rebase_rebump` when bump plumbing is fixed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Recovery rebase verify ignores fork base remotes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Phase 1–4 resume recovery verify may use `origin/main` on fork instead of threaded `base_remote` / `base_ref` (pre-existing gap).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Fetch-fail semantics differ between `ci-behind-count` and `ci-status`
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `ci-status` pending vs `BEHIND_COUNT=0` fail-open can let post-fix plain-push proceed without rebase while `ci-wait` would retry; pre-existing unless policy moves to fail-closed rebase on count errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] `ci-status` / `ship-pr` behind parsing helpers not shared
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `ci-status` (`awk`) vs `ship-pr` (`kv_value`) parsing divergence is a maintenance hazard when either script is touched again (overlaps in-scope FINDING_11 for the `awk` issue on `ci-status` itself).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] `hook-anti-read-poll.sh` nosession fallback shares poll counters
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Missing session metadata can false-positive poll warnings across unrelated runs; not #3210 scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

---

**Merge notes (for voters, not votes):**
- Input items 1, 24, 26, 37 → **FINDING_1** (same `behind=0` + `CI_FIX_REBASE_PENDING` skip re-verify / persistence-on-failed-push cluster).
- Input items 9, 19 → **FINDING_2** (outer vendor waterfall vs push-only retry — distinct fix from FINDING_1).
- Input items 2, 10, 20, 29, 38 → **FINDING_3**.
- Input items 3, 11, 17, 28, 35 → **FINDING_4**; items 16, 36 → **FINDING_5**.
- Input items 12, 25, 27 → **FINDING_7**; item 23 + 34 → **FINDING_20** / **FINDING_21** (OOS policy vs OOS helper-sharing).
- Input items 7, 13, 22 → **FINDING_17**; items 8, 14 → **FINDING_18**.

All specialist slots used the same boilerplate **Suggested revision** line; substantive fix directions live in the normalized **Concern** text above. No `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` line (non-empty merge).
