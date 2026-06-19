### OOS_15: [OUT_OF_SCOPE] Unrelated design-lifecycle changes bundled in branch diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-symilar-parity-output.txt
- **Severity**: nit
- **Concern**: Unrelated `python/design_lifecycle.py` and `skills/design/*` changes are bundled in the same branch diff, outside duplicate-code review scope. Wider regression blast radius unrelated to the duplicate-code feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track in separate review if needed.
  - From cursor-specialist-testing-output.txt: Split or review separately


### OOS_16: [OUT_OF_SCOPE] CI lacks ≤90s wall-time evidence and matrix sharding for duplicate-code job
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-parallel-pairs-output.txt, dyn-lint-surface-output.txt
- **Severity**: latent
- **Concern**: No CI sharding for the duplicate-code job and no evidenced ≤90s `ubuntu-latest` wall-time acceptance. If runtime exceeds 90s, plan acceptance criteria are not met.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Measure GHA wall time; add matrix sharding if needed.
  - From cursor-specialist-testing-output.txt: Add full-tree parity gate to CI; measure GHA wall time and add matrix sharding if >90s
  - From dyn-parallel-pairs-output.txt: The job comment still describes the old pylint `-j 1` constraint; no matrix sharding was added. Plan acceptance for ≤90s GHA wall time is not evidenced in this branch (measurement-dependent).
  - From dyn-lint-surface-output.txt: The plan’s ≤90s `ubuntu-latest` wall-time acceptance gate and conditional `ci.yaml` matrix sharding are not reflected in this diff; `.github/workflows/ci.yaml` has no sharding changes for `python-lint-duplicate-code`.


