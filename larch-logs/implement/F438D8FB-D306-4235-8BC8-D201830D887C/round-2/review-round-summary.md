# Review Round 2

- Mode: `diff`
- 10 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Fence-aware plan command parsing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: `parse_plan_commands` recognizes plan headings before applying Markdown fence state, so heading-like lines inside fenced Markdown examples can produce phantom `NEW` or `UPDATED` command rows. This can make command extraction disagree with other fence-aware consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-grammar-compat: Either route `_trailer_map` through `plan_grammar.match_trailer_line` (documenting any intentional legacy tolerance in one place) or snapshot only keys that strict parsing also recognizes, and add a Gate B → revise integration test that runs snapshot, dedup, and `validate_optional_trailer_keys_preserved` on the same legacy-spelling plan.


### FINDING_2: Revise-waterfall heading preservation
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: The revise-waterfall `_heading_count` guard still uses a private level-three colon-only regex. Supported `##` and bracket firm headings can therefore count as zero, allowing an autofix that removes all such headings to pass heading-preservation validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-grammar-compat: Replace `_heading_count` with `len(list(plan_grammar.iter_plan_headings(text)))` (or the same firm-heading iterator used elsewhere), and add a revise-waterfall regression where the original plan uses `##` / bracket headings.


### FINDING_3: Bootstrap provenance stripping must require terminal trailers
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-edge-cases, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: Bootstrap provenance stripping anchors on an arbitrary or last textual `diff_lines` match rather than a valid terminal trailer block. Earlier non-terminal examples, trailing prose, or incompatible fence handling can cause provenance to be removed from the wrong region.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-grammar-compat: Resolve the trailer boundary with `plan_grammar.parse_final_trailers(..., require_diff_lines=True)` and reuse `plan_grammar.iter_heading_events` fence semantics (or a shared helper), with a test for body `diff_lines:` plus a terminal block and for fenced trailer-like lines.


### FINDING_4: Publication provenance splice must use terminal trailer parsing
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: Publication provenance insertion still uses an arbitrary final `diff_lines` regex match. A non-terminal `diff_lines` example followed by prose can receive provenance at an invalid metadata boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-grammar-compat: Use `parse_final_trailers` with `require_diff_lines=True` for the insertion point and do not splice invalid terminal structures.


### FINDING_5: Override-region classification must use typed trailer matching
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: `_is_override_trailer_region_line` uses permissive private patterns instead of the shared typed trailer grammar. Invalid values such as `diff_added: 08` can be treated as part of the override region even though shared parsing rejects them, causing inconsistent trailer boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-grammar-compat: Classify override-region lines with `plan_grammar.match_trailer_line` and the documented optional-size key subset, and add a test where `diff_added: 08` is excluded from the override region.


### FINDING_6: Malformed recognized metadata must be rejected
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: Malformed recognized metadata is silently ignored and replaced with defaults. Invalid values such as `mechanical_churn: TRUE` or `rounds_completed: nope` can therefore allow processing to continue instead of returning the existing invalid-metadata refusal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_7: Revise replacements must contain a valid terminal diff_lines trailer
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: Revise-waterfall file replacement validation accepts any multiline `diff_lines` match rather than requiring a terminal trailer block. Patches containing earlier or non-terminal `diff_lines` lines can pass validation while remaining inconsistent with `emit_plan` and downstream terminal parsing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-grammar-compat: Require `plan_grammar.terminal_diff_lines(repl) is not None` and reject plans where that value is not the sole terminal trailer owner, matching `emit_plan` in `plan_review_loop.py:179`.


### FINDING_8: Preflight regression coverage for metadata and terminal trailers
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Preflight lacks regression coverage for blank-separated review metadata, malformed and non-terminal trailer cases, duplicates, and full trailer sets. These gaps can allow regressions in blank-tolerant lookup or malformed-metadata refusal without CI detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_9: Consumer parity and migration regression suites are incomplete
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Consumer-level tests do not fully lock parity across supported heading forms, size gates, command parsing, terminal trailer handling, difficulty confidence, drafter behavior, Step 5c composition, publication splicing, and bootstrap stripping. Shared grammar changes can therefore cause consumers to diverge without focused failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_10: Gate B trailer snapshots must agree with strict parsing
- **Reviewer(s)**: dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: Gate B builds trailer snapshots with a lax whole-document regex while post-apply validation reads optional trailers through strict `plan_grammar.parse_final_trailers`. Legacy spellings such as `diff_added: 08` or `mechanical_churn: 1` can therefore be snapshotted and deduplicated even though strict parsing rejects them, causing Gate B, revise, publish, and size-gate metadata to disagree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-grammar-compat: Either route `_trailer_map` through `plan_grammar.match_trailer_line` (documenting any intentional legacy tolerance in one place) or snapshot only keys that strict parsing also recognizes, and add a Gate B → revise integration test that runs snapshot, dedup, and `validate_optional_trailer_keys_preserved` on the same legacy-spelling plan.
