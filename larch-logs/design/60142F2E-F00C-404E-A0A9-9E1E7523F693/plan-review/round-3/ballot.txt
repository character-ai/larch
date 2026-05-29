### FINDING_1: Dedup helper changes do not trigger owning harness
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Concern**: New dedup helper is not mapped to `test-plan-review-loop`. Scenario: a future change touching only `skills/design/scripts/dedup-plan-lines.py` or its sibling doc can pass `relevant-checks` without running the harness that owns dedup behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add skills/design/scripts/dedup-plan-lines.py and skills/design/scripts/dedup-plan-lines.md to the existing plan-review-loop case that appends test-plan-review-loop

### FINDING_2: Planned dead-script exclusion may widen lint coverage unnecessarily
- **Reviewer(s)**: Cursor-dyn-exclusion-scope-audit
- **Severity**: important
- **Concern**: Mandatory dead-script exclusion for `dedup-plan-lines.py` may be unnecessary scope creep. Scenario: `plan-review-loop.sh` already uses the same `$PLUGIN_ROOT` assignment plus `"$VAR"` invocation for `DESIGN_DRIVER_SH` / `CHECK_PLAN_SIZE_SH` / `INVOKE_PLAN_VALIDATOR_SH` without `agent-lint.toml` entries (`plan-review-loop.sh:21-23`, `:603`, `:624`, `:639`); adding `dedup-plan-lines.py` to the global exclude list widens dead-script coverage without evidence `G004` fails on that pattern.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-exclusion-scope-audit: Omit the .py exclude unless relevant-checks/agent-lint flags the new file after the DEDUP_PLAN_LINES_PY assignment lands; keep the focused dedup-plan-lines.md sibling-block exclusion (or a literal cite from plan-review-loop.md / SKILL.md) for S030
