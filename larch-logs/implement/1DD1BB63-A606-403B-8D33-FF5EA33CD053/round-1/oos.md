### FINDING_13: [OUT_OF_SCOPE] correctness: scripts/step-telemetry-mark.sh:35-37
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Helper suppresses read-session-env-key stderr; inline fences did not. Harder to diagnose read failures during live runs; marks likely unchanged. Align stderr handling with inline fences if diagnostic parity matters (optional).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_20: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/step-telemetry-mark.sh:32-42` — The helper trusts `session-env.sh` under `--implement-tmpdir` for `LARCH_TOKEN_SESSION_ID`, `LARCH_CLAUDE_SOURCE_FILE`, and `LARCH_TIMING_LEDGER` without extra validation; a hostile or corrupted `session-env.sh` could steer ledger paths or session IDs within the constraints of existing ledger validators. **Why out of scope:** identical trust model to the removed inline trio; not introduced or amplified by this refactor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **risk-integration** `skills/implement/SKILL.md:894,1308,1343,1413` — `|| true` plus a non-executable helper (exit 126) still fails open for telemetry (marks dropped, step continues). The new harness `[ -x ]` mitigates the exec-bit regression in CI, not at runtime against a broken install. **Why out of scope:** deliberate never-fatal telemetry policy from the plan; integrity/availability, not a new exploit path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `skills/implement/SKILL.md:1343-1350` — Step 17 no longer re-exports ledger keys into the orchestrator shell before `write-final-report.sh`; that script’s optional `token-report.sh` fallback uses `${LARCH_TOKEN_SESSION_ID:-}` from the parent environment (often Step 0’s export). **Why out of scope:** pre-existing pattern for scripts that read `session-env` via `--implement-tmpdir` vs those that inherit env; session ID is stable for a normal run and the fallback path is unchanged in substance from prior step-boundary exports.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_29: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:513
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Prose mandates trio rehydration in later fences but Step 17 write-final-report fence omits it (pre-existing). Maintainers may assume rehydration happens where it does not. Update prose or add inline read (predates this branch).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_30: [OUT_OF_SCOPE] architecture: skills/implement/SKILL.md:659-677
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 2 conditional token mark vs unconditional timing mark asymmetry remains. Future blanket helper conversion could break token-budget ordering on external coder paths. Keep Step 2 out of helper scope (already documented).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] code-quality: skills/implement/SKILL.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Nine trio-only inline rehydration sites remain outside this extraction Future editors still copy long boilerplate for most steps Follow-on sweep when safe per plan backlog
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-implement-timing-rehydration.md:7-12
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Invariant 2 docs omit helper delegation Readers may assume B still covers converted step-ENTRY fences Update docs when invariant B is extended
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 1. **correctness** `scripts/test-implement-timing-rehydration.sh:39-76` — Invariant B only checks fences that directly invoke `timing-ledger.sh` / `timing-report.sh` in SKILL.md; converted step-ENTRY sites delegate to `step-telemetry-mark.sh`, so a future helper regression that drops `LARCH_TIMING_LEDGER` rehydration would not be caught by invariant B (only by the unit harness happy path, which always sets `LARCH_TIMING_LEDGER` in session-env). **Why out of scope:** pre-existing structural-test limitation amplified, not introduced, by this refactor; current helper code correctly reads and exports all three keys.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] code-quality
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 2. **code-quality** `scripts/test-implement-timing-rehydration.sh:1-20` — The plan called for updating the header comment as well as the `PASS:` line; only the latter was changed. **Why out of scope:** documentation drift vs plan, not a runtime defect.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

