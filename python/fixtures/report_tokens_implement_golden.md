## Report Tokens Analysis

Analyzed 1 parseable runs.
Tracked total estimated cost: $6.00.

## Aggregate cost

| Label | Runs | Total | Median | Mean | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| All runs | 1 | $6.00 | $6.00 | $6.00 | $6.00 |

## Vendor breakdown

| Vendor | Cost | Tokens |
| --- | ---: | ---: |
| Claude | $1.00 | 10 |
| Codex | $2.00 | 20 |
| Cursor | $3.00 | 30 |
| Claude (subprocess) | $4.00 | 40 |

## Top runs by estimated cost

| Issue | Started | Total | Claude | Codex | Cursor | Claude (sub) |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| [#7](https://example.invalid/7) | 2026-01-01 | $6.00 (python-pricing) | $1.00 | $2.00 | $3.00 | $4.00 |

## Phase breakdown

| Vendor | Phase | Runs | Tokens |
| --- | --- | ---: | ---: |

## Per-day cost trends

### Total cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $6.00 |

### Claude cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $1.00 |

### Codex cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $2.00 |

### Cursor cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $3.00 |

### Claude (subprocess) cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $4.00 |

## Cost-reduction suggestions

- Review the highest-cost runs above before optimizing lower-cost phases.
- Cache-read tokens observed: 0; preserve prompt stability where cache hits are useful.
- Treat dollar values as estimates; `python/larch/report/report_tokens_cost.py` remains the pricing authority used for headline totals.

Cache JSON: <CACHE>
