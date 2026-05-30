### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:75-87 (planned Bash branch)
- **Concern**: Bash matcher underspecified for multiline/compound commands. Scenario: Plan says detect a read when the command is cat/tail/head/… whose argument matches the classifier; #3175 polling often used multiline Bash with leading assignments and embedded `cat …/tasks/<id>.output` (not cat as argv[0]). A literal argv-only matcher passes the planned single-line harness but misses the incident shape.
- **Proposed resolution**: Specify matching against the full `tool_input.command` string: require a read-verb token and a `tasks/<id>.output` path match anywhere in the body (newlines/pipelines/`&&` OK); add one multiline `Bash` harness case mirroring incident transcripts.


