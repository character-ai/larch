# hook-anti-read-poll.sh

PostToolUse hook registered in `hooks/hooks.json` under `matcher: "Read"`. Emits
a `system-reminder` when the orchestrator reads the same `file_path` + `offset`
three or more times consecutively within a 30-second window.

## Purpose

Detects the Read-poll anti-pattern: an orchestrator waiting for a file to appear
by issuing repeated identical `Read` calls in quick succession (observed in run
5CD2EA11, transcript lines 459 and 465). Different `offset` values count as
distinct reads and do not trigger the warning.

## State

Per-project state is stored at `${TMPDIR:-/tmp}/larch-read-poll/state-<cwd_hash>.tsv`
(one TSV line: `last_path\tlast_offset\tcount\tfirst_ts`). The CWD hash is
derived from the hook event's `cwd` field so multiple projects do not share state.

## Parameters

Reads from stdin (Claude Code hook event JSON). Relevant fields:
- `tool_name` — must be `"Read"` or the hook exits 0 silently.
- `tool_input.file_path` — the path being read.
- `tool_input.offset` — read offset (default 0); different offsets reset the counter.
- `cwd` — project working directory (used to scope the state file).

## Output

On the third (or later) consecutive identical read within the 30 s window, emits
a JSON `hookSpecificOutput.additionalContext` message instructing the orchestrator
to use the Bash background-job completion notification instead.

## Test harness

`scripts/test-hook-anti-read-poll.sh`
