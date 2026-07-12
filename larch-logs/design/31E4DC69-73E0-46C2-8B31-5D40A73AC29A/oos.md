### FINDING_1: PR references are rendered as issue regression chains
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: major
- **Concern**: The planned origin model stores issue and pull-request references in the same integer field, while headline rendering treats every reference as an issue-to-issue regression chain. A marker such as `introduced by PR #123` can therefore produce `#123 -> #6672`, misrepresenting the causal artifact.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a `ref_kind` (`issue` vs `pr`) or equivalent to `Origin`, render `#origin -> #current` chains only for issue refs, and either omit PR refs from chains or render an explicit `PR #N -> #current` form; extend headline and marker tests to cover PR-only markers.
  - From Cursor-Innovation: Omit PR-sourced refs from chain lines (still count them in regression totals), or add an explicit ref kind and render PR chains as PR #N -> #<current>.
  - From Cursor-Pragmatic: Pin chain behavior in the plan and tests: add `ref_kind` (`issue|pr`) and render PR chains as `PR #N -> #<current>`, or keep PR classification but omit PR-sourced refs from `#X -> #Y` chains while still counting them in the regression ratio
  - From Cursor-Requirements: Keep PR markers as `kind=regression`, but either add a `ref_kind` (`issue|pr`) and render PR chains as `PR #<ref> -> #<current>` (or omit PR refs from the chain list while still counting them in regression totals), and add a unit/headline fixture for `introduced by PR #N` so the chain grammar is pinned.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

