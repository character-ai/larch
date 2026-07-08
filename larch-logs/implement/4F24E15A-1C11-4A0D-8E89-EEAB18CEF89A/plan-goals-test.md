## Goal
Implement issue #6621: [IMPLEMENTING] [FEATURE] Seed ARCHITECTURAL_INVARIANTS.md with INV-Gate-1 and INV-Pause-1.

## Implementation Plan
## Plan

## Scope

Documentation-only change. Edit `ARCHITECTURAL_INVARIANTS.md` only. Do not edit code, tests, hooks, or lints.

Confidence: high.

## Operator decision (heading format)

The issue supplies `INV-Gate-1` / `INV-Pause-1` heading IDs. Those are accepted by the learn-from-bugs coverage indexer (`_INVARIANT_ID_RE` in `python/larch/issue/learn_from_bugs.py`, which accepts both `INV-*` and `I-*`), so the issue's acceptance check passes with them. But the reader that folds invariants into `/design` and `/implement` drafting — `architectural-invariants read` / `present-note`, backed by `_INVARIANT_HEADING_RE` in `python/larch/core/architectural_guidelines.py` (`^#{1,6}\s+(I-[A-Za-z0-9-]+-\d+):`) — matches only the `I-*` shape, so `INV-*` headings would be recorded and counted yet invisible to that reader. The operator chose the `I-*` shape (`I-Gate-1`, `I-Pause-1`), which both regexes accept, so the invariants are counted AND readable. This is the sole deviation from the issue's verbatim heading text; the two body paragraphs stay byte for byte.

## Files to modify/create

### UPDATED: ARCHITECTURAL_INVARIANTS.md

1. Delete the placeholder line `_No invariants recorded yet._`.
2. Keep the existing header paragraph (the "Absolute invariants ..." block) unchanged.
3. Insert two entries in order. Each entry is: one blank line, then the heading line (exactly three `#`, one space, the ID, a colon, a space, the title), then one blank line, then the body paragraph.

Entry 1 heading line to write: `### I-Gate-1: A gate never disarms on data authored by the gated entity`
Entry 1 body: paste the Entry 1 fenced paragraph from issue #6621 verbatim (without the fence markers, no "Deviate when" clause).

Entry 2 heading line to write: `### I-Pause-1: A pause snapshot contains every artifact a resume guard reads`
Entry 2 body: paste the Entry 2 fenced paragraph from issue #6621 verbatim (without the fence markers, no "Deviate when" clause).

Only the heading ID prefix changes from the issue text (`INV-` becomes `I-`). The title after the colon and both body paragraphs are unchanged.

## Approach

- Preserve the header paragraph as-is.
- Replace the single placeholder line with the two entries above.
- Use `I-Gate-1` / `I-Pause-1` (operator decision), not the issue's `INV-*` IDs.
- Do not reflow, reword, or re-wrap the supplied body paragraphs.

## Edge cases

- Two readers parse this file: `_INVARIANT_ID_RE` (coverage index; 2-4 `#`; accepts `INV-*` and `I-*`) and `_INVARIANT_HEADING_RE` (`architectural-invariants read`; 1-6 `#`; `I-*` only). Both are satisfied by `I-Gate-1` / `I-Pause-1` at three `#`.
- Keep the colon immediately after the ID; both regexes require it.
- Do not edit `ARCHITECTURAL_GUIDELINES.md`, `python/larch/issue/learn_from_bugs.py`, or `python/larch/core/architectural_guidelines.py`. The `I-*` shape needs no code change.

## Testing strategy

- Run `python3 python/cli.py learn-from-bugs coverage-index --root .`; confirm the JSON `invariants` array has exactly 2 entries, `I-Gate-1` then `I-Pause-1`.
- Run `python3 python/cli.py architectural-invariants read`; confirm it now surfaces both `I-Gate-1` and `I-Pause-1` (present, non-empty), proving the reader path sees them too.
- Optionally run the changed-file Markdown lint if available locally.

## Acceptance

- Run `python3 python/cli.py learn-from-bugs coverage-index --root .`; confirm the JSON `invariants` array has exactly 2 entries, `I-Gate-1` then `I-Pause-1`.
- Run `python3 python/cli.py architectural-invariants read`; confirm it now surfaces both `I-Gate-1` and `I-Pause-1` (present, non-empty), proving the reader path sees them too.
- Optionally run the changed-file Markdown lint if available locally.

diff_added: 21
diff_deleted: 1
mechanical_churn: false
diff_lines: 22

## Test plan
(no test plan section in plan-file)
