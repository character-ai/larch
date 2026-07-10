## Decision 1: 3-lane cursor classification
- **Question**: How to classify BUCKETS_cursor_by_model?
- **Resolution**: auto lane (CURSOR_AUTO_MODEL), grok lane (grok-4.5), composer lane (everything else including composer-2.5, unknown, model-less legacy)
- **Source**: codebase (matches codex's mini/default pattern)

## Decision 2: New flag names for grok tokens
- **Question**: What flag names to use for grok tokens?
- **Resolution**: --cursor-grok-input-tokens, --cursor-grok-cache-read-tokens, --cursor-grok-output-tokens; keep existing --cursor-* for composer/legacy (backward compat)
- **Source**: codebase (existing --cursor-auto-* pattern)

## Decision 3: CURSOR_COST remains aggregate
- **Question**: Does CURSOR_COST stay as aggregate or split?
- **Resolution**: CURSOR_COST stays as aggregate (composer + grok + auto); add CURSOR_GROK_COST as additive field
- **Source**: feature description ("preserving aggregate CURSOR_COST")

## Decision 4: No enrich_cursor_by_model needed
- **Question**: Does tokens.py need enrich_cursor_by_model?
- **Resolution**: No. tokens.py already writes BUCKETS_cursor_by_model in build_report_from_ledgers. New runs will have it. Legacy runs fall back to aggregate CURSOR_COST per acceptance criteria.
- **Source**: codebase (tokens.py:1103-1111)
