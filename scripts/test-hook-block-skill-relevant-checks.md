# test-hook-block-skill-relevant-checks.sh

Purpose: regression-test `scripts/hook-block-skill-relevant-checks.sh` and its active-session resolver.

The harness constructs disposable `.larch-keepalive` fixtures under `${XDG_CACHE_HOME}/larch/sessions`, then asserts that both `tool_input.skill` and `tool_input.skill_name` shapes deny `/relevant-checks` inside active `claude-implement-*` and `claude-review-*` sessions. It also covers `larch:relevant-checks`, non-target skills, cwd mismatch (allow), hook-session-id mismatch (deny — confirms resolver binds on cwd + TTL only, never on the hook payload's `session_id`), stale keepalive TTL (allow), and missing-`jq` fail-open behavior. A `/tmp`-fallback fixture exercises the resolver's acceptance of `/tmp/claude-implement-*` direct children.

Primary callers: `make test-hook-block-skill-relevant-checks` and `make test-harnesses`.

Edit in sync: update this harness with `scripts/hook-block-skill-relevant-checks.sh`, `scripts/hook-block-skill-relevant-checks.md`, `scripts/lib-resolve-active-larch-session.sh`, and `hooks/hooks.json` whenever hook payload parsing, active-session matching, deny output, or fail-open behavior changes.
