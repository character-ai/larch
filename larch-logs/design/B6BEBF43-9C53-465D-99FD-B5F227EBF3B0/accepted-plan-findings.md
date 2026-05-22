### FINDING_1: skills/show-skill/scripts/show.sh missing from plan's delete list
- **Concern**: The plan lists `skills/show-skill/` contents as "SKILL.md + scripts/show.md + scripts/test-show-skill.{sh,md}" but omits `scripts/show.sh`. The actual contents are `show.{sh,md}` + `test-show-skill.{sh,md}` (4 files in scripts/, not 3). The `git rm -rf skills/show-skill/` handles deletion correctly regardless, but the plan's documentation is incomplete and could mislead future reviewers.
- **Proposed resolution**: Update the "Files to delete" section to list `skills/show-skill/` as `SKILL.md + scripts/{show.{sh,md}, test-show-skill.{sh,md}}`.

### FINDING_2: skills/compress-skill/scripts/discover-md-set.{sh,py} missing from plan's delete list
- **Concern**: The plan lists `skills/compress-skill/` contents as "SKILL.md + scripts/build-feature-description.{sh,md}" (2 files in scripts/), but the actual contents include `discover-md-set.sh` and `discover-md-set.py` as well (4 files in scripts/, not 2). The `git rm -rf` handles deletion regardless, but the plan documentation is incomplete.
- **Proposed resolution**: Update the "Files to delete" section to list `skills/compress-skill/` as `SKILL.md + scripts/{build-feature-description.{sh,md}, discover-md-set.{sh,py}}`.

### FINDING_3: agent-lint.toml line 164 comment update not in plan
- **Concern**: The comment at agent-lint.toml lines 158–168 enumerates pure-delegator SKILL.md files including `create-skill, simplify-skill, compress-skill` (line 164). The plan covers removal of allowed-path entries and other comments (lines 79–90, 866, 873, 1068, 525, 1067, 1075, 1126) but does not explicitly call out updating this list comment. After Phase 5 strips the same names from `scripts/test-anti-halt-banners.sh:48–50`'s `DELEGATORS` array, the comment will be out of sync with the harness.
- **Proposed resolution**: Add an explicit edit to agent-lint.toml line 164: update the pure-delegators enumeration to list only the remaining delegators (`im, imaq`).

### FINDING_4: Makefile test-render-skill bundles two skill harnesses
- **Concern**: The plan lists `test-render-skill` in the targets-to-remove block but does not mention that this Makefile target's recipe has TWO lines: one invokes `skills/create-skill/scripts/test-render-skill-md.sh` and the other invokes `skills/show-skill/scripts/test-show-skill.sh`. Both lines are removed when the target is removed; this is documented for clarity in the plan to avoid ambiguity for reviewers.
- **Proposed resolution**: In the Makefile section, note explicitly that `test-render-skill` aggregates both a `create-skill` harness AND a `show-skill` harness, both removed by the target's deletion.

### FINDING_5: `/review --no-issues` flag documentation not in plan's Phase 3 doc updates
- **Concern**: The plan updates `skills/review/SKILL.md` to drop the `/umbrella` auto-issue-filing path and recommends removing the `--no-issues` flag. But the `--no-issues` flag is also documented in `README.md` (description of /review row), `docs/skills.md` (line discussing `/review` description mode), and `docs/workflow-lifecycle.md` (the `/review` Standalone Usage entry). After the auto-filing is removed, these docs should drop the `--no-issues to suppress` parenthetical. The plan's `skills/shared/voting-protocol.md` updates partially overlap but the README and docs prose is not explicitly listed.
- **Proposed resolution**: Add three doc edits to Phase 3: update `README.md` `/review` row, `docs/skills.md` `/review` entry, and `docs/workflow-lifecycle.md` Standalone Usage `/review` entry to remove the `--no-issues to suppress` framing now that there is nothing to suppress.
