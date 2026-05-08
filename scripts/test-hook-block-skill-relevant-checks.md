# test-hook-block-skill-relevant-checks.sh

Purpose: regression-test `scripts/hook-block-skill-relevant-checks.sh` and its active-session resolver.

The harness constructs disposable `.larch-keepalive` fixtures under `${XDG_CACHE_HOME}/larch/sessions`, then asserts that both `tool_input.skill` and `tool_input.skill_name` shapes deny `/relevant-checks` inside active `claude-implement-*` and `claude-review-*` sessions. It also covers `larch:relevant-checks`, non-target skills, cwd mismatch, session mismatch, stale keepalive TTL, and missing-`jq` fail-open behavior.

Primary callers: `make test-hook-block-skill-relevant-checks` and `make test-harnesses`.

Edit in sync: update this harness with `scripts/hook-block-skill-relevant-checks.sh`, `scripts/hook-block-skill-relevant-checks.md`, `scripts/lib-resolve-active-larch-session.sh`, and `hooks/hooks.json` whenever hook payload parsing, active-session matching, deny output, or fail-open behavior changes.
