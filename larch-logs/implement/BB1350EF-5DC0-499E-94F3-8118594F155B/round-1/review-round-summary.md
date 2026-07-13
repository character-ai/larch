# Review Round 1

- Mode: `diff`
- 5 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Validate self-review untracked inventory
- **Reviewer(s)**: codex-specialist-correctness, cursor-specialist-edge-cases, codex-specialist-edge-cases, codex-specialist-testing
- **Severity**: major
- **Concern**: Self-review does not validate the untracked inventory with `_snapshot_inventory()`, allowing malformed, duplicate, or unsafe entries to skew staging scope instead of failing soft.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness: Address the concern above.
  - From cursor-specialist-edge-cases: Address the concern above.
  - From codex-specialist-edge-cases: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_4: Fix monkeypatch lint violation
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: The new test monkeypatches the `_git_output` facade without the required lint suppression or regenerated baseline, causing `py-lint-checks-fast` to fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_5: Add staged-only probe-policy coverage
- **Reviewer(s)**: cursor-specialist-testing, codex-specialist-testing
- **Severity**: major
- **Concern**: The probe-policy tests lack a staged-only change, so accidental cached-path enumeration would not be detected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.
  - From codex-specialist-testing: Address the concern above.


### FINDING_6: Test fail-soft handling of hostile tracked inventory
- **Reviewer(s)**: cursor-specialist-testing
- **Severity**: major
- **Concern**: There is no regression test proving hostile tracked inventory causes `_collect_self_review_stage_paths` to return `[]` rather than failing or staging unsafe paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing: Address the concern above.


### FINDING_9: Preserve compatibility with stripped snapshot artifacts
- **Reviewer(s)**: codex-specialist-testing
- **Severity**: major
- **Concern**: Matching raw stdout against legacy stripped artifacts can classify pre-existing dirty files as coder deltas during resumed runs and stage them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing: Address the concern above.
