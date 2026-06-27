## Goal
Implement issue #5606: [IMPLEMENTING] [BUG] Findings aggregator merge frequently fails semantic validation, consuming retries and exhausting (design + implement).

## Implementation Plan
## Approach

- Treat `NO_SKETCHES` as binding. Draft from direct repo inspection and the approved outline.
- Keep scope to failure-rate reduction.
- Do not raise `_AGGREGATE_VALIDATION_RETRIES`.
- Do not add best-attempt fallback on validation exhaustion.
- Do not enable `LARCH_AGGREGATE_REVISION_TRACE_STRICT` by default.
- Do not touch `python/plan_review_round.py` or `python/review_pipeline.py`.

## Files to modify/create

### UPDATED: agents/orchestrator-aggregator.md

Strengthen the aggregator instructions without changing the output grammar.

Add guidance that:

- Every required input reviewer slot must appear in at least one merged output block.
- The `- **Reviewer(s)**:` line must use only reviewer slots from the caller-provided inventory.
- A `- From <slot>:` revision bullet must use a slot from the same inventory.
- A `- From <slot>:` revision bullet must quote fix text from that slot's scoped input.
- The aggregator must not invent reviewer slots or paraphrase distinct fixes.
- Existing `[OUT_OF_SCOPE]` rules still apply:
  - Do not promote an exclusively out-of-scope reviewer into an in-scope block.
  - Put that reviewer in an `[OUT_OF_SCOPE]` block if it raised only out-of-scope input.

Keep the existing empty-merge attestation rules.

### UPDATED: python/review_aggregate.py

Add a small prompt-construction helper for required slots.

Recommended shape:

- `_required_reviewer_slots_prompt_section(input_text: str) -> str`
  - Parse `_input_blocks(input_text)`.
  - Reuse `_reviewer_line_slots()`, `_normalize_slot()`, and `_heading_line()`.
  - Build a deterministic mapping of normalized slot to:
    - observed raw labels
    - whether it appears on in-scope input, out-of-scope input, or both
  - Return a compact Markdown section.
  - Return an empty string only when no slots are found.

Add the section to `aggregate_findings()` after raw reviewer findings are appended to `prompt_parts`.

Suggested section content:

- Header: `## Required reviewer slots (validator inventory)`
- One bullet per normalized slot.
- Include observed labels only when they differ from the normalized slot.
- Include scope class: `in-scope`, `out-of-scope-only`, or `mixed`.
- Include direct instructions:
  - Every listed slot must appear in at least one `- **Reviewer(s)**:` line.
  - Use only listed slots for `Reviewer(s)` and `From` labels.
  - `From` bullets must quote fix text from that slot's input.
  - Out-of-scope-only slots may appear only in `[OUT_OF_SCOPE]` output blocks.

Add `_NARROW_TRIGGER_RC = 9` near the other validation RC constants.

Change `_validate_aggregate_output()` so the `nonconforming_heading_with_attestation` branch returns `_NARROW_TRIGGER_RC` instead of `1`.

Change `_apply_aggregate_candidate()` so `_NARROW_TRIGGER_RC` joins the retryable validation classes:

- `_OOS_ATTRIBUTION_RC`
- `_MISSING_REVIEWER_RC`
- `_MISSING_ATTRIBUTION_RC`
- `_PREAMBLE_SLIP_RC`
- `_NARROW_TRIGGER_RC`

Update the adjacent comments so they describe the current retryable set.

Do not change `_validation_retry_budget()`.

Do not change `_AGGREGATE_VALIDATION_RETRIES`.

Keep non-retryable semantic validation failures single-shot.

When narrow-trigger retries exhaust, let the existing retryable-validation path degrade without applying a candidate and without best-attempt fallback.

### UPDATED: python/test_review_aggregate.py

Add focused unit coverage for the new required-slot prompt helper.

Cover:

- Multiple slots produce deterministic bullets.
- Artifact suffix normalization is reflected in the canonical slot.
- Observed raw labels are retained when useful.
- Out-of-scope-only slots are marked distinctly.

Add end-to-end prompt coverage in `aggregate_findings()`.

Use an existing dispatch stub or an inline stub, then assert `aggregator-prompt.md` contains:

- `## Required reviewer slots (validator inventory)`
- each input reviewer slot
- the instruction that every listed slot must appear
- the instruction that `From` labels must use listed slots

Add narrow-trigger retry coverage.

Recommended cases:

1. **Retry then success**
   - Input has two findings.
   - First dispatch emits the existing narrow-trigger body:
     - a nonconforming `### FINDING_1 ...` pseudo-heading
     - `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`
   - Second dispatch emits a valid merged finding.
   - Assert:
     - `AGGREGATED=true`
     - `REASON=ok`
     - dispatch count is `2`
     - final findings file contains the valid merge
     - retry prompt includes `nonconforming_heading_with_attestation`

2. **Retry budget exhausted**
   - Same failure body for every attempt.
   - Keep `LARCH_AGGREGATE_VALIDATION_RETRIES=2`.
   - Assert:
     - dispatch count is `3`
     - original findings remain unchanged
     - no best-attempt fallback is applied
     - result does not rely on raising the retry count

Update existing tests that currently expect the narrow-trigger fixture to be a single-shot `validation-exhausted` path.

Prefer rewriting those expectations to the new retry behavior rather than adding duplicate tests.

Do not add tests for strict revision-traceability mode unless an existing assertion must be adjusted.

## Edge cases

- **Plan mode:** Build the required-slot inventory from `source_file`, not the original `findings_file`, after scope-reduction blocks are withheld.
- **Out-of-scope-only slots:** The prompt must not tell the model to place those slots in in-scope blocks.
- **Suffix normalization:** Keep accepting both raw artifact labels and normalized slot labels.
- **Empty merge:** Valid attestation-only output remains accepted only when there are no merged `### FINDING_N:` blocks.
- **Strict traceability:** Leave `LARCH_AGGREGATE_REVISION_TRACE_STRICT` opt-in behavior unchanged.

## Failure modes

- The stronger prompt may not eliminate all LLM merge slips.
- The bounded retry loop may still exhaust when every attempt repeats the same invalid output.
- On exhaustion, the implementation must preserve the original findings file.
- Do not add fallback selection of a best invalid attempt.

## Testing strategy

Run focused tests for changed surfaces:

- `python3 -m pytest python/test_review_aggregate.py`

Run lint for changed Python files:

- `python3 -m ruff check python/review_aggregate.py python/test_review_aggregate.py`
- `python3 -m pyright python/review_aggregate.py python/test_review_aggregate.py` if the repo target supports file-scoped pyright.

Manually inspect the generated `aggregator-prompt.md` in tests to confirm the new required-slot section is readable and compact.

diff_added: 130
diff_deleted: 25
mechanical_churn: false
diff_lines: 155

## Test plan
(no test plan section in plan-file)
