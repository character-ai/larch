## Proposed Design Outline

### Goals
- Split three shared references so live content loads without retired choreography or nested-only scaffolding.
- Cut ~200 retired dialectic lines off the conditional Gate C read, ~50 dead voter-argv lines off the voting read, and ~52 nested-only step-prefix lines off every standalone progress read.
- Zero runtime behavior change; all live consumers keep working.

### Non-goals
- No edits to `skills/design/SKILL.md`, `skills/implement/SKILL.md`, or `skills/review/SKILL.md` (owned by sibling md-to-py-VII issues #5562 / #5401).
- No Python changes; the empty `dialectic-resolutions.md` placeholder handling in `python/design_lifecycle.py` stays as-is.
- No deleting live grammar/threshold/scoring content; no renaming the active `dialectic-protocol.md` / `voting-protocol.md`; no fixing pre-existing dangling refs inside the relocated legacy text.

### Approach sketch
- `dialectic-protocol.md`: relocate the legacy debater/judge/tally/resolutions/Consumer-Contract choreography (including the duplicated judge argv block) into a new `skills/design/references/dialectic-legacy.md`; keep ballot grammar, position rotation, attribution stripping, parser tolerance, thresholds, disposition enum, and the clarifier binding in the active file, with a one-line "legacy parked in dialectic-legacy.md" pointer.
- `voting-protocol.md`: delete the two inline voter-argv contracts + wait/collect boilerplate; replace with a one-line citation to `plan-review voter-dispatch` (/design) and `agent dispatch-voters` (/review, /implement).
- `progress-reporting.md`: move the `## --step-prefix Encoding` section into a new `skills/shared/step-prefix-encoding.md`; leave a short nested-only pointer behind.
- `flags.md`: repoint its single `--step-prefix` encoding-spec citation from progress-reporting.md to the new sub-reference.
- Verify-only: `dialectic-clarifier.md:64` still resolves to kept content; voting-protocol doc citations don't depend on removed argv; new files are reachable (not orphaned); `make lint` clean.

### Surfaces in scope
- `skills/shared/dialectic-protocol.md`, `skills/shared/voting-protocol.md`, `skills/shared/progress-reporting.md`
- NEW `skills/design/references/dialectic-legacy.md`, NEW `skills/shared/step-prefix-encoding.md`
- `skills/design/references/flags.md` (one-line repoint)

### Open questions
- None. Dialectic relocate-vs-delete resolved to relocate in Round 1; the dead-parser risk is verified.
