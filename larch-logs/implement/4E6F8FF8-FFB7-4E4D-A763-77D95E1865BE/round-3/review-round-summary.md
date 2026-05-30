# Review Round 3

- Mode: `diff`
- 12 accepted, 7 rejected (4 exonerated)

## Accepted Findings

### FINDING_1: code-quality: skills/design/scripts/test-trailer-awk.sh:168-176
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] keys mode is not asserted on duplicate-diff-added or block-boundary fixtures. A keys-only awk regression (duplicate key lines or wrong order on split blocks) could pass while parse/values/has_key still pass. Add assert_keys for duplicate-diff-added (single diff_added) and block-boundary (diff_added only).
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: skills/design/scripts/test-trailer-awk.sh:176-177
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] has_key absent-key coverage on none-present only probes diff_added not diff_deleted/mechanical_churn. Regression in has_mech/has_deleted clearing could pass keys/parse while has_key for those keys wrongly returns 0. Add assert_has_key none-present diff_deleted 1 and mechanical_churn 1.
- **Suggested revision**: Address the concern above.


### FINDING_14: architecture: skills/cleanup/scripts/cleanup.sh:99-111
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] /tmp cleanup lost descendant freshness guard present in pre-change should_remove_by_age. Long /implement claude-implement-* dir with stale top-level mtime but recently touched nested logs/state is removed while still in use; cache dirs with same shape are kept. Apply cache-style fresh-descendant skip (or subtree mtime) for /tmp directory matches; add regression test under LARCH_TEST_TMP_ROOT.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: skills/cleanup/scripts/cleanup.sh:32-36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cache_entry_has_fresh_descendant treats find errors as no fresh files. find fails inside an old-looking session dir; entry is rm -rf'd despite possible active work; old code warned and skipped. Fail closed on find errors: warn and skip removal instead of empty-pipe false negative.
- **Suggested revision**: Address the concern above.


