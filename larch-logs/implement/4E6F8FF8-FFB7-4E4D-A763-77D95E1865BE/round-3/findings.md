### FINDING_1: code-quality: skills/design/scripts/test-trailer-awk.sh:168-176
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] keys mode is not asserted on duplicate-diff-added or block-boundary fixtures. A keys-only awk regression (duplicate key lines or wrong order on split blocks) could pass while parse/values/has_key still pass. Add assert_keys for duplicate-diff-added (single diff_added) and block-boundary (diff_added only).
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/test-trailer-awk.sh:26-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_has_key duplicates run_awk awk invocation wiring. Two places to update when trailer_nr or mode flags change. Fold has_key into run_awk with an optional key parameter.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/design/scripts/test-trailer-awk.md:15-17
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Expected-failure prose implies has_key exit 1 for any block-boundary case. Readers may expect block-boundary to return rc=1 before reading the split-fixture note. Rewrite to state orphan/blank fixtures rc=1 and in-block block-boundary rc=0 first.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] code-quality: skills/design/scripts/test-trailer-*.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Thin trailer adapter scripts still lack sibling .md files. Orphan-doc risk if someone adds uncited .md later. Optional follow-up docs or citations if policy tightens.
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

### FINDING_8: [OUT_OF_SCOPE] correctness: docs/configuration-and-permissions.md:254
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Cleanup retention text omits descendant freshness skip present in cleanup.sh. Operator assumes top-level mtime alone controls deletion; may mis-predict when stale parent dirs are retained due to fresh descendants. Mention cache descendant skip alongside top-level mtime (match SECURITY.md / cleanup.md).
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: skills/review-and-fix/scripts/review-and-fix.sh:488-491
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New fail-closed path refuses commit when tracked dirty paths fall outside coder-stage-paths.txt manifest; harness only covers pre-commit hook follow-up/persistent residue. A coder that edits both an in-manifest file and another tracked file (e.g. larch-logs/) could reach production without a regression test; manifest guard could be removed or broken silently. Add test-review-and-fix.sh orchestrator case: stub modifies manifest path plus extra tracked path; expect exit 2 and CODER_STATUS=failed.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: (branch)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Branch stacks #3204 #3209 #3212 review-and-fix version bumps and larch-logs in one diff. CI or make lint failure on shard-12 cannot be attributed to trailer harness vs cleanup vs ship-pr without manual bisect. Split commits by issue or run targeted make targets per surface before merge.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: skills/design/scripts/test-trailer-awk.sh:176-177
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] has_key absent-key coverage on none-present only probes diff_added not diff_deleted/mechanical_churn. Regression in has_mech/has_deleted clearing could pass keys/parse while has_key for those keys wrongly returns 0. Add assert_has_key none-present diff_deleted 1 and mechanical_churn 1.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/design/scripts/lib-plan-optional-trailers.awk` (unchanged) — Plan optional-trailer metadata is parsed from operator-/issue-controlled `plan.txt` bodies. Strict regexes and octal rejection limit abuse, but a malicious issue author could still influence gating metadata. This branch adds tests/docs only; it does not widen that trust boundary.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/ship-pr.sh` / committed `larch-logs/` — Pre-rebase auto-commit of tracked `larch-logs/` changes can land run artifacts on the branch. That is intentional for CI/rebase hygiene (#3209); redaction expectations remain those in `SECURITY.md` for committed logs vs session tmpdirs. Not introduced by #3204. --- **Summary:** From a **Security and Trust Boundaries** lens, this branch is tests, documentation, structural regression pins, and two hygiene commits that narrow or document existing local-operator trust boundaries. No actionable in-scope security defects.
- **Suggested revision**: Address the concern above.

### FINDING_14: architecture: skills/cleanup/scripts/cleanup.sh:99-111
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] /tmp cleanup lost descendant freshness guard present in pre-change should_remove_by_age. Long /implement claude-implement-* dir with stale top-level mtime but recently touched nested logs/state is removed while still in use; cache dirs with same shape are kept. Apply cache-style fresh-descendant skip (or subtree mtime) for /tmp directory matches; add regression test under LARCH_TEST_TMP_ROOT.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/cleanup/scripts/cleanup.sh:32-36
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cache_entry_has_fresh_descendant treats find errors as no fresh files. find fails inside an old-looking session dir; entry is rm -rf'd despite possible active work; old code warned and skipped. Fail closed on find errors: warn and skip removal instead of empty-pipe false negative.
- **Suggested revision**: Address the concern above.

