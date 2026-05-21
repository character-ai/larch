# token-cost.sh

Per-vendor USD cost estimate from token counts and optional per-million-token
rates. Used by `scripts/render-run-summary.sh` and the final-report helpers for
`/implement` and `/fix-issue`.

## Usage

```bash
bash scripts/token-cost.sh \
  --claude-tokens <N> \
  --codex-tokens <N> \
  --cursor-tokens <N>
```

## Environment

| Variable | Role |
|----------|------|
| `LARCH_CLAUDE_RATE_PER_M` | USD per 1M Claude tokens (preferred). |
| `LARCH_TOKEN_RATE_PER_M` | Fallback when Claude rate is unset, empty, or zero. |
| `LARCH_CODEX_RATE_PER_M` | USD per 1M Codex tokens. |
| `LARCH_CURSOR_RATE_PER_M` | USD per 1M Cursor tokens. |

Unset, empty, or zero rates yield `N/A` for that vendor’s cost. `TOTAL_COST`
sums only vendors with numeric costs; if none apply, `TOTAL_COST=N/A`.

## Output (stdout)

Lines of the form `KEY=value`:

- `CLAUDE_COST`, `CODEX_COST`, `CURSOR_COST`, `TOTAL_COST` — `0.00` style or `N/A`
- `CLAUDE_TOKENS`, `CODEX_TOKENS`, `CURSOR_TOKENS`, `TOTAL_TOKENS` — integers

## Note on `/research`

`/research` uses `token-tally.sh` with a single-rate column — different
semantics from this helper. Do not assume parity between the two surfaces.
