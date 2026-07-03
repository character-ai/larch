### [rejected] FINDING_4

**Rejected subtype:** dismissed (0 YES)

### FINDING_4: Consumer aliases point at the dev-only readability path
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: important
- **Concern**: `python/larch/core/alias_skill.py` generates private aliases in consumer repos with a `$PWD/skills/shared/readability-style.md` directive, but non-plugin targets resolve to `.claude/skills` and usually do not have that shared file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Use `${CLAUDE_PLUGIN_ROOT}/skills/shared/readability-style.md` for consumer-repo aliases, and reserve `$PWD/...` only for this repo’s dev-only `.claude/skills`; add a regression that combines non-plugin target resolution with `alias generate`.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0

