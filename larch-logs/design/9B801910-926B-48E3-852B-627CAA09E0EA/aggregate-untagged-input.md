### FINDING_1:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: minor
- **Focus area**: correctness
- **Location**: python/larch/bgjob/cli.py:24,64
- **Concern**: `start_main` still parses `--tmpdir` as required. Scenario: The plan-mandated omitted-`--tmpdir` regression case exits in argparse before the planned environment fallback runs.
- **Proposed resolution**: Call `_add_common_job_args` with `tmpdir_required=False` for `bgjob start`, then apply the planned fallback and missing-tmpdir error.
