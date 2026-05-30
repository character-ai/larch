### FINDING_10: Harness covers only `cat` for Bash task-output polls
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Harness exercises only `cat` while the hook implements `tail`/`head`/`less`/`more`/`sed -n`; a regex edit removing non-`cat` verbs could ship green while `tail …/tasks/id.output` evades warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add minimal two-call Bash cases for at least tail and sed -n on a tasks/<id>.output path.


### FINDING_11: Harness omits `|| echo` (and similar) after `.output` path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Plan-listed `|| echo` suffix after task `.output` path is untested; only pipe/redirect suffixes are covered. Incident-shaped `cat …/tasks/id.output || echo …` could regress if suffix parsing changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add a two-invocation Bash case with || echo (or || true) after the .output path.


### FINDING_17: Doc overstates session isolation for task-output counters
- **Reviewer(s)**: dyn-state-file-isolation-output.txt
- **Severity**: latent
- **Concern**: `hook-anti-read-poll.md` claims distinct Claude sessions do not share counts within 600s TTL, but that holds only when `session_id` or `conversation_id` is present; `nosession` path contradicts the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-file-isolation-output.txt: Narrow the sentence to “sessions with distinct `session_id`/`conversation_id` hashes” and explicitly document that missing metadata collapses to a shared `nosession` bucket (with the cross-session bleed behavior above).


### FINDING_7: `echo`-only skip hides `cat` on same `||` segment
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `bash_segment_is_echo_only` uses `echo*`/`printf*` prefix match on whole `;`/`&&` segments, skipping any trailing read verb in the same segment. Plan-shaped `echo "waiting" || cat …/tasks/id.output` can exit 0 twice with no reminder while embedded `cat` is never classified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Restrict echo-only skip to segments with no read verb/path (or split on `||` before the echo check); add harness case for echo || cat task-output polling.


