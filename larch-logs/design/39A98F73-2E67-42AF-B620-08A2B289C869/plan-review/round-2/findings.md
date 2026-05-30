### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:79-83; scripts/test-hook-anti-read-poll.sh:93-99
- **Concern**: Task-output classifier uses end-anchored `.output$` on the full Bash command string. Scenario: Item 1 defines `(^|/)tasks/[A-Za-z0-9._-]+\.output$` and item 2(b) applies that classifier to the entire `tool_input.command`. Incident transcripts use `cat …/tasks/<id>.output 2>/dev/null`, `… | head -5`, and `|| echo` suffixes, so the command does not end at `.output` and the Bash branch stays silent while polling continues. Planned harness cases use bare `cat …/tasks/<id>.output` only, so CI can pass while production misses #3175.
- **Proposed resolution**: Split path vs command matching: keep `$` only for `Read` `file_path`. For Bash, match `tasks/<id>.output` with a suffix-tolerant pattern (e.g. allow trailing whitespace, `2>`, `|`, `;`, `&&`, `||`) or extract the path token first. Add a harness case mirroring transcript suffixes (`2>/dev/null`, `| head -5`).

### FINDING_2:
- **Reviewer(s)**: Cursor-dyn-hook-mechanics
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/hook-anti-read-poll.sh:14; plan.txt:71-87
- **Concern**: hooks.json widens to Read|Bash but the plan never requires replacing the script's Read-only tool_name gate. Scenario: After hooks.json changes, every Bash PostToolUse still hits [ "$tool_name" = "Read" ] || exit 0 at line 14 and exits before the new Bash branch runs — the #3175 fix is dead in production
- **Proposed resolution**: Add an explicit plan step: replace the single-tool guard with Read|Bash branching (e.g. case on tool_name) before classifier/Bash logic; mirror in hook-anti-read-poll.md
