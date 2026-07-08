## Decision 1: Scope is documentation-only

- **Question**: Does this feature change any behavior, or is it purely a docs edit to `ARCHITECTURAL_INVARIANTS.md`?
- **Resolution**: Documentation-only. Edit `ARCHITECTURAL_INVARIANTS.md` alone. No code, lint, hook, or test changes. The issue states explicitly: "No behavior change anywhere else; this is a documentation-only change."
- **Source**: codebase (issue body Acceptance section)

## Decision 2: Entry text is final and byte-for-byte

- **Question**: May the invariant heading/body wording be edited for style or readability?
- **Resolution**: No. "The entry texts are final. Do not rewrite them for style." Insert the two headings and body paragraphs exactly as given. Do not add a "Deviate when" clause (the file's header forbids it for invariants).
- **Source**: codebase (issue body "How to apply" + Entry sections)

## Decision 3: Placeholder removal and header preservation

- **Question**: What structural edits are required?
- **Resolution**: Delete the placeholder line `_No invariants recorded yet._`; keep the header paragraph (lines 1-7) unchanged; insert INV-Gate-1 then INV-Pause-1, each as `### <heading>` (exactly three `#`, one space) with a blank line before the heading, a blank line after it, and the body paragraph.
- **Source**: codebase (issue body "How to apply")

## Decision 4: Done criterion is the coverage indexer count

- **Question**: How is completion verified?
- **Resolution**: The learn-from-bugs coverage index verb (`coverage_index` reading `ARCHITECTURAL_INVARIANTS.md` via `_INVARIANT_ID_RE` in `python/larch/issue/learn_from_bugs.py`) must report exactly 2 indexed invariants. Headings must match `^#{2,4}\s+((?:INV|I)-[A-Za-z0-9]*-?\d+):` at 2-4 hashes; use exactly 3.
- **Source**: codebase (issue body Acceptance + `learn_from_bugs.py:63`)
