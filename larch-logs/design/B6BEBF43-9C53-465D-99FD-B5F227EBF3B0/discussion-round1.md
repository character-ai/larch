## Decision 1: Scrub depth (historical vs. runtime)
- **Question**: How thoroughly should references to these 6 skills be scrubbed beyond the skill directories themselves?
- **Resolution**: Runtime refs only. Delete the 6 skill dirs + their tests, and update runtime files (README.md, docs/skills.md, .claude/settings.json, agent-lint.toml, SECURITY.md, shared docs in skills/shared/, alias/resolve-target, and scripts/test-*.sh harnesses that fixture these skills). Leave CHANGELOG.md entries and larch-logs/ run records untouched (they are immutable history).
- **Source**: user

## Decision 2: Umbrella workflow integration in /issue and SECURITY.md
- **Question**: Should the planned implementation also remove the `umbrella` workflow integration in `/issue` (e.g., `/umbrella` references in create-one.{sh,md}, parse-input.md, SECURITY.md `/umbrella --blocked-by-issue` section + helpers.sh wire-dag entries)?
- **Resolution**: Yes, scrub umbrella refs broadly. Update SECURITY.md to remove the `/umbrella --blocked-by-issue` section and umbrella-specific helpers.sh wire-dag bullets. Update /issue prose to drop `/umbrella` workflow caller references. The `--blocked-by-issue` flag in /issue is caller-agnostic and stays; only `/umbrella`-specific prose is scrubbed.
- **Source**: user
