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

## Note on `/research` — intentional divergence from `token-tally.sh`

`/research` uses `token-tally.sh`, which has deliberately different semantics:

| Dimension | `token-cost.sh` (this file) | `token-tally.sh` |
|-----------|----------------------------|------------------|
| Callers | `/implement`, `/fix-issue` | `/research` only |
| Rate env vars | Three separate vendor rates: `LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M` | Single `LARCH_TOKEN_RATE_PER_M` across all lanes |
| N/A behavior | Each vendor independently shows `N/A` when its rate is unset/zero | `$` column omitted entirely when `LARCH_TOKEN_RATE_PER_M` is unset/zero |
| Output shape | Flat KV lines (`CLAUDE_COST=`, `CODEX_COST=`, etc.) | Markdown `## Token Spend` section with phase rows |

Do not assume parity between the two surfaces; changes to one do not imply the other needs matching updates.
