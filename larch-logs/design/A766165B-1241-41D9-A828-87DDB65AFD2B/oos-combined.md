### OOS_1: Aggregated rollup of 2 capped OOS items
- **Description**: Cap 1 (OOS_ISSUES_PER_RUN_CAP) exceeded; the following 2 items were rolled up by skills/implement/scripts/oos-issue-cap.sh:
  - **- **Description**: [OUT_OF_SCOPE] Agentic timeout recovery can trust a stale push checkpoint. Scenario: A previous delegate writes ci-agentic-push-checkpoint.latest; a later delegate in the same tmpdir times out before its first push; the parent reports pushed or rebase pending from the old run**: OOS_1: - Description: [OUT_OF_SCOPE] Agentic timeout recovery can trust a stale push checkpoint. Scenario: A previous delegate writes ci-agentic-push-checkpoint.latest; a later delegate in the same t… [Files: python/ci_monitor.py:1435-1517 python/ci_agentic_fix.py:143-160]
  - **- **Description**: Delegate timeout uses 2x SUBPROCESS_DEFAULT per cycle while verify_job_locally runs per fixable job. Scenario: Multi-job failures can exceed the added budget; parent may still kill a valid delegate on heavy matrices**: OOS_1: - Description: Delegate timeout uses 2x SUBPROCESS_DEFAULT per cycle while verify_job_locally runs per fixable job. Scenario: Multi-job failures can exceed the added budget; parent may still k… [Files: python/ci_monitor.py:1456-1459]
- **Reviewer**: Combined: capped per-run rollup
- **Vote tally**: N/A — capped rollup of 2 entries
- **Phase**: implement
