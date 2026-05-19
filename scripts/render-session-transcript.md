# render-session-transcript.py contract

## Purpose

`scripts/render-session-transcript.py` converts a Claude Code session JSONL (the file Claude Code writes under `~/.claude/projects/<encoded-cwd>/<session>.jsonl`) into a chat-view markdown file that approximates what the operator saw in the chat UI — but with the harness-side bulk (re-injected SKILL.md prompt expansions, file-history snapshots, attachment frames, routine tool outputs) elided. The committed `session-transcript` larch-log batch ships as the rendered markdown rather than the raw `.jsonl`.

## Interface

```text
render-session-transcript.py --input <jsonl> [--output <md>]
```

`--input` is the raw Claude Code session JSONL. `--output` writes the rendered markdown to a file; without it the markdown is written to stdout. Exit codes: `0` success, `2` input missing or unreadable, `3` parsed but produced zero records (suspect format), other non-zero on unexpected exceptions.

## Filter rules

- **Drop** records with `isMeta: true`. These carry harness-injected slash-command expansions (`Base directory for this skill: …`) and `@file` inlines; the chat UI never shows these to the user.
- **Drop** records whose `type` is one of: `permission-mode`, `file-history-snapshot`, `attachment`, `last-prompt`, `queue-operation`, `system`.
- **User records** are rendered as the line the operator actually typed. `<command-message>` / `<command-name>` / `<command-args>` blocks collapse to `> /name args`. Plain text is preserved verbatim with `<system-reminder>` blocks stripped. `tool_result` blocks are rendered per the tool_result rule below.
- **Assistant records** render `text` blocks verbatim, `tool_use` blocks as `[name(compact-input)]` (the input dict is JSON-encoded and truncated at 200 chars), and `thinking` blocks only when at least one `tool_use` in the same assistant turn produced an errored `tool_result` (see "adjacency").
- **tool_result** blocks are kept in full when either:
  1. The block has `is_error: true`, or
  2. The tool is `Bash` and the first 500 chars of the output match `^(Error:|Exit code [1-9])` or contain a case-insensitive `warning:` substring.

  Otherwise the body is replaced with `[Tool → N bytes elided]`.

## Adjacency rule for `thinking` blocks

A `thinking` block is "adjacent to an error" when its enclosing assistant turn contains a `tool_use` whose corresponding `tool_result` (in the following user turn) qualifies under the tool_result error rule. The mapping is computed in a first pass over the file (tool-use IDs → tool names and tool-use IDs → error status); orphan tool_results whose originating tool_use is not in the JSONL (a Claude Code session-resume artifact) render with tool name `?`.

## Failure mode in the flush pipeline

`scripts/capture-session-transcript.sh` runs the renderer before `larch-log.sh write`. If the renderer exits non-zero or produces an empty file, the wrapper emits `SESSION_TRANSCRIPT_STATUS=render-failed` or `render-empty`, appends a `Warnings` entry to the execution-issues log via `append-execution-issue.sh`, and skips the flush entirely. The parent `/implement` run continues; no raw `.jsonl` is committed.

## Edit-in-sync

Update `scripts/capture-session-transcript.sh`, `scripts/capture-session-transcript.md`, and `scripts/larch-log-batches.sh` (`session-transcript` row) when changing the renderer's output shape or filter rules.
