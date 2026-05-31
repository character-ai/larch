## Proposed Design Outline

### Goals
- Replace `/implement`'s 41 byte-identical 4-line awk plugin-root rehydration fences with one guarded source line each.
- Emit a minimal, tmpdir-local `plugin-root.env` from the sanctioned writer (`write-session-env.sh`) so each prelude only **sources** one export.
- Remove ~120 lines of repeated boilerplate from `skills/implement/SKILL.md` with zero behavioral change.

### Non-goals
- No change to `/design` or `/review` preludes (already fence-free; defer to OOS).
- No new runtime behavior — same resolved `CLAUDE_PLUGIN_ROOT` value; refactor-only.
- No mutation of `session-env.sh` and no prompt-side env writes (NEVER #14 intact).

### Approach sketch
- Extend `scripts/write-session-env.sh` to also emit a sibling `plugin-root.env` (`CLAUDE_PLUGIN_ROOT=<value>` + `export`) next to its `--output` target, reusing the already-validated `CLAUDE_PLUGIN_ROOT_VALUE`.
- Replace each awk fence with: `[ -z "${CLAUDE_PLUGIN_ROOT:-}" ] && [ -n "${IMPLEMENT_TMPDIR:-}" ] && [ -f "$IMPLEMENT_TMPDIR/plugin-root.env" ] && . "$IMPLEMENT_TMPDIR/plugin-root.env"` (guards keep it a safe no-op at cold start / under `set -u`).
- Update the "Bash block prelude" prose to document the one-line form as canonical.
- Add writer-side regression that `plugin-root.env` is emitted and sources cleanly.

### Surfaces in scope
- `skills/implement/SKILL.md` — 41 fence sites + the "Bash block prelude" prose.
- `scripts/write-session-env.sh` (+ `write-session-env.md` contract sibling).
- Rehydration/writer tests: `test-session-env-roundtrip.sh`, `test-implement-timing-rehydration.sh`, `test-run-step5-review.sh`, `test-run-step1-plan-log.sh`.
- `lint-skill-md-flag-signature.sh` — verify it still resolves unchanged `${CLAUDE_PLUGIN_ROOT}/…` tokens.

### Open questions
- None. (Cold-start no-op and `set -u`/`IMPLEMENT_TMPDIR` guard resolved in Round 1.)
