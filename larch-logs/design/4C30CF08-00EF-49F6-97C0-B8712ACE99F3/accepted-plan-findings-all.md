### FINDING_1: Create the bgjob parent directory before seeding result envs
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: `_seed_step3_downstream()` seeds `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` without first creating the `bgjob/` parent directory, so fresh `tmp_path` runs can raise `FileNotFoundError` before the new cleanup/regression assertions execute.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Create tmp_path / "bgjob" with mkdir(parents=True, exist_ok=True) before writing the seeded result envs
  - From Codex-Innovation: Create tmp_path / "bgjob" with parents=True before seeding the new result-env files
  - From Codex-Pragmatic: Create tmp_path / "bgjob" in the helper before writing the new seeded files.
  - From Codex-Requirements: Create tmp_path / "bgjob" with mkdir(parents=True, exist_ok=True) before writing the seeded result env files


### FINDING_1: Seed the stale bgjob result envs for the cleanup regression
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: The new regression helper leaves the bgjob result env files unseeded, so the cleanup assertions can pass vacuously instead of proving that stale re-entry state is actually removed or preserved as intended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add explicit seed writes for both bgjob result env files after creating `bgjob/`, with minimal regular-file contents that the tests can assert on.
  - From Codex-Pragmatic: Seed both `bgjob/design-step3-review.result.env` and `bgjob/design-step4-tail.result.env` in the helper after creating `bgjob/`, then assert they are removed or preserved in the listed tests.
  - From Codex-Requirements: Spell out both seed writes in _seed_step3_downstream() after creating tmp_path / "bgjob".

