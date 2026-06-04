## Proposed Design Outline

### Goals
- Restore the canonical numbered Step 9a.1 OOS-filing procedure as a new `skills/implement/references/oos-pipeline.md`, with a MANDATORY load directive in SKILL.md so the broken `step 3.4 / 3.4b` citations resolve.
- Pin the `oos-issues-created.md` sentinel format (issue URLs + tallies) so its writer and the disposition-gate reader cannot drift.
- Add a durable, awk-robust CI regression guard so a third silent deletion fails CI.

### Non-goals
- No change to OOS pipeline behavior, helper invocation order, triage rules, voting, or filing.
- No refactor of `/design`'s `file-design-oos.sh` writer (keep it compatible, do not touch it).
- No new helper scripts or runtime capabilities; documentation/structure + test only.

### Approach sketch
- New `skills/implement/references/oos-pipeline.md`: numbered procedure reconstructed against current helpers (collect accepted-OOS → exclude already-`Filed URL` blocks → combine Rules A/B + criteria 5/6 → `oos-issue-cap.sh` → `oos-file-conflict-deps.sh` → `/issue` batch → record URLs → `oos-issues`/`run-statistics` larch-log batches → disposition checkpoint → clear `OOS_PENDING`) and current carve-outs (fork-mode, repo_unavailable, NEVER #5 ndjson append).
- SKILL.md: add the MANDATORY load directive at the Step 8+ OOS-checkpoint consumption point; repoint the `step 3.4 / 3.4b` and "execute the Step 9a.1 pipeline" citations.
- Pin the `oos-issues-created.md` format inside oos-pipeline.md, cross-referencing `oos-disposition-gate.md` counting rules (loose URL-token grep + Invariant #1 URL/tally recovery).
- Extend `scripts/test-implement-structure.sh` with assertions for: oos-pipeline.md exists, the SKILL.md load directive, citation resolution, and the format-pin anchor.

### Surfaces in scope
- `skills/implement/references/oos-pipeline.md` (new)
- `skills/implement/SKILL.md` (load directive + citation repoint)
- `scripts/test-implement-structure.sh` (regression guard) + `Makefile` target wiring if needed
- `skills/implement/scripts/oos-disposition-gate.md` / `oos-issue-cap.md` / `oos-file-conflict-deps.md` (see-also pointer touch-ups)

### Open questions
- None. (Placement = reference file and fidelity = reconstruct-to-current were resolved in Round 1.)
