# cache-key-runtime-audit.py

**Purpose**: Runtime audit for prompt cache-key drift in committed `/implement` session transcripts. It reads `larch-logs/implement/<RUN_ID>/session-transcript.jsonl`, reconstructs the stable prompt-prefix material for each unique assistant API request, and reports whether consecutive requests preserved that prefix.

**Primary callers**: Manual operator runs through `make audit-cache-keys-runtime RUNS=N`, or direct diagnostics via `python3 scripts/cache-key-runtime-audit.py --runs N --log-root larch-logs/implement`.

**Inputs**:
- `--log-root`: directory containing implement run directories.
- `--runs`: number of most recent run directories with `session-transcript.jsonl` to inspect.
- `--max-diff-chars`: per-finding diff truncation limit.

**Classification contract**:
- `BASELINE`: first assistant request in a run.
- `EXPECTED-GROWTH`: the stable prefix is unchanged or extends by newly loaded prompt material, usually a `user` entry with `isMeta=true`.
- `EXPECTED-CHANGE`: runtime `system` transcript entries changed or were appended. These entries are useful for audit visibility but are not treated as cache-invalidating prompt content by this script.
- `CACHE-INVALIDATING`: stable user/meta prefix content changed at a previously established prefix position.

**Invariants**:
- Assistant entries are deduplicated by `requestId`, falling back to message id and then `uuid`, because Claude Code may write multiple transcript entries for one API request.
- Invalid NDJSON lines are skipped and counted in the report.
- Parent chains are cycle-guarded; missing or cyclic parent links are reported as warnings, and the reachable chain is still audited.
- Content blocks are normalized through structured JSON handling rather than ad hoc line splitting.
- Per-finding diffs are truncated so large skill prompts do not dominate the report.
- User entries containing `tool_result`, `tool_use`, image, document, file, or other non-text content blocks (`type != "text"`) are classified as `user:attachment` and included in the stable-prefix set. This prevents false-negative EXPECTED-GROWTH classifications when attachment content mutates between turns.
- Top-level transcript `attachment` entries are also included in the stable-prefix set. This covers prompt-bearing runtime material such as `command_permissions`, `deferred_tools_delta`, and `skill_listing`.
- Non-text attachment blocks contribute a redacted summary (`type` plus payload SHA256) to the stable-prefix digest and diff output rather than exposing raw attachment payloads in reports.

**Makefile wiring**: `make audit-cache-keys-runtime RUNS=10` invokes this script against `larch-logs/implement`. The target is standalone operator instrumentation and is not part of `make lint`.

**Edit-in-sync**: When changing transcript capture semantics, stable-prefix selection, classification labels, or the Makefile target, update this document in the same PR. Keep `docs/run-logs.md` synchronized if the committed `session-transcript.jsonl` batch contract changes.
