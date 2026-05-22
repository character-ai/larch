# skills/implement/scripts/hook-post-design.sh — contract

`hook-post-design.sh` is the plugin-shipped `PostToolUse` hook registered for the `Skill` tool. It reads Claude Code hook JSON on stdin and **no-ops** unless `tool_name` is `Skill` and `tool_input.skill` or `tool_input.skill_name` is `design` or `larch:design`.

On a match, the hook:

1. Parses `session_id` from stdin and, when non-empty, exports `LARCH_TOKEN_SESSION_ID` so downstream helpers can resolve the active `/implement` tmpdir.
2. Sources `lib-resolve-implement-tmpdir.sh`, resolves `IMPLEMENT_TMPDIR` from the stdin `cwd` field, and emits a single quiet-stream breadcrumb: boundary injection was retired (issue #2485); only the session-id export remains.

**Issue #2485 / post-design-boundary retirement**: Historical `post-design-boundary.sh` dispatch, `hookSpecificOutput` JSON injection, and Stop-hook coupling described in older docs are **not** implemented here. For archive semantics and why the boundary wrapper path was retired, see deprecated `post-design-boundary` material in the repo history and issue #2485. Do not assume this hook injects orchestrator directives or `additionalContext` payloads.

**Fail-open behavior**: `set -e` is intentionally omitted. Missing `jq`, malformed stdin, non-design Skill calls, and missing tmpdir all exit **0** without blocking tool completion.

**Edit-in-sync**: `lib-resolve-implement-tmpdir.sh`, `hooks/hooks.json`, and `skills/implement/scripts/test-post-design-boundary.sh` (or successor harnesses) when tmpdir resolution or hook registration changes.
