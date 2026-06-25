### [Plan Review] FINDING_5

### FINDING_5: Step 8+ second `require_near` 1200-char window may be too small for retained inline skeleton
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: After relocation the entry read is first, but handoff rules, `route-exit`, discriminators, and pre-driver predicate remain inline (~1500+ chars). `require_near` only searches ±limit around the anchor, so the pre-driver fence may not be found even when ordering is correct, causing `make lint` to fail on a valid SKILL layout or forcing implementers to drop the second adjacency check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Switch the pre-driver pin to `assert_line_precedes`-style ordering (add a Python equivalent to `test-implement-structure.sh`) or chain anchors (`require_near` from read→route-exit, then route-exit→pre-driver) with limits sized to the retained skeleton.
  - From Cursor-Pragmatic: Raise the limit to match other immediate-background pins (1400–2000), split into ordered line-index checks, or shrink/count the inline skeleton bytes in the plan before fixing the limit.


### [Plan Review] FINDING_6

### FINDING_6: Plan mandates `assert_line_precedes` but omits copy-paste-safe helper definition
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The plan requires a new `assert_line_precedes` bash helper but does not ship a copy-paste-safe definition. Without the awk function body, implementers may invent incompatible semantics (windowed vs global, first vs last match) and still pass review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Include the full helper in the plan (mirroring `assert_followed_count_at_least` style) plus one worked example showing first-line-index `<` second-line-index across the Step 5b skeleton gap.


### [Plan Review] FINDING_7

### FINDING_7: `require_near` proximity check does not enforce read-before-fence ordering
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `require_near` only checks that `after` appears anywhere within ±limit of the anchor. A fence placed before the entry read but still within the window can pass, so relocated matrix/cleanup reads may be skipped on first entry while the harness stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: For Step 8+ and Step 18 entry reads, use an ordered helper (`assert_line_precedes` in the design harness, or add the same awk helper to the implement harness) instead of proximity-only `require_near`.


