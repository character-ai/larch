## Proposed Design Outline

### Goals
- Make `parse_issue_input` fence-aware so a `### ` line inside a fenced code block is body content, not an item boundary.
- The verified reproduction parses as `ITEMS_TOTAL=1` with a byte-exact body; the 2026-07-08 four-item batch parses as 4 items with no masking.
- Fix the whole fence-unaware class — both the generic path and the OOS Description path — not just the generic reproduction (G-Fix-1).

### Non-goals
- No change to unfenced in-body `### ` behavior; #2152's split-boundary rule and its `parse-input:` breadcrumb stay exactly as-is.
- No rewrite or refactor of the existing state machine beyond inserting the two-pass fence gate.
- No new CLI flags, config, or fence syntax beyond backtick/tilde fences.

### Approach sketch
- Pass 1: a small helper scans `text.splitlines()` and records the line indices covered by *balanced* fence pairs (opener = stripped line of ≥3 backticks/tildes + optional info string; closer = same marker char, length ≥ opener, no suffix; an unclosed opener degrades to plain text).
- Pass 2: the existing `parse_issue_input` loop runs unchanged, except the three heading/field checks (`OOS_HEADING_RE`, `PLAIN_HEADING_RE`, `consume_oos_field`) are gated on "this line index is not fenced"; fenced lines fall through to the existing body-append branch.
- Add the five enumerated regression tests in `python/test_issue_create.py`.
- Narrow the `/issue` SKILL.md "Authoring caution (generic fallback)" to unfenced `### ` only; keep the #2152 breadcrumb unchanged.

### Surfaces in scope
- `python/larch/issue/issue_create.py` — new balanced-fence helper + fence-gated checks in `parse_issue_input`.
- `python/test_issue_create.py` — regression tests.
- `skills/issue/SKILL.md` — authoring-caution narrowing.

### Open questions
- None.
