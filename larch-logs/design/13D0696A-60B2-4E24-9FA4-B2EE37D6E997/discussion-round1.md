## Decision 1: Scope — no code outside pricing consolidation
- **Question**: Are there any adjacent changes (error handling, logging, unrelated refactors) to include?
- **Resolution**: No. Changes are limited to: rate constant correction, deduplication of pricing code to a single module, blended-rate derivation, model drift guard, drafter sidecar ingestion, docs update, and fixture/test updates.
- **Source**: codebase (issue body §Out of scope)

## Decision 2: Backward compatibility — blended env overrides stay working
- **Question**: Do the existing blended env var overrides (LARCH_CODEX_RATE_PER_M etc.) need to keep working?
- **Resolution**: Yes. Env-var ladder unchanged; only the default fallback values change.
- **Source**: codebase (issue body acceptance criteria)

## Decision 3: Historical run logs — no migration
- **Question**: Must committed run logs be re-processed with new rates?
- **Resolution**: No. `/report-tokens` reprices at render time; corrected rates apply retroactively at next render.
- **Source**: codebase (issue body §Plan 2)

## Decision 4: report_tokens_models.py — env_rate / display_rates deleted, not shimmed
- **Question**: Should the duplicate functions be deleted or kept as deprecated shims?
- **Resolution**: Delete. Tests in test_report_tokens_models.py that test the deleted copies are dropped/repointed.
- **Source**: codebase (issue body §Plan 1)
