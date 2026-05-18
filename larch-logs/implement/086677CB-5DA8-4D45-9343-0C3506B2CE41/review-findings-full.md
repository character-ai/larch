### FINDING_1: panel [code-review/accepted]

## **Nit** `risk-integration` — `docs/linting.md:22`, `docs/linting.md:71`, `.github/workflows/ci.yaml:186`, and `scripts/test-harness-shards-coverage.md:26-27` still contain stale `10`-shard references after the Makefile/workflow moved to 11 shards. The most operationally relevant one is the LPT snippet using `range(10)`, which would regenerate 10 bins if a maintainer follows the documented rebalance procedure. Update these references to 11, including the workflow step label and the shard-coverage sibling contract.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `risk-integration` — `docs/linting.md:22`, `docs/linting.md:71`, `.github/workflows/ci.yaml:186`, and `scripts/test-harness-shards-coverage.md:26-27` still contain stale `10`-shard references after the Makefile/workflow moved to 11 shards. The most operationally relevant one is the LPT snippet using `range(10)`, which would regenerate 10 bins if a maintainer follows the documented rebalance procedure. Update these references to 11, including the workflow step label and the shard-coverage sibling contract.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## code-quality: scripts/test-harness-shards-coverage.md:26-27

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Sibling doc still names harnesses-10 as last shard and 1..10 umbrella span Script contract doc contradicts Makefile after reshard Update literals to 11 or describe highest-N generically
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: .github/workflows/ci.yaml:186

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step name still says shard X of 10 while matrix has 11 shards GitHub Actions UI and logs show wrong denominator for shard 11 and contradict eleven-shard docs Update display string to of 11 or otherwise sync with shard count
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## code-quality: docs/linting.md:22

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Usage CI bullet still documents harnesses-1 through harnesses-10 Readers get wrong CI matrix span vs ci.yaml and later doc sections Use through make test-harnesses-11
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## code-quality: docs/linting.md:42

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Example uses make -j10 after eleven-way sharding Readers may run one fewer parallel shard than exists Use -j11 or neutral wording
- **Suggested revision**: Address the concern above.

