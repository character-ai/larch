## Proposed Design Outline

### Goals
- Cut prose density in the 8 implement references named in the issue (3 eager, 5 conditional), keeping every KV grammar token, manifest schema literal, fenced command, and routing token byte-identical.
- Preserve every prose substring pinned by `scripts/test-implement-structure.sh` and `scripts/test-implement-fence-shape.sh` so both harnesses keep passing unchanged.
- Show a measurable per-file token or byte reduction with zero control-flow change.

### Non-goals
- No control-flow, routing, or KV-grammar changes.
- No edits to `skills/implement/SKILL.md` itself; only the 8 reference files.
- No new measurement tooling. The just-landed heatmap is directional context only; its sample is too thin to gate file selection.

### Approach sketch
- Per file: snapshot the exact `require()` / `forbid()` substrings in `test-implement-structure.sh` and `test-implement-fence-shape.sh` that target it, then compress only the surrounding, unpinned prose.
- Sequence low-pin-risk files first (`step2-dispatch.md`, `codex-manifest-schema.md`) to prove the method, then the higher-pin files (`self-review.md`, `ship-pr-exit-matrix.md`).
- After each file, run both harnesses plus a before/after byte or token count to prove reduction and zero regressions.

### Surfaces in scope
- `skills/implement/references/ship-pr-exit-matrix.md`
- `skills/implement/references/self-review.md`
- `skills/implement/references/step18-cleanup.md`
- `skills/implement/references/step2-dispatch.md`
- `skills/implement/references/checks-repair-loop.md`
- `skills/implement/references/codex-manifest-schema.md`
- `skills/implement/references/conflict-resolution.md`
- `skills/implement/references/stall-recovery.md`
- `scripts/test-implement-structure.sh`, `scripts/test-implement-fence-shape.sh` (read-only pin inventory)

### Open questions
- None.
