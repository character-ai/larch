# render-run-summary.sh

Shared renderer for the terminal / tracking-issue **run summary** markdown block
used by `/implement`. Callers normalize inputs from their own
state surfaces, then invoke this script so the block stays byte-aligned across
surfaces.

## Usage (summary)

```bash
bash scripts/render-run-summary.sh \
  --skill implement \
  --outcome <value> \
  --run-id <id> \
  --mode '<flags-or-N/A>' \
  --workflow-path SIMPLE|HARD|N/A \
  --duration '<elapsed-or-N/A>' \
  --claude-tokens <n> --codex-tokens <n> --cursor-tokens <n> \
  --claude-input-tokens <n> ... --cursor-output-tokens <n> \
  --issue-number <n> --issue-url <url> \
  ...
```

Pass **per-bucket** counts (from `token-report.json` `BUCKETS_*`) when available so the cost line matches `token-cost.sh` per-bucket pricing; aggregate `--*-tokens` remains as backward-compatible fallbacks.

## Output

- **Body**: written to `--output-file` when set; otherwise a temp file path is
  returned only via the envelope.
- **Envelope** (always): `STATUS=ok` and `OUTPUT_FILE=<path>` on **stderr**
  (never mixed into `--print-stdout` markdown).
- **`--print-stdout`**: prints the full markdown body (including note appendix)
  to the contract stdout stream (FD 3 when `lib-quiet.sh` is active, else FD 1).
- **Outcome / PR bullets**: `- **Outcome**:` is emitted only when `--outcome`
  matches `bailed*` or `stalled`. `- **PR**:` is omitted when the normalized PR
  display resolves to `N/A`.

## Sentinel

The block ends with `<!-- larch:run-summary v=1 -->` on its own line. The
tracking-issue upsert marker for `/implement` remains
`<!-- larch:final-summary v1 runid=$RUN_ID -->` — unchanged; callers embed this
renderer’s body inside that upsert payload.

## Cost line

This script shells to `scripts/token-cost.sh` for per-vendor costs (per-bucket flags when callers supply them). The markdown body includes a **single** `- **Cost**:` bullet with the dollar-primary line (`💰 TOTAL ~$… — Claude $…, Codex $…, Cursor $…  |  Tokens: …k`). There is **no** separate `- **Tokens**:` bullet. On computation failure, emit `- **Cost**: N/A` only.

See `scripts/token-cost.md` for env vars and blended-fallback warning semantics.
