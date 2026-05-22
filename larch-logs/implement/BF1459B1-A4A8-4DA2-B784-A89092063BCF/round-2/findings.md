### FINDING_1: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **code-quality** `larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/round-2/*` — Session/run-log artifacts still contain scout/reviewer text about the old `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` bypass; that is historical run metadata, not part of the provided `diff.txt` surface for this fix. **Suggested fix:** None for this PR unless you intentionally want to refresh or drop those committed logs in a separate change. --- Plan note: the written plan mentioned `docs/larch-log.md` / `docs/ship-pr.md`; this repo only has the script-local contracts under `scripts/`, and the diff updates those—no gap versus the actual tree.
- **Suggested revision**: Address the concern above.

### FINDING_2: risk-integration: scripts/test-ship-pr.sh:1367-1391
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] HEAD vs origin/main orphan assertion runs with stubbed larch-log and finalize so it does not independently prove the post-merge larch-log commit regression is gone. Reintroduce ship-pr post-merge larch-log commit while keeping stubs: stub still exits 1 without mutating HEAD; rev-list count stays 0 but production would orphan-commit main. Reword test intent or add a disposable-repo test using real larch-log.sh commit after sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: scripts/ship-pr.sh:1755-1756
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Stale comment claims postmerge re-render makes the committed run-log reflect OUTCOME=merged after commits were removed from this phase. Maintainer misreads invariant and expects a git commit on main during postmerge. Update comment to refer to tmpdir-only updates.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: scripts/test-ship-pr.sh:1387-1391
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] orphan_count coerces git failures to the literal string error producing a confusing fail line. git rev-list fails; message says left error commit(s). Handle rev-list failure explicitly instead of echoing error into the count.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/round-2/scout-round2-manifest.json
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Scout/reviewer prompts still describe the removed bypass as current behavior. Historical log snapshot may confuse humans grepping the repo. Optional editorial refresh only if desired.
- **Suggested revision**: Address the concern above.

