### FINDING_4: `larch-log.md` would remain stale for phased dynamic Codex artifacts
- **Reviewer(s)**: Cursor-dyn-doc-narrative-sync, Codex-dyn-doc-narrative-sync
- **Severity**: important
- **Concern**: The plan updates tests and harness documentation for phased dynamic Codex outputs and sidecars, but does not require the primary `scripts/larch-log.md` contract enumeration to cover those same phased forms, risking cross-document drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-doc-narrative-sync: Add matching larch-log.md bullets: phased dynamic Codex outputs and sidecars are explicitly allowed; unphased `.cap-hit` remains documented; revise lines 30-33 instead of appending a standalone paragraph.
  - From Codex-dyn-doc-narrative-sync: Extend the scripts/larch-log.md step to update the existing write-round enumeration so it explicitly covers both unphased and phased dynamic Codex .txt .meta .json and .cap-hit inclusion, while preserving the unchanged-behavior framing and existing prompt/events exclusions.


