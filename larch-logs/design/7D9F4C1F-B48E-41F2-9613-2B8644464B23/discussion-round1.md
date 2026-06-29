## Decision 1: Cap value
- **Question**: Is 200 chars the exact description length cap, or should a different value be used?
- **Resolution**: 200 chars. The issue lists "for example 200 chars" and identifies 8 public skills with 200-250 char descriptions, matching that boundary. All 14 descriptions over 200 chars (including dev-only ones) are compressed; the 14 under-200 ones are untouched.
- **Source**: codebase (measured all 28 values; split at 200 is natural)

## Decision 2: What "length" means for the lint
- **Question**: Does the lint check the description VALUE length (text only) or the YAML frontmatter line length?
- **Resolution**: VALUE length (text, excluding `description: ` prefix and surrounding quotes). Issue's specific numbers (249, 243, etc.) confirm this is VALUE-based.
- **Source**: codebase (verified against actual SKILL.md files)

## Decision 3: Dev-only skill descriptions
- **Question**: Are dev-only `.claude/skills/*/SKILL.md` descriptions in scope for compression?
- **Resolution**: Yes, explicitly. The issue scope states "description: fields in skills/*/SKILL.md and dev-only .claude/skills/*/SKILL.md". Six dev-only descriptions are over 200 chars (combine-issues 834, agnix-fix 373, release 316, audit-runs 289, rebalance-tests 271, analyze-issues 252).
- **Source**: issue body, codebase

## Decision 4: Lint placement
- **Question**: Where should the new length-cap lint live?
- **Resolution**: New Python module `python/larch/lint/lint_skill_description_length.py`, registered in `python/larch/cli.py`, wired as a local pre-commit hook, tested in `python/test_lint_skill_description_length.py`. Matches the pattern used by `lint-skill-invocations` and other local lints.
- **Source**: codebase (examined lint/ directory and .pre-commit-config.yaml)

3 decisions resolved from codebase; 1 from issue body.
