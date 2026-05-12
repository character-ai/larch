## Goal
Fix stale Codex/Cursor vendor rates and add Gemini accounting to `/report-tokens` analysis.

## Implementation Plan
Update `skills/report-tokens/scripts/run-analysis.sh`:
- Correct Cursor rates: input $3.00→$0.50, output $15.00→$2.50, aggregate $0.30→$0.20 (Composer 2)
- Correct Codex rates: input $1.25→$5.00, output $10→$30.00 (GPT-5.5); keep aggregate=$5.00; add cache_read=$0.50
- Add Gemini 2.5 Pro entry: input=$1.25, output=$10.00
- Add LARCH_REPORT_TOKENS_ACTUAL_SPEND reconciliation line
- Add per-vendor cost breakdown in workflow summary
- Add section_name explicit gemini case

## Test plan
- Run `bash skills/report-tokens/scripts/test-rate-assertions.sh`
- Run `make lint` (pre-commit + agent-lint)
