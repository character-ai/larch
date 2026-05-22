### OOS_1: Forked / downstream consumer repos silently skip checks until they migrate

- **Description**: After this PR merges, third-party repos using larch as a plugin that have NOT added `scripts/relevant-checks.sh` will silently skip local checks on every `/implement` / `/review` / `ship-pr.sh` invocation. The wrapper's machine signal (`RELEVANT_CHECKS_SKIPPED=true`) and stderr breadcrumb are visible but easy to miss in long transcripts. No in-repo automation can fully remediate; a release-notes / Slack-announcement / migration-checklist follow-up is needed in the downstream side.
- **Reviewer**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Innovation
- **Phase**: design


Vote tally: YES=2 NO=1 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: Cursor-local skill mirror at /.cursor/skills-cursor/relevant-checks/SKILL.md

- **Description**: Operators running Cursor as the orchestrator may have a Cursor-local mirror of the skill at `~/.cursor/skills-cursor/relevant-checks/SKILL.md` (outside this repository). That install surface is not covered by this PR. If Cursor users rely on the mirror, they need a separate migration note.
- **Reviewer**: Cursor-Requirements
- **Phase**: design


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_3: Historical larch-logs/ references to /relevant-checks

- **Description**: Many committed run logs under `larch-logs/implement/*/round-*/dyn-*.md` still instruct `/relevant-checks` as a slash-skill. The PR-final grep excludes `larch-logs/` (per the plan), so the verification step does not flag them, but anyone running a repo-wide search without the exclusion will see the stale instructions. Worth a separate hygiene issue if the immutability policy on `larch-logs/` ever changes.
- **Reviewer**: Cursor-Innovation, Cursor-Requirements
- **Phase**: design

Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated

