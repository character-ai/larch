### OOS_1: [OUT_OF_SCOPE] unsafe right-hand `||` fallback is not checked
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: The candidate selection logic only inspects the first grep-family command on a line, so an unsafe search on the right-hand side of `||` can bypass the `../` guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] pattern-file operands skip ascent checks
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: important
- **Concern**: The path guard does not inspect `-f` / `--file` operands, so a parent-ascent path hidden in the pattern-file argument can still evade detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] later pipeline or semicolon commands are skipped
- **Reviewer(s)**: cursor-specialist-correctness
- **Severity**: latent
- **Concern**: Grep-family commands that appear after a pipe or semicolon are skipped entirely, so later commands on the same line are never checked for `../` operands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] split-value ripgrep options can bypass the guard
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: important
- **Concern**: Split-value forms for ripgrep options like `--include` and `--exclude` can still be misparsed, letting a parent-ascent operand slip past the no-path guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] duplicated argv walkers can drift
- **Reviewer(s)**: cursor-specialist-edge-cases, cursor-specialist-testing
- **Severity**: latent
- **Concern**: The explicit-path and parent-ascent checks duplicate argv parsing loops, so a future option-parser edit could update one walker but not the other and reintroduce missed `../` operands or stdin false positives.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Extract one shared path-operand parser when a third caller justifies the refactor
  - From cursor-specialist-testing: Extract a shared path-operand walker on the next lint change.

### OOS_6: [OUT_OF_SCOPE] continuation-line probes escape line-based scanning
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The line-based scan cannot see `../` on continuation lines, so multiline fenced probes can bypass parent-ascent detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_7: [OUT_OF_SCOPE] absolute search roots remain unbounded
- **Reviewer(s)**: cursor-specialist-edge-cases
- **Severity**: latent
- **Concern**: The linter still allows unbounded absolute search roots, so a probe can recurse through a huge tree even without any `..` segments.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases: Address the concern above.

### OOS_8: [OUT_OF_SCOPE] stale test-lint-bare-grep-probe docs row
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: nit
- **Concern**: The documentation inventory row for `make test-lint-bare-grep-probe` still points at an outdated shard name and no longer matches the current test setup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Refresh the inventory row to match scripts/test-lint-bare-grep-probe.md and Makefile shard test-harnesses-2.

