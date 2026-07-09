### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:27-31
- **Concern**: The new fixture seeding is left blank after `Seeds:`.. Scenario: `_seed_step3_downstream()` will only create `.completed` markers, so the added cleanup assertions cannot prove that stale `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` are removed, and the no-op test cannot assert they survive when `.step3-reentry` is absent.
- **Proposed resolution**: Add explicit seed writes for both bgjob result env files after creating `bgjob/`, with minimal regular-file contents that the tests can assert on.

### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: python/tests/review/test_plan_review.py:27-30
- **Concern**: _seed_step3_downstream() does not explicitly seed the two bgjob result env files the plan’s new assertions depend on.. Scenario: The new cleanup checks can pass vacuously on missing files, so the regression path is not actually exercised or verified.
- **Proposed resolution**: Seed both `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` in the helper after creating `bgjob/`, then assert they are removed or preserved in the listed tests.

### FINDING_3:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: plan.txt:27-30
- **Concern**: _seed_step3_downstream() leaves the new Seeds step unspecified, so it never says to write the two bgjob result envs the cleanup tests depend on.. Scenario: The updated no-op and cleanup assertions can pass vacuously or fail at setup because the helper still seeds only downstream sentinels, not bgjob/design-step3-review.result.env and bgjob/design-step4-tail.result.env.
- **Proposed resolution**: Spell out both seed writes in _seed_step3_downstream() after creating tmp_path / "bgjob".
