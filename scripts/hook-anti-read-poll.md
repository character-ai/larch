# hook-anti-read-poll.sh

PostToolUse hook registered in `hooks/hooks.json` under `matcher: "Read|Bash"`. Emits
a `system-reminder` when the orchestrator polls repeatedly: generic identical `Read`
calls (path+offset, 30 s window, threshold 3) or per-turn reads of a background task
`tasks/<id>.output` file via `Read` or `Bash` (normalized token key, 600 s window,
threshold 2; offset ignored for task-output paths).

## Purpose

Detects Read-poll and task-output-poll anti-patterns: an orchestrator waiting for a
file or background task by re-reading the same target each turn (issue #3175: ~80
Bash `cat …/tasks/<id>.output` reads). Different `offset` values on non-task-output
paths count as distinct reads. Task-output paths key state by the normalized
`tasks/<id>.output` token so wrapper/suffix command variants share one counter.

## State

Per-project state under `${TMPDIR:-/tmp}/larch-read-poll/`:

- `state-<cwd_hash>.tsv` — generic Read: `last_path\tlast_offset\tcount\tfirst_ts`
- `state-taskout-<cwd_hash>.tsv` — task output: `last_token\tcount\tfirst_ts`

The CWD hash is derived from the hook event's `cwd` field so multiple projects do not
share state.

## Parameters

Reads from stdin (Claude Code hook event JSON). Relevant fields:

- `tool_name` — must be `"Read"` or `"Bash"` or the hook exits 0 silently.
- `Read`: `tool_input.file_path` (end-anchored `tasks/<id>.output` classifier);
  `tool_input.offset` (ignored for task-output paths).
- `Bash`: `tool_input.command` (full string; read-verb + suffix-tolerant
  `tasks/<id>.output` match anywhere in the body, including multiline/compound
  commands and transcript suffixes after `.output` such as `2>/dev/null` or `| head`).
- `cwd` — project working directory (used to scope state files).

## Output

On threshold crossing, emits JSON `hookSpecificOutput.additionalContext` instructing
the orchestrator to use the Bash `<task-notification>` instead of polling. The
reminder does not echo raw paths back into high-priority context.

## Fail-open invariant

Never blocks tool use; `set -e` is intentionally omitted; any parse failure exits 0.

## Test harness

`scripts/test-hook-anti-read-poll.sh`
