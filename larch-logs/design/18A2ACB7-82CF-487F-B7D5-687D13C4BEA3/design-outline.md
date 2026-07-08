## Proposed Design Outline

### Goals
- Record the first two absolute invariants (INV-Gate-1, INV-Pause-1) in `ARCHITECTURAL_INVARIANTS.md`, replacing the empty placeholder.
- Make the learn-from-bugs coverage indexer report exactly 2 indexed invariants.

### Non-goals
- No code, lint, hook, or test changes; no behavior change anywhere else.
- No rewording of the supplied entry text; no "Deviate when" clause added.
- No edits to `ARCHITECTURAL_GUIDELINES.md` or to the `_INVARIANT_ID_RE` indexer.

### Approach sketch
- Edit `ARCHITECTURAL_INVARIANTS.md` only.
- Delete the placeholder line `_No invariants recorded yet._`; keep the header paragraph unchanged.
- Append INV-Gate-1 then INV-Pause-1, each as a `### ` heading (exactly three `#`) that matches `_INVARIANT_ID_RE`, followed by its body paragraph verbatim.
- Separate header/heading/paragraph blocks with single blank lines.

### Surfaces in scope
- `ARCHITECTURAL_INVARIANTS.md` (the only edited file).
- `python/larch/issue/learn_from_bugs.py` (read-only reference: heading regex + coverage verb; not modified).

### Open questions
- None.
