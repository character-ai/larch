## Proposed Design Outline

### Goals
- Remove em-dashes from user-facing print literals in design-outline.md and finalize-step5.md.
- Remove em-dashes from report template prose in write-final-report.md.
- Stop the outline file-list format from modeling the banned `path — description` separator.

### Non-goals
- Do not edit machine-parsed tokens, sentinels, KEY=value grammars, or code fences.
- Do not scrub em-dashes in files outside the three named surfaces.
- Do not change any behavioral logic, only prose and print-literal text.

### Approach sketch
- Read each of the three files and identify every em-dash in user-facing prose or print literals.
- Replace each em-dash with the appropriate compliant punctuation (period, colon, or comma depending on context).
- Change the file-list format in design-outline.md from `` `path` — description `` to `` `path`: description ``.
- Check for any structural test harnesses that pin line content in these files and update them.

### Surfaces in scope
- skills/design/references/design-outline.md
- skills/design/references/finalize-step5.md
- skills/implement/scripts/write-final-report.md
- Any test files that assert line-level content in the above files.

### Open questions
- None.
