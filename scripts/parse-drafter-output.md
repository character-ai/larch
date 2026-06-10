# parse-drafter-output.py

## Purpose

Shared sentinel parser for `/design` Step 2b plan drafter output. Extracts
`LARCH_PLAN_BEGIN/END` and `LARCH_SUMMARY_BEGIN/END` blocks from a raw drafter
output file and writes `plan.txt` and (when present) `plan-summary.md`.

Extracted from the inline heredoc that was duplicated in `launch-codex-drafter.sh`
and `launch-claude-drafter.sh`.

## Usage

```
python3 scripts/parse-drafter-output.py <raw-file> <plan-out> <summary-out>
```

- `<raw-file>` — raw drafter output (full text including sentinel markers).
- `<plan-out>` — path where the extracted plan body is written.
- `<summary-out>` — path where the extracted summary body is written (when present).

Prints `PLAN_LINES=N`, `DIFF_LINES=N`, `SUMMARY_WRITTEN=true|false` to stdout.
Exits non-zero with a single-line message on stderr on any validation failure.

## Sentinel contract

- `LARCH_PLAN_BEGIN` / `LARCH_PLAN_END` — required, exactly one balanced pair.
- `LARCH_SUMMARY_BEGIN` / `LARCH_SUMMARY_END` — optional; when present, exactly
  one balanced non-empty pair; must not be nested inside the plan envelope nor
  contain the plan envelope.
- The extracted plan body must be non-empty and its final non-blank line must
  match `diff_lines: <N>`.

## Primary callers

- `scripts/launch-codex-drafter.sh` — Codex plan drafter launcher.
- `scripts/launch-claude-drafter.sh` — Claude plan drafter launcher.

## Edit-in-sync

- `scripts/launch-codex-drafter.sh` and `scripts/launch-claude-drafter.sh` —
  both call this script; sentinel contract changes affect both launchers.
- `scripts/test-launch-codex-drafter.sh` and `scripts/test-launch-claude-drafter.sh`
  — regression harnesses that exercise this parser indirectly via the launchers.
