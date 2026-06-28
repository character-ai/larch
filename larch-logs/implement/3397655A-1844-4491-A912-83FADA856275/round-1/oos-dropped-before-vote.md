### OOS_1: [OUT_OF_SCOPE] Pre-existing Consumer Contract formatting defects in attic dialectic doc
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: `docs/attic/dialectic-legacy.md:307-308` — The Consumer Contract still mixes `$DESIGN_TMPDIR/dialectic-resolutions.md` with “under `$DIALECTIC_TMPDIR`” in adjacent bullets, and line 307 runs into 308 without a blank line. Pre-existing legacy archaeology content carried over by the move; not introduced by this diff and not on an active runtime path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Optional attic-doc cleanup in a follow-up; not required for this retirement.

### OOS_2: [OUT_OF_SCOPE] No harness pin asserting `dialectic-protocol.md` cites attic path
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Dialectic retirement is pinned for attic existence and runtime absence, but nothing in `test-design-structure.sh` asserts that `skills/shared/dialectic-protocol.md` still points at `docs/attic/dialectic-legacy.md`. A future edit could delete or relocate the attic file, regress the protocol line, or leave a broken pointer without failing design-structure tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Add a `contains` pin on `dialectic-protocol.md` for the attic path, mirroring the doc-pointer updates.
  - From cursor-specialist-testing: Add a `contains` pin on `dialectic-protocol.md` for the attic path, mirroring the doc updates in this PR.

### OOS_3: [OUT_OF_SCOPE] Adjacent `oos-step5b-dispatch.md` retirement deferred per plan
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-doc-relocation
- **Severity**: latent
- **Concern**: `skills/design/references/oos-step5b-dispatch.md` remains in the runtime reference tree and `skills/design/scripts/design-step5b-prepare.md:32` still points at it. The plan marked adjacent OOS retirement as `MAY_UPDATE` only; this branch intentionally deferred that cleanup. No runtime regression from the primary retirements, but ~27 lines of non-loaded surface remain for follow-up.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Calibration fixture diffs still embed retired paths
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-doc-relocation
- **Severity**: nit
- **Concern**: `python/test_fixtures/plan-fidelity-calibration/diffs/` still mention retired paths such as `skills/implement/references/summary-comment-template.md` and `pr-body-template.md`. The plan explicitly excludes these fixtures; they will not break CI but will keep appearing in targeted `rg` discovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh fixtures only if a calibration harness starts validating path literals against the live tree.

### OOS_5: [OUT_OF_SCOPE] Attic dialectic doc retains runtime-style consumer headers
- **Reviewer(s)**: dyn-dyn-doc-relocation
- **Severity**: nit
- **Concern**: `docs/attic/dialectic-legacy.md:1-7` retains runtime-style `**Consumer**` / `**When to load**` headers. That is intentional audit archaeology and the path is outside `skills/*/references/`, so it does not reintroduce per-turn runtime loading; only the broken line-13 callout (FINDING_1) is a material integrity defect in this change.
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (subsumed input):** FINDING_1–6, 9–10, and 14–20 from the specialist slots were implementation-verification summaries (relocations, deletions, harness updates, passing tests) with boilerplate “Address the concern above” revisions and no distinct behavioral risk beyond confirming plan execution. They were fully subsumed and not emitted as separate blocks. Slot coverage for `cursor-specialist-correctness`, `cursor-specialist-edge-cases`, and `cursor-specialist-testing` is preserved through their OOS and mixed-scope items above.

