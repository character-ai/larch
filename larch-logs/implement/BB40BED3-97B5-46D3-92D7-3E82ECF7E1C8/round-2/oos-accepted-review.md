### OOS_1: [OUT_OF_SCOPE] `/bug` missing from consumer catalogs and strict-permissions allowlist
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: The skill is described as public/exported but is absent from `README.md` and `docs/skills.md`, and strict-permissions documentation in `docs/configuration-and-permissions.md` lists `Skill(issue)` / `Skill(larch:issue)` but not `Skill(bug)` / `Skill(larch:bug)`. Strict-permissions consumers who copy the documented allowlist cannot invoke or delegate to `/bug`, so runtime export does not match documented setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add `/bug` rows/sections to `README.md` and `docs/skills.md` in a follow-up.
  - From cursor-specialist-testing-output.txt: Extend the copy-paste allowlist when documenting the new skill.
  - From codex-generic-output.txt: Add `Skill(bug)` and `Skill(larch:bug)` in sorted order to `docs/configuration-and-permissions.md` and the matching reference settings surface if intended, then add `/bug <bug description>` entries to `README.md` and `docs/skills.md` that point to `skills/bug/SKILL.md` and describe the investigate-then-file behavior.


