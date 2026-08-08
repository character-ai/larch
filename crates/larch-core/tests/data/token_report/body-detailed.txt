## Report Tokens Analysis

Analyzed 1 parseable runs.
Tracked total estimated cost: $1.86.

## Aggregate cost

| Label | Runs | Total | Median | Mean | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| All runs | 1 | $1.86 | $1.86 | $1.86 | $1.86 |

## Vendor breakdown

| Vendor | Cost | Tokens |
| --- | ---: | ---: |
| Claude | $1.23 | 24,500 |
| Codex | $0.45 | 5,900 |
| Cursor Composer | $0.08 | — |
| Cursor Grok | $0.03 | — |
| Cursor | $0.11 | 2,450 |
| Claude (subprocess) | $0.07 | 960 |

## Top runs by estimated cost

| Issue | Started | Total | Claude | Codex | Cursor | Claude (sub) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [#101](https://github.com/character-ai/larch/issues/101) | 2026-05-01 | $1.86 (python-pricing) | $1.23 | $0.45 | $0.11 (Composer $0.08, Grok $0.03) | $0.07 |

## Phase breakdown

| Vendor | Phase | Runs | Tokens |
| --- | --- | ---: | ---: |
| claude | Step 2 — implementation | 1 | 24,000 |
| codex | Step 5 — review | 1 | 4,900 |

## Per-day cost trends

### Total cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $1.86 |

### Claude cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $1.23 |

### Codex cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $0.45 |

### Cursor cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $0.11 |

### Cursor Composer cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $0.08 |

### Cursor Grok cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $0.03 |

### Claude (subprocess) cost

| Date | Cost |
| --- | ---: |
| 2026-05-01 | $0.07 |

## Cost-reduction suggestions

- Review the highest-cost runs above before optimizing lower-cost phases.
- Cache-read tokens observed: 20,700; preserve prompt stability where cache hits are useful.
- Treat dollar values as estimates; `python/larch/report/report_tokens_cost.py` remains the pricing authority used for headline totals.

## Rates used for display/fallback

Claude: input 5.0/M, cache read 0.5/M, output 25.0/M.
Codex: input 5.0/M, cached input 0.5/M, output 30.0/M.
Cursor Composer: input 0.75/M, cache read 0.45/M, output 2.75/M.
Cursor Grok: input 2.0/M, cache read 0.5/M, output 6.0/M.

Cache JSON: <CACHE>