# render-session-transcript.py contract

## Purpose

`scripts/render-session-transcript.py` converts a Claude Code session JSONL (the file Claude Code writes under `~/.claude/projects/<encoded-cwd>/<session>.jsonl`) into a filtered, machine-readable JSONL with one structured record per turn. The committed `session-transcript` larch-log batch ships as the rendered JSONL rather than the raw `.jsonl`. Per-record metadata that the chat UI never shows (parentUuid, promptId, sessionId, isMeta blocks, attachments, file-history snapshots, last-prompt, queue-operation, system records) is dropped.

## Interface

```text
render-session-transcript.py --input <raw-jsonl> [--output <jsonl>]
```

`--input` is the raw Claude Code session JSONL. `--output` writes the rendered JSONL to a file; without it the JSONL is written to stdout. Exit codes: `0` success, `2` input missing or unreadable, `3` parsed but produced zero records (suspect format), other non-zero on unexpected exceptions.

## Output schema (v1)

The first line is a header object:

```json
{"v": 1, "source_basename": "<input-basename>", "turns": <int>}
```

Subsequent lines are per-turn objects:

```json
{"turn": <int>, "role": "user" | "assistant", "blocks": [<block>, ...]}
```

`blocks` is an ordered list. Each block has a `type` field:

| `type`        | Other fields                                                                  | Meaning |
|---------------|-------------------------------------------------------------------------------|---------|
| `command`     | `name` (e.g. `/larch:fix-issue`), `args` (optional)                           | User-typed slash command. |
| `text`        | `value`                                                                       | Plain user or assistant prose (with `<system-reminder>` blocks stripped). |
| `thinking`    | `value`                                                                       | Assistant thinking. Kept only when at least one `tool_use` in the same assistant turn produced an errored or warned `tool_result`. |
| `tool_call`   | `id` (tool_use_id), `name`, `input` (full object)                             | Assistant tool invocation. |
| `tool_result` | `tool_use_id`, `name`, plus body fields below                                 | User-side tool result. |

`tool_result` body fields are mutually exclusive between elided and kept variants:

- **Elided (routine)**: `elided_bytes` only.
- **Kept (errored)**: `text` (verbatim body), `error: true`, optional `exit_code: <int>` when a Bash `Exit code N` prefix was parsed.
- **Kept (warning)**: `text` (verbatim body), `warning: true`. Only set when the result was not also classified as an error.

A result is kept (full body retained) when either:

1. The harness flagged `is_error: true` on the original block, or
2. The tool is `Bash` and the first 500 chars of the output contain `^(Error:|Exit code [1-9])` or a `warning:` substring (case-insensitive).

Otherwise the body collapses to `elided_bytes`.

## First pass / orphan results

The renderer walks the raw JSONL twice. The first pass builds `tool_use_id → tool_name` and `tool_use_id → kept_status` maps so the second pass can both label `tool_result` blocks and decide which `thinking` blocks to keep. Orphan `tool_result` blocks (whose originating `tool_use` is not in the JSONL — a Claude Code session-resume artifact) render with `name: "?"`.

## Failure mode in the flush pipeline

`scripts/capture-session-transcript.sh` runs this renderer before `larch-log.sh write`. If the renderer exits non-zero or produces an empty file, the wrapper emits `SESSION_TRANSCRIPT_STATUS=render-failed` or `render-empty`, appends a `Warnings` entry to the execution-issues log via `append-execution-issue.sh`, and skips the flush entirely. The parent `/implement` run continues; no raw `.jsonl` is committed in either form.

## Edit-in-sync

Update `scripts/capture-session-transcript.sh`, `scripts/capture-session-transcript.md`, and `scripts/larch-log-batches.sh` (`session-transcript` row) when changing the renderer's output shape or filter rules. Bump `v` in the header when changing the schema in a way that breaks downstream parsers.
