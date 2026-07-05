### FINDING_1: Segment cursor must advance past non-grep segments
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The multi-candidate loop can still stop scanning after ordinary commands that are not grep-family, which would leave later `||`, `;`, or pipeline-separated probes unchecked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify loop control explicitly: when `advance_to_command_start` finds no grep-family token, still search forward for the next segment boundary (`||`, `&&`, `;`, `|`, `|&`) and continue; never `next` the line solely because the current segment has no candidate.
  - From Cursor-Pragmatic: Define the loop as: from cursor `pos`, call `advance_to_command_start(pos)`; if grep-family, run the per-candidate checks; then always find the next unquoted segment separator and set `pos` to the token after it, whether or not the current segment produced a candidate. Add a regression such as `echo ok; rg PATTERN ../root`
  - From Cursor-Requirements: Add an outer loop rule: from each boundary restart, if advance_to_command_start does not yield a grep-family command, scan forward to the next listed separator and repeat until a grep-family candidate is found or the line is exhausted; only a safe evaluated candidate may continue scanning.


### FINDING_2: Pipe-fed stdin detection must treat `|&` like `|`
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The pipe-fed predicate appears to recognize only `|`, so `|&` producers could be misclassified and either false-positive on allowed inputs or miss the intended pipe-fed exemption.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add `|&` to the pipe-fed predecessor check (and document it beside `|` in the contract and harness bullets).
  - From Cursor-Innovation: When deciding a candidate is pipe-fed, treat the immediately preceding unquoted token as `|` or `|&`; document the same rule in `scripts/lint-bare-grep-probe.md`.


### FINDING_3: `is_bare_wrapper_grep` must anchor to the segment start
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: Bare-wrapper detection is still described as line-start oriented, so a `grep` after `||` or `;` on the right-hand side can evade the bare-wrapper check even if the multi-candidate loop reaches it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Make `is_bare_wrapper_grep` take the segment boundary index from `advance_to_command_start` and treat `grep` as bare when it is the first command word after that peel (still exempt command `grep` and allowed pipe-fed forms).
  - From Cursor-Requirements: Rebase `is_bare_wrapper_grep` (or pass `segment_start`) so bare-wrapper detection uses the same segment-local prefix peeling as `advance_to_command_start`, with the existing pipe-fed grep carve-out.


### FINDING_5: Attached short `-fVALUE` operands still need parent-ascent checks
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Concern**: The parent-ascent guard covers split and long-form pattern-file operands, but attached short `-fVALUE` forms can still hide a `../` path in the value and bypass the check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Treat attached short `-fVALUE` as a consumed pattern-file value in the shared walker, run `has_parent_ascent_segment()` on `VALUE`, and add one regression with a follow-on safe search path.