### FINDING_22: **correctness** `skills/cleanup/scripts/cleanup.sh:99-109` — The `/tmp` pass deletes every top-level match with `-mtime +N` and never calls `cache_entry_has_fresh_descendant` (or any equivalent), while the cache pass at lines 47–59 skips removal when any descendant was touched inside the retention window. `scripts/session-setup.sh` still falls back to `/tmp/claude-implement-*` when the cache root is unavailable (lines 264–270), and parent-directory mtimes are not reliably bumped when nested session files are written (the design notes for #3212 call this out for APFS). A long-running `/implement` in `/tmp` can therefore be `rm -rf`'d while still writing under `larch-logs/` or similar, even though the same layout under `~/.cache/larch/sessions/` would be kept — a behavioral regression versus the pre-#3212 depth-5 activity scan that applied to both roots. **Suggested fix:** Reuse the same descendant freshness probe for `/tmp` directory candidates (shared helper, not cache-only naming), or if `/tmp` is intentionally legacy/best-effort, touch the session root on active writes and document that operators must not rely on `/tmp` for multi-day runs; add a harness case under `LARCH_TEST_TMP_ROOT` mirroring `stale-toplevel-with-fresh-deep-child-kept`.
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:99-109` — The `/tmp` pass deletes every top-level match with `-mtime +N` and never calls `cache_entry_has_fresh_descendant` (or any equivalent), while the cache pass at lines 47–59 skips removal when any descendant was touched inside the retention window. `scripts/session-setup.sh` still falls back to `/tmp/claude-implement-*` when the cache root is unavailable (lines 264–270), and parent-directory mtimes are not reliably bumped when nested session files are written (the design notes for #3212 call this out for APFS). A long-running `/implement` in `/tmp` can therefore be `rm -rf`'d while still writing under `larch-logs/` or similar, even though the same layout under `~/.cache/larch/sessions/` would be kept — a behavioral regression versus the pre-#3212 depth-5 activity scan that applied to both roots. **Suggested fix:** Reuse the same descendant freshness probe for `/tmp` directory candidates (shared helper, not cache-only naming), or if `/tmp` is intentionally legacy/best-effort, touch the session root on active writes and document that operators must not rely on `/tmp` for multi-day runs; add a harness case under `LARCH_TEST_TMP_ROOT` mirroring `stale-toplevel-with-fresh-deep-child-kept`.
- **Suggested revision**: Address the concern above.


### FINDING_23: **correctness** `skills/cleanup/scripts/cleanup.sh:32-36` — `cache_entry_has_fresh_descendant` silences `find` errors (`2>/dev/null`) and treats any empty result as “no fresh descendant,” which makes the cache loop proceed to `rm -rf`. The removed `newest_activity_mtime` path explicitly warned and skipped deletion when descendant enumeration failed. A transient `find` failure (permissions, I/O) on an otherwise live session directory can now be misclassified as stale and deleted. **Suggested fix:** Distinguish `find` failure from “no matches” (capture exit status, or use a pattern that fails closed), and `continue` without incrementing `CACHE_REMOVED` when the descendant probe cannot run — matching the old per-entry skip semantics.
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **correctness** `skills/cleanup/scripts/cleanup.sh:32-36` — `cache_entry_has_fresh_descendant` silences `find` errors (`2>/dev/null`) and treats any empty result as “no fresh descendant,” which makes the cache loop proceed to `rm -rf`. The removed `newest_activity_mtime` path explicitly warned and skipped deletion when descendant enumeration failed. A transient `find` failure (permissions, I/O) on an otherwise live session directory can now be misclassified as stale and deleted. **Suggested fix:** Distinguish `find` failure from “no matches” (capture exit status, or use a pattern that fails closed), and `continue` without incrementing `CACHE_REMOVED` when the descendant probe cannot run — matching the old per-entry skip semantics.
- **Suggested revision**: Address the concern above.


### FINDING_24: **risk-integration** `skills/cleanup/scripts/test-cleanup.sh` — There is no test for “stale top-level `/tmp/claude-implement-*` mtime + fresh nested file,” only for cache (`stale-toplevel-with-fresh-deep-child-kept`, lines 154–164) and for unconditionally stale tmp removal (`stale-tmp-dir-removed`, lines 212–220). The `/tmp` descendant-fresh regression called out in the scout brief is therefore unguarded, so the cache/tmp asymmetry above can reappear without CI signal. **Suggested fix:** Add a case under `LARCH_TEST_TMP_ROOT` with stale parent `touch -t` and a fresh nested artifact, asserting `TMP_REMOVED=0` and directory retention if `/tmp` should match cache semantics (or document and assert removal if `/tmp` is intentionally stricter).
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **risk-integration** `skills/cleanup/scripts/test-cleanup.sh` — There is no test for “stale top-level `/tmp/claude-implement-*` mtime + fresh nested file,” only for cache (`stale-toplevel-with-fresh-deep-child-kept`, lines 154–164) and for unconditionally stale tmp removal (`stale-tmp-dir-removed`, lines 212–220). The `/tmp` descendant-fresh regression called out in the scout brief is therefore unguarded, so the cache/tmp asymmetry above can reappear without CI signal. **Suggested fix:** Add a case under `LARCH_TEST_TMP_ROOT` with stale parent `touch -t` and a fresh nested artifact, asserting `TMP_REMOVED=0` and directory retention if `/tmp` should match cache semantics (or document and assert removal if `/tmp` is intentionally stricter).
- **Suggested revision**: Address the concern above.


### FINDING_25: **code-quality** `skills/cleanup/scripts/test-cleanup.sh:154-164` — The fixture work directory is named `stale-toplevel-with-fresh-deep-child-removed` (lines 154–155) while the section comment, failure messages, and `test-cleanup.md` all say `-kept` with `CACHE_REMOVED=0`. The behavior under test is “kept,” so the `-removed` dirname contradicts the assertions and invites a future edit that inverts the intended semantics. **Suggested fix:** Rename the work directory and section header to `stale-toplevel-with-fresh-deep-child-kept` so names, docs, and assertions align.
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **code-quality** `skills/cleanup/scripts/test-cleanup.sh:154-164` — The fixture work directory is named `stale-toplevel-with-fresh-deep-child-removed` (lines 154–155) while the section comment, failure messages, and `test-cleanup.md` all say `-kept` with `CACHE_REMOVED=0`. The behavior under test is “kept,” so the `-removed` dirname contradicts the assertions and invites a future edit that inverts the intended semantics. **Suggested fix:** Rename the work directory and section header to `stale-toplevel-with-fresh-deep-child-kept` so names, docs, and assertions align.
- **Suggested revision**: Address the concern above.


### FINDING_5: correctness: skills/design/scripts/test-trailer-awk.sh:168-176
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] keys mode is not asserted for block-boundary or duplicate-diff-added fixtures despite parse/values/has_key coverage. A keys-only regression (e.g. has_added cleared while values/has_key still pass) would not fail make test-trailer-helpers. Add assert_keys for block-boundary (diff_added) and duplicate-diff-added (diff_added once).
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: scripts/ship-pr.md:97
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Documented pre-rebase fixup uses full-tree git add -u when any tracked porcelain is dirty; ship-pr.sh only fixups larch-logs/. Dirty tracked files outside larch-logs/ during rebump are not fixup-committed; drop-bump Guard 1 can still stall despite the doc promising a full-tree fixup. Align ship-pr.md with larch-logs/-scoped implementation or widen fixup to match the documented full-tree behavior.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: skills/review-and-fix/scripts/review-and-fix.sh:467-487
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Round-mode staging uses a tracked-path manifest instead of git add -A. Coder produces only untracked files: non-empty porcelain, empty manifest, round returns exit 2 failed instead of committing or no-changes. Document fail-closed behavior and add a harness case, or extend manifest/no-changes handling for untracked-only dirt.
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:488-491
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New fail-closed path refuses commit when tracked dirty paths fall outside coder-stage-paths.txt manifest; harness only covers pre-commit hook follow-up/persistent residue. A coder that edits both an in-manifest file and another tracked file (e.g. larch-logs/) could reach production without a regression test; manifest guard could be removed or broken silently. Add test-review-and-fix.sh orchestrator case: stub modifies manifest path plus extra tracked path; expect exit 2 and CODER_STATUS=failed.
- **Suggested revision**: Address the concern above.


