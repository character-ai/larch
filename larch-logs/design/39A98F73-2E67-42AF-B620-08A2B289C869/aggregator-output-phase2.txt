Verifying the cited code so normalized concerns match the implementation.
Two independent correctness gaps for the planned #3175 Bash/task-output work: neither subsumes the other, so they stay as separate findings.

### FINDING_1: Bash task-output classifier end-anchored on full command
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The task-output classifier applies an end-anchored `(^|/)tasks/[A-Za-z0-9._-]+\.output$` pattern to the entire `tool_input.command`. Real incident transcripts use suffixes after the path (`2>/dev/null`, `| head -5`, `|| echo`), so the command does not end at `.output`, the Bash branch stays silent, and polling continues. Planned harness cases use bare `cat …/tasks/<id>.output` only, so CI can pass while production still misses #3175.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Split path vs command matching: keep `$` only for `Read` `file_path`. For Bash, match `tasks/<id>.output` with a suffix-tolerant pattern (e.g. allow trailing whitespace, `2>`, `|`, `;`, `&&`, `||`) or extract the path token first. Add a harness case mirroring transcript suffixes (`2>/dev/null`, `| head -5`).

### FINDING_2: Read-only `tool_name` gate blocks Bash PostToolUse
- **Reviewer(s)**: Cursor-dyn-hook-mechanics
- **Severity**: important
- **Concern**: `hooks.json` is widened to `Read|Bash`, but the plan does not require replacing the script’s Read-only `tool_name` gate. After the hooks.json change, every Bash `PostToolUse` still hits `[ "$tool_name" = "Read" ] || exit 0` (currently line 14) and exits before any new Bash branch runs, so the #3175 fix is dead in production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-hook-mechanics: Add an explicit plan step: replace the single-tool guard with Read|Bash branching (e.g. case on tool_name) before classifier/Bash logic; mirror in hook-anti-read-poll.md

**Merge note:** FINDING_1 is classifier/harness fidelity on commands that reach the Bash path; FINDING_2 is whether Bash events reach that path at all. Both must be addressed for #3175 to work in production. On current `main`, line 14 is still the Read-only early exit reviewers cite; the `.output` classifier and extended harness lines refer to the planned change under review, not yet present in the tree I read.
