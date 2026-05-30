Normalizing the supplied reviewer findings into merged blocks with stable IDs, severity merge rules, and separate OOS entries.


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

### FINDING_5: System-reminder fires only when count equals 2
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: After turn 2, further per-turn polls in the same 600s window get no additional system-reminder because the hook only emits when count equals 2.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Fire on count ge threshold with cooldown, or document one-shot nudge per window in hook-anti-read-poll.md

### FINDING_6: 600s window may warn on legitimate second post-completion read
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Orchestrator may read task output once after notification and again within 10 minutes for debugging; hook still emits reminder on the second read.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document as expected warn-only noise or raise threshold / add reset signal.

### FINDING_7: hooks.json harness does not pin matcher to anti-read-poll hook
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Test pin does not require `Read|Bash` matcher on the same PostToolUse entry as `hook-anti-read-poll.sh`; a stray `Read|Bash` elsewhere or `Read`-only hook block can keep the harness green while Bash PostToolUse never invokes the hardened script.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Pin co-location with jq or a span-based assertion on the PostToolUse block
  - From cursor-specialist-edge-cases-output.txt: Use jq to assert command and matcher co-occur in one PostToolUse block.

### FINDING_8: Duplicated windowed counter logic in two handlers
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `handle_task_output_poll` and `handle_generic_read_poll` duplicate bump/window logic; threshold or window tweaks in one handler may diverge warn behavior between task-output and generic Read paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract a shared bump-and-maybe-emit helper; keep only classifiers in each handler

### FINDING_9: No cheap prefilter before full Bash command parsing
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Every Bash tool use pays quote-strip/line-grep cost during heavy `/implement` runs even when the command cannot reference task output paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add early exit when command lacks tasks/ or .output before bash_is_task_output_poll

### FINDING_10: Missing `session_id` collapses hooks into one `nosession` bucket
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Two Claude sessions in the same cwd can share task-output counters; one session’s reads can trigger another’s reminder or dilute counts if `session_id` is absent from PostToolUse payloads.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Verify session_id is always present in production PostToolUse; else add a stronger session key and test isolation.

### FINDING_11: Non-atomic read-modify-write on task-output state files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parallel PostToolUse can lose increments; threshold-2 reminder may not fire during fast per-turn polling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use flock or atomic append-per-event counting; optional parallel harness.

### FINDING_12: Harness omits multiline incident-shaped Bash fixtures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: No archived multiline echo-then-cat layout from implement transcripts; regression could re-break that shape without CI failure while single-line cases pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add multiline fixture mirroring larch-logs implement transcripts.

### FINDING_13: Doc describes per-line Bash matching vs plan full-body semantics
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `hook-anti-read-poll.md` documents per-line matching while the plan called for full-command-string suffix-tolerant matching; readers expect full-body semantics that differ from implementation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Update doc after classifier matches plan, or align classifier then doc.

### OOS_1: [OUT_OF_SCOPE] Portable `sed` read-verb detection uses `\b` in grep ERE
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `sed -n` detection uses `\b`; portable `sed`-as-read-verb behavior may vary by platform `grep`; does not affect primary `cat` path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Replace \b with explicit character-class anchors like cat/tail matchers

### OOS_2: [OUT_OF_SCOPE] Task-output state files accumulate without deletion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Pre-existing generic-state pattern; long runs leave stale `state-taskout-*` files under `larch-read-poll` until tmp cleanup.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Optional periodic prune or reuse single keyed TSV per cwd
  - From cursor-specialist-edge-cases-output.txt: Unlink on window expiry or cap files per session_hash+cwd_hash.

### OOS_3: [OUT_OF_SCOPE] `jq` absence disables all hook warnings
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing: no `jq` on PATH makes Read|Bash anti-poll a no-op for every session.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document in installation prerequisites; already noted for other hooks.

### OOS_4: [OUT_OF_SCOPE] PostToolUse concurrency documented for audit log only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: General platform concern that parallel hooks can interleave; state-file hooks inherit the class; not introduced solely by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] `session_id` hashing for task-output state was not in plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Round-1 addition; if hook events lack `session_id`, unrelated sessions share `nosession` counters. Out of scope for #3195 plan; verify production payloads if needed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Affirmation — token/verb short-circuit chain is correct
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: `extract_task_output_token` / `bash_line_is_task_output_poll` return chain correctly short-circuits on missing token before verb checks; exit status follows `bash_has_read_verb`. No change requested.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_7: [OUT_OF_SCOPE] Affirmation — `sed -n` per-line branch is reasonable
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: `[^|;&]*` before `\-n\b|--quiet` avoids false read-verb on later pipeline segments; harness `sed -i.bak …; grep -rn` decoy stays silent. No change requested.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_8: [OUT_OF_SCOPE] Affirmation — task ID charset matches transcripts
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: Real task IDs match `[A-Za-z0-9._-]+`; classifier limit is consistent with plan and #3175 shapes. No change requested.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_9: [OUT_OF_SCOPE] Affirmation — incident logs mostly unquoted same-line paths; gaps documented
- **Reviewer(s)**: dyn-bash-classification-output.txt
- **Severity**: nit
- **Concern**: #3175-style Bash bodies in `larch-logs` overwhelmingly use unquoted absolute `cat`/`tail` on same line; quoted/variable-only paths remain documented warn-only gaps in `hook-anti-read-poll.md` and plan “Hook false negatives”. No change requested beyond in-scope quoted-path fixes.
- **Suggested revisions (informational for voters; coder decides)**:
