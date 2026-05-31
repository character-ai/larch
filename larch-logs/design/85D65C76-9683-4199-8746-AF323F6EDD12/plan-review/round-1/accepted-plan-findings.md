### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:27-28; scripts/lib-validate-meta-path.sh:14-25; scripts/test-launch-review.sh:1871-1878
- **Concern**: launch-review --stderr-sink validation says reject .. but reuse validate_meta_scalar_path which only checks the charset allowlist (same as run-external-agent --stderr-sink and launch-review --output). Scenario: test-launch-review.sh extension pins .. rejection at parse time; implementer following validate_meta_scalar_path only passes newline tests and .. reaches .meta / retry
- **Proposed resolution**: Align the plan and harness: either drop .. from launch-review parse-time rejection (keep .. fail-closed in validate_retry_stderr_sink_or_mark only, matching --output) or add an explicit *..* guard beside validate_meta_scalar_path and pin exact message + exit code


