### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/step-5-resume.sh:108-112
- **Concern**: [SCOPE-REDUCTION] Planned commit-route delegation omits errexit-safe stdout capture under set -euo pipefail. Prior round-4 neutral finding still applies; the plan replaces the inline commit-fixes block but never requires the existing set +e / capture / set -e guard.. Scenario: The wrapper runs with set -euo pipefail. When implement commit-route exits non-zero without NEXT_ACTION (stall-seed failure, usage error, malformed envelope), errexit aborts before commit_output is captured or NEXT_ACTION/COMMIT_OUTCOME KVs are relayed. The orchestrator then cannot hit lacks-envelope branch 3 and may mis-route to generic Step 5 preflight. scripts/test-implement-structure.sh:369 pins the old guard and the plan drops that needle without a commit-route replacement.
- **Proposed resolution**: In step-5-resume.sh, wrap commit-route in the same set +e capture block used today (capture commit_output and commit_rc, then set -e). Parse NEXT_ACTION from commit_output before branching. Add a structure-harness pin requiring set +e around implement commit-route --site step5-resume-handoff capture.
