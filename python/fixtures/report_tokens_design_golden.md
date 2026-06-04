## Report Tokens Analysis

Analyzed 2 parseable runs.
Tracked total estimated cost: $13.00.

## Aggregate cost by workflow

| Workflow | Runs | Total | Median | Mean | Max |
| --- | ---: | ---: | ---: | ---: | ---: |
| HARD | 1 | $7.00 | $7.00 | $7.00 | $7.00 |
| SIMPLE | 1 | $6.00 | $6.00 | $6.00 | $6.00 |

## Vendor breakdown

| Vendor | Cost | Tokens |
| --- | ---: | ---: |
| Claude | $2.00 | 20 |
| Codex | $4.00 | 40 |
| Cursor | $6.00 | 60 |

## Top runs by estimated cost

| Issue | Workflow | Started | Total | Claude | Codex | Cursor |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| [#8](https://example.invalid/HARD) | HARD | 2026-01-01 | $7.00 (token-cost) | $1.00 | $2.00 | $3.00 |
| [#7](https://example.invalid/SIMPLE) | SIMPLE | 2026-01-01 | $6.00 (token-cost) | $1.00 | $2.00 | $3.00 |

## Phase breakdown

| Workflow | Vendor | Phase | Runs | Tokens |
| --- | --- | --- | ---: | ---: |

## Per-day cost trends

### HARD

### HARD Total cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $7.00 |

### HARD Claude cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $1.00 |

### HARD Codex cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $2.00 |

### HARD Cursor cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $3.00 |

### SIMPLE

### SIMPLE Total cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $6.00 |

### SIMPLE Claude cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $1.00 |

### SIMPLE Codex cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $2.00 |

### SIMPLE Cursor cost

| Date | Cost |
| --- | ---: |
| 2026-01-01 | $3.00 |

## Cost-reduction suggestions

- Review the highest-cost runs above before optimizing lower-cost phases.
- Cache-read tokens observed: 0; preserve prompt stability where cache hits are useful.
- Treat dollar values as estimates; `scripts/token-cost.sh` remains the pricing authority used for headline totals.

## Rates used for display/fallback

Claude: input 5.0/M, cache read 0.5/M, output 25.0/M.
Codex: input 0.44/M, cached input 0.04/M, output 3.5/M.
Cursor: input 1.25/M, cache read 0.25/M, output 6.0/M.

Cache JSON: <CACHE>
