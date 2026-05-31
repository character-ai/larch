### OOS_1:
- **Description**: Age is measured by each entry's top-level mtime persists after plan lands. Scenario: `docs/skills.md` is manually maintained (not auto-generated from SKILL.md), is covered by `scripts/test-quick-mode-docs-sync.sh` as a checked public doc but "top-level mtime" is not in STALE_PHRASES — so no CI guard catches it. After the plan corrects five files, docs/skills.md remains directly contradictory to all of them.
- **Reviewer**: unknown-slot
- **Severity**: important
- **Focus area**: architecture
- **Location**: docs/skills.md:47
- **Phase**: design

