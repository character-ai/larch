# Review Round 1

- Mode: `diff`
- 4 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: review-round-count parsing must match Step 3 authority
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-gate-render
- **Severity**: important
- **Concern**: Gate C reads `review-round-count.txt` with bare `int(raw)` instead of the digit-only, symlink-aware contract used by Step 3. Inputs like `+2`, `-1`, or `1_000` can desync cap decisions and hide or show the Re-run review panel differently from Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-gate-render: Reuse the same parsing contract as `_read_count()` / `_read_review_round_count()` (digit-only match, symlink rejection, `errors="replace"`, `OSError` → `0`), and emit `REVIEW_ROUND_COUNT_WARN=non-numeric` only when the file is non-empty and fails that contract.


### FINDING_2: Gate C should fail open on unreadable review-round-count.txt
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-gate-render
- **Severity**: important
- **Concern**: An `OSError` while reading `review-round-count.txt` currently aborts render-gate instead of falling back to count `0`. Permission errors or transient I/O issues can block final approval instead of rendering the cap-aware prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-gate-render: Match the publish/plan-review fail-open behavior: treat unreadable/missing/symlinked count files as `0`, and reserve non-zero exit for true CLI argument errors only.


### FINDING_3: Keep chooser option descriptions byte-identical and tested
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-testing
- **Severity**: important
- **Concern**: The new `OPTION_*_DESCRIPTION` strings are shorter than the prior approval-gates copy, and tests do not pin them. That lets visible chooser text drift even when the labels stay the same.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Copy prior chooser descriptions into renderer constants and assert every `OPTION_*_DESCRIPTION`.
  - From cursor-specialist-testing: Address the concern above.


### FINDING_7: Preserve panel-failed acknowledgement on See full plan rerenders
- **Reviewer(s)**: codex-specialist-edge-cases, dyn-dyn-gate-render
- **Severity**: important
- **Concern**: When Gate C is rerendered after a structured See full plan choice on a failed panel path, the follow-up render can drop `--panel-failed true` and revert the approval label instead of keeping the acknowledgment variant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From dyn-dyn-gate-render: Document that every Gate C re-render after panel failure must pass both `--design-tmpdir "$DESIGN_TMPDIR"` and `--panel-failed true` (plus `--without-see-full-plan` when applicable), and add a golden test for `--panel-failed true --without-see-full-plan`.


