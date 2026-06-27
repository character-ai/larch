## Decision 1: Severity threshold for neutral rescue
- **Question**: Which severity qualifies the single YES endorser to rescue a neutral finding to OOS?
- **Resolution**: blocker or major only (HIGH_SEVERITIES). Minor and nit endorsements stay dropped.
- **Source**: user

## Decision 2: NEUTRAL_COUNT for rescued findings
- **Question**: Should rescued neutrals appear in NEUTRAL_COUNT / the round-summary "(K neutral)" line?
- **Resolution**: No. Rescued neutrals are excluded from NEUTRAL_COUNT and REJECTED_COUNT, consistent with the latent-rerouted path. They appear only in OOS_REJECTED_COUNT.
- **Source**: user

## Decision 3: Which tallies to update
- **Question**: Code-review only, or both code-review and plan-review?
- **Resolution**: Both — review_tally.py (code review) and plan_review_tally.py (plan review).
- **Source**: user

## Decision 4: Tally-level dedup against existing OOS
- **Question**: Should the tally check for existing OOS before writing a neutral-rescued finding?
- **Resolution**: No. OOS dedup is already handled downstream by oos_filer.py / oos-issues.ndjson. The tally writes to oos.md and the filer deduplicates cross-run.
- **Source**: codebase (oos_filer.py / python/larch/review review pipeline)
