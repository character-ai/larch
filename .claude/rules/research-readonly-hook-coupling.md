---
paths: ["skills/research/SKILL.md", "skills/research/references/research-phase.md", "skills/bug/SKILL.md", "scripts/deny-edit-write.sh", "scripts/deny-edit-write.md", "scripts/test-deny-edit-write.sh", "scripts/test-deny-edit-write.md", "scripts/test-research-structure.sh", "scripts/test-research-structure.md", "scripts/test-bug-structure.sh", "scripts/test-bug-structure.md", "SECURITY.md"]
---

# Read-Only Hook Coupling

`scripts/deny-edit-write.sh` is a token-gated PreToolUse hook currently wired by two skills:

- `/research`: matcher `Edit|Write|NotebookEdit`, command `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh research`.
- `/bug`: matcher `Write`, command `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh bug`.

The frontmatter matchers, token arguments, activation sentinels, deny script, harnesses, and `SECURITY.md` framing enforce each skill's advertised no-repo-write posture.

When editing any part, check the coupled surfaces in the same change:

- Keep `/research`'s matcher exactly `Edit|Write|NotebookEdit` unless redesigning hook and harness together. Widening it without updating `scripts/test-deny-edit-write.sh` leaves a green harness that misses new tools; narrowing it weakens the advertised contract.
- Keep `/bug`'s matcher `Write` unless redesigning the `/bug` scratch-write flow and structural tests together.
- Keep hook commands anchored at `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh <token>` so they resolve in the plugin install tree, not the consumer cwd.
- Keep recognized activation token prefixes limited to `research` and `bug`, with TTL-bounded liveness, no `$PPID` correlation, and tokenless or unknown invocations inactive. A fresh `bug-*` sentinel must not activate a `research` hook, and a fresh `research-*` sentinel must not activate a `bug` hook.
- While active, the deny script's allow predicate must remain canonical-`/tmp`-only: exact equality with `ALLOWED_ROOT` (canonical `/tmp`) or `$ALLOWED_ROOT/`-prefixed. Bash, Skill, Agent, and external-tool writes are NOT mechanically enforced by this hook; session-tmpdir conventions and external reviewer policy rely on prompt-level posture and `SECURITY.md`, not the PreToolUse guard.
- `SECURITY.md` must continue to describe the contract end-to-end, including the activation gate, stale-registration fail-open behavior, `/bug` as a hook consumer, and the `Bash` residual mechanical bypass.

**prevents**: silent weakening of `/research`'s or `/bug`'s advertised read-only-repo contract; leaked tokenless hook registrations blocking unrelated skills; one skill's fresh sentinel re-arming the other skill's leaked registration; agents mutating the repo via matched Claude tools while harnesses still pass.
