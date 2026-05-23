# token-cost.sh

Per-vendor USD cost estimate from token counts and optional per-million-token
rates. Used by `scripts/render-run-summary.sh` and the final-report helpers for
`/implement` and `/fix-issue`, and by `scripts/render-cost-line.sh` for `/design`
terminal summaries.

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
| `LARCH_TOKEN_RATE_PER_M` | Fallback when Claude rate is unset, empty, zero, or malformed. |
| `LARCH_CODEX_RATE_PER_M` | USD per 1M Codex tokens. |
| `LARCH_CURSOR_RATE_PER_M` | USD per 1M Cursor tokens. |

### Default rates

When an effective per-vendor rate is **unset**, **empty**, **zero**, or **fails strict numeric validation** (`^[0-9]+(\.[0-9]+)?$`), `token-cost.sh` substitutes a conservative blended default (USD per 1M **total** tokens):

| Vendor | Default (`DEFAULT_*_RATE_PER_M`) |
|--------|----------------------------------|
| Claude | `6.00` |
| Codex  | `10.00` |
| Cursor | `10.00` |

Precedence is unchanged: explicit `LARCH_CLAUDE_RATE_PER_M` / `LARCH_CODEX_RATE_PER_M` / `LARCH_CURSOR_RATE_PER_M` override defaults; Claude still prefers `LARCH_TOKEN_RATE_PER_M` when the Claude-specific env is unset, empty, or zero **before** the Claude default applies.

`TOTAL_COST` **always** sums all three vendor numeric costs (each lane is always numeric once defaults apply).

> **Note**: Default rates are conservative blended estimates, not invoice-grade billing data. Operators with real billing visibility should set their own rates via the env vars above.

## Output (stdout)

Lines of the form `KEY=value`:

- `CLAUDE_COST`, `CODEX_COST`, `CURSOR_COST`, `TOTAL_COST` — `0.00` style decimals (no `$` in the KV values)
- `CLAUDE_TOKENS`, `CODEX_TOKENS`, `CURSOR_TOKENS`, `TOTAL_TOKENS` — integers

## Note on `/research` — intentional divergence from `token-tally.sh`

`/research` uses `token-tally.sh`, which has deliberately different semantics:

| Dimension | `token-cost.sh` (this file) | `token-tally.sh` |
|-----------|----------------------------|------------------|
| Primary skills / workflows | `/implement`, `/fix-issue` (via `scripts/render-run-summary.sh`; see intro); `/design` terminal line (via `scripts/render-cost-line.sh`) | `/research` only |
| Rate env vars | Per-vendor `LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M`; **Claude-only**: when the Claude rate is unset, empty, zero, or malformed, `token-cost.sh` falls back to `LARCH_TOKEN_RATE_PER_M` (Codex/Cursor never use that var), then to per-vendor defaults. | Single `LARCH_TOKEN_RATE_PER_M` across all lanes |
| N/A behavior | With defaults, every lane yields a numeric cost; zero tokens with a positive rate yield `0.00`. | `$` column omitted when `LARCH_TOKEN_RATE_PER_M` is unset, malformed, or non-positive |
| Cost display | Dollar amounts from awk, two decimal places, no dollar prefix in KV values. | Markdown cost suffix from awk, dollar-prefixed four decimal places beside totals. |
| Output shape | Flat KV lines (`CLAUDE_COST=`, etc.) | Markdown `## Token Spend` section with phase rows |

Do not assume parity between the two surfaces; changes to one do not imply the other needs matching updates.
