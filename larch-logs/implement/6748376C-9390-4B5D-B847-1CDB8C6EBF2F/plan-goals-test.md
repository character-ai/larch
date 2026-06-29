## Goal
Implement issue #5784: [IMPLEMENTING] md-to-py-IX: compress skill description frontmatter (Tier-1) + length-cap lint.

## Implementation Plan
## Plan

## Approach

Implement the approved outline with the smallest safe change.

- Treat `approach-synthesis.txt` as `NO_SKETCHES`.
- Keep scope to `description:` frontmatter in:
  - `skills/*/SKILL.md`
  - `.claude/skills/*/SKILL.md`
- Compress only the 14 descriptions currently over 200 chars.
- Keep every rewritten value in `Use when ...` form so `agent-lint` S017 stays satisfied.
- Add a new stdlib-only lint:
  - command: `python3 python/cli.py lint skill-description-length`
  - cap: description value length `<= 200`
  - length unit: Python `len()` of the extracted value, excluding `description:` and matching surrounding quotes.
- Do not edit SKILL bodies or `@` import prose.

## Files to modify/create

### UPDATED: skills/alias/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when creating shortcut aliases for existing larch skills with preset flags. Routes plugin-source aliases to skills/ unless --private forces .claude/skills/.`

### UPDATED: skills/bug/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when filing, investigating, or root-causing a software bug. Reads the repo, drafts a detailed GitHub issue, and invokes /issue with dedup enabled.`

### UPDATED: skills/design/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when authoring or vetting an issue-anchored GitHub implementation plan. Runs direct drafting, plan review, clarify loop, and issue-body plan markers.`

### UPDATED: skills/fluff-analysis/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when analyzing review fluff in committed larch run logs: rejected, OOS, or accepted-low-value findings, plus tuning recommendations.`

### UPDATED: skills/gc-run-logs/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when slimming or deleting aged larch run-log directories to cap repo growth. Applies age retention and creates a log-only PR for operator merge.`

### UPDATED: skills/issue/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when creating GitHub issues with semantic dedup and blocker-dependency analysis. Supports single or batch mode plus dry-run and dependency flags.`

### UPDATED: skills/set-up-forked-open-source-repo/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when configuring a clone for upstream-fork OSS work: set origin/upstream remotes, disable upstream pushes, and optionally mirror-sync the fork.`

### UPDATED: skills/voter-calibration/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when analyzing voter agreement, severity calibration, and chronic outliers from committed larch run logs. Diagnostic only; changes no thresholds or points.`

### UPDATED: .claude/skills/agnix-fix/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when fixing an open agent-sh/agnix issue from this larch clone. Prepares fork label state, then forwards to /implement --forked after /design writes the plan.`

### UPDATED: .claude/skills/analyze-issues/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when generating a GitHub-issue backlog report: coverage, categories, growth chart, waste signatures, reviewer/persona, and voter diagnostics.`

### UPDATED: .claude/skills/audit-runs/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when auditing recently merged larch run logs for anomalies, filing the chain-of-history audit issue, and proposing user-approved bug follow-ups.`

### UPDATED: .claude/skills/combine-issues/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when combining open issues to reduce issue count and token cost. Use /combine-issues --oos for OOS issues; verifies actuality and proposes combined replacements.`

### UPDATED: .claude/skills/rebalance-tests/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when rebalancing CI test harness shards, Python unit test shards, or both from recent timings. Creates one PR and verifies the selected shard plan.`

### UPDATED: .claude/skills/release/SKILL.md

Replace only the `description:` value with a shorter S017-compliant value, for example:

`Use when cutting a larch release: collect merged PRs, classify semver bump, open and merge the version PR, tag, publish GitHub Release, and promote Latest.`

### NEW: python/larch/lint/lint_skill_description_length.py

Add a stdlib-only lint module.

Implementation shape:

- Define `MAX_DESCRIPTION_CHARS = 200`.
- Define `GLOB_PATTERNS = ("skills/*/SKILL.md", ".claude/skills/*/SKILL.md")`.
- Use `lint_common.run_file_lint(...)` for shared `--root`, error handling, and exit codes.
- Enumerate matching skill files in deterministic order.
- Read UTF-8 text.
- Normalize BOM and CRLF.
- Extract YAML frontmatter bounded by leading `---` and the next `---`.
- Find the top-level `description:` line.
- Extract the value text:
  - remove the `description:` prefix
  - trim whitespace
  - strip an inline comment only when `#` appears outside quotes and after whitespace
  - strip one matching pair of surrounding single or double quotes
