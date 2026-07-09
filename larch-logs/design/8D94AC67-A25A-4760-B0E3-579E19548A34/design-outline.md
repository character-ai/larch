## Proposed Design Outline

### Goals
- Add `- Mechanized: <lint target>` marker support to `ARCHITECTURAL_GUIDELINES.md` entries.
- Slim the normalized payload for marked entries to heading + Mechanized line only, dropping Why and Deviate bullets.
- Apply markers to G-Bash-3 and G-Cfg-1 (G-Cfg-1 with a partial-coverage note).

### Non-goals
- Mark G-Py-11 (companion suppression-reason lint has not landed).
- Add a new make target or CLI verb for lint discovery from this marker.
- Change any downstream consumer of `parse_guideline_entries`.

### Approach sketch
- Add a `_MECHANIZED_RE` regex in `architectural_guidelines.py` to capture `- Mechanized:` bullets.
- Update `parse_guideline_entries`: when an entry contains a Mechanized line, emit heading + Mechanized line only; drop Why and Deviate bullets for that entry.
- Add the marker to G-Bash-3 and G-Cfg-1 in `ARCHITECTURAL_GUIDELINES.md`.
- Add parser unit tests: mechanized entry slim form, unmarked entry byte-stable normalization.

### Surfaces in scope
- `python/larch/core/architectural_guidelines.py`
- `python/tests/core/test_architectural_guidelines.py`
- `ARCHITECTURAL_GUIDELINES.md` (G-Bash-3, G-Cfg-1 entries only)

### Open questions
- None.
