### OOS_1: [SCOPE-REDUCTION] New fingerprint hasher duplicates checks_lint_fix _RepoSnapshot primitives
- **Description**: [SCOPE-REDUCTION] New fingerprint hasher duplicates checks_lint_fix _RepoSnapshot primitives. Scenario: Parallel staged/unstaged diff and untracked digest logic in checks_lint_fix.py risks drift and adds bulk to a minimum-change fix
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/implement/checks_result_identity.py
- **Phase**: design



### OOS_2: Live rejoin should distinguish missing launch identity from active mismatch
- **Description**: Live rejoin should distinguish missing launch identity from active mismatch. Scenario: When a live registry row exists but merge/result envs lack identity fields, treating empty stored identity as a mismatch can fail closed with the wrong error class and block otherwise-safe rejoin during early live windows.
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: skills/implement/scripts/step-8-assessment.sh:734-741
- **Phase**: design



