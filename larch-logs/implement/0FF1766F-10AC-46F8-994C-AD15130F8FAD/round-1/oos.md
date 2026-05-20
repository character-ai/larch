### FINDING_10: [OUT_OF_SCOPE] **Double guard / exit-code parity:** `create-pr.sh` runs the porcelain guard before any push (`scripts/create-pr.sh:96-103`), so a dirty tree at script entry never reaches `git-force-push.sh`; the helper guard is defense-in-depth for direct callers (`merge-pr.sh`, `implement-finalize.sh` Step 8b, `ship-pr.sh` rebase-rebump). Both failure modes use exit 1, consistent with the updated `scripts/create-pr.md` exit table; stderr text differs (`ERROR: Uncommitted…` vs `git-force-push.sh: uncommitted…`), so operators are not forced to rely on exit-code subtyping alone.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Double guard / exit-code parity:** `create-pr.sh` runs the porcelain guard before any push (`scripts/create-pr.sh:96-103`), so a dirty tree at script entry never reaches `git-force-push.sh`; the helper guard is defense-in-depth for direct callers (`merge-pr.sh`, `implement-finalize.sh` Step 8b, `ship-pr.sh` rebase-rebump). Both failure modes use exit 1, consistent with the updated `scripts/create-pr.md` exit table; stderr text differs (`ERROR: Uncommitted…` vs `git-force-push.sh: uncommitted…`), so operators are not forced to rely on exit-code subtyping alone.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] **Pre-existing / not introduced by this diff:** `scripts/ship-pr.sh` is unchanged; pushes still flow through `scripts/create-pr.sh` and `scripts/git-force-push.sh`, so behavior is covered indirectly even though the feature text mentioned `ship-pr.sh` by name.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **Pre-existing / not introduced by this diff:** `scripts/ship-pr.sh` is unchanged; pushes still flow through `scripts/create-pr.sh` and `scripts/git-force-push.sh`, so behavior is covered indirectly even though the feature text mentioned `ship-pr.sh` by name.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] **TOCTOU:** Any point-in-time `git status` check can pass and the working tree can still change before `git push`; that race is inherent and not introduced solely by this branch (the guard still removes the dominant “forgot to commit” failure mode).
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **TOCTOU:** Any point-in-time `git status` check can pass and the working tree can still change before `git push`; that race is inherent and not introduced solely by this branch (the guard still removes the dominant “forgot to commit” failure mode).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] **`scripts/create-pr.sh:40-43`:** `trap cleanup EXIT` already removes `REDACTED_BODY_FILE` on the new `exit 1` path, so the dirty-tree abort does not leave the redaction tempfile behind (the scout note about cleanup is not a defect here).
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **`scripts/create-pr.sh:40-43`:** `trap cleanup EXIT` already removes `REDACTED_BODY_FILE` on the new `exit 1` path, so the dirty-tree abort does not leave the redaction tempfile behind (the scout note about cleanup is not a defect here).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] **`scripts/merge-pr.sh:193-196`:** `git-force-push.sh` output is merged stdout/stderr with `PUSHED` parsed from lines; a dirty-tree exit leaves `PUSHED` non-`true`, so the existing failure branch still trips without requiring a new parser shape.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **`scripts/merge-pr.sh:193-196`:** `git-force-push.sh` output is merged stdout/stderr with `PUSHED` parsed from lines; a dirty-tree exit leaves `PUSHED` non-`true`, so the existing failure branch still trips without requiring a new parser shape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] code-quality: scripts/test-ship-pr.sh:404-414
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Rebump harness stubs git-force-push.sh with exit 0. New real-script guard is not exercised in ship-pr tests. Pre-existing stub pattern; only note if end-to-end ship-pr coverage of the guard is desired later.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] risk-integration: feature_description vs branch
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Feature text names ship-pr and test-ship-pr; branch targets leaf scripts and test-create-pr. Documentation of intent vs file-level plan wording mismatch. No code change required if issue #2434 accepts leaf-script enforcement.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_2: **architecture** `scripts/implement-finalize.sh:896-913` — `run_force_push_gate` parses `STATUS` from the captured `git-force-push.sh` output and treats anything outside `pushed|noop_same_ref` as the default case, emitting a hard-coded `warn_line` about a lease refusal. A dirty-tree failure yields an empty `STATUS` (and `rc=1`), so it follows that same branch and surfaces the wrong headline to the operator even though `larch_err` in the captured output explains the real cause; the same default branch already treats `STATUS=diverged_retry_failed` as “lease check refused,” so the new guard widens the audience for that misleading message without fixing the underlying misclassification. **Suggested fix:** Detect dirty-tree failures (e.g., non-zero `rc` with no `STATUS=` line or a stderr/grep sentinel from the merged capture) and emit a distinct warning / `append_execution_issue` string, reserving the lease wording for true `diverged_retry_failed` (and optionally other push-failure shapes).
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **architecture** `scripts/implement-finalize.sh:896-913` — `run_force_push_gate` parses `STATUS` from the captured `git-force-push.sh` output and treats anything outside `pushed|noop_same_ref` as the default case, emitting a hard-coded `warn_line` about a lease refusal. A dirty-tree failure yields an empty `STATUS` (and `rc=1`), so it follows that same branch and surfaces the wrong headline to the operator even though `larch_err` in the captured output explains the real cause; the same default branch already treats `STATUS=diverged_retry_failed` as “lease check refused,” so the new guard widens the audience for that misleading message without fixing the underlying misclassification. **Suggested fix:** Detect dirty-tree failures (e.g., non-zero `rc` with no `STATUS=` line or a stderr/grep sentinel from the merged capture) and emit a distinct warning / `append_execution_issue` string, reserving the lease wording for true `diverged_retry_failed` (and optionally other push-failure shapes).
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_23: correctness: scripts/git-push.sh:39-45
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Ship-pr still calls git-push.sh after CI fixes without a clean-tree guard; only create-pr and git-force-push were hardened. Uncommitted OOS or stray edits remain local while git-push.sh pushes the new Fix CI commit; remote advances without those files; same silent data-loss pattern as issue #2434. Add porcelain abort to git-push.sh before push; extend test-git-push.sh or ship-pr tests; update workflow-lifecycle invariant text to list all push wrappers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] **Acceptance vs diff:** The precomputed diff does not add `scripts/test-ship-pr.sh` coverage or touch `scripts/ship-pr.sh` directly; enforcement is delegated to `create-pr.sh` / `git-force-push.sh`. If issue #2434 explicitly required a `ship-pr.sh`-level hook or ship-pr harness tests, that gap is outside this diff’s surface (no `ship-pr.sh` changes in `diff.txt`).
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Acceptance vs diff:** The precomputed diff does not add `scripts/test-ship-pr.sh` coverage or touch `scripts/ship-pr.sh` directly; enforcement is delegated to `create-pr.sh` / `git-force-push.sh`. If issue #2434 explicitly required a `ship-pr.sh`-level hook or ship-pr harness tests, that gap is outside this diff’s surface (no `ship-pr.sh` changes in `diff.txt`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] **Caller tolerance:** `scripts/create-pr.sh:138-140` appends helper stderr via `2>>"$PUSH_STDERR"` while discarding stdout; with `larch_quiet_init`, `larch_err` writes to the saved original stderr FD (`scripts/lib-quiet.sh:80-86`), so dirty-tree diagnostics still land in `PUSH_STDERR` and get surfaced by the parent’s `ERROR: Failed to push branch on existing-PR fast-path: …` path. `scripts/ship-pr.sh:1444-1448` keys off `rc` and logs combined output to `fail_file`, which is sufficient for the new exit 1. `scripts/merge-pr.sh:193-200` uses `PUSHED`/`STATUS` awk extraction with `|| true`; an empty `PUSHED` on dirty-tree failure still routes to `MERGE_RESULT=error` without merging, which is safe even though the prose says “force-push failed” generically.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Caller tolerance:** `scripts/create-pr.sh:138-140` appends helper stderr via `2>>"$PUSH_STDERR"` while discarding stdout; with `larch_quiet_init`, `larch_err` writes to the saved original stderr FD (`scripts/lib-quiet.sh:80-86`), so dirty-tree diagnostics still land in `PUSH_STDERR` and get surfaced by the parent’s `ERROR: Failed to push branch on existing-PR fast-path: …` path. `scripts/ship-pr.sh:1444-1448` keys off `rc` and logs combined output to `fail_file`, which is sufficient for the new exit 1. `scripts/merge-pr.sh:193-200` uses `PUSHED`/`STATUS` awk extraction with `|| true`; an empty `PUSHED` on dirty-tree failure still routes to `MERGE_RESULT=error` without merging, which is safe even though the prose says “force-push failed” generically.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

