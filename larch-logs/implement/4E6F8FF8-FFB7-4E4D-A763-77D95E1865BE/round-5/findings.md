### FINDING_1: code-quality: skills/design/scripts/test-trailer-awk.sh:37-42
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] assert_eq_lines exits directly instead of using shared fail() helper Inconsistent failure formatting vs test-gate-b-dedup-plan.sh and test-trailer-helpers.sh makes triage slightly harder when mixing harness output Delegate assertion failures to fail() after formatting got/want
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/test-trailer-awk.sh:18-21
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dead shift in write_fixture after taking name Misleading API shape for future editors who might expect additional positional fixture args Remove the unused shift
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/test-trailer-awk.sh:14-16
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] trailer_nr() duplicates _plan_optional_trailer_nr() without sync comment If last-non-empty-line semantics change in lib-plan-optional-trailers.sh only, awk unit tests and production wrappers diverge silently Add must-stay-in-sync comment or extract shared one-liner
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-trailer-*.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Thin wrapper adapters unchanged; overlap with integration fixtures in test-gate-b-dedup-plan.sh Not introduced by this branch; plan scoped awk harness only Consolidate fixtures only if a future refactor explicitly targets harness DRY
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-trailer-helpers.sh:43
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] test-trailer-awk.sh invoked after slower adapter tests Awk failures reported later in make test-trailer-helpers output Optionally run test-trailer-awk.sh first for fail-fast (not plan-required)
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `skills/design/scripts/test-trailer-awk.sh` — No fixture with only `diff_deleted:` (no `diff_added`). `diff_deleted` is still exercised in `all-three-present`, `retain-010`, and `octal-rejected`; a deletion-only regression would need to break the shared `diff_deleted` branch, not just interaction with `diff_added`. **Suggested fix:** optional `diff_deleted-only` fixture if you want symmetric coverage; not required by the plan.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Branch diff also includes **#3209** (`ship-pr.sh` pre-rebase `larch-logs/` fixup), **#3212** (cleanup), and **review-and-fix** changes — outside the #3204 implementation plan; not reviewed here beyond noting they share the PR.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. Branch diff also includes **#3209** (`ship-pr.sh` pre-rebase `larch-logs/` fixup), **#3212** (cleanup), and **review-and-fix** changes — outside the #3204 implementation plan; not reviewed here beyond noting they share the PR.
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: skills/design/scripts/test-trailer-awk.sh:76-219
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No diff_deleted-only fixture; diff_deleted always paired with diff_added in tests. A regression that only breaks diff_deleted parsing when diff_added is absent could pass keys/values/has_key on combined fixtures while check-plan-size or preservation logic fails on deletion-only plans. Add a diff_deleted-only fixture and assert parse/keys/values/has_key per plan edge-case intent.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/design/scripts/test-trailer-awk.md:13-17
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Contract omits blank-before-diff-lines case documented in plan block-boundary edge case. Future editors may remove the blank-line fixture thinking it is redundant with boundary-orphan-only. Mention blank-before-diff-lines in the block-boundary section of test-trailer-awk.md.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] risk-integration: skills/cleanup/scripts/cleanup.sh:36-52
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] find-failure return path (rc=2) untested in new test-cleanup.sh. A broken find under a session dir might skip deletion without a harness catching unintended behavior change. Not #3204 scope; add a stubbed find-failure scenario to test-cleanup.sh under #3212.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] architecture: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Multi-issue PR bundles unrelated harness and production changes. CI failure or bisect on trailer work requires disentangling ship-pr/cleanup/review-and-fix commits. Prefer stacked PRs or clearer commit boundaries when possible.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/test-trailer-*.sh (pre-existing)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Wrapper adapters still lack parse/octal/mech coverage. .sh wrapper regressions could slip if only test-trailer-awk.sh is run in isolation during local dev. Awareness only; awk harness is the intended new guard per plan.
- **Suggested revision**: Address the concern above.

