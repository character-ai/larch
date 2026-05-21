# render-run-summary.sh

Shared renderer for the terminal / tracking-issue **run summary** markdown block
used by `/implement` and `/fix-issue`. Callers normalize inputs from their own
state surfaces, then invoke this script so the block stays byte-aligned across
surfaces.

## Usage (summary)

```bash
bash scripts/render-run-summary.sh \
  --skill implement|fix-issue \
  --outcome <value> \
  --run-id <id> \
  --mode '<flags-or-N/A>' \
  --workflow-path SIMPLE|HARD|N/A \
  --duration '<elapsed-or-N/A>' \
  --claude-tokens <n> --codex-tokens <n> --cursor-tokens <n> \
  --issue-number <n> --issue-url <url> \
  --pr-number <n> --pr-url <url> \
  --plan-review-line '<text>' \
  --code-review-line '<text>' \
  --oos-count <n> --oos-urls '<comma-list-or-empty>' \
  --exec-issues <n> --warnings <n> \
  --run-logs-path '<path-or-empty>' \
  [--note-lines-file <file>] \
  [--print-stdout] \
  [--output-file <path>]
```

## Output

- **Body**: written to `--output-file` when set; otherwise a temp file path is
  returned only via the envelope.
- **Envelope** (always): `STATUS=ok` and `OUTPUT_FILE=<path>` on **stderr**
  (never mixed into `--print-stdout` markdown).
- **`--print-stdout`**: prints the full markdown body (including note appendix)
  to the contract stdout stream (FD 3 when `lib-quiet.sh` is active, else FD 1).

## Sentinel

The block ends with `<!-- larch:run-summary v=1 -->` on its own line. The
tracking-issue upsert marker for `/implement` remains
`<!-- larch:final-summary v1 runid=$RUN_ID -->` — unchanged; callers embed this
renderer’s body inside that upsert payload.

## Cost line

This script shells to `scripts/token-cost.sh` for per-vendor costs. See
`scripts/token-cost.md` for env vars (`LARCH_CLAUDE_RATE_PER_M`, etc.).
