# render-run-summary.sh

Shared renderer for the terminal / tracking-issue **run summary** markdown block
used by **`/implement` and `/design`**. Callers normalize inputs from their own
state surfaces, then invoke this script so the block stays byte-aligned across
surfaces.

## Single-source dollar-line invariant

The `- **Cost**:` bullet from this script is the **sole** authoritative
dollar-primary cost line for both skills. Do not duplicate that line in
`SKILL.md` prose, `token-report.sh --summary`, `timing-report.sh --summary`, or
committed log batches.

## Usage (summary)

```bash
bash scripts/render-run-summary.sh \
  --skill implement|design \
  --outcome <value> \
  --run-id <id> \
  --mode '<flags-or-N/A>' \
  --workflow-path SIMPLE|HARD|N/A \
  [--emergency-requested true|false] \
  --duration '<elapsed-or-N/A>' \
  --claude-tokens <n> --codex-tokens <n> --cursor-tokens <n> \
  --claude-input-tokens <n> ... --cursor-output-tokens <n> \
  --issue-number <n> --issue-url <url> \
  ...
```

Pass **per-bucket** counts (from `token-report.json` `BUCKETS_*`) when available so the cost line matches `token-cost.sh` per-bucket pricing; aggregate `--*-tokens` remains as backward-compatible fallbacks. `--emergency-requested` defaults to `false`; when `true`, the body includes `- Emergency: true`.

### `--skill design`

- Title uses `## /design run …`.
- Omits `- **PR**:` and `- **Code review**:` entirely (skipped `printf`s — not empty-string bullets) so stdout matches `--output-file` bytes.
- Emits `- **Plan review**:` from `--plan-review-line`.
- Omits `- **Lines (PR diff)**:` entirely (implement-only bullet).
- **Outcome bullet**: printed when `--outcome` matches `bailed*`, `stalled`,
  `cancelled-*`, or `failed-*` (not printed for `approved` or other happy-path
  implement outcomes).

## Output

- **Body**: written to `--output-file` when set; otherwise a temp file path is
  returned only via the envelope.
- **Envelope** (always): `STATUS=ok` and `OUTPUT_FILE=<path>` on **stderr**
  (never mixed into `--print-stdout` markdown).
- **`--print-stdout`**: prints the full markdown body (including note appendix)
  to the contract stdout stream (FD 3 when `lib-quiet.sh` is active, else FD 1).
- **Outcome / PR bullets (implement)**: `- **Outcome**:` is emitted only when `--outcome`
  matches `bailed*`, `stalled`, `cancelled-*`, or `failed-*`. `- **PR**:` is omitted when the normalized PR
  display resolves to `N/A` or when `--skill design`.

## Byte alignment

When both `--output-file` and `--print-stdout` are set, the file body and stdout
must be **byte-identical** (`cmp -s`). Field suppression for `--skill design` uses
skipped `printf`s (never empty bullets) so this invariant holds.

## Sentinel

The block ends with `<!-- larch:run-summary v=1 -->` on its own line. The
tracking-issue upsert marker remains
`<!-- larch:final-summary v1 runid=$RUN_ID -->` — unchanged; callers embed this
renderer’s body inside that upsert payload.

## Cost line

This script shells to `scripts/token-cost.sh` for per-vendor costs (per-bucket flags when callers supply them). The markdown body includes a **single** `- **Cost**:` bullet with the dollar-primary line (`💰 TOTAL ~$… — Claude $…, Codex $…, Cursor $…  |  Tokens: …k`). There is **no** separate `- **Tokens**:` bullet. On computation failure, emit `- **Cost**: N/A` only.

See `scripts/token-cost.md` for env vars and blended-fallback warning semantics.

## Lines (PR diff) — implement only

Optional flags `--code-added`, `--code-deleted`, `--logs-added`,
`--logs-deleted` (default empty). These are all-or-nothing integer inputs:
when any value is empty or non-integer, the bullet renders
`- **Lines (PR diff)**: N/A`. When all four are present:

`- **Lines (PR diff)**: code +<CA>/-<CD>, larch-logs +<LA>/-<LD>`

Emitted only when `--skill implement`, immediately after `- **Code review**:`.

`/design` callers omit the four flags; the bullet is suppressed via skipped
`printf` (not an empty bullet).

## Cost unavailable mode

`--cost-unavailable` is an explicit boolean mode for callers that know token data
is unavailable or unreliable. When set, the renderer skips `token-cost.sh`
entirely and emits exactly `- **Cost**: N/A`.

Callers should use this flag instead of omitting token flags or passing explicit
zero counts: omitting flags preserves the default zero-token pricing path and
therefore yields `💰 TOTAL ~$0.00 — Claude $0.00, Codex $0.00, Cursor $0.00`.
The flag is compatible with token flags; when both are present,
`--cost-unavailable` wins and cost computation is skipped.

## Outcome strings (normative)

| Skill | Outcome values with `- **Outcome**:` bullet |
|-------|-----------------------------------------------|
| `/implement` | `bailed*`, `stalled`, `cancelled-*`, `failed-*` (shell pattern; includes design-style strings if ever passed) |
| `/design` | `cancelled-clarify`, `cancelled-already-planned`, `cancelled-reentry-guard`, `cancelled-sprawl`, `cancelled-plan-size-hard`, `failed-plan-write`, `failed-publish`, `publish-skipped` (plus implement-style `bailed*` / `stalled` if reused) |
| Both | `approved` and other happy-path implement outcomes **omit** the Outcome bullet |

## Recent contract coverage

- `RUN_LOGS_PATH=N/A` no longer synthesizes a run-log path when `RUN_ID=unknown`, `OUTCOME=failed-publish`, or `OUTCOME=publish-skipped`; `publish-skipped` emits an Outcome bullet.
