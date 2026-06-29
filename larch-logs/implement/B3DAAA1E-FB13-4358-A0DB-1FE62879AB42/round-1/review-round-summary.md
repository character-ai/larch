# Review Round 1

- Mode: `diff`
- 3 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Test target is not wired into harness shards
- **Reviewer(s)**: codex-specialist-correctness, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: important
- **Concern**: The new `test-lint-skill-closure-growth` target is defined, but no `test-harnesses-*` shard depends on it. CI and `make test-harnesses` can skip the regression test, leaving the ratchet untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_2: UTF-8 decode failures bypass tool-specific errors
- **Reviewer(s)**: codex-specialist-correctness
- **Severity**: latent
- **Concern**: Invalid UTF-8 in the baseline JSON or referenced markdown files can raise `UnicodeDecodeError` and print a traceback instead of exiting through the lint tool’s expected error path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.


### FINDING_3: Skill closure baseline is stale and too permissive
- **Reviewer(s)**: codex-specialist-edge-cases, codex-specialist-testing, codex-generalist
- **Severity**: important
- **Concern**: The committed `/design` skill closure baseline is higher than the live scanner output. The ratchet can allow about 85 lines of growth before failing, defeating the intended regression guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.
  - From codex-generalist: Address the concern above.
