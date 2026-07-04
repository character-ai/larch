### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3-review.sh:421-427
- **Concern**: [SCOPE-REDUCTION] Step 3 launch identity capture still lands in Bash. Scenario: The plan says move retained-pid checks into Python, but also assigns Bash to write a sidecar with ps start time and command signature right after _loop_pid=$!. That reintroduces fragile Bash 3.2 ps parsing the plan explicitly avoids, and duplicates logic process_identity.py will own.
- **Proposed resolution**: After background launch, call one quiet Python helper to capture ps identity and atomically write the sidecar (for example plan-review write-loop-identity --design-tmpdir ... --pid $_loop_pid with expected needle derived from the launch argv). Keep Bash to pid bookkeeping, wait, and trap gating only.


