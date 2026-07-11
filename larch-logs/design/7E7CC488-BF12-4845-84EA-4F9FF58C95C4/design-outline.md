## Proposed Design Outline

### Goals
- Make the /implement architectural-assessment outcome author-supplied at persist time, so an explicit outcome (not prose) decides ship routing.
- Fail closed when a note declares `clean` but names an `I-*`/`G-*` id without the clean lead (one-way cross-check).
- Collapse the three tolerant-prose classifiers into one shared helper.

### Non-goals
- Do not change the tolerant-prose classifier logic; relocate it into one helper and demote it to a cross-check.
- Do not touch the /design `persist-design-assessment` path (already explicit).
- No symmetric cross-check: an explicit `violation`/`deviation` paired with a clean-shaped note is honored, not re-author-forced.

### Approach sketch
- Add one shared classifier helper in `architectural_guidelines.py` (serving both `clean|deviation` and `clean|violation` vocab); import it from `ship_guidelines.py`; delete the 3 copies.
- Add a required `--outcome` flag to the /implement `write-compose-assessment` (and `write-staged-assessment`) verbs; record it as the authoritative `ASSESSMENT_KIND` in note metadata / outcome sidecar.
- On present invariants/guidelines, an omitted `--outcome` fails closed with a re-author request; prose never routes.
- Cross-check at write time: declared `clean` + classifier says violation/deviation, fail closed.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py`; `python/larch/implement/ship_guidelines.py`
- `skills/implement/scripts/step-architectural-{invariants,guidelines}-write-compose.sh`; `...-write-staged.sh`
- Tests: `python/tests/core/test_architectural_guidelines.py`; `python/tests/implement/test_ship.py`

### Open questions
- None. Both scope forks (hard cutover, one-way cross-check) resolved in Round 1.
