# skills/implement/scripts/hook-stop-fail-close.sh — contract

`hook-stop-fail-close.sh` is the plugin-shipped `Stop` hook that guards post-skill halt boundaries inside an active `/implement` run (post-/review; the retired post-/design manifest gate is no longer enforced here — issue #2487).

**Post-/review boundary** (issue #1862): blocks session stop when `review-round-summary.md` exists (review ran) but neither `.review-boundary-passed` nor `.run-cleaned-up` exists. `.review-boundary-passed` is written by the orchestrator at the start of Step 6 after all three required post-/review actions complete (Cross-Skill Presence Propagation + Track Rejected Code Review Findings + Step 6 breadcrumb). Recovery: execute those three actions in order, then `touch "$IMPLEMENT_TMPDIR/.review-boundary-passed"`.

**Post-/release boundary — retired Phase 1 (#3364):** `/implement` no longer arms a release sentinel or runs a release precheck gate on the ship path; version bumps are operator- or `/release`-initiated via `.claude/skills/release/SKILL.md`. This hook no longer enforces a post-/release stop gate.

All checks share the `.run-cleaned-up` sentinel as the terminal escape: once teardown writes it the hook allows all stops through. The `stop_hook_active` guard prevents a continuation-loop trap. The block envelope shape (top-level `{"decision":"block","reason":"..."}`) was verified against the Claude Code hooks reference. If `jq` is missing, the hook emits a static literal block envelope.

The hook reads `session_id` from the Stop payload before tmpdir resolution. A non-empty `session_id` is surfaced as `LARCH_TOKEN_SESSION_ID` so `scripts/larch.sh session resolve-implement-tmpdir` can bind to the matching session identity. An empty, missing, or null `session_id` unsets any inherited `LARCH_TOKEN_SESSION_ID` before tmpdir resolution, then the resolver can fall back to TTL matching.

Tmpdir resolution is delegated to `scripts/larch.sh session resolve-implement-tmpdir --cwd "$HOOK_CWD"`. Before spawning the resolver, the hook performs a cheap bash glob pre-check for `claude-implement-*` directories under these roots:

1. `${XDG_CACHE_HOME:-${HOME:-/tmp}/.cache}/larch/sessions`
2. `/tmp`
3. `/private/tmp`

The resolver call is fail-open and must keep this capture shape:

```bash
IMPLEMENT_TMPDIR=$(CLAUDE_PLUGIN_ROOT="$PLUGIN_ROOT" "$PLUGIN_ROOT/scripts/larch.sh" session resolve-implement-tmpdir --cwd "$HOOK_CWD" 2>/dev/null) || IMPLEMENT_TMPDIR=""
```

A failed resolver, empty stdout, a missing matching tmpdir, a stale candidate, or `.run-cleaned-up` all allow Stop to proceed.

Edit in sync with `hooks/hooks.json`, `skills/implement/SKILL.md` Steps 6 and 8, `crates/larch-cli/src/session_lifecycle_commands.rs`, and `scripts/test-implement-anti-halt.sh`.