### FINDING_13: `test-trailer-awk.sh` covers all four awk modes and the normative edge cases from the plan: `block_len` vs distinct keys (duplicate `diff_added:`), last-match-wins, `08`/`09` rejection vs `010` retention, `mechanical_churn` true/false, block boundary, blank-line boundary, and no-trailers.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `test-trailer-awk.sh` covers all four awk modes and the normative edge cases from the plan: `block_len` vs distinct keys (duplicate `diff_added:`), last-match-wins, `08`/`09` rejection vs `010` retention, `mechanical_churn` true/false, block boundary, blank-line boundary, and no-trailers.
- **Suggested revision**: Address the concern above.

### FINDING_14: Expected `has_key` exit **1** probes use `set +e` / `set -e` with explicit `rc` checks; the round-4 split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1) matches awk semantics and is documented in `test-trailer-awk.md`.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Expected `has_key` exit **1** probes use `set +e` / `set -e` with explicit `rc` checks; the round-4 split (`block-boundary` rc=0 vs `boundary-orphan-only` / `blank-before-diff-lines` rc=1) matches awk semantics and is documented in `test-trailer-awk.md`.
- **Suggested revision**: Address the concern above.

### FINDING_15: `(3175)` pins replace weak `snapshot` substrings with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` (BSD-safe); preservation greps at 404–405, 409–410, 412–415 are untouched.
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `(3175)` pins replace weak `snapshot` substrings with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'` (BSD-safe); preservation greps at 404–405, 409–410, 412–415 are untouched.
- **Suggested revision**: Address the concern above.

### FINDING_16: Harness is `100755` and invoked from `test-trailer-helpers.sh` (existing `make test-trailer-helpers` / shard-12 path; no orphan shard target needed).
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - Harness is `100755` and invoked from `test-trailer-helpers.sh` (existing `make test-trailer-helpers` / shard-12 path; no orphan shard target needed).
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **correctness** `branch vs main` — The branch diff vs `main` also ships #3212 (`skills/cleanup/`), #3209 (`scripts/ship-pr.sh`, `scripts/test-ship-pr.sh`), `skills/review-and-fix/`, plugin version/docs bumps, and a `chore(larch-logs)` flush. None of those appear in the #3204 plan’s file list; they are separate issues bundled on the same branch, not gaps in the #3204 implementation itself.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] **nit** `skills/design/scripts/test-trailer-awk.sh:221` — The plan text asks for an explicit trailing `exit 0` after `PASS`; the harness relies on `echo`’s zero exit status. Behavior is equivalent under `set -e`. **Suggested fix:** Add `exit 0` only if you want literal plan wording match (optional).
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **nit** `skills/design/scripts/test-trailer-awk.sh:221` — The plan text asks for an explicit trailing `exit 0` after `PASS`; the harness relies on `echo`’s zero exit status. Behavior is equivalent under `set -e`. **Suggested fix:** Add `exit 0` only if you want literal plan wording match (optional).
- **Suggested revision**: Address the concern above.

