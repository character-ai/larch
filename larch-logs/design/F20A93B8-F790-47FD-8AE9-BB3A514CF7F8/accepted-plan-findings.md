### FINDING_1: `diff_lines: 280` is likely undercount
- **Concern**: The plan touches ~20 Bash blocks in `skills/design/SKILL.md` (each gets a one-line prelude addition), plus deletes the Step 1 block (~30 lines), modifies `approval-gates.md` Gate A section (~50 lines net), adds a new ~80-line writer script + ~30-line .md sibling, adds a new ~100-line regression harness + ~30-line .md sibling, and touches step-name-registry.tsv + flags.md + AGENTS.md narrative changes. A more honest estimate is ~340-380 lines added/changed. Update the trailing `diff_lines:` line accordingly.
- **Proposed resolution**: Bump `diff_lines:` to `360` (round to nearest 20).

### FINDING_2: Ambiguity in prelude form (conditional vs unconditional source)
- **Concern**: The plan body says both "The prelude is one line: `source ~/.cache/larch/design-current-env.sh` (with a conditional `[ -f ... ] && source ...` for the first Step 0 block where the file doesn't exist yet)" and "Prepend the prelude line to every Bash block from Step 1c onward." Implementers will not know whether to use conditional or unconditional source for blocks after Step 0.
- **Proposed resolution**: Standardize on the conditional form `[ -f ~/.cache/larch/sessions/current-design-env.sh ] && source ~/.cache/larch/sessions/current-design-env.sh` for EVERY non-Step-0 Bash block. This protects against pre-upgrade in-progress runs and against unexpected absences (the env-var bug surfaces clearly as "DESIGN_TMPDIR: unbound variable" with `set -u`, rather than as a corrupted source). Document this single form in the new "Bash block prelude" subsection.

### FINDING_3: Anti-pattern #4 half-rewrite adds churn without payoff
- **Concern**: The plan proposes to "keep the structural rule but rewrite the body" of Anti-pattern #4 (`NEVER pass --caller-env to session-setup.sh when SESSION_ENV_PATH is empty`). Since SESSION_ENV_PATH is never non-empty in production (the user's "/design NEVER runs from /implement EVER" decision), the rule's preamble becomes vacuously true and the body becomes misleading.
- **Proposed resolution**: Leave Anti-pattern #4 entirely unchanged in this PR — it remains a correct defensive rule even though its current trigger is unreachable. Broader nested-mode cleanup (including this anti-pattern's eventual fate) is the follow-up OOS_1.

### FINDING_4: Symlink path inconsistent with existing `~/.cache/larch/sessions/...` convention
- **Concern**: The plan proposes `~/.cache/larch/design-current-env.sh` as the stable handoff path. Existing session tmpdirs live under `~/.cache/larch/sessions/<...>`. Inconsistent naming will confuse operators looking for /design session state.
- **Proposed resolution**: Use `~/.cache/larch/sessions/current-design-env.sh` for the stable symlink (still a symlink, still under the `sessions/` parent). Update all SKILL.md prelude references and the writer's `--output` default. Reflected in FINDING_2's resolution above.
