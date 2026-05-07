---
paths: ["skills/research/SKILL.md", "scripts/deny-edit-write.sh", "scripts/deny-edit-write.md", "scripts/test-deny-edit-write.sh", "scripts/test-deny-edit-write.md", "SECURITY.md"]
---

# /research Read-Only Hook Coupling

`/research` is the only larch skill whose SKILL.md frontmatter wires a
PreToolUse `hooks:` block to
`${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh` against the matcher
`Edit|Write|NotebookEdit`. This three-part contract — frontmatter
matcher, deny script, and `SECURITY.md` framing — is what enforces the
advertised read-only-repo posture for `/research`. The harness
`scripts/test-deny-edit-write.sh` pins the script-side allow predicate
but not the SKILL.md frontmatter shape.

When you edit any of the four parts (SKILL.md frontmatter, deny script,
harness, security framing), check the other three in the same change:

- The matcher must remain exactly `Edit|Write|NotebookEdit` unless the
  hook and harness are redesigned together. Widening the matcher
  without updating `scripts/test-deny-edit-write.sh` produces a green
  harness that no longer covers the new tools; narrowing it weakens the
  advertised contract.
- The hook command must stay anchored at
  `${CLAUDE_PLUGIN_ROOT}/scripts/deny-edit-write.sh` so it resolves
  against the plugin install tree, not the consumer cwd.
- The deny script's allow predicate must remain canonical-`/tmp`-only:
  exact equality with `ALLOWED_ROOT` (canonical `/tmp`) or
  `$ALLOWED_ROOT/`-prefixed. Bash, Skill, Agent, and external-tool
  writes are NOT mechanically enforced by this hook —
  session-tmpdir conventions and external reviewer policy are covered
  by prompt-level posture and `SECURITY.md`, not the PreToolUse guard.
- `SECURITY.md` must continue to describe the contract end-to-end,
  including the `Bash`-residual mechanical bypass.

**prevents**: silent weakening of `/research`'s advertised
read-only-repo contract — agents mutating the repo via `Edit`/`Write`/
`NotebookEdit` despite the prompt-level posture, with the harness
still passing because no test pins the SKILL.md frontmatter shape.
