# Review Round 2

- Mode: `diff`
- 7 accepted, 6 rejected (6 exonerated)

## Accepted Findings

### FINDING_1: Quoted-path Bash polls evade classification after `bash_strip_quoted`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-classification-output.txt
- **Severity**: important
- **Concern**: `bash_strip_quoted` removes single- and double-quoted spans before task-output matching, so repeated Bash reads like `cat "/…/tasks/<id>.output"` or paths only inside `"$VAR"` never accumulate toward threshold 2. Unquoted `cat` on the same path would warn; quoted-path polling (#3175-style) can continue silently. Harness lacks quoted-path cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Classify on original command or extract tasks/<id>.output from quotes before strip; add harness cases for quoted paths with suffixes
  - From cursor-specialist-testing-output.txt: Detect tasks/<id>.output before quote-stripping or add quoted-path harness cases and fix matching.
  - From cursor-specialist-edge-cases-output.txt: Detect using unstripped command for token extraction; limit stripping to echo/printf guards.
  - From cursor-specialist-plan-fidelity-output.txt: Match task-output tokens in the raw command string or only strip quotes for echo/printf line filtering.
  - From dyn-bash-classification-output.txt: Run token/verb matching on the unstripped line (or only strip quote spans that do not contain `tasks/…\.output`), or have `bash_is_task_output_poll` return the matched token from the same line and pass that into `handle_task_output_poll` instead of re-deriving from stripped text; add a harness case for `cat '/tmp/proj/tasks/testtask123.output'`.


### FINDING_10: Missing `session_id` collapses hooks into one `nosession` bucket
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Two Claude sessions in the same cwd can share task-output counters; one session’s reads can trigger another’s reminder or dilute counts if `session_id` is absent from PostToolUse payloads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Verify session_id is always present in production PostToolUse; else add a stronger session key and test isolation.


### FINDING_13: Doc describes per-line Bash matching vs plan full-body semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `hook-anti-read-poll.md` documents per-line matching while the plan called for full-command-string suffix-tolerant matching; readers expect full-body semantics that differ from implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update doc after classifier matches plan, or align classifier then doc.


### FINDING_2: Detection line vs counting token can disagree on multiline Bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-bash-classification-output.txt
- **Severity**: latent
- **Concern**: `bash_is_task_output_poll` can match on one stripped line while `extract_task_output_token` on the full sanitized command uses `tail -1`, so compound commands with multiple `tasks/<id>.output` paths can increment state for the wrong task id or miss the polled task.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Key state from the line that matched bash_line_is_task_output_poll
  - From dyn-bash-classification-output.txt: Have `bash_is_task_output_poll` (or `bash_line_is_task_output_poll`) emit the token from the matching line and pass only that token to `handle_task_output_poll`; add a harness with two different task ids in one multiline command.


### FINDING_3: Per-line Bash classifier misses split verb/path and plan full-body semantics
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Classification requires read verb and `tasks/<id>.output` on the same line after newline split, not suffix-tolerant full-command matching per plan. Multiline commands, backslash continuations, or `TASK=…/tasks/id.output` then `cat "$TASK"` on the next line evade the hook while prose/Read rules still apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Implement plan-style full-string matching or document and test the accepted gap explicitly
  - From cursor-specialist-edge-cases-output.txt: Normalize backslash-newline continuations or allow verb/path on adjacent lines.
  - From cursor-specialist-plan-fidelity-output.txt: Classify the full sanitized command (or full body with line-based echo/printf exclusions) for read-verb plus suffix-tolerant tasks/<id>.output; add a harness case for two-line variable indirection.


### FINDING_4: echo/printf line skip misses same-line compound poll reads
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Lines starting with `echo`/`printf` skip the whole line, so one-liners like `echo "=== … ==="; cat …/tasks/id.output` never increment the task-output counter and sustained polling via that shape gets no reminder.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Scan semicolon/&&-separated segments per line, or only skip lines that are exclusively echo/printf.


### FINDING_7: hooks.json harness does not pin matcher to anti-read-poll hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Test pin does not require `Read|Bash` matcher on the same PostToolUse entry as `hook-anti-read-poll.sh`; a stray `Read|Bash` elsewhere or `Read`-only hook block can keep the harness green while Bash PostToolUse never invokes the hardened script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pin co-location with jq or a span-based assertion on the PostToolUse block
  - From cursor-specialist-edge-cases-output.txt: Use jq to assert command and matcher co-occur in one PostToolUse block.


