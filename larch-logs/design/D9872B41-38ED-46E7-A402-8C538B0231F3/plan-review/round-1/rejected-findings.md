### [Plan Review] FINDING_3

### FINDING_3: Test-harness pytest dependency may remain unnecessarily pinned
- **Reviewer(s)**: Codex-dyn-ci-shard-contract
- **Severity**: latent
- **Concern**: The plan keeps the test-harness pytest pin because of `scripts/test-relevant-checks.sh`, but that harness stubs pytest rather than requiring the installed package. Removing `test-merge-parity` may leave the test-harness CI shard installing pytest and carrying Python parity comments without a remaining harness consumer.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-ci-shard-contract: Remove pytest==9.0.3 from .github/workflows/requirements-test-harnesses.txt and update the related comments to PyYAML-only; keep python/requirements-test.txt for make py-test


