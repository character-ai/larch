## Proposed Design Outline

### Goals
- Single-source the guideline/invariant ID-heading grammar so the /design reader and the /learn-from-bugs coverage indexer parse the identical (id, title) population.
- Add a lint that hard-bans a second literal for that grammar and for the `[BUG]` bug-title predicate, so the drift class cannot recur (G-Fix-1, G-Cfg-3).

### Non-goals
- Do not widen the reader grammar: guidelines stay `###`-only; invariants stay `#{1,6}`; `INV-*` stays rejected everywhere.
- Do not change `bug_title_match` semantics or the reader's per-line `.match` behavior.
- Do not re-home or refactor unrelated regexes.

### Approach sketch
- Promote the two reader regexes in `architectural_guidelines.py` to public constants `GUIDELINE_HEADING_RE` / `INVARIANT_HEADING_RE`, compiled with `re.MULTILINE`.
- Repoint `learn_from_bugs.py`: delete `_GUIDELINE_ID_RE` / `_INVARIANT_ID_RE`, import the shared constants, pass them to `_scan_marked_ids`.
- Add one lint module `lint_shared_convention_regex` in `python/larch/lint/`, mirroring `lint_lifecycle_prefix_literal.py`, with an owner-module convention table and same-line suppression; skip what `lint_lifecycle_prefix_literal` already flags.
- Wire the lint into `make py-lint`; land with an empty baseline and a hard ban.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py` (shared constants)
- `python/larch/issue/learn_from_bugs.py` (repoint indexer)
- `python/larch/lint/lint_shared_convention_regex.py` (new lint) plus its `make py-lint` wiring
- Cross-module regression test and lint unit tests under `python/tests/`

### Open questions
- None.
