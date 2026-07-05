### OOS_1: [OUT_OF_SCOPE] Depth-blind segment splitting can misclassify grouped one-liners
- **Reviewer(s)**: cursor-specialist-edge-cases, dyn-dyn-awk-segments
- **Severity**: latent
- **Concern**: Segment-boundary detection does not track paren/brace nesting, so `;`, `|`, and `&` inside grouped commands can still split segments and mis-attribute `pipe_fed` or segment starts. The reviewers frame this as a pre-existing or explicitly accepted limitation rather than a regression in this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Track nesting depth or document as an explicit limitation if accepted.
  - From dyn-dyn-awk-segments: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Only the first violation class is reported per candidate
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: nit
- **Concern**: The per-segment if/else-if chain reports only the first violation class, so a candidate that hits multiple classes will surface just one message. The reviewer treats that as an accepted single-report behavior rather than a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Report all applicable violation types per segment, or document single-report behavior.

### OOS_3: [OUT_OF_SCOPE] Continuation-line and absolute-root probes remain documented residual limits
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Continuation lines and absolute search roots are still unchecked, so multiline or absolute-root probes can evade the linter by design. The output marks this as a pre-planned limitation, not a new bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Missing `&` boundary fixture leaves a restated separator case unverified
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The harness already covers `||`, `&&`, and `;`, so the proposed `&` case is the same separator path with a different token. The reviewer explicitly calls it out as a restated boundary test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] Named parity harness for explicit-path vs parent-ascent is an alternative design
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: latent
- **Concern**: The plan asked for dedicated explicit-path vs parent-ascent parity tests, but the implementation folded both checks into one `argv_walk()`. The reviewer treats that as acceptable design drift rather than a regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Missing `|&` parent-ascent failure test leaves the new stderr-pipe path unverified
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: nit
- **Concern**: The harness allows `|&` but does not assert the parent-ascent failure for that path, so CI still lacks a regression test for the stderr-pipe branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Add a cat file.txt |& rg PATTERN ../root violation case mirroring the existing | parent-ascent test.

### OOS_7: [OUT_OF_SCOPE] Normal argument-order assumptions still allow obfuscated path-first probes
- **Reviewer(s)**: dyn-dyn-awk-segments
- **Severity**: latent
- **Concern**: Parent-ascent detection still assumes the usual `pattern`-before-`path` layout, so a path-first probe such as `rg ../root PATTERN` can be misclassified and slip past the pipe-fed no-path gate. The reviewer marks this as pre-existing obfuscation risk rather than a regression from the refactor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-awk-segments: Address the concern above.