### FINDING_19: **correctness** `skills/cleanup/scripts/cleanup.sh:36-51` — In `entry_has_fresh_descendant`, the pipeline `find … | grep -q .` is followed by `local rc=$?` and then `find_rc=${PIPESTATUS[0]:-1}`. Bash resets `PIPESTATUS` on each simple command, so `PIPESTATUS[0]` after `local` is the exit status of `local` (almost always 0), not `find`. The `return 2` branch (`find_rc -ne 0`) is therefore effectively dead: a failed descendant probe is indistinguishable from “no fresh descendant” and returns 1. Callers treat only `0|2` as skip (`case "$_fresh_rc" in 0|2) continue ;; esac` at lines 72–74 and 128–130), so a `find` failure on a stale top-level session/tmp entry can still lead to `rm -rf` instead of the documented conservative skip. **Suggested fix:** Capture pipeline status before any other command, e.g. run the pipeline, then immediately `find_rc=${PIPESTATUS[0]:-1}` and `rc=${PIPESTATUS[1]:-1}` (or `_ps=("${PIPESTATUS[@]}")`), then branch on those values; only use `local` afterward.
- **Reviewer**: dyn-bash-pipestatus-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:36-51` — In `entry_has_fresh_descendant`, the pipeline `find … | grep -q .` is followed by `local rc=$?` and then `find_rc=${PIPESTATUS[0]:-1}`. Bash resets `PIPESTATUS` on each simple command, so `PIPESTATUS[0]` after `local` is the exit status of `local` (almost always 0), not `find`. The `return 2` branch (`find_rc -ne 0`) is therefore effectively dead: a failed descendant probe is indistinguishable from “no fresh descendant” and returns 1. Callers treat only `0|2` as skip (`case "$_fresh_rc" in 0|2) continue ;; esac` at lines 72–74 and 128–130), so a `find` failure on a stale top-level session/tmp entry can still lead to `rm -rf` instead of the documented conservative skip. **Suggested fix:** Capture pipeline status before any other command, e.g. run the pipeline, then immediately `find_rc=${PIPESTATUS[0]:-1}` and `rc=${PIPESTATUS[1]:-1}` (or `_ps=("${PIPESTATUS[@]}")`), then branch on those values; only use `local` afterward.
- **Suggested revision**: Address the concern above.

### FINDING_20: **correctness** `skills/cleanup/scripts/test-cleanup.sh:119-275` — The branch removes the former `find-failure-skips-deletion` case (see `test-cleanup.md` diff: that bullet is gone) and adds depth/bounded-freshness cases, but nothing exercises `entry_has_fresh_descendant`’s `return 2` or proves that a per-entry `find` failure keeps the directory. With the `PIPESTATUS` ordering bug above, that gap means the regression can ship without failing CI. **Suggested fix:** Restore a focused harness case (e.g. unreadable subdirectory or a stub `find` on `PATH` for one entry) that expects the entry to remain and `CACHE_REMOVED=0`, and fix `cleanup.sh` first so `return 2` is reachable.
- **Reviewer**: dyn-bash-pipestatus-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/test-cleanup.sh:119-275` — The branch removes the former `find-failure-skips-deletion` case (see `test-cleanup.md` diff: that bullet is gone) and adds depth/bounded-freshness cases, but nothing exercises `entry_has_fresh_descendant`’s `return 2` or proves that a per-entry `find` failure keeps the directory. With the `PIPESTATUS` ordering bug above, that gap means the regression can ship without failing CI. **Suggested fix:** Restore a focused harness case (e.g. unreadable subdirectory or a stub `find` on `PATH` for one entry) that expects the entry to remain and `CACHE_REMOVED=0`, and fix `cleanup.sh` first so `return 2` is reachable.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] **#3204 (trailer awk harness):** `test-trailer-awk.sh`, tightened `(3175)` pins in `scripts/test-design-structure.sh`, `test-trailer-helpers.sh` wiring, and the new `.md` contracts align with `lib-plan-optional-trailers.awk` (including `block_len`, last-match-wins, octal `08`/`09`, and `set +e` around expected `has_key` failures). `lib-plan-optional-trailers.awk` / `.sh` are unchanged in the diff.
- **Reviewer**: dyn-bash-pipestatus-output.txt
- **Concern**: - **#3204 (trailer awk harness):** `test-trailer-awk.sh`, tightened `(3175)` pins in `scripts/test-design-structure.sh`, `test-trailer-helpers.sh` wiring, and the new `.md` contracts align with `lib-plan-optional-trailers.awk` (including `block_len`, last-match-wins, octal `08`/`09`, and `set +e` around expected `has_key` failures). `lib-plan-optional-trailers.awk` / `.sh` are unchanged in the diff.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] **`cleanup.sh` behavior change:** Removal of the epoch/`date +%s` cutoff and the `date-failure-errors` harness case is a separate behavior shift (now relies on `find -mtime`); not tied to the `PIPESTATUS` defect.
- **Reviewer**: dyn-bash-pipestatus-output.txt
- **Concern**: - **`cleanup.sh` behavior change:** Removal of the epoch/`date +%s` cutoff and the `date-failure-errors` harness case is a separate behavior shift (now relies on `find -mtime`); not tied to the `PIPESTATUS` defect.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] **Other branch commits** (`ship-pr.sh` #3209 pre-rebase `larch-logs/` fixup, `review-and-fix.sh` coder delta staging): no additional correctness issues identified in this pass beyond the cleanup probe bug above.
- **Reviewer**: dyn-bash-pipestatus-output.txt
- **Concern**: - **Other branch commits** (`ship-pr.sh` #3209 pre-rebase `larch-logs/` fixup, `review-and-fix.sh` coder delta staging): no additional correctness issues identified in this pass beyond the cleanup probe bug above. **Commits on branch (since `main`):** `d33cdfb70` (#3204), `a8183aa1c` (#3212 cleanup), `c45f52e55` (#3209 ship-pr), plus review/lint follow-ups.
- **Suggested revision**: Address the concern above.

### FINDING_24: **risk-integration** `skills/cleanup/scripts/cleanup.sh:36-75` — The cache age pass selects candidates with `find … -mtime +"$RETENTION_DAYS"` (strictly older than N 24-hour blocks), but `entry_has_fresh_descendant` treats “fresh” as `find … -mtime "-${RETENTION_DAYS}"` (strictly younger than N blocks). On BSD/macOS `find`, an entry whose mtime falls in the exactly-N block matches neither `+N` nor `-N`. Top-level dirs at exactly N days are not age-listed (safe), but a dir with stale top-level mtime in the `+N` set and a descendant whose last write is in that same N-day block is classified as having no fresh descendant and is `rm -rf`’d. The prior epoch cutoff (`newest < NOW - N*86400`) kept such sessions when `newest` was still on the retention side of the cutoff. Harness fixtures only use extreme `touch -t` stamps (`200001010000` / `209901010000`), so this boundary is neither tested nor documented in `cleanup.md`. **Suggested fix:** Make the freshness probe the logical complement of the stale predicate (e.g. `find "$entry" … ! -mtime +"$RETENTION_DAYS" -print -quit` instead of `-mtime "-${RETENTION_DAYS}"`), or restore a single shared epoch cutoff for both passes; add a harness case that seeds a stale parent and a child at the N-day boundary and document 24-hour rounding in `cleanup.md` / `SECURITY.md`.
- **Reviewer**: dyn-mtime-find-platform-output.txt
- **Concern**: - **risk-integration** `skills/cleanup/scripts/cleanup.sh:36-75` — The cache age pass selects candidates with `find … -mtime +"$RETENTION_DAYS"` (strictly older than N 24-hour blocks), but `entry_has_fresh_descendant` treats “fresh” as `find … -mtime "-${RETENTION_DAYS}"` (strictly younger than N blocks). On BSD/macOS `find`, an entry whose mtime falls in the exactly-N block matches neither `+N` nor `-N`. Top-level dirs at exactly N days are not age-listed (safe), but a dir with stale top-level mtime in the `+N` set and a descendant whose last write is in that same N-day block is classified as having no fresh descendant and is `rm -rf`’d. The prior epoch cutoff (`newest < NOW - N*86400`) kept such sessions when `newest` was still on the retention side of the cutoff. Harness fixtures only use extreme `touch -t` stamps (`200001010000` / `209901010000`), so this boundary is neither tested nor documented in `cleanup.md`. **Suggested fix:** Make the freshness probe the logical complement of the stale predicate (e.g. `find "$entry" … ! -mtime +"$RETENTION_DAYS" -print -quit` instead of `-mtime "-${RETENTION_DAYS}"`), or restore a single shared epoch cutoff for both passes; add a harness case that seeds a stale parent and a child at the N-day boundary and document 24-hour rounding in `cleanup.md` / `SECURITY.md`.
- **Suggested revision**: Address the concern above.

### FINDING_25: **risk-integration** `skills/cleanup/scripts/cleanup.sh:63-79` — The cache pass now enumerates every top-level non-symlink (`! -type l`) and may `rm -rf` it after the descendant probe, whereas the removed `should_remove_by_age` required `[[ -d "$entry" && ! -L "$entry" ]]`. A stale regular file, fifo, or other non-directory directly under `larch/sessions/` would now be deleted; the old path never removed non-directories. **Suggested fix:** Restore an explicit `[[ -d "$entry" ]]` guard (or `find … -type d`) before `entry_has_fresh_descendant` / `rm -rf` on the cache pass, matching the documented “session directory” contract and prior behavior.
- **Reviewer**: dyn-mtime-find-platform-output.txt
- **Concern**: - **risk-integration** `skills/cleanup/scripts/cleanup.sh:63-79` — The cache pass now enumerates every top-level non-symlink (`! -type l`) and may `rm -rf` it after the descendant probe, whereas the removed `should_remove_by_age` required `[[ -d "$entry" && ! -L "$entry" ]]`. A stale regular file, fifo, or other non-directory directly under `larch/sessions/` would now be deleted; the old path never removed non-directories. **Suggested fix:** Restore an explicit `[[ -d "$entry" ]]` guard (or `find … -type d`) before `entry_has_fresh_descendant` / `rm -rf` on the cache pass, matching the documented “session directory” contract and prior behavior.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] **`rm -rf` on plain `/tmp` files** (`skills/cleanup/scripts/cleanup.sh:132-133`): Replacing `rm -f` with `rm -rf` for stale pattern files is semantically safe on the repo’s macOS/Linux targets (`rm -rf` on a non-directory removes the file only). No issue.
- **Reviewer**: dyn-mtime-find-platform-output.txt
- **Concern**: - **`rm -rf` on plain `/tmp` files** (`skills/cleanup/scripts/cleanup.sh:132-133`): Replacing `rm -f` with `rm -rf` for stale pattern files is semantically safe on the repo’s macOS/Linux targets (`rm -rf` on a non-directory removes the file only). No issue.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] **Issue #3204 trailer work** (`skills/design/scripts/test-trailer-awk.sh`, `test-trailer-helpers.sh`, `scripts/test-design-structure.sh`): The awk harness uses the prescribed `set +e` / `set -e` pattern for expected `has_key` failures, is wired through `test-trailer-helpers.sh`, and the `(3175)` pins correctly use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'`. `lib-plan-optional-trailers.awk` / `.sh` are absent from the diff (byte-stable as planned). Low integration risk for that slice.
- **Reviewer**: dyn-mtime-find-platform-output.txt
- **Concern**: - **Issue #3204 trailer work** (`skills/design/scripts/test-trailer-awk.sh`, `test-trailer-helpers.sh`, `scripts/test-design-structure.sh`): The awk harness uses the prescribed `set +e` / `set -e` pattern for expected `has_key` failures, is wired through `test-trailer-helpers.sh`, and the `(3175)` pins correctly use `grep -Fq -- '--snapshot-trailers'` / `'--dedup'`. `lib-plan-optional-trailers.awk` / `.sh` are absent from the diff (byte-stable as planned). Low integration risk for that slice.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] **Bundled non-#3204 commits** on this branch (`ship-pr.sh`, `review-and-fix.sh`, etc.) are outside the `mtime-find-platform` scout scope; not reviewed here beyond noting they share the same diff artifact.
- **Reviewer**: dyn-mtime-find-platform-output.txt
- **Concern**: - **Bundled non-#3204 commits** on this branch (`ship-pr.sh`, `review-and-fix.sh`, etc.) are outside the `mtime-find-platform` scout scope; not reviewed here beyond noting they share the same diff artifact.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] **Removed `date +%s` fail-closed path**: Cleanup no longer refuses all deletions when epoch time is unavailable; `test-cleanup` dropped `date-failure-errors`. That is a deliberate posture change on the #3212 cleanup rewrite, not introduced by the trailer harness work.
- **Reviewer**: dyn-mtime-find-platform-output.txt
- **Concern**: - **Removed `date +%s` fail-closed path**: Cleanup no longer refuses all deletions when epoch time is unavailable; `test-cleanup` dropped `date-failure-errors`. That is a deliberate posture change on the #3212 cleanup rewrite, not introduced by the trailer harness work.
- **Suggested revision**: Address the concern above.

