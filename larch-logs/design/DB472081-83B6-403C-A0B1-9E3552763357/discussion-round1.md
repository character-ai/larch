## Decision 1: Marker auto-committed without operator approval
- **Question**: Is the learn-from-bugs state marker committed automatically or gated behind operator approval in Step 5?
- **Resolution**: Automatic — the issue says "committed by /learn-from-bugs runs" without mentioning approval. The marker is tracking metadata (like run logs), not a functional repo mutation.
- **Source**: issue text + analogy with design/implement log commits

## Decision 2: "Newer" = issue number, not date
- **Question**: For the backlog count, should "newer than the marker" filter by closedAt > run_date or number > max_issue_number?
- **Resolution**: Filter by closedAt > run_date (ISO8601 stored in marker). The run_date is the natural "since last run" boundary and matches how GitHub search works. The max issue number is stored as a secondary field but backlog count uses the date boundary.
- **Source**: codebase reasoning + issue spec storing both fields

## Decision 3: Nudge is a chat suggestion line, not part of the filed audit report
- **Question**: Where does the nudge appear — in the filed audit report issue, or printed to chat during the audit run?
- **Resolution**: Printed to chat during the audit run ("print one suggestion line"). Not part of the filed issue body. Emitted after scanning, before or after the post-report user prompt.
- **Source**: issue text: "print one suggestion line naming the count and the /learn-from-bugs command"

## Decision 4: Marker write happens via new CLI verb in learn_from_bugs.py
- **Question**: Is the marker write/read implemented as a Python CLI verb or inline LLM logic in the SKILL.md?
- **Resolution**: Python CLI verb (write-state and read-state) in learn_from_bugs.py, registered in larch/cli.py. Required for unit tests.
- **Source**: architecture pattern (all operations with test requirements use Python verbs) + issue requirement for unit tests
