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

Per-project state under `${TMPDIR:-/tmp}/larch-read-poll/` (mode `700`; entries `600`):

- `state-<cwd_hash>.tsv` — generic Read: `last_path\tlast_offset\tcount\tfirst_ts`
- `state-taskout-<session_hash>-<cwd_hash>-<task_id>.tsv` — task output: `count\tfirst_ts`

Task-output counters are scoped by hook `session_id` (hashed; falls back to
`conversation_id`, then a shared `nosession` bucket when both are absent), `cwd`, and
the normalized `tasks/<id>.output` task id so distinct background tasks do not share one
counter. Sessions with distinct `session_id`/`conversation_id` hashes do not share
counts within the **600 s** TTL. When metadata is missing, all callers collapse to
`nosession` and can share counters across sessions (cross-session bleed). State files
expire logically after **600 s** without a matching poll (window reset, not file
deletion).

## Parameters

Reads from stdin (Claude Code hook event JSON). Relevant fields:

- `tool_name` — must be `"Read"` or `"Bash"` or the hook exits 0 silently.
- `Read`: `tool_input.file_path` (end-anchored `tasks/<id>.output` classifier);
  `tool_input.offset` (ignored for task-output paths).
- `Bash`: `tool_input.command` (normalized for backslash-newline continuations; each
  logical line split on `;`, `&&`, and `||` outside single/double/backtick quotes;
  per-segment read verb + `tasks/<id>.output` on the unstripped segment text so
  quoted paths count; segments that are only
  `echo`/`printf` ignored; multiline bodies and transcript suffixes after `.output`
  such as `2>/dev/null` or `| head` supported when the read verb and path share a
  segment). Same-line `VAR=tasks/<id>.output` assignments expand into simple
  `"$VAR"` / `$VAR` read targets; `read`, `awk`, and `python` paths are not tracked.
  Multiple qualifying segments on one line each advance the per-task counter.
  Cross-line shell variable indirection remains an accepted gap.
- `cwd` — project working directory (used to scope state files).

## Output

On threshold crossing, emits JSON `hookSpecificOutput.additionalContext` instructing
the orchestrator to use the Bash `<task-notification>` instead of polling. The
reminder does not echo raw paths back into high-priority context.

## Fail-open invariant

Never blocks tool use; `set -e` is intentionally omitted; any parse failure exits 0.

## Test harness

`scripts/test-hook-anti-read-poll.sh`
