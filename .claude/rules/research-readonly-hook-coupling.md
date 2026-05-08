---
paths: ["skills/research/SKILL.md", "scripts/deny-edit-write.sh", "scripts/deny-edit-write.md", "scripts/test-deny-edit-write.sh", "scripts/test-deny-edit-write.md", "SECURITY.md"]
---

# /research Read-Only Hook Coupling

`/research` is the only larch skill whose SKILL.md frontmatter wires a
PreToolUse `hooks:` block to
`${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh` against the matcher
`Edit|Write|NotebookEdit`. Frontmatter matcher, deny script, and
`SECURITY.md` framing enforce `/research`'s advertised read-only-repo
posture. The harness `scripts/test-deny-edit-write.sh` pins only the
script-side allow predicate, not the SKILL.md frontmatter shape.

When editing any part (SKILL.md frontmatter, deny script, harness,
security framing), check the other three in the same change:

- Keep the matcher exactly `Edit|Write|NotebookEdit` unless redesigning
  hook and harness together. Widening it without updating
  `scripts/test-deny-edit-write.sh` leaves a green harness that misses new
  tools; narrowing it weakens the advertised contract.
- Keep the hook command anchored at
  `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh` so it resolves in
  the plugin install tree, not the consumer cwd.
- The deny script's allow predicate must remain canonical-`/tmp`-only:
  exact equality with `ALLOWED_ROOT` (canonical `/tmp`) or
  `$ALLOWED_ROOT/`-prefixed. Bash, Skill, Agent, and external-tool writes
  are NOT mechanically enforced by this hook; session-tmpdir conventions
  and external reviewer policy rely on prompt-level posture and
  `SECURITY.md`, not the PreToolUse guard.
- `SECURITY.md` must continue to describe the contract end-to-end,
  including the `Bash`-residual mechanical bypass.

**prevents**: silent weakening of `/research`'s advertised read-only-repo
contract; agents mutating the repo via `Edit`/`Write`/`NotebookEdit`
despite prompt posture, while the harness still passes because no test
pins the SKILL.md frontmatter shape.