### FINDING_16: architecture: skills/design/scripts/test-trailer-awk.sh:14-16
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness duplicates trailer_nr awk one-liner instead of sharing wrapper helper. Future edit to _plan_optional_trailer_nr only breaks production parsing; test-trailer-awk.sh still passes. Document must-stay-in-sync linkage or factor shared trailer_nr helper used by both paths.
- **Suggested revision**: Address the concern above.

### FINDING_17: `parse`: all-three, none, octal-rejected, block-boundary, blank boundary, mech true/false, `010` retention, duplicate `diff_added` (`block_len=2`, last-match-wins value `2`) — covered
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `parse`: all-three, none, octal-rejected, block-boundary, blank boundary, mech true/false, `010` retention, duplicate `diff_added` (`block_len=2`, last-match-wins value `2`) — covered
- **Suggested revision**: Address the concern above.

### FINDING_18: `keys` / `values`: mech true/false, `010`, octal empty/retained, last-match-wins on duplicate — covered
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `keys` / `values`: mech true/false, `010`, octal empty/retained, last-match-wins on duplicate — covered
- **Suggested revision**: Address the concern above.

### FINDING_19: `has_key`: present keys, absent/octal/boundary exit-1 with `assert_has_key` wrapper — covered; block-boundary split (in-block rc=0 vs orphan rc=1) documented in `test-trailer-awk.md`
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `has_key`: present keys, absent/octal/boundary exit-1 with `assert_has_key` wrapper — covered; block-boundary split (in-block rc=0 vs orphan rc=1) documented in `test-trailer-awk.md` Claim #1 (Gate A/B wiring) was correctly scoped as already resolved; only structural pin tightening was required and delivered.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 1. **architecture** `Makefile` / `skills/cleanup/` / `scripts/ship-pr.sh` / `skills/review-and-fix/` — The branch diff vs `main` includes merged or follow-on work (#3212, #3209, round-2 review-and-fix) outside the #3204 “Files to modify/create” list. That is PR scope composition, not a gap in the #3204 plan deliverables themselves. **Suggested fix:** None for plan fidelity; keep #3204 acceptance checks scoped to the six planned paths if signing off the OOS issue alone.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: 2. **correctness** `skills/design/scripts/test-trailer-awk.sh` — Octal edge-case bullet names four literal forms (`diff_added: 08/09`, `diff_deleted: 08/09`); the harness exercises `diff_added: 08` and `diff_deleted: 09` only (both awk branches, symmetric `/^0[89]$/`). **Suggested fix:** Optional follow-up fixtures for the other two literals; low risk given shared rejection logic in `.awk`.
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

### FINDING_26: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **correctness** `skills/cleanup/SKILL.md:9` and `docs/configuration-and-permissions.md:271` — Both still state that entries are removed when “top-level mtime” is older than the cutoff, without noting that cache entries with fresh descendants are retained. `SECURITY.md:234` and `skills/cleanup/scripts/cleanup.md:9` document the cache exception; the operator-facing SKILL and config doc do not, which can mislead troubleshooting of “why wasn’t my session deleted?” **Suggested fix:** Align SKILL.md and `docs/configuration-and-permissions.md` with `cleanup.md` / `SECURITY.md` (cache descendant skip; `/tmp` policy stated explicitly).
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **risk-integration** `skills/cleanup/scripts/test-cleanup.sh` — Depth-4 manifest and depth-5 round-artifact cache cases were removed in the #3212 diff; the new descendant probe is unbounded-depth `find` (not depth-5), so behavior likely still covers those paths, but regression signal for implement run-log depth is weaker than before.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] **#3204 trailer harness** — `lib-plan-optional-trailers.awk` / `.sh` are unchanged in the diff; `test-trailer-awk.sh` covers the plan’s edge cases (`parse`/`keys`/`values`/`has_key`, octal guard, last-match-wins, `block_len`, `set +e` probes); `test-design-structure.sh` tightens `(3175)` pins with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'`. No correctness defects identified in that slice on this pass.
- **Reviewer**: dyn-cleanup-tmp-descendant-protection-output.txt
- **Concern**: - **#3204 trailer harness** — `lib-plan-optional-trailers.awk` / `.sh` are unchanged in the diff; `test-trailer-awk.sh` covers the plan’s edge cases (`parse`/`keys`/`values`/`has_key`, octal guard, last-match-wins, `block_len`, `set +e` probes); `test-design-structure.sh` tightens `(3175)` pins with `grep -Fq -- '--snapshot-trailers'` / `'--dedup'`. No correctness defects identified in that slice on this pass.
- **Suggested revision**: Address the concern above.

