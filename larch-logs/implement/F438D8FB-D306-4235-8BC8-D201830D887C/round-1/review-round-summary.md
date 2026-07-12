# Review Round 1

- Mode: `diff`
- 14 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Fence closing must honor the opening fence length
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Fence tracking closes on any same-character fence, even when the closing run is shorter than the opener. A four-backtick fence containing a three-backtick line can expose embedded heading-like text to plan parsing, scope extraction, or heading counting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: Scope extraction must use fence-aware section detection
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-testing
- **Severity**: major
- **Concern**: Raw detection of the Files-to-modify/create section can recognize fenced examples and disagree with fence-aware heading traversal. A fenced section heading can suppress fallback behavior, while later valid entries are ignored or extracted inconsistently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_3: Preserve root-level paths during scope extraction
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: `extract_scope_paths` filters candidates by requiring `/`, dropping valid root-level or single-segment paths such as `README.md` and `Makefile`. This makes scope extraction disagree with command parsing and firm-heading consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-grammar-compat: Remove the slash-only filter or match the prior acceptance rule (reject only `+` prefixes / empty tokens); add fixtures for `##` / `###` and bracket firm headings without directory separators, including the fenced-heading / later-entry cases promised in the plan.


### FINDING_4: Route size checking through terminal trailer parsing
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: `check-size` still identifies `diff_lines` using a last-line regex while other consumers use `terminal_diff_lines`. Non-terminal examples, trailing prose, or multiple metadata islands can cause size gates, drift counting, and review continuation to interpret the same plan differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-grammar-compat: Route `check-size` through `plan_grammar.terminal_diff_lines` (or `parse_final_trailers(..., require_diff_lines=True)`) and align `plan_lines` / `metadata_trailer_lines` math with the shared parser span; add parity fixtures for non-terminal and post-trailer tail lines.


### FINDING_5: Unify optional metadata parsing with the shared grammar
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: `parse_optional_metadata` and related consumers retain private trailer classifiers and regexes alongside `plan_grammar`. Lax forms such as `mechanical_churn: 1` or `diff_added: 08` can therefore be accepted by one path and rejected by another, causing size-gate, snapshot, publish, and review behavior to diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-grammar-compat: Rebuild `parse_optional_metadata` on `plan_grammar.parse_final_trailers` (or typed `match_trailer_line` over the final span), preserve only deliberate legacy carve-outs in one documented place, and add fixtures for `mechanical_churn: 1` vs `mechanical_churn: true` and `diff_added: 08`.


### FINDING_6: Make Preflight metadata lookup use typed terminal trailers
- **Reviewer(s)**: cursor-specialist-testing, dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: Preflight’s blank-tolerant metadata window still uses prefix checks and a last-`diff_lines` scan rather than shared typed trailer recognition. Malformed prefix-sharing lines or non-terminal `diff_lines` entries can expand or anchor the window incorrectly, and the planned blank-separated metadata fixtures are missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-grammar-compat: Keep the blank-tolerant window policy, but locate `diff_lines` with `plan_grammar.terminal_diff_lines`, extend the window only across lines that `match_trailer_line` accepts (still allowing blank separators), and add the promised preflight fixtures.


### FINDING_7: Preserve Gate B compatibility for legacy optional trailers
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-grammar-compat
- **Severity**: major
- **Concern**: Gate B’s `_trailer_map` now applies strict shared-trailer validation where the prior whole-document matcher tolerated legacy optional trailer spellings. Historical plans may produce different snapshot maps and fail deduplication with `trailer-key-drift` despite unchanged operator-visible semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-grammar-compat: Document the intentional tightening in `plan_review_common.py`, add whole-document Gate B fixtures for every `OPTIONAL_SIZE_TRAILER_KEYS` entry (valid and previously tolerated invalid lines), and decide whether compatibility requires a documented lax whole-document matcher separate from terminal-block parsing.


### FINDING_8: Use grammar-aware heading iteration for revision guards
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases
- **Severity**: major
- **Concern**: The revision-waterfall heading count retains a private level-three colon-only grammar. Supported level-two or bracket headings can bypass heading-preservation checks, potentially allowing an autofix to remove valid plan sections.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.


### FINDING_9: Bootstrap provenance stripping should use the terminal diff trailer
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Bootstrap provenance stripping still resolves its insertion/removal point from an arbitrary trailing `diff_lines` regex match. Earlier examples or non-terminal metadata can cause the wrong trailer region to be stripped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.


### FINDING_10: Add consumer regression coverage for grammar migration
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: Only `test_plan_grammar.py` was updated, leaving migrated Preflight, Gate B, issue-wire, difficulty, drafter, publish, bootstrap, and plan-quality behavior without targeted regression coverage. Required cases include fenced and level-two scope headings, terminal `diff_lines`, blank-separated metadata, and consumer compatibility behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_11: Restrict Step 5c trailer peeling to intended keys
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: `_peel_trailing_optional_trailers` now peels every trailer key except `diff_lines`, expanding beyond the previous auto-compose behavior. Orphan `review_status` or `rounds_completed` lines may be silently moved during sidecar recovery without lifecycle coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_12: Keep command extraction fence-aware
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: `parse_plan_commands` matches headings line-by-line without fence state, so heading-like text inside fenced examples can be counted for command extraction while being ignored by scope and size consumers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-grammar-compat: Iterate with `plan_grammar.iter_heading_events` (or skip heading handling while inside fences) so command parsing matches the shared grammar contract.


### FINDING_13: Migrate remaining marker-regex bypasses separately
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: Marker ownership remains implemented locally in `decompose.py`, `learn_from_bugs.py`, and `design_router.py`, outside the current plan’s migration scope. Marker drift can therefore continue through those paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-grammar-compat: File follow-up issues through the Step 5b OOS pipeline as the plan directs.


### FINDING_14: Use typed trailer matching for override-region detection
- **[OUT_OF_SCOPE]**
- **Reviewer(s)**: dyn-dyn-grammar-compat
- **Severity**: minor
- **Concern**: `_is_override_trailer_region_line` still uses hand-written patterns and prefix checks, so oversize-override editing can classify values such as `diff_added: 08` differently from the shared grammar.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-grammar-compat: Delegate optional-trailer region detection to `plan_grammar` typed matchers for consistency with publish and Gate B.
