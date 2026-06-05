### FINDING_1: code-quality: skills/implement/scripts/test-write-final-report.sh:530-533
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] New impl-lines-fb fallback test uses substring asserts only unlike adjacent stage2 test which also runs assert_schema_ordered A reorder or missing <!-- larch:run-summary v=1 --> sentinel in compose_self_fallback could pass the new case while breaking summary contract Add assert_schema_ordered for merged fallback with bucketed Lines bullet PR bullet and both sentinels mirroring lines 477-493
- **Suggested revision**: Address the concern above.

### FINDING_2: `a4084dead` — Cover PR line counts in final-summary fallback  
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `a4084dead` — Cover PR line counts in final-summary fallback
- **Suggested revision**: Address the concern above.

### FINDING_3: `9c165b885` — chore(larch-logs): flush implement run (out of review scope per instructions)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `9c165b885` — chore(larch-logs): flush implement run (out of review scope per instructions) **Summary:** The feature commit is a focused test-only change (+27 lines in `test-write-final-report.sh`, +2 lines in the harness doc). It matches the plan: a new `impl-lines-fb` fixture forces renderer failure while PR line-count data is valid, then asserts the `compose_self_fallback` path emits the degraded banner, fallback marker, bucketed `Lines (PR diff)` bullet (`+17/-3, +5/-1` from the shared gh shim), and PR bullet. Stub save/restore follows the existing stage2 pattern. Expected counts align with the shim fixture and `compute-pr-line-counts.sh` bucketing logic.
- **Suggested revision**: Address the concern above.

### FINDING_4: risk-integration: skills/implement/scripts/test-write-final-report.sh:530-533
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] New impl-lines-fb case uses substring asserts only not assert_schema_ordered unlike adjacent impl_bl stage2 block If compose_self_fallback bullet order regresses (e.g. Lines or PR moves after Run logs) the four assert_contains checks can still pass Add assert_schema_ordered for merged fallback output mirroring lines 477-493 (heading banner Lines PR sentinels)
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] risk-integration: skills/implement/scripts/test-write-final-report.sh:555-557
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] fork_fb reaches stage2 fallback with LINES_DATA_OK likely true but never asserts bucketed Lines bullet Forked-dry-run fallback may emit bucketed line counts alongside fork notes without any assertion catching format regressions on that combined path Optionally extend fork_fb with the same Lines and PR assert_contains calls (not required for this PR plan)
- **Suggested revision**: Address the concern above.

### FINDING_6: `a4084dead` — Cover PR line counts in final-summary fallback  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `a4084dead` — Cover PR line counts in final-summary fallback
- **Suggested revision**: Address the concern above.

### FINDING_7: `9c165b885` — chore(larch-logs): flush implement run F50F0756-CD96-4B17-8053-20341D3AA988  
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `9c165b885` — chore(larch-logs): flush implement run F50F0756-CD96-4B17-8053-20341D3AA988   **Scope:** The feature commit touches only `skills/implement/scripts/test-write-final-report.sh` and its harness doc — test-only coverage for `compose_self_fallback` when `LINES_DATA_OK=true`. No production scripts (`compute-pr-line-counts.sh`, `write-final-report.sh`, `render-run-summary.sh`) are modified.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `skills/implement/scripts/write-final-report.sh:521-526` — `compose_self_fallback` emits `PR_URL` and `ISSUE_URL` from `ship-pr-state.sh` / session files into markdown via `printf --` without URL allowlisting or markdown escaping; the new test now pins that PR bullet shape (`- **PR**: #43 — https://example.test/pr/43`). **Suggested fix:** If GitHub comment injection from poisoned session state is a concern, apply outbound sanitization (e.g. `redact-secrets.sh` plus URL scheme/host allowlist) to `summary-final.md` before `tracking-issue-summary.sh` upsert — pre-existing behavior, not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `scripts/compute-pr-line-counts.sh:58` — `gh api --paginate` has no explicit timeout; a hung network call could stall `write-final-report.sh`. **Suggested fix:** Documented accepted limitation per the issue plan; optional hardening would be a separate change — not in this diff.
- **Suggested revision**: Address the concern above.

### FINDING_10: `a4084dead` — Cover PR line counts in final-summary fallback  
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `a4084dead` — Cover PR line counts in final-summary fallback
- **Suggested revision**: Address the concern above.

### FINDING_11: `9c165b885` — chore(larch-logs): flush implement run (intentional run-log artifact; not reviewed as scope drift)
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: - `9c165b885` — chore(larch-logs): flush implement run (intentional run-log artifact; not reviewed as scope drift) The feature commit is test-only: one new `compose_self_fallback` harness case in `test-write-final-report.sh` plus a one-line doc update in `test-write-final-report.md`. No production-code changes.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **correctness** `skills/implement/scripts/test-write-final-report.sh:530-533` — The new case asserts substring presence (banner, marker, lines bullet, PR bullet) but not `<!-- larch:run-summary v=1 -->` or `assert_schema_ordered`, unlike the preceding `impl_bl` stage2 block (`477-493`). **Suggested fix:** If bullet-order regressions in merged-outcome fallback matter, mirror the stage2 schema-order assertions with the bucketed-lines expected sequence; otherwise this is acceptable minimal coverage per the plan.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 2. **architecture** `skills/implement/scripts/write-final-report.sh:119` — `compute-pr-line-counts.sh` is invoked with no explicit timeout; a hung `gh api` would stall `write-final-report.sh` before any fallback path. **Why out of scope:** pre-existing production limitation, explicitly accepted as document-only in the issue plan; this branch does not touch that code.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 3. **risk-integration** `skills/implement/scripts/test-write-final-report.sh:528-529` — Helper stderr is redirected to `/dev/null`, so diagnostics from `compute-pr-line-counts` or render-failure logging are invisible when assertions fail. **Why out of scope:** same suppression pattern as neighboring fallback tests (`472-473`, `555-556`); not introduced by this diff.
- **Suggested revision**: Address the concern above.

