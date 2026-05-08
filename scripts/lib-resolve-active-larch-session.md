# lib-resolve-active-larch-session.sh

Purpose: resolve whether a Claude Code hook event belongs to an active larch `/implement` or `/review` session. It is an executable helper, not a sourced library, so hooks can call it without sharing shell state.

Primary caller: `scripts/hook-block-skill-relevant-checks.sh`.

Input: hook JSON on stdin. The helper reads `.cwd` and `.session_id` with `jq`. Missing `jq`, malformed JSON, missing `cwd`, or missing `session_id` all fail open with empty stdout and exit 0.

Resolution contract: scan `${XDG_CACHE_HOME:-$HOME/.cache}/larch/sessions/` for `claude-implement-*` and `claude-review-*` directories containing `.larch-keepalive`. A candidate matches only when `CLONE_PATH=<cwd>` and `SESSION_ID=<session_id>` are both present and exact. The helper does not depend on `manifest.env`, so quick-mode `/implement` and standalone `/review` sessions are covered.

Staleness: `.larch-keepalive` mtime must be younger than `LARCH_ACTIVE_SESSION_TTL_SECONDS` (default 21600). Set the variable to `0` in tests to disable TTL. When `date +%s` or `stat` cannot produce numeric values, the candidate is skipped.

Output: empty stdout on no match. On match, one line:

```text
PREFIX=claude-implement TMPDIR=/path/to/session
```

or `PREFIX=claude-review ...`.

Harness: `scripts/test-hook-block-skill-relevant-checks.sh` covers resolver-positive, resolver-negative, stale, cwd mismatch, session mismatch, and jq-missing behavior through the hook.

Edit in sync: update this file, `scripts/hook-block-skill-relevant-checks.sh`, and `scripts/test-hook-block-skill-relevant-checks.sh` when changing keepalive keys, root enumeration, TTL behavior, or stdout grammar.