### FINDING_6: risk-integration: scripts/test-larch-log.sh:357-392
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Real larch-log commit+sentinel test never sets LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1 so CI cannot detect reintroducing the bypass in larch-log.sh if the ship-pr stub drifted or stayed strict while production regressed. A future PR restores bypass in larch-log.sh only; make test-larch-log still passes sentinel refusal without env; ship-pr stub tests still pass; bypass ships to consumers. Extend scripts/test-larch-log.sh sentinel commit test with LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1 and assert non-zero exit and refusal message; HEAD unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_7: risk-integration: scripts/larch-log.sh:459-466
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Post-merge larch-log commit bypass via LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR was removed; commit after post-merge-sentinel is always refused. External or custom scripts that still set LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR=1 and call larch-log.sh commit after merge (or export it into a shared shell) will fail with exit 1 and may stall CI or local wrappers that expected the old allow path. Document removal in operator-facing docs or release notes; remove the env var from any automation; align with NEVER #19 (tmpdir-only post-merge logs).
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] architecture: larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/round-2/*
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Scout/reviewer artifacts still reference the pre-2552 bypass review prompt. Stale guidance if those files ship unchanged; not part of the provided diff hunks. Regenerate or drop stale archetype text if included in a future log commit.
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/ship-pr.md:93
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Schema note implies post-merge committed manifests carry merge-finalized manifest keys. Downstream automation or operators grepping git-backed larch-logs on main may expect status=done/pr_number after merge but ship-pr no longer performs a post-merge log commit; plausible false negatives or wrong merge diagnostics. Reword to distinguish tmpdir postmerge manifest vs git-committed snapshots and note NEVER #19 means no post-merge log commit publishes those keys.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-ship-pr.sh:1332-1393
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Postmerge tests use a stub larch-log.sh and a narrow git rev-list vs self-remote HEAD snapshot. Real larch-log.sh regressions in commit guard behavior are not exercised in the postmerge integration path; orphan assertion does not model a real origin remote. Extend real-binary coverage in test-larch-log.sh or add one disposable-repo ship-pr case using real larch-log.sh.
- **Suggested revision**: Address the concern above.

### FINDING_11: correctness: scripts/test-ship-pr.sh:1473-1477
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] postmerge --no-logs-commit assertion dropped explicit no-commit grep. Future edits could weaken ordering checks and miss a stray commit invocation without failing the env-focused conjunct. Re-add ! grep '^LARCH_LOG_ARGS=commit' alongside existing assertions.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] code-quality: larch-logs/implement/3890E7C4-6C5E-4070-BD32-F9974BFA66DB/round-2/*
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Stale reviewer/session text references the removed bypass env var. Confusing only when browsing old run logs; not runtime behavior. Leave as historical artifact or refresh in a separate logs hygiene change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_13: **correctness** `scripts/test-ship-pr.sh:1367-1391` — The new `git rev-list --count origin/main..HEAD` check only proves **no new git objects** were added on `HEAD` in this disposable repo; `larch-log.sh` is a stub here and never runs `git commit`, so a regression that **reintroduces a post-merge `larch-log.sh commit` call** (especially one that fails fast and only shows up in `larch-log-calls.txt` / `postmerge-order.log`) would generally **not** move `HEAD` and could still pass this assertion while violating the intended policy. **Suggested fix:** Keep treating the grep / ordering assertions in the adjacent `postmerge_flush` and missing-manifest tests as the primary lock for “no post-merge `commit` invocation,” and either add an explicit `! grep -q '^LARCH_LOG_ARGS=commit'` check to this same scenario or add a short comment above `orphan_count` clarifying it is defense-in-depth for unexpected real `git commit` paths, not a substitute for the stub call-log assertions.
- **Reviewer**: dyn-callsite-audit-output.txt
- **Concern**: - **correctness** `scripts/test-ship-pr.sh:1367-1391` — The new `git rev-list --count origin/main..HEAD` check only proves **no new git objects** were added on `HEAD` in this disposable repo; `larch-log.sh` is a stub here and never runs `git commit`, so a regression that **reintroduces a post-merge `larch-log.sh commit` call** (especially one that fails fast and only shows up in `larch-log-calls.txt` / `postmerge-order.log`) would generally **not** move `HEAD` and could still pass this assertion while violating the intended policy. **Suggested fix:** Keep treating the grep / ordering assertions in the adjacent `postmerge_flush` and missing-manifest tests as the primary lock for “no post-merge `commit` invocation,” and either add an explicit `! grep -q '^LARCH_LOG_ARGS=commit'` check to this same scenario or add a short comment above `orphan_count` clarifying it is defense-in-depth for unexpected real `git commit` paths, not a substitute for the stub call-log assertions.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Repository-wide search still mentions `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` in `skills/implement/SKILL.md` (historical context inside NEVER #19), `scripts/test-ship-pr.sh` (legacy-env negative test), and under tracked `larch-logs/implement/...` session/reviewer artifacts from prior work; none of that reintroduces a runtime bypass in `scripts/larch-log.sh` or `scripts/ship-pr.sh` per the diff.
- **Reviewer**: dyn-callsite-audit-output.txt
- **Concern**: - Repository-wide search still mentions `LARCH_LOG_COMMIT_POSTMERGE_SHIP_PR` in `skills/implement/SKILL.md` (historical context inside NEVER #19), `scripts/test-ship-pr.sh` (legacy-env negative test), and under tracked `larch-logs/implement/...` session/reviewer artifacts from prior work; none of that reintroduces a runtime bypass in `scripts/larch-log.sh` or `scripts/ship-pr.sh` per the diff.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] The written implementation plan referenced `docs/larch-log.md` / `docs/ship-pr.md` cross-links; this branch updates [`scripts/larch-log.md`](scripts/larch-log.md) and [`scripts/ship-pr.md`](scripts/ship-pr.md) instead, and there are no matching filenames under `docs/` in this tree, so there is no additional doc surface to reconcile from the diff alone.
- **Reviewer**: dyn-callsite-audit-output.txt
- **Concern**: - The written implementation plan referenced `docs/larch-log.md` / `docs/ship-pr.md` cross-links; this branch updates [`scripts/larch-log.md`](scripts/larch-log.md) and [`scripts/ship-pr.md`](scripts/ship-pr.md) instead, and there are no matching filenames under `docs/` in this tree, so there is no additional doc surface to reconcile from the diff alone.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] [`SECURITY.md`](SECURITY.md) `larch-logs/` subsection remains consistent with unconditional post-sentinel refusal (no bypass described there).
- **Reviewer**: dyn-callsite-audit-output.txt
- **Concern**: - [`SECURITY.md`](SECURITY.md) `larch-logs/` subsection remains consistent with unconditional post-sentinel refusal (no bypass described there).
- **Suggested revision**: Address the concern above.

### FINDING_17: **correctness** `scripts/ship-pr.sh:1755-1756` — The inline comment above the post-merge `write-final-report.sh` call still claims the goal is so the **committed** run-log reflects `OUTCOME=merged`, but this change set removes the post-merge `larch-log.sh commit` path and codifies NEVER #19 (no post-merge git commits). After merge, `final-summary.md` and related artifacts are updated under `$IMPLEMENT_TMPDIR` (and the tracking-issue comment via the report helper), not as a new commit on `main`. **Suggested fix:** Reword the comment to describe tmpdir/API outcomes only (for example, that the tmpdir `final-summary.md` / report output aligns with `MERGE_RESULT`), and drop “committed” so it cannot contradict `scripts/ship-pr.md` and NEVER #19.
- **Reviewer**: dyn-state-ordering-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1755-1756` — The inline comment above the post-merge `write-final-report.sh` call still claims the goal is so the **committed** run-log reflects `OUTCOME=merged`, but this change set removes the post-merge `larch-log.sh commit` path and codifies NEVER #19 (no post-merge git commits). After merge, `final-summary.md` and related artifacts are updated under `$IMPLEMENT_TMPDIR` (and the tracking-issue comment via the report helper), not as a new commit on `main`. **Suggested fix:** Reword the comment to describe tmpdir/API outcomes only (for example, that the tmpdir `final-summary.md` / report output aligns with `MERGE_RESULT`), and drop “committed” so it cannot contradict `scripts/ship-pr.md` and NEVER #19.
- **Suggested revision**: Address the concern above.

### FINDING_18: **correctness** `scripts/ship-pr.sh:1734-1736` — When `recovery_ok=false`, the branch is a no-op (`:`) but the comment still says “Skip commit” and warns that “committing would produce a partial dir,” even though post-merge `git commit` was removed and the skipped work is the entire `else` tail (`status=done` manifest finalize plus `write-final-report.sh`), not merely a commit step. **Suggested fix:** Replace the comment with wording that matches control flow (skip manifest finalization and final-report when manifest recovery failed, since downstream assumes a coherent manifest tree).
- **Reviewer**: dyn-state-ordering-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:1734-1736` — When `recovery_ok=false`, the branch is a no-op (`:`) but the comment still says “Skip commit” and warns that “committing would produce a partial dir,” even though post-merge `git commit` was removed and the skipped work is the entire `else` tail (`status=done` manifest finalize plus `write-final-report.sh`), not merely a commit step. **Suggested fix:** Replace the comment with wording that matches control flow (skip manifest finalization and final-report when manifest recovery failed, since downstream assumes a coherent manifest tree).
- **Suggested revision**: Address the concern above.

