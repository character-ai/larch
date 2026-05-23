## Goal
Insert a 'plan vs current state' paragraph into the /design plan-review prompt heredoc, update the sibling contract, and add a test assertion.

## Implementation Plan
## Plan

### Files to modify

#### UPDATED: `skills/design/scripts/render-plan-review-prompt.sh`

Insert a "Plan vs current state" paragraph into the `cat <<EOF` heredoc body, between the existing line that begins "Review the implementation plan file at" and the next line that begins "Walk five focus areas".

**Exact insertion location**: between lines 93 and 94 of the current file (heredoc body lines, not source-file lines — i.e., between the existing `Review the implementation plan file at ${PLAN_FILE}. Explore the codebase following file paths named in the plan, then inspect adjacent files only when needed to validate contracts and integration points.` line and the next `Walk five focus areas: code-quality / risk-integration / correctness / architecture / security.` line).

**Exact text to insert** (one paragraph, no leading/trailing blank lines added inside the heredoc — the heredoc emits each line as-is and the surrounding lines already separate logically):

```
The plan describes the codebase AFTER this PR lands. Files cited in Files-to-modify subsections have NOT yet been changed when you read them — the plan PROPOSES those changes. Do NOT flag a current-state behavior as a finding when the plan already addresses it; the plan's mention of current state is motivation for the change, not a claim about post-change state. Findings should target deficiencies of the PROPOSED change: missing steps, wrong target file, incomplete contracts, conflicts with other proposed changes, or actual code paths the plan fails to address.
```

The implementation is a single text insert into the heredoc. No control-flow changes, no new variables, no new flags. The paragraph applies uniformly to all 5 archetypes (arch, edge, innovation, pragmatic, requirements) and both vendors (cursor, codex) because they all use the same `cat <<EOF` heredoc body.

#### UPDATED: `skills/design/scripts/render-plan-review-prompt.md`

Add a short note in the sibling contract documenting the prompt fix and its rationale. Suggested wording (place near any existing "Output format" or "Heredoc body" subsection — if none exists, add a new "### Prompt body invariants" subsection):

```markdown
### Plan-vs-current-state invariant

The rendered prompt body MUST contain the paragraph "The plan describes the codebase AFTER this PR lands. …" between the "Review the implementation plan file at" sentence and the "Walk five focus areas" sentence. This paragraph instructs plan reviewers that the plan describes post-implementation state — preventing the systematic false-positive class where reviewers flag current-code behaviors as bugs even when the plan itself addresses them. The invariant is enforced by `skills/design/scripts/test-plan-review-prompt.sh` (substring assertion).
```

#### UPDATED: `skills/design/scripts/test-plan-review-prompt.sh`

The existing harness (verified at `skills/design/scripts/test-plan-review-prompt.sh:22-26`) defines `assert_contains LABEL NEEDLE FILE` and loops over `vendor` × `archetype` calling `assert_contains` for each invariant substring (see lines 53-56 of the current file). Add this line to the existing assertion list inside the loop body:

```bash
assert_contains "$vendor/$archetype plan-vs-current-state guidance" "The plan describes the codebase AFTER this PR lands" "$out"
```

This follows the exact pattern already in use at lines 53-56 (label, needle, file). The new assertion runs for every (archetype × vendor) combination already exercised by the harness — 5 archetypes × 2 vendors = 10 cases. The substring assertion should pass identically for all 10 because the new paragraph is in the shared heredoc body (not gated by `$ARCHETYPE` or `$VENDOR`).

### Approach

Single-file insertion into a Bash heredoc + sibling-doc note + test assertion. Estimated work: < 30 lines of changes total across 3 files.

### Edge cases

- The new paragraph is inserted as a single line in the heredoc (no embedded newlines in the rendered prompt body — multiple sentences but one logical line, matching the existing heredoc convention where each `EOF` body line is a paragraph).
- The paragraph contains no shell metacharacters that need escaping (`${PLAN_FILE}` and similar expansions are not present in the new text).
- No interaction with the TSV/JSON sentinel output format instructions (line 92, which precedes line 93 with output-format guidance). The new paragraph clarifies the WHAT-to-review semantics; the existing line 92 clarifies the HOW-to-report semantics.

### Failure modes

- **Prompt-rendering regression**: if the heredoc syntax breaks (e.g., a stray `$(` introduces command substitution), `render-plan-review-prompt.sh` will fail with a Bash parse error and `test-plan-review-prompt.sh` will catch it. **Mitigation**: the inserted text contains no `$`, no backticks, no `$(...)` — pure prose. Heredoc is `<<EOF` (interpolating) but no interpolation is needed in the new paragraph.
- **Test-harness assertion drift**: if the harness pattern for assertions diverges from what's documented here, the implementer should match the harness's existing assertion style rather than the suggested wording above. The functional requirement is "rendered prompt must contain the substring `The plan describes the codebase AFTER this PR lands`".

### Testing strategy

- **Unit test**: run `skills/design/scripts/test-plan-review-prompt.sh`. The new substring assertion must pass for every (archetype × vendor) combination already exercised.
- **Run `make lint`**: ensures Bash 3.2 compliance, sibling-`.md` rule satisfied, no markdown lint regressions in the sibling doc update.
- **Manual smoke test** (not required by acceptance, but recommended during PR review): run `skills/design/scripts/render-plan-review-prompt.sh --archetype arch --vendor cursor --plan-file <some-plan.txt>` and verify the rendered prompt to stdout contains the new paragraph between the "Review the implementation plan file" line and the "Walk five focus areas" line.

## Acceptance

- `skills/design/scripts/render-plan-review-prompt.sh` heredoc body contains the new paragraph beginning `The plan describes the codebase AFTER this PR lands.` between the "Review the implementation plan file at" line and the "Walk five focus areas" line.
- `skills/design/scripts/render-plan-review-prompt.md` sibling contract documents the new invariant (substring presence) in a "Prompt body invariants" subsection or equivalent.
- `skills/design/scripts/test-plan-review-prompt.sh` asserts the rendered prompt contains the substring `The plan describes the codebase AFTER this PR lands` for all (archetype × vendor) combinations.
- `make lint` passes (including the test harness).
- No behavioral changes to `/implement` code review (the fix is only to the `--mode description` plan-review prompt).

diff_lines: 80


## Test plan
(no test plan section in plan-file)
