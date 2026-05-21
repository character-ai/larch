# token-tally.sh contract

**Sibling script**: `scripts/token-tally.sh`.

**Purpose**: Per-run token-cost telemetry helper for `/research`. Implements the two subcommands consumed by `/research` Step 4: `write` (record one per-lane sidecar) and `report` (render the `## Token Spend` section). Telemetry is observability-only — there is no budget enforcement.

**Sole owner of the `## Token Spend` section**: `report` emits the full section (header + body). SKILL.md just calls the script and prints its stdout. Do NOT emit a duplicate `## Token Spend` header from the caller — designating one owner avoids drift if the script's section structure later changes.

## Subcommands

### `write --phase <p> --lane <l> --tool <t> --total-tokens <N|unknown> --dir <d>`

Records one per-lane sidecar file at `<d>/lane-tokens-<phase>-<safe-lane>.txt`, where `<safe-lane>` is the lane label lowercased with non-alphanumeric runs replaced by `-`.

- `--phase` must be `research` or `validation`. Other values exit 1.
- `--lane` is the stable slot name (e.g., `Code`, `Cursor`, `Codex`, `architecture`, `edge-cases`, `external-comparisons`, `security`, `planner`).
- `--tool` is currently always `claude` (only Claude subagent invocations have measurable usage). Reserved for future expansion if external tools ever expose token counts.
- `--total-tokens` is a non-negative integer OR the literal `unknown`. Other values exit 1. Use `unknown` when the orchestrator could not parse `total_tokens:` from the Agent tool's `<usage>` block.
- `--dir` MUST be under `/tmp/`, `/private/tmp/`, or `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/`. Any other path exits 1 (defense in depth; mirrors `cleanup-tmpdir.sh`).

Sidecar schema:

```
PHASE=<phase>
LANE=<lane>
TOOL=<tool>
TOTAL_TOKENS=<integer or unknown>
```

### `report --dir <d>`

Globs `<d>/lane-tokens-*.txt`, aggregates by phase, and emits the `## Token Spend` section to stdout. Fixed-shape output: one Research-phase row, one Validation-phase row, one Total row.

- `--dir` MUST be under `/tmp/`, `/private/tmp/`, or `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/`. If the directory does not exist (e.g., already cleaned by `cleanup-tmpdir.sh`), the script emits a graceful placeholder (`_(token telemetry unavailable: $RESEARCH_TMPDIR was already removed)_`) and exits 0.

**Cost column** (optional `$` column): rendered only when `LARCH_TOKEN_RATE_PER_M` is set to a positive number (USD per million tokens). When unset, malformed, or zero, the `$` column is omitted entirely. Both `total=` and the per-phase rows show the cost. Cost is computed via `awk` floating-point: `(total * rate) / 1_000_000`.

**Coverage line**: every phase row includes a coverage parenthetical: `(<lane-count> lanes, <measured> measured[, <unknown> unmeasurable])`. The unmeasurable fragment is omitted when zero.

## Sidecar file naming

`<dir>/lane-tokens-<phase>-<safe-lane>.txt` where `<safe-lane>` is `lane | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g'`. Repeated `write` calls for the same `<phase>+<lane>` overwrite — the orchestrator's last call for a given lane is the canonical reading.

## Path validation

Both subcommands validate `--dir` is under `/tmp/`, `/private/tmp/`, or the larch cache sessions root (matching `cleanup-tmpdir.sh`). This is defense in depth: although the orchestrator only ever passes `$RESEARCH_TMPDIR`, a misinvocation or future caller mistake could otherwise glob and read filenames from any user-supplied directory. Reject early with exit 1.

