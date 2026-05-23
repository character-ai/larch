## Decision 1: Marker shape enforcement granularity
- **Question**: Should the canonical `**⚠ Foreground required — do NOT set \`run_in_background: true\`.**` banner be the ENTIRE prose unit above the fence, or only the LEADING line of a longer warning paragraph?
- **Resolution**: Leading-line match — the canonical phrase MUST appear as the leading line; longer paragraphs (e.g., the `ship-pr.sh` state-machine context, recovery patterns, `--resume-phase` semantics) stay intact below the canonical leader.
- **Source**: user

## Decision 2: Lint location
- **Question**: Should the lint live in a dedicated new target (`make lint-foreground` + `scripts/test-foreground-markers.sh`), or extend existing skill structure tests (`scripts/test-design-structure.sh`, `scripts/test-implement-structure.sh`)?
- **Resolution**: Dedicated new target. New `Makefile` entry + new `scripts/test-foreground-markers.sh` harness file.
- **Source**: user

## Decision 3: Audit and lint coverage for `.claude/` dev surfaces
- **Question**: Should the audit/lint cover `.claude/skills/*/SKILL.md` and `.claude/rules/*.md` in addition to runtime `skills/**/SKILL.md` + `skills/**/references/*.md`?
- **Resolution**: Include `.claude/skills/*/SKILL.md` and `.claude/rules/*.md`. Per `AGENTS.md` they are Tier-1b and Tier-1c sources loaded into Claude's context and can invoke blocking scripts — same drift risk.
- **Source**: user

## Decision 4: Inline `# Foreground required` comment placement
- **Question**: Where in the bash code fence should the `# Foreground required: see BASH_AUTHORING.md §4` comment go?
- **Resolution**: Immediately above the invocation line of the denylisted script (matches the preview the user accepted with the Banner+comment option). Lint asserts the comment is within ±5 source lines above the invocation line, inside the same fenced code block.
- **Source**: codebase (preview shown to and accepted by user during clarification)

## Decision 5: Bash blocks invoking multiple Family B scripts
- **Question**: When a single fenced bash block invokes multiple denylisted basenames (e.g., a block that runs `collect-agent-results.sh` then a tally helper), does each invocation need its own marker pair?
- **Resolution**: One marker pair per FENCE is sufficient when the fence contains a single Family B basename; when a fence contains multiple Family B basenames, the lint requires at minimum the canonical ⚠ banner above the fence AND a `# Foreground required` comment within ±5 lines of EACH Family B invocation line. Why: the inline comment is the per-invocation override against the Bash-tool background-bias reflex; one comment far away from a second invocation in the same fence does not adequately remind Claude on the second invocation.
- **Source**: codebase

## Decision 6: Test scripts under `scripts/test-*.sh`
- **Question**: Should the lint scan test harness files for Family B basename invocations?
- **Resolution**: No — the audit scope (`skills/**/SKILL.md`, `skills/**/references/*.md`, `.claude/skills/*/SKILL.md`, `.claude/rules/*.md`) is .md-only by construction. Test harnesses are .sh files and naturally fall outside scope. Why: test harnesses fabricate fake invocations as fixture text; flagging them would be false positives.
- **Source**: codebase
