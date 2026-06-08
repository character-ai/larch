## Goal
Implement issue #3718: [IMPLEMENTING] logs-size-reduction: Phase 4: prose-and-errors-only session transcripts\n\n## Context.

## Implementation Plan
## Context

Phase 4 of the logs-size-reduction series. After #3708's trim (Edit/Write input stubs + 1 KB cap), `session-transcript.jsonl` remains the single largest residual item: **~22.6 MB corpus-wide** (414 runs), ~55 KB/run on new runs.

Operator decision for this phase: go to **prose-and-errors-only** transcripts — drop ALL `tool_call` and non-error `tool_result` blocks. Accepted capability loss (explicit): tool-sequence reconstruction for clean runs (e.g., #3175-style "how many times did it re-read the file" audits) is no longer possible from the committed transcript; incident forensics of that shape must use live-session artifacts instead.

Blocked on #3708 (builds on the renderer changes landing there).

## Policy (renderer contract v3)

Keep:
- assistant `text` blocks (prose, decisions, `Inline-triage rule` lines — read by the `oos-silent-drop` audit scan)
- user-typed commands/text blocks
- `tool_result` blocks **only when errored** (`is_error`, `^Exit code [1-9]`, `^Error:`, `warning:` — same predicate as today), plus a minimal `{tool, summary}` stub identifying what failed
- `thinking` blocks under today's rule (only in turns with an errored tool_use)
- the `{"v": 3, ...}` header with a `policy: "prose-errors-only"` marker

Drop:
- all `tool_call` blocks
- all non-error `tool_result` blocks (today already elided to byte counts; now removed)

## Changes

1. `scripts/render-session-transcript.py` — implement the v3 policy; bump header version; update `scripts/render-session-transcript.md` schema doc.
2. `docs/run-logs.md` session-transcript section — document the policy and the explicit capability loss.
3. **Retroactive sweep included** (one log-only PR): re-render all 414 committed transcripts through the v3 filter (pure JSONL transform — deterministic, no session data needed). File stays present (audit `required-file-presence` unaffected).
4. Codex-impl transcripts are out of scope here (#3714 covers their trim).

## Consumer safety

- `oos-silent-drop` greps `Inline-triage rule` from assistant prose — kept.
- `required-file-presence` — file remains.
- No other scan or tool parses transcript tool blocks (verified against `scans-implement.tsv` and `python/`/`scripts/` readers).

## Expected effect

22.6 → ~6–8 MB corpus (−15 MB); new runs ~55 → ~15–20 KB. Combined with Phases 1–3, `session-transcript.jsonl` stops being the dominant log item.


## Test plan
(no test plan section in plan-file)
