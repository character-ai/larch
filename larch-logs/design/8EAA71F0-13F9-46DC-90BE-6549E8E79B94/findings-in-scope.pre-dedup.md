### FINDING_1:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: python/larch/review/review_and_fix.py:177-200
- **Concern**: Plan explicitly leaves regenerated baseline ownership unchanged. Scenario: Only baseline files are dirty, so the new empty-intersection noop still carries those files into later steps and can reproduce the stranded-tree recovery failure
- **Proposed resolution**: Choose and implement one policy for run-generated baselines: commit them with the review fix or revert them, while preserving unrelated user changes



### FINDING_2:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/review/review_and_fix.py:177-200
- **Concern**: Define NUL-safe and rename-aware status-path parsing. Scenario: An untracked collected path containing a quoted or control character can be emitted literally by the collector but quoted by non-NUL porcelain; intersection then omits it and incorrectly returns noop
- **Proposed resolution**: Use `git status --porcelain=v1 -z --untracked-files=all` with canonical parsing, including rename/copy records, and add a matching regression case



