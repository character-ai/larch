### OOS_1: [SCOPE-REDUCTION] Validate $state_dir before mkdir/chmod instead of after
- **Description**: [SCOPE-REDUCTION] Validate $state_dir before mkdir/chmod instead of after. Scenario: The plan runs mkdir -p and chmod 700 on $state_dir before the non-symlink directory check, so a preplaced symlink can still get follow-on directory creation or mode changes on the redirect target even though later temp creation is blocked
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Phase**: design



### OOS_2: Operator-facing hook doc is not in the firm file list
- **Description**: Operator-facing hook doc is not in the firm file list. Scenario: SECURITY.md will note symlink posture, but hook-anti-read-poll.md remains the shipped operator inventory for this hook and still omits the new read/write state rules
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.md
- **Phase**: design



### OOS_3: Operator-facing hook note not updated alongside SECURITY.md
- **Description**: Operator-facing hook note not updated alongside SECURITY.md. Scenario: SECURITY.md will document symlink-safe state handling, but the shipped `hook-anti-read-poll.md` inventory still describes only generic repeated-Read behavior with no temp-state trust boundaries.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.md
- **Phase**: design



