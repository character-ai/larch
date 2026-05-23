# render-cost-line.sh

**Purpose**: Emit a single terminal line with USD cost estimates and total token thousands for standalone `/design` runs. This is **not** a substitute for `scripts/render-run-summary.sh`, which renders a markdown bullet block with a `<!-- larch:run-summary v=1 -->` sentinel for tracking-issue comments and committed run logs.

## Usage

```bash
scripts/render-cost-line.sh \
  --claude-tokens <N> \
  --codex-tokens <N> \
  --cursor-tokens <N> \
  [--quiet-on-empty]
```

- Token counts are integers (total tokens per vendor for the run window you pass in).
- `--quiet-on-empty`: when all three counts are zero, print nothing and exit `0`.

## Output grammar (exact)

One line to stdout, newline-terminated:

```
💰 Cost: TOTAL ~$X.XX — Claude $A.AA, Codex $B.BB, Cursor $C.CC  |  Tokens: <T>k
```

- Literal `💰 Cost: TOTAL ~` prefix; amounts use two decimal places and a leading `$` per slot.
- ASCII em dash `—` between the total and the per-vendor breakdown.
- **Two spaces** before and after the pipe character (ASCII U+007C), i.e. two spaces, then the pipe, then two spaces, before `Tokens:`.
- `Tokens: <T>k` uses the same thousands rounding as `render-run-summary.sh` (`int((total+500)/1000)`).

## Internals

Shells to `scripts/token-cost.sh` for rate resolution and per-vendor dollar amounts; does not duplicate `token-cost.sh` math beyond formatting with `$` prefixes.

## Callers

- `/design` Step 0b / Step 5 exit paths per `skills/design/SKILL.md` (`### Terminal cost line`), after `token-report.sh --full --format json` writes `$DESIGN_TMPDIR/token-report.json` and **before** `cleanup-tmpdir.sh` deletes the session tmpdir.

## Rationale vs `render-run-summary.sh`

Different surface: terminal one-liner for Claude Code chat vs markdown bullets + sentinel for durable artifacts.
