### FINDING_2: Guard promotion against directory destinations
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic
- **Severity**: major
- **Concern**: The promote step still uses bare `mv` into the state file, so a directory or symlink-to-directory destination can cause the temp file to be dropped into an attacker-chosen tree instead of replacing the state entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Reject non-regular destinations immediately before promotion and only rename over an absent path or plain file.
  - From Cursor-Pragmatic: Before promote, skip when [ -d "$state_file" ]; when [ -L "$state_file" ], require readlink target not be a directory (or rm -f the symlink leaf first), then mv; on guard failure rm the temp file and exit 0


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### FINDING_5:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: risk-integration
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Concern**: [SCOPE-REDUCTION] mkdir/chmod run before the directory-safety check. Scenario: With a preplaced symlink at `$TMPDIR/larch-read-poll`, `mkdir -p`/`chmod 700` can touch the attacker-chosen target before the planned fail-open exit, adding side effects the issue does not require.
- **Proposed resolution**: Validate `$state_dir` as a non-symlink directory first; call `mkdir -p` and `chmod 700` only when that check passes.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [SCOPE-REDUCTION] Validate $state_dir before mkdir/chmod instead of after
- **Description**: [SCOPE-REDUCTION] Validate $state_dir before mkdir/chmod instead of after. Scenario: The plan runs mkdir -p and chmod 700 on $state_dir before the non-symlink directory check, so a preplaced symlink can still get follow-on directory creation or mode changes on the redirect target even though later temp creation is blocked
- **Reviewer**: Cursor-Innovation
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.sh:38-40
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: Operator-facing hook doc is not in the firm file list
- **Description**: Operator-facing hook doc is not in the firm file list. Scenario: SECURITY.md will note symlink posture, but hook-anti-read-poll.md remains the shipped operator inventory for this hook and still omits the new read/write state rules
- **Reviewer**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.md
- **Phase**: design




Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: Operator-facing hook note not updated alongside SECURITY.md
- **Description**: Operator-facing hook note not updated alongside SECURITY.md. Scenario: SECURITY.md will document symlink-safe state handling, but the shipped `hook-anti-read-poll.md` inventory still describes only generic repeated-Read behavior with no temp-state trust boundaries.
- **Reviewer**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: architecture
- **Location**: scripts/hook-anti-read-poll.md
- **Phase**: design

Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

