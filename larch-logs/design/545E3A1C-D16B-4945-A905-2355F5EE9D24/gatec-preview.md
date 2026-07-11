## Final Design Plan

## Approach

Update the digest parser in one bounded change.

- Expand `_HEADING_RE` from h2-h3 to h2-h4.
- Rewrite `_split_sections` to scan lines while tracking Markdown fence state.
- Recognize backtick and tilde fences with matching marker characters and sufficient closing length.
- Ignore headings from the opening fence through its closing fence. Treat an unclosed fence as fenced through end of input.
- Preserve section text boundaries, normalization, caps, and `_pick_sections` first-word dedup behavior.
- Do not change plan-boundary detection, near-miss heading mapping, or h5+ handling.

## Files to modify/create

### UPDATED: python/larch/issue/learn_from_bugs.py

- Widen `_HEADING_RE` to `#{2,4}`.
- Add a local fence-marker pattern or small typed helper for fence-state detection. Do not import another module's private parser helper.
- Change `_split_sections` to collect heading positions only from lines outside fenced code.
- Preserve exact source offsets so section slicing and whitespace normalization remain unchanged for existing h2/h3 bodies.
- Support both backtick and tilde fences. Require a closing fence to use the opener's marker character, meet or exceed its length, and contain no trailing info string.
- Leave `WANT_SECTIONS`, `_pick_sections`, `_squeeze`, and `FREEFORM_CAP` unchanged.

### UPDATED: python/tests/issue/test_learn_from_bugs.py

- Add an h4 fixture with canonical `Summary`, `Root cause`, and `Suggested fix(es)` headings.
- Assert the h4 body produces `structured=True`, retains the canonical root-cause and suggested-fix sections, and does not use `_freeform`.
- Add a fenced-heading fixture where `## Root cause` appears inside a code fence under a real summary.
- Assert the fenced heading does not create a root-cause section or terminate the summary early.
- Cover both backtick and tilde fence forms, including a longer opener that cannot be closed by a shorter marker.
- Pin the existing h2/h3 digest mapping so the parser rewrite cannot alter established section names or content.

## Edge cases

- Closing markers shorter than their opener stay inside the fence.
- A fence using the other marker character does not close the active fence.
- Info strings are allowed on opening fences but not closing fences.
- An unclosed fence suppresses heading recognition through the end of the body.
- Duplicate canonical headings retain the existing dictionary and first-word dedup behavior.
- h1, h5, and deeper headings remain unrecognized.
- `Problem` and `Evidence` remain unmapped unless a canonical section is also present.

## Failure modes

- Incorrect offset accounting may truncate or include a heading in section content.
- A simple toggle may close on the wrong marker or on a shorter marker.
- Reusing a fence helper with different Markdown rules may change existing digest output.
- Applying fence logic to `_BOUNDARY_PATTERNS` would exceed scope and could change where appended plans are removed.

## Testing strategy

- Run the targeted test module:
  - `cd python && pytest tests/issue/test_learn_from_bugs.py`
- Run changed-file Python lint and type checks for the production module and test module.
- Run `python3 python/cli.py lint markdown-heading-fence-state` to confirm the new parser follows the existing G-Md-3 ratchet.
- If GitHub-backed acceptance data is available, run `learn-from-bugs prepare` on a selection containing issue `#6618` and inspect its `digest.jsonl` record. Confirm `structured` is true and the root-cause section is retained. Do not make this network-dependent check a unit-test requirement.

difficulty: MODERATE
diff_added: 70
diff_deleted: 10
mechanical_churn: false
diff_lines: 80
