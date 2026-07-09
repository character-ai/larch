## Goal
Implement issue #6745: [IMPLEMENTING] architectural-knowledge-IV [BUG] parse_invariant_entries drops every invariant body; design drafter, Gate C, review prompts, and implementers see title-only invariants.

## Implementation Plan
## Plan

## Approach

`approach-synthesis.txt` is `NO_SKETCHES`, so this plan is based on direct code and test inspection. `discussion-round1.md` resolves the only scope question: do not change `parse_guideline_entries` behavior; only document that `- Guidance:` bullets stay omitted.

Implement the smallest parser fix:

- Change `parse_invariant_entries` so each `I-*` heading starts a normalized entry heading: `### <id>: <title>`.
- Collect every following non-heading line as body text until the next Markdown heading.
- Preserve body lines verbatim, including prose paragraphs, blank lines inside the body, and `- Why:` bullets.
- Collapse leading and trailing blank body lines per entry.
- Keep non-entry headings as hard boundaries. A `##` section or a non-`I-*` `###` heading closes the current entry and does not leak its body.
- Do not special-case `_WHY_RE` inside invariant parsing. Verbatim body retention keeps future `- Why:` bullets working.
- Leave `parse_guideline_entries` logic unchanged.

Downstream consumers should need no code change because they already consume `.content`:

- `/design` Step 2b calls `architectural_guidelines.read_invariants()` and emits `invariant_result.content`.
- `architectural-invariants read` and `present-note` emit `result.content`.
- plan and code review prompt rendering calls `_architectural_guidelines_review_section()`, which emits `result.content`.
- implement dispatch snapshots read the same `read_invariants()` result.

## Files to modify/create

### UPDATED: python/larch/core/architectural_guidelines.py

Update docstrings:

- `parse_invariant_entries`: describe normalized headings plus verbatim body retention until the next Markdown heading.
- `parse_guideline_entries`: keep the current wording for `Why` and `Deviate when`, and add that `Guidance` and other bullets are intentionally omitted.

Refactor `parse_invariant_entries` with a small local finalization helper or equivalent simple code:

- Track `current_heading: str | None`.
- Track `current_body: list[str]`.
- On finalization, trim body lines while `line.strip() == ""` at the front or back.
- Append `[current_heading, *trimmed_body]` when an entry is active.
- On `INVARIANT_HEADING_RE`, finalize any active entry, then start a new one with the normalized `### I-...` heading.
- On `_MARKDOWN_HEADING_RE`, finalize any active entry and clear state.
- When an entry is active and the line is not a Markdown heading, append the raw line to `current_body`.

Keep all existing file validation, `read_invariants`, CLI emitters, and review rendering code unchanged.

### UPDATED: python/tests/core/test_architectural_guidelines.py

Add or update focused parser coverage:

- Add a multi-paragraph prose invariant test. Assert paragraphs and internal blank lines survive, preamble text is ignored, and the heading is normalized to `###`.
- Add a test where an invariant is followed by a `##` section heading. Assert the invariant body stops before the section body.
- Add a test where one `### I-*` entry is followed by another `### I-*` entry. Assert both entries are present and no body text leaks across entries.
- Add a bullet-style invariant entry test. Assert `- Why:` remains present under the normalized heading.
- Rewrite `test_invariants_present_file_emits_normalized_entries` for verbatim body retention and boundary exclusion:
  - Replace the `- Deviate when: ignored` fixture line with a short prose body line under `## I-Sec-1` (Deviate-when is guideline terminology, not invariant semantics).
  - Drop the stale `assert "Deviate when" not in result.content` assertion; the new parser correctly retains arbitrary body lines and this assertion would fail on a correct implementation.
  - Keep asserting preamble text is ignored, `### Not emitted` and its `- Why:` line stay excluded, normalized `I-Sec-1` and `I-Py-2` headings are present, and `- Why:` survives under `I-Sec-1`.
  - Assert the new prose body line under `I-Sec-1` is present in `result.content`.
- Add a copied fixture from the current seeded `ARCHITECTURAL_INVARIANTS.md` entries. Assert the normalized output contains all four seeded headings plus body phrases such as `A hard gate`, `Evidence of violation:`, and `Mechanical backing:`.
- Keep existing guideline parser tests unchanged except for any docstring-only expectation, if present.

## Edge cases

- An `I-*` heading may appear at heading levels `#` through `######`; keep the current regex behavior and normalize all of them to `###`.
- A non-entry Markdown heading must stop the current invariant body.
- Text before the first `I-*` heading stays ignored.
- Entries with no body remain valid and emit only the normalized heading.
- Blank lines inside a body stay intact; only leading and trailing blank body lines are removed.
- Any non-heading line under an active invariant entry, including bullets other than `- Why:`, is retained verbatim.
- `parse_guideline_entries` must still omit `- Guidance:` bullets.

## Failure modes

- If the parser only appends lines matching `_WHY_RE`, invariant bodies remain title-only and the bug persists.
- If the parser does not stop at non-entry Markdown headings, section prose can leak into the prior invariant.
- If `test_invariants_present_file_emits_normalized_entries` still asserts `Deviate when` is absent while the fixture retains a Deviate line, the test fails on a correct parser.
- If tests read only synthetic bullet entries, the real prose-file regression can return.
- If downstream render checks are skipped, CLI output may pass while review prompts still lack bodies due to a separate rendering path.

## Testing strategy

Run focused unit tests:

- `python3 -m pytest python/tests/core/test_architectural_guidelines.py -k "invariant or parse_guideline_entries"`

Verify the CLI emits real invariant body text:

- `python3 python/cli.py architectural-invariants read`
- Confirm the output includes seeded body phrases such as `A hard gate`, `Evidence of violation:`, and `Mechanical backing:`.

Verify one rendered review prompt includes invariant bodies:

- Create a temporary design tmpdir and minimal plan file.
- Run `python3 python/cli.py render plan-review --archetype requirements --vendor codex --plan-file "$tmpdir/plan.md" --design-tmpdir "$tmpdir"`.
- Confirm the prompt contains the `architectural_invariants` block and seeded body text, not only titles.

Optionally run the changed Python file through relevant checks:

- `python3 python/cli.py checks run-relevant`

## Acceptance

Run focused unit tests:

- `python3 -m pytest python/tests/core/test_architectural_guidelines.py -k "invariant or parse_guideline_entries"`

Verify the CLI emits real invariant body text:

- `python3 python/cli.py architectural-invariants read`
- Confirm the output includes seeded body phrases such as `A hard gate`, `Evidence of violation:`, and `Mechanical backing:`.

Verify one rendered review prompt includes invariant bodies:

- Create a temporary design tmpdir and minimal plan file.
- Run `python3 python/cli.py render plan-review --archetype requirements --vendor codex --plan-file "$tmpdir/plan.md" --design-tmpdir "$tmpdir"`.
- Confirm the prompt contains the `architectural_invariants` block and seeded body text, not only titles.

Optionally run the changed Python file through relevant checks:

- `python3 python/cli.py checks run-relevant`

diff_lines: 130

## Test plan
(no test plan section in plan-file)
