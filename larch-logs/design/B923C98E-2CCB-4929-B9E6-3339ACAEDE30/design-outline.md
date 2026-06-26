## Proposed Design Outline

### Goals
- Delete three orphaned reference files with no runtime loader.
- Preserve unique content (topology.tsv constraints) by porting them to the path-triggered rule that already fires when `topology.tsv` is edited.
- Remove stale consumer pointers in `python/voting.py`, `.github/workflows/ci.yaml`, and `codex-manifest-schema.md`.

### Non-goals
- Re-wiring CI-fix grounding into `python/ci_agentic_fix.py` or `python/agents.py`.
- Changing the focus-area enum or adding new canonical focus-area definitions.
- Changing the manifest schema or its validation logic.
- Editing `/implement` SKILL.md or any agent prompt.

### Approach sketch
- Port the two unique topology.tsv field constraints from `ci-fix-failure-patterns.md` into `.claude/rules/topology-generation.md`, then delete the file.
- Remove `skills/shared/focus-area-prompt.md` from `python/voting.py` `BACKTICKED_FOCUS_FILES` and from `.github/workflows/ci.yaml` `BACKTICKED_FILES`, then delete the file.
- Remove the edit-in-sync bullet for `codex-manifest-schema.digest.md` from `skills/implement/references/codex-manifest-schema.md`, then delete the digest file.
- Run `make lint` (or local subset: `py-lint`, `agent-sync`) to verify no regressions.

### Surfaces in scope
- `.claude/rules/topology-generation.md` (add two constraints)
- `skills/shared/ci-fix-failure-patterns.md` (delete)
- `skills/shared/focus-area-prompt.md` (delete)
- `python/voting.py` (remove one entry from `BACKTICKED_FOCUS_FILES`)
- `.github/workflows/ci.yaml` (remove one entry from `BACKTICKED_FILES`)
- `skills/implement/references/codex-manifest-schema.digest.md` (delete)
- `skills/implement/references/codex-manifest-schema.md` (remove one edit-in-sync bullet)

### Open questions
- None.
