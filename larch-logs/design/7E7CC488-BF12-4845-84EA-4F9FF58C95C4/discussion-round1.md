## Decision 1: Cutover strategy for the explicit outcome
- **Question**: When a /implement architectural-assessment author omits an explicit outcome on the write-compose/write-staged verbs, should the gate fail closed (hard cutover) or fall back to prose classification?
- **Resolution**: Fail closed, hard cutover. An explicit `--outcome` is authoritative; omission on a present-invariants/present-guidelines path fails closed with a re-author request. Prose classification NEVER decides ship routing. The ~3 Step 8 write fences in `skills/implement/scripts/` are updated to pass the explicit outcome.
- **Source**: user

## Decision 2: Cross-check directionality
- **Question**: Besides "declared clean but note names I-*/G-* ids without the clean lead", should the fail-closed cross-check also fire on the reverse (declared violation/deviation but note looks clean)?
- **Resolution**: One-way only — fail closed solely on the clean-claimed-but-violation-shaped direction (the dangerous "ship a real violation" case, per the issue's literal wording). An explicit violation/deviation is honored as-is because it safely blocks/pins the ship.
- **Source**: user

## Hard constraints (must not break)
- The Step 8 outcome JSON validators (`validate_invariant_ship_outcome_record`, `validate_guideline_ship_outcome_record`) keep `schema_version == "1"`; the author-supplied outcome reuses the existing `outcome` / `assessment_kind` fields — the *source* of the value changes, not the JSON shape.
- The /design side already uses explicit `--assessment clean` (`persist-design-assessment`); do not regress it. Scope is the /implement author verbs + the shared classifier dedup.
- Guideline vocabulary is `clean|deviation`; invariant vocabulary is `clean|violation`. The shared classifier/cross-check must serve both without collapsing the two vocabularies.

## Architectural-invariant constraints (binding)
- **I-Gate-1**: the explicit `clean` outcome may not, on its own, disarm the ship gate. The independent prose cross-check stays a HARD fail-closed veto: declared `clean` + note that names an `I-*`/`G-*` id without the clean lead fails closed regardless of the declaration. The self-declared outcome softens presentation/labeling; the independent classifier keeps the block-on-violation trigger. Declared `violation`/`deviation` is honored as-is (safe, stricter-on-self direction).
- **I-Stale-1**: store the explicit outcome inside the existing HEAD-SHA + `DIFF_FINGERPRINT`-pinned note metadata / outcome sidecar. Do not add a separate outcome store that is consumed without the same fingerprint validation (`note_consumable`, `_staged_fingerprint_valid`).
- **G-Gate-1**: land the required-`--outcome` gate atomically with the ~3 Step 8 write fences that satisfy it (same change), so the gate never lands ahead of its producers and stalls valid /implement runs (#6880/#6882 lineage).
- **G-Py-12 / layering**: the one shared classifier helper lives in the core module `python/larch/core/architectural_guidelines.py`; `ship_guidelines.py` (which already imports that module top-level) imports it. Do not create a new leaf→domain import.
- **G-CLI-2 / G-Cfg-1**: give the re-author-required fail-closed case a distinct, documented exit code so the fence can branch; define the outcome vocab and the new exit code once (config constants / existing REASON_* pattern), not inline literals.

## Non-goals
- Do not change the tolerant-prose classifier's *logic* (first-line-clean-lead + I-*/G-* id search). It is relocated into one shared helper and demoted to a cross-check; its behavior is preserved.
- Do not touch consumers beyond what the cutover requires (e.g. `gc_run_logs.py`).
