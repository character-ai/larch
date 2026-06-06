### FINDING_8: [OUT_OF_SCOPE] risk-integration: (branch)
[nit] Full branch diff includes unrelated larch-log and Codex launcher test changes from other merged commits. Merge CI/runtime failures may be attributed to Phase 7 while originating elsewhere. Split or clearly label unrelated commits in the PR.

### FINDING_9: [OUT_OF_SCOPE] risk-integration: scripts/design-pause-load.sh
[latent] Phase 7 commit updates pause-load docs but not the script; clearing behavior comes from #3529 on the same branch. Reverting #3529 while keeping Phase 7 would leave docs claiming behavior the script lacks. Ensure #3529 ships with Phase 7 or land the script change in the Phase 7 commit.

### FINDING_28: [OUT_OF_SCOPE] security
- **security** `scripts/design-log-publish.sh:294-327` — Top-level `*-plan-voter-prompt.txt` files (e.g. `codex-plan-voter-prompt.txt` from `scripts/dispatch-plan-voters.sh:67`) remain publishable; round staging excludes `*-vote-prompt.txt` but the top-level gate does not. Committed design logs already contain these prompt files. Pre-existing gap, not introduced by this branch.

### FINDING_29: [OUT_OF_SCOPE] architecture
- **architecture** `scripts/lib-design-round-artifacts.sh:8` — The `dyn-*-output.txt` exclude pattern matches no current producer (`cursor-plan-dyn-*-output.txt` and `codex-primary-plan-dyn-*-output.txt` are covered by other arms / the default catch-all). Harmless for publication today but repeats the dead-pattern class the branch fixed for `codex-plan-*` → `codex-primary-plan-*`.

### FINDING_30: [OUT_OF_SCOPE] security
- **security** `scripts/larch-log.sh:85-99` — `round_artifact_included()` ordering looks correct on this branch: the `dyn-*-codex-output-retry*` deny sits before the explicit dynamic-Codex allow and before the broad `*-output*` catch-all; `scripts/test-larch-log.sh` pins the intended include/exclude matrix. No ordering regression found relative to the scout checklist.

### FINDING_31: [OUT_OF_SCOPE] security
- **security** `scripts/design-pause-load.sh:321` — Phase 7’s post-restore `rm -f "$restore_tmp/.pause-requested"` is a positive hardening change (prevents immediate re-pause loops); no defect found.

### FINDING_34: [OUT_OF_SCOPE] `scripts/test-design-structure.sh:1914-1926` asserts sentinel-before-pause ordering for the Step 2a.5 **prelude** and Step 2b prelude, but does not extract or check the separate SIMPLE repair fence (`skills/design/SKILL.md:842-875`). That leaves the repair-fence ordering gap above uncaught by CI even though Phase 7 documents the global before-pause contract.
- `scripts/test-design-structure.sh:1914-1926` asserts sentinel-before-pause ordering for the Step 2a.5 **prelude** and Step 2b prelude, but does not extract or check the separate SIMPLE repair fence (`skills/design/SKILL.md:842-875`). That leaves the repair-fence ordering gap above uncaught by CI even though Phase 7 documents the global before-pause contract.

### FINDING_35: [OUT_OF_SCOPE] Most other pinned hosts (Step 1d.5 prelude, Step 2a entry SIMPLE guards with `jq`/`brainstorm_requested`, zero-sketch degraded fence, Step 3 entry, Step 5/6 preludes, Step 6 cleanup after-pause exception, Step 5c publish pause-before-`design-publish.sh`) match the plan’s ordering in the current `SKILL.md` text; the Step 2a entry regression and the uncovered repair fence are the material correctness gaps found in this review.
- Most other pinned hosts (Step 1d.5 prelude, Step 2a entry SIMPLE guards with `jq`/`brainstorm_requested`, zero-sketch degraded fence, Step 3 entry, Step 5/6 preludes, Step 6 cleanup after-pause exception, Step 5c publish pause-before-`design-publish.sh`) match the plan’s ordering in the current `SKILL.md` text; the Step 2a entry regression and the uncovered repair fence are the material correctness gaps found in this review.

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **code-quality** `scripts/test-check-reviewers.sh:30-43` — The `2>/dev/null` on the awk invocation in `assert_argv_immediately_after_c` suppresses awk diagnostic output (e.g., "can't open input file"). When the argv log file is absent (test setup failure), the function correctly calls `fail` via the `else` branch, but the developer sees only the generic label-based message rather than the file-not-found context. This makes debugging setup failures harder but does not create a correctness issue since awk exits non-zero on a missing input file.

### FINDING_39: [OUT_OF_SCOPE] code-quality
- **code-quality** `scripts/test-check-reviewers.sh:19-27` — `assert_no_probe_homes` uses `find "$tmpdir" -maxdepth 1 ... 2>/dev/null || true`. If `$tmpdir` was never created (test-setup failure), `find` errors are silenced and `survivors` is the empty string, causing the function to pass silently. In the current callers, the tmpdir is always created by `run_cr` before this assertion, so this is not a practical concern, but adding a `[[ -d "$tmpdir" ]] || fail "$label: tmpdir missing: $tmpdir"` guard would make setup failures visible.

