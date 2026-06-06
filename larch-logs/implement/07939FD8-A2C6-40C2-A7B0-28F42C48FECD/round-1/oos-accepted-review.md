### OOS_1: [OUT_OF_SCOPE] architecture: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:109-117
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] A1 scanner omits record-round emitters outside its 15-file enum and same-line pin rule. Step 5 deferred round timing can lose implement skill pinning without failing the new A1 guard. Add the helper to the scanner set and/or extend awk to record-round with export-or-same-line pin rules.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] correctness: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:99-104
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Round-only idempotency short-circuit predates this branch. Deferred Step 5 timing emit after a partial row exits 0 without updating start/end timestamps. Align pre-check with design helper full-tuple fingerprinting.
- **Suggested revision**: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **risk-integration** `skills/review-and-fix/scripts/record-implement-review-round-timing.sh` — Production `/implement` Step 5 path emits `timing-ledger.sh record-round` with `export LARCH_TIMING_SKILL=implement` on a separate line; the new A1 scanner (plan-scoped to `mark` / `record-vendor-task` / `timing-report.sh`) does not cover this subcommand. A dropped export would not fail the new harness.
- **Suggested revision**: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-telemetry-attribution-output.txt
- **Concern**: - **risk-integration** `scripts/lint-fix-loop.sh:366-373` / `scripts/launch-codex-exec.sh:211-218` — `/implement` lint-fix still reaches an unpinned `record-vendor-task` through `lint-fix-loop.sh` → `launch-codex-exec.sh` (shared across design/review/research). Under a polluted `LARCH_TIMING_SKILL=design` shell, Codex lint-fix vendor rows can still be tagged `design` while the new 15-file scanner passes. This matches the plan’s intentional A2 exclusion of generic launchers; fixing it would need an implement-session guard at the lint-fix dispatch site, not a blanket `=implement` pin on `launch-codex-exec.sh`.
- **Suggested revision**: Address the concern above.


