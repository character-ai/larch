### OOS_1: [OUT_OF_SCOPE] correctness: lint gate is enabled before the baseline is clean
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, codex-specialist-testing, dyn-dyn-lint-scope
- **Severity**: blocking
- **Concern**: The new em-dash lint is wired into `make lint`, pre-commit, and CI before the repository is scrubbed, so the current tree still fails on `python/larch/review/voting.py:1167`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From dyn-dyn-lint-scope: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] correctness: subprocess timing labels remain unscanned
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-lint-scope
- **Severity**: latent
- **Concern**: Timing labels passed through subprocess argv still contain U+2014 and sit outside the current sink-literal scan, so they can remain unlinted even after the new check lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.
  - From dyn-dyn-lint-scope: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] correctness: assign-then-emit bypasses the lint
- **Reviewer(s)**: cursor-specialist-correctness, dyn-dyn-lint-scope
- **Severity**: important
- **Concern**: The AST pass only checks string literals passed directly to sinks, so a U+2014 literal can be assigned to a variable and then emitted later without being caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From dyn-dyn-lint-scope: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] architecture: fenced markdown examples stay outside the matcher
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: Fenced markdown examples with U+2014 are still excluded, so documentation examples can remain unlinted even when they model emitted output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From cursor-specialist-testing: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] correctness: stdout/stderr sink coverage lacks tests
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The documented `sys.stdout.write` and `sys.stderr.write` sink paths do not have pytest coverage, so a regression in sink handling could slip by unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] risk-integration: shell breadcrumb templates stay outside lint scope
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: Shell `printf` breadcrumb templates can still emit U+2014 while the Python and markdown lint passes, so that surface remains uncovered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] correctness: rendering prompt assembly bypasses sink-literal scanning
- **Reviewer(s)**: dyn-dyn-lint-scope
- **Severity**: latent
- **Concern**: Review/voter prompt text in `python/larch/rendering/rendering.py` is assembled outside the sink model and only printed later, so its U+2014 literals remain invisible to the lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-lint-scope: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] correctness: review dispatch f-strings bypass sink-literal scanning
- **Reviewer(s)**: dyn-dyn-lint-scope
- **Severity**: latent
- **Concern**: Dynamic reviewer bodies in `python/larch/review/review_dispatch_panel.py` are built in returned f-strings rather than direct sink calls, so their U+2014 literals remain outside the lint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-lint-scope: Address the concern above.