**Symlink-parent canonicalization**: `validate_dir` walks `--dir` upward via `dirname` to the nearest **existing-or-symlink** ancestor (the `! -e && ! -L` loop guard catches dangling symlinks instead of walking past them), canonicalizes that ancestor with `cd … && pwd -P`, and accepts only when the canonical anchor is exactly one of the allowed roots or under it. `/tmp`, `/private/tmp` when present, and the larch cache sessions root when present are canonicalized at validation time. A nearest existing ancestor that is a regular file (or symlink-to-file) is rejected — `validate_dir` does not silently take its parent. The pattern mirrors `scripts/deny-edit-write.sh`'s nearest-existing-ancestor probe with an allowed-root predicate.

## Test harness

`scripts/test-token-tally.sh` is the offline regression harness. Test cases:

1. `report` empty dir → "(no measurements available)" placeholder.
2. `report` populated fixtures across both phases → expected aggregate.
3. `report` with `unknown` sidecar → coverage line shows unmeasurable count.
4. `report` with `LARCH_TOKEN_RATE_PER_M` set → `$` column appears.
5. `report` without env var → `$` column omitted.
6. `write` malformed `--total-tokens` → exit 1.
7. `write --total-tokens=unknown` → succeeds.
8. Path validation: `--dir /home/foo` → exit 1 across both subcommands.
9. `report` after dir removed → graceful placeholder.
10. `write --phase=adjudication` → exit 1 (phase enum restricted to research|validation).

Wired into Makefile via `.PHONY` line, exactly one `test-harnesses-N:` shard prerequisite list, and a dedicated `test-token-tally:` recipe.

## Note on `/implement` and `/fix-issue` — intentional divergence from `token-cost.sh`

`/implement` and `/fix-issue` final summaries pull optional USD cost lines through `scripts/render-run-summary.sh`, which shells `token-cost.sh`; `token-cost.sh` has deliberately different semantics than `token-tally.sh` (this file):

| Dimension | `token-tally.sh` (this file) | `token-cost.sh` |
|-----------|------------------------------|-----------------|
| Primary skills / workflows | `/research` only | `/implement`, `/fix-issue` (via `scripts/render-run-summary.sh`; see `scripts/token-cost.md` intro) |
| Rate env vars | Single `LARCH_TOKEN_RATE_PER_M` across all lanes | Per-vendor `LARCH_CLAUDE_RATE_PER_M`, `LARCH_CODEX_RATE_PER_M`, `LARCH_CURSOR_RATE_PER_M`; **Claude-only**: when the Claude rate is unset, empty, or zero, `token-cost.sh` falls back to `LARCH_TOKEN_RATE_PER_M` (Codex/Cursor never use that var). |
| N/A behavior | `$` column omitted when `LARCH_TOKEN_RATE_PER_M` is unset, malformed, or non-positive | Each vendor uses `rate_or_na` on its effective raw rate: Claude can still yield a numeric `CLAUDE_COST` when only `LARCH_TOKEN_RATE_PER_M` is set; Codex/Cursor show `N/A` without their rates. `TOTAL_COST` sums only numeric vendor costs. |
| Cost display | Markdown cost suffix from awk, dollar-prefixed four decimal places beside totals. | Dollar strings from awk, two decimal places, no dollar prefix in KV values. |
| Output shape | Markdown `## Token Spend` section with phase rows | Flat KV lines (`CLAUDE_COST=`, `CODEX_COST=`, etc.) |

Do not assume parity between the two surfaces; changes to one do not imply the other needs matching updates.

## Edit-in-sync rules

When editing `token-tally.sh`:

1. **Test harness**: update `scripts/test-token-tally.sh` to add or modify regression cases for new behavior. Run it locally before commit.
2. **SKILL.md and references**: `skills/research/SKILL.md` Step 4 invokes `report --dir <d>`. The two reference files (`skills/research/references/research-phase.md`, `validation-phase.md`) call `write` after each Claude subagent return.
3. **Sidecar schema changes**: any new `KEY=` field or any rename requires updating both this contract and the test fixtures.
4. **Cost-column changes**: `LARCH_TOKEN_RATE_PER_M` is documented in `docs/configuration-and-permissions.md`; any addition of input/output split (when Agent tool exposes it) must update both this contract AND the docs entry.
