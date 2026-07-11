## Proposed Design Outline

### Goals
- Activate the combined Step 8 route: the `assessments` branch delegates to the `implement-step8-assessment` bgjob adapter instead of authoring assessments inline.
- Remove main-agent diff reading, draft authorship, individual compose-writer calls, and inline fallback from all three assessment routes.
- Document the activated read-only delegation trust boundary in SECURITY.md.

### Non-goals
- No change to `step-8-assessment.sh` / `.md` (piece 3 adapter) or the Python `ship route-exit` / `architectural-assessment` drivers (pieces 1-2).
- No new `NEXT_ACTION` tokens; back-compat `invariants-assessment` / `guidelines-assessment` stay as dormant legacy aliases.
- No change to assessment kind tokens, result states, or the deterministic pre-filter.

### Approach sketch
- Rewrite the SKILL.md `assessments` branch to invoke `step-8-assessment.sh` as one blocking foreground fence, validate `ASSESSMENT_*` KVs (`BGJOB_RC=0`, step identity, fingerprint, kinds, `ASSESSMENT_STATUS=complete`), then relaunch `step-8-ship.sh` exactly once; back-compat branches delegate the same way.
- Rewrite `architectural-invariants-present.md` and `architectural-guidelines-present.md` to describe read-only bgjob delegation, not inline authorship.
- Retarget `ship-pr-exit-matrix.md` branch semantics to the adapter fence.
- Update the three named test files to assert the new fences/strings; add a SECURITY.md trust-boundary section.

### Surfaces in scope
- `skills/implement/SKILL.md` (Step 8 assessment branches)
- `skills/implement/references/architectural-invariants-present.md`, `architectural-guidelines-present.md`, `ship-pr-exit-matrix.md`
- `skills/implement/scripts/test-architectural-guidelines-step.sh`, `scripts/test-implement-fence-shape.sh`, `python/tests/implement/test_implement_dispatch.py`
- `SECURITY.md`

### Open questions
- None. Integration model resolved in Step 1c (blocking foreground fence); back-compat routes confirmed dormant.
