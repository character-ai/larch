### OOS_1:
- **Description**: Guard blind spot for multi-file pytest targets is real but a guard rewrite is unnecessary scope. Scenario: Extending extract_pytest() or ENFORCED semantics to attribute multiple files per recipe is extra machinery when classify-bump can be fixed in the Makefile alone
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/lint-harness-pytest-partition.py:95-132
- **Phase**: design
- **Filed URL**: https://github.com/character-ai/larch/issues/4592
### OOS_2:
- **Description**: Plan omits docs/linting.md sync when test-classify-bump drops test_release.py. Scenario: The table still says classify-bump covers release helper CLIs via test_release.py, so operators may assume release pytest coverage still rides that target after the harness change
- **Reviewer**: Cursor-Requirements
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:222
- **Phase**: design

### OOS_1:
- **Description**: Approved outline requires filing a /rebalance-tests harness follow-up issue; the plan only documents running rebalance after merge. Scenario: Tracking work may be lost even though shard imbalance is accepted in this PR
- **Reviewer**: Cursor-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:21
- **Phase**: design

### OOS_1:
- **Description**: After `test-classify-bump` stops invoking `python/test_release.py`, the linting harness table still describes release-helper CLIs on that target. Scenario: Operators reading docs may believe release tests still run under `make test-classify-bump`; harness behavior still passes via dedicated release targets
- **Reviewer**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/linting.md:222
- **Phase**: design

