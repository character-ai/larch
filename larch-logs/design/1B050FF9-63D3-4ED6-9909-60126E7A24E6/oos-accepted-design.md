### OOS_1: Forked / downstream consumer repos silently skip checks until they migrate

- **Description**: After this PR merges, third-party repos using larch as a plugin that have NOT added `scripts/relevant-checks.sh` will silently skip local checks on every `/implement` / `/review` / `ship-pr.sh` invocation. The wrapper's machine signal (`RELEVANT_CHECKS_SKIPPED=true`) and stderr breadcrumb are visible but easy to miss in long transcripts. No in-repo automation can fully remediate; a release-notes / Slack-announcement / migration-checklist follow-up is needed in the downstream side.
- **Reviewer**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Innovation
- **Phase**: design


