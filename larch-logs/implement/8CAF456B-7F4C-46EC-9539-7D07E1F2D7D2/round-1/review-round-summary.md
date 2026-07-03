# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_2: Marker-only diagnosis exemptions are too broad
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing, dyn-dyn-hook-isolation
- **Severity**: important
- **Concern**: `bash_is_marker_only_diagnosis` treats commands as marker diagnosis when they merely contain `.bg-wait-active`, which lets mixed reads, extra operands, basename collisions, or comment-suffix probes bypass the normal progress-poll deny path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Validate that Bash diagnosis commands target only the retained .bg-wait-active marker, or reject tmpdir variables/live-dir text and extra path arguments; add a regression for marker plus tmpdir artifact reads
  - From cursor-specialist-edge-cases: Require every path argument to basename-match .bg-wait-active or reject multi-path diagnosis commands; add a space-separated multi-arg regression test
  - From codex-specialist-edge-cases: Make the exemption match only simple commands whose sole filesystem operand is exactly the live `$dir/.bg-wait-active` marker, or replace the marker token and continue through the generic deny logic if any live-dir path, tmpdir variable, or extra operand remains.
  - From codex-specialist-testing: Restrict the exemption to commands whose only guarded target is .bg-wait-active and add a mixed same-tmpdir regression test.
  - From dyn-dyn-hook-isolation: Parse the diagnosis target path(s) explicitly (only paths whose final component is `.bg-wait-active`) or strip `#` comments before matching; reject commands where every non-comment argument does not resolve to a `.bg-wait-active` file. Add a regression test for the comment-suffix bypass shape.


