# token-cost.sh

Per-vendor USD cost estimate from token counts and optional per-million-token
rates. Used by `scripts/render-run-summary.sh` (the `- **Cost**:` bullet in the
`larch:final-summary` block) for `/implement` and `/design`, and by the
`/fix-issue` helpers. The legacy `render-cost-line` bash helper remains available
for **deprecated** standalone operator cost queries with no in-flow skill callers
after PR #2714.

## Usage

```bash
bash scripts/token-cost.sh \
  [--per-bucket flags] \
  [--claude-tokens <N> --codex-tokens <N> --cursor-tokens <N>]
```

Per-bucket (preferred when counts are known):

- Claude: `--claude-input-tokens`, `--claude-cache-read-tokens`, `--claude-cache-write-5m-tokens`, `--claude-cache-write-1h-tokens`, `--claude-output-tokens`
- Codex: `--codex-input-tokens`, `--codex-cached-input-tokens`, `--codex-output-tokens`
- Cursor: `--cursor-input-tokens`, `--cursor-cache-read-tokens`, `--cursor-output-tokens`

**Blended fallback**: when only aggregate `--claude-tokens` / `--codex-tokens` / `--cursor-tokens` are supplied, each lane is priced at a conservative cache-heavy blended default (see table below). The script prints one stderr line: `token-cost.sh: WARNING: per-bucket counts unavailable; using blended rate (may overstate by ~3-10x)`.

## Environment

| Variable | Role |
|----------|------|
| Per-bucket | `LARCH_CLAUDE_INPUT_RATE_PER_M`, `LARCH_CLAUDE_CACHE_READ_RATE_PER_M`, `LARCH_CLAUDE_CACHE_WRITE_5M_RATE_PER_M`, `LARCH_CLAUDE_CACHE_WRITE_1H_RATE_PER_M`, `LARCH_CLAUDE_OUTPUT_RATE_PER_M`, `LARCH_CODEX_INPUT_RATE_PER_M`, `LARCH_CODEX_CACHED_INPUT_RATE_PER_M`, `LARCH_CODEX_OUTPUT_RATE_PER_M`, `LARCH_CURSOR_INPUT_RATE_PER_M`, `LARCH_CURSOR_CACHE_READ_RATE_PER_M`, `LARCH_CURSOR_OUTPUT_RATE_PER_M` — each overrides the corresponding bucket default when set to a positive decimal. |
| `LARCH_CLAUDE_RATE_PER_M` | Legacy blended USD per 1M Claude tokens (used only when per-bucket counts are absent and per-bucket env vars are unset for a bucket — nested fallback before the per-bucket default constant). |
| `LARCH_TOKEN_RATE_PER_M` | Claude-only legacy blended fallback when `LARCH_CLAUDE_RATE_PER_M` is unset, empty, zero, or malformed. |
| `LARCH_CODEX_RATE_PER_M` | Legacy blended USD per 1M Codex tokens (aggregate-only path). |
| `LARCH_CURSOR_RATE_PER_M` | Legacy blended USD per 1M Cursor tokens (aggregate-only path). |

### Default rates

Vendor defaults for **per-bucket** mode match Anthropic Opus 4.7, GPT-5.3-Codex, and Cursor Auto list pricing **verified 2026-05-22** (see source URLs in `scripts/token-cost.sh` comments).

When only **aggregate** counts are provided, conservative blended defaults (USD per 1M total tokens for that vendor) apply:

| Vendor | Blended default |
|--------|-----------------|
| Claude | `0.80` |
| Codex  | `2.00` |
| Cursor | `1.50` |

Precedence for each bucket: **per-bucket env** → **legacy blended env** (`LARCH_CLAUDE_RATE_PER_M` / `LARCH_TOKEN_RATE_PER_M` for Claude buckets, vendor blended for Codex/Cursor) → **per-bucket default constant**. Malformed env values fall through to the next tier.

`TOTAL_COST` **always** sums all three vendor numeric costs (each lane is always numeric once defaults apply).

> **Note**: Default rates are estimates, not invoice-grade billing. Set env overrides from your own billing visibility.

## Output (stdout)

Lines of the form `KEY=value`:

- `CLAUDE_COST`, `CODEX_COST`, `CURSOR_COST`, `TOTAL_COST` — `0.00` style decimals (no `$` in the KV values)
- `CLAUDE_TOKENS`, `CODEX_TOKENS`, `CURSOR_TOKENS`, `TOTAL_TOKENS` — integers

## Note on `/research` — intentional divergence from `token-tally.sh`

`/research` uses `token-tally.sh`, which has deliberately different semantics:

| Dimension | `token-cost.sh` (this file) | `token-tally.sh` |
|-----------|----------------------------|------------------|
| Primary skills / workflows | `/implement`, `/fix-issue`, `/design` (dollar line via `scripts/render-run-summary.sh` only) | `/research` only |
| Rate env vars | Per-bucket `LARCH_*_RATE_PER_M` names (see Usage); legacy blended `LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M` apply to **aggregate** pricing only (not as fallbacks for individual per-bucket lanes when per-bucket token flags are supplied); **Claude-only** `LARCH_TOKEN_RATE_PER_M` when Claude blended is unset. | Single `LARCH_TOKEN_RATE_PER_M` across all lanes |
| N/A behavior | With defaults, every lane yields a numeric cost; zero tokens with a positive rate yield `0.00`. | `$` column omitted when `LARCH_TOKEN_RATE_PER_M` is unset, malformed, or non-positive |
| Cost display | Dollar amounts from awk, two decimal places, no dollar prefix in KV values. | Markdown cost suffix from awk, dollar-prefixed four decimal places beside totals. |
| Output shape | Flat KV lines (`CLAUDE_COST=`, etc.) | Markdown `## Token Spend` section with phase rows |

## Orchestration note

Token-cost work may occasionally share a branch with `/implement` Step 5 (review loop) refactors. Treat those as separate risk surfaces unless the PR explicitly documents intentional coupling; the scripts in this directory are validated by the `test-token-cost*` and `test-render-cost-line*` harnesses without exercising Step 5.

Do not assume parity between **`token-cost.sh`** and **`token-tally.sh`**; changes to one do not imply the other needs matching updates.
