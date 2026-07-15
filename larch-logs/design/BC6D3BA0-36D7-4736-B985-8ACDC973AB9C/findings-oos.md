### OOS_1: Reuse existing _valid_repo_relative_path for commit-derived paths
- **Description**: Reuse existing _valid_repo_relative_path for commit-derived paths. Scenario: Plan asks for new safe-path validation though _valid_repo_relative_path already enforces bounded in-repo relative paths for sweep findings.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:3365-3377
- **Phase**: design



### OOS_2: Parallel ORCHESTRATION_ZONE_PREFIXES duplicate zone_for_path
- **Description**: Parallel ORCHESTRATION_ZONE_PREFIXES duplicate zone_for_path. Scenario: Plan adds a second prefix taxonomy and label helper beside zone_for_path, which already maps paths to stable analytics zones. Two zone models can drift and add maintenance cost.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: python/larch/issue/analyze_bugs.py:866-878
- **Phase**: design



### OOS_3: Harness coverage gaps omit budget-skipped fixes
- **Description**: Harness coverage gaps omit budget-skipped fixes. Scenario: Runtime selection only inspects orchestration paths for executed unique SHAs. Budget-skipped fixes that touch unmapped orchestration zones never get UNVERIFIED_RUNTIME annotations or coverage-gap rows.
- **Reviewer**: Cursor-Arch
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/issue/analyze_bugs.py
- **Phase**: design



