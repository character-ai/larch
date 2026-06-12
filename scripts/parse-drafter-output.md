# parse-drafter-output.py

## Purpose

Shared sentinel parser for `/design` Step 2b plan drafter output. Extracts
`LARCH_PLAN_BEGIN/END` and `LARCH_SUMMARY_BEGIN/END` blocks from a raw drafter
output file and writes `plan.txt` and (when present) `plan-summary.md`.

Extracted from the inline heredoc that was duplicated in `launch-codex-drafter.sh`
and `launch-claude-drafter.sh`.

## Usage

```
python3 scripts/parse-drafter-output.py <raw-file> <plan-out> <summary-out> [scout-out]
```

- `<raw-file>` — raw drafter output (full text including sentinel markers).
- `<plan-out>` — path where the extracted plan body is written.
- `<summary-out>` — path where the extracted summary body is written (when present).
- `[scout-out]` — optional path where a basic-shape valid scout JSON candidate is written.

Prints `PLAN_LINES=N`, `DIFF_LINES=N`, `SUMMARY_WRITTEN=true|false`,
`SCOUT_CANDIDATE_WRITTEN=true|false`, and `SCOUT_FAIL_REASON=<reason>` when
the optional scout output path is supplied.
Exits non-zero with a single-line message on stderr on any validation failure.

## Sentinel contract

- `LARCH_PLAN_BEGIN` / `LARCH_PLAN_END` — required, exactly one balanced pair.
- `LARCH_SUMMARY_BEGIN` / `LARCH_SUMMARY_END` — optional. Existing no-summary
  output remains valid. When present, the summary is exactly one balanced
  non-empty pair before the plan envelope.
- `LARCH_SCOUT_BEGIN` / `LARCH_SCOUT_END` — optional. When present, the only
  valid order is optional summary, plan, optional scout.
- The extracted plan body must be non-empty and its final line must match
  `diff_lines: <N>`. The extracted `plan.txt` therefore ends with that trailer.
- Plan parsing remains strict. The parser does not decontaminate, strip, or
  rewrite the plan body.
- Scout sentinels before or inside the summary or plan block are fatal.
- Malformed scout sentinels or scout JSON after `LARCH_PLAN_END` are non-fatal
  when the plan is valid; the scout candidate is omitted.
- `plan.txt` must never contain `LARCH_SCOUT_*` sentinels or a standalone
  top-level scout manifest object. Scout JSON examples inside fenced code
  blocks are not rejected solely for being examples.
- Launcher-side filtering is responsible for full scout validation before
  canonical materialization.

## Primary callers

- `scripts/launch-codex-drafter.sh` — Codex plan drafter launcher.
- `scripts/launch-claude-drafter.sh` — Claude plan drafter launcher.

## Edit-in-sync

- `scripts/launch-codex-drafter.sh` and `scripts/launch-claude-drafter.sh` —
  both call this script; sentinel contract changes affect both launchers.
- `scripts/test-launch-codex-drafter.sh` and `scripts/test-launch-claude-drafter.sh`
  — regression harnesses that exercise this parser indirectly via the launchers.
