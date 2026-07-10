# Discussion Round 1 — resolved scope and constraints

Issue #6855: when the main agent runs GLM-5.2, the final-report cost line mis-prices
the Claude main-agent value (it falls back to Opus rates). Update the pricing table
and the final-report cost line.

## Decision 1: GLM-5.2 per-token rates (rate-table row)
- **Question**: Which rates for the `glm-5.2` row in the claude rate table?
- **Resolution**: Official Z.ai rates per 1M tokens: input $1.40, cache-read $0.26,
  output $4.40; cache-write free, so `cache_create_5m` = `cache_create_1h` = 0.0.
- **Source**: user

## Decision 2: TOTAL semantics — token vs plan
- **Question**: What should the headline `TOTAL ~$X` sum to when the main agent is GLM-5.2?
- **Resolution**: The operator is ALWAYS on a plan and never pays per-token. The
  `token` value is reference only (pretend pay-per-token = main-agent usage x GLM
  rates). `estimated` (token / 15) is the approximation of actual plan cost. The
  headline TOTAL therefore reflects the estimated/plan cost for the Claude main
  agent (token / 15) plus the per-token costs for Codex, Cursor, and Claude-subprocess.
- **Source**: user

## Decision 3: Plan divisor
- **Resolution**: Hardcode the divisor as a named constant `15` (the token -> plan
  approximation factor per the issue). Not env-configurable (YAGNI).
- **Source**: codebase + issue

## Decision 4: Scope boundary — claude_sub excluded from plan pricing
- **Question**: Does the /15 plan treatment apply to spawned Claude subprocesses too?
- **Resolution**: No. The plan/estimated treatment applies ONLY to the main-agent
  `claude` lane. `claude_sub` (spawned reviewers/voters/scouts) are real Claude
  subprocesses priced at Claude rates; their cost is NOT divided.
- **Source**: codebase (issue targets "Claude main agent value"; claude_sub is distinct)

## Decision 5: Detection — which runs get the GLM/plan treatment
- **Question**: How do we know the main agent ran GLM-5.2?
- **Resolution**: Trigger when the main-agent model (`manifest.json` `model_roster.main`,
  sourced from the transcript `message.model`) resolves to glm-5.2. Normalize away a
  trailing `[1m]` context-variant suffix before lookup, so `glm-5.2[1m]` matches.
  Non-GLM runs are unchanged.
- **Source**: codebase

## Decision 6: Scope boundary — /report-tokens analysis vs final report
- **Question**: Does the plan-based TOTAL also change the /report-tokens dashboard?
- **Resolution**: Minimum change. The rate-table fix (glm-5.2 row) propagates to the
  shared pricing layer, which corrects CLAUDE_COST for GLM runs everywhere (no more
  Opus fallback). The plan-based TOTAL (token / 15), the `Claude token $T (estimated
  $E)` segment, and the explanation line are FINAL-REPORT cost-line changes only.
  /report-tokens keeps its existing token-based totals and tables.
- **Source**: codebase + minimum-change

## Hard constraints (must not break)
- Non-GLM runs: the final-report cost line and all pricing outputs stay byte-identical
  to today (existing tests and downstream parsers must not change).
- The cost-line grammar (`- **Cost**: 💰 TOTAL ~$...: Claude $..., ... | Tokens: Nk`)
  remains parseable; the GLM case only swaps the `Claude $C` sub-segment and appends
  one explanation bullet.