- Measure only the extracted value with `len(value)`.
- Emit one violation per over-cap skill:
  - include lint name, relative path, observed length, cap, and a short repair hint.
- Ignore missing `description:` fields so this lint does not duplicate `agent-lint` schema or S017 behavior.

### NEW: python/test_lint_skill_description_length.py

Add focused pytest coverage.

Tests to include:

- clean quoted description at exactly 200 chars passes.
- 201-char description fails with relative path, observed length, and cap.
- both `skills/*/SKILL.md` and `.claude/skills/*/SKILL.md` are scanned.
- missing `description:` exits 0 and does not duplicate schema validation.
- unquoted value length is measured correctly.
- inline comments after unquoted values do not count.
- `#` inside quoted descriptions counts as content, not a comment.
- CRLF and UTF-8 BOM are accepted.
- non-UTF-8 input returns exit 2 through `LintError`.
- malformed frontmatter without a closing marker does not crash.

### UPDATED: python/larch/cli.py

Register the new command in `_REGISTRY` near the other lint entries:

- `("lint", "skill-description-length"): ("larch.lint.lint_skill_description_length", "main")`

### UPDATED: .pre-commit-config.yaml

Add a local hook for the new lint.

Preferred placement: near the existing `lint-skill-invocations` hook.

Hook shape:

- id: `lint-skill-description-length`
- name: `Lint skill description length`
- entry: `python3 python/cli.py lint skill-description-length`
- language: `system`
- pass_filenames: `false`
- always_run: `true`
- files: `^(skills|\.claude/skills)/[^/]+/SKILL\.md$`

### UPDATED: Makefile

Wire local convenience targets.

Changes:

- Add `lint-skill-description-length` to `.PHONY`.
- Add `test-lint-skill-description-length` to `.PHONY`.
- Add `lint-skill-description-length` to the `lint:` dependency list near other direct custom lints.
- Add target:

`lint-skill-description-length:
	python3 python/cli.py lint skill-description-length`

- Add target:

`test-lint-skill-description-length:
	python3 python/cli.py timing harness-mark --label $@ -- python3 -m pytest python/test_lint_skill_description_length.py -q`

## Edge cases

- **S017 trigger clause:** every compressed description must still start with `Use when`.
- **Value length:** measure only the value, not `description: ` or quotes.
- **Unquoted descriptions:** support them in the lint even if current repo values are quoted.
- **Inline comments:** ignore comments outside quotes for unquoted values.
- **Quoted `#`:** count it as content.
- **Malformed frontmatter:** do not crash. Treat missing or malformed description as no length violation.
- **Read errors:** preserve fail-closed exit 2 via `LintError`.

## Failure modes

- A compressed description can become too vague and reduce trigger quality.
  - Mitigation: preserve the main noun, action, and trigger phrase for each skill.
- The new lint can overlap with `agent-lint`.
  - Mitigation: enforce only length. Leave trigger wording and schema requirements to `agent-lint`.
- Pre-commit can fail to run on scoped SKILL changes if the hook uses filenames incorrectly.
  - Mitigation: use `always_run: true` and `pass_filenames: false`, matching existing repo lint style.

## Testing strategy

Run focused checks:

- `python3 -m pytest python/test_lint_skill_description_length.py -q`
- `python3 python/cli.py lint skill-description-length`
- `python3 python/cli.py lint skill-invocations`
- `pre-commit run lint-skill-description-length --all-files`

Run related repo targets if time permits:

- `make test-lint-skill-description-length`
- `make lint-skill-description-length`
- `make agent-lint`

## Acceptance

Run focused checks:

- `python3 -m pytest python/test_lint_skill_description_length.py -q`
- `python3 python/cli.py lint skill-description-length`
- `python3 python/cli.py lint skill-invocations`
- `pre-commit run lint-skill-description-length --all-files`

Run related repo targets if time permits:

- `make test-lint-skill-description-length`
- `make lint-skill-description-length`
- `make agent-lint`

diff_added: 300
diff_deleted: 14
mechanical_churn: false
diff_lines: 314

## Test plan
(no test plan section in plan-file)
