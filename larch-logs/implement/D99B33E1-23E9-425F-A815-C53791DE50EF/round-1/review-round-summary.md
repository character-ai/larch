# Review Round 1

- Mode: `diff`
- 14 accepted, 16 rejected (8 exonerated)

## Accepted Findings

### FINDING_1: code-quality: scripts/hook-anti-read-poll.sh:68-122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] extract_task_output_token prefers absolute paths over the tasks/<id>.output tail so Read and Bash can use different state keys for the same task. An orchestrator polls via Read on /…/tasks/id.output then Bash cat tasks/id.output (or vice versa); each tool stays at count 1 and no reminder fires despite per-turn polling. Always canonicalize the state key to the tasks/<id>.output tail; add a harness case alternating Read+Bash paths for one id.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: scripts/hook-anti-read-poll.sh:68-82
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Absolute vs relative task-output tokens may not share counter Alternating /tmp/proj/tasks/id.output and tasks/id.output reads could evade threshold 2 Normalize to tasks/<id>.output tail only or add mixed-path harness case
- **Suggested revision**: Address the concern above.


### FINDING_11: risk-integration: scripts/test-hook-anti-read-poll.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No task-output 600s window expiry test unlike generic Read 30s expiry case Polls spaced >600s apart reset counter silently until two reads fall within window Add task-output expiry harness case or document blind spot in hook-anti-read-poll.md
- **Suggested revision**: Address the concern above.


### FINDING_2: correctness: scripts/hook-anti-read-poll.sh:68-82,97-111
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] State key prefers absolute path when present so Read (full path) and Bash (relative tasks/id.output) do not share a counter Turn 1 Read /…/tasks/id.output then turn 2 Bash cat tasks/id.output resets count; sustained polling may never trigger the turn-2 reminder Normalize state key to canonical tasks/<id>.output tail for all branches
- **Suggested revision**: Address the concern above.


### FINDING_22: architecture: scripts/hook-anti-read-poll.sh:31-33,84-121
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Task-output poll state persists in TMPDIR for 600s with no session/run scope. A finished /implement leaves count=2 for a task id; a new Claude session within 10 minutes reads that output twice for legitimate reasons and gets a false Task-output poll reminder. Key state with session/run id from hook JSON if available or canonicalize to tasks/<id>.output only; document TTL; optionally clear on SessionStart.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/hook-anti-read-poll.sh:68-82,97-111
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Token normalization splits absolute vs relative paths into different state keys. Read uses full path then Bash uses cat tasks/id.output for the same background task; each branch only counts once so threshold 2 is never reached. Canonicalize all task-output keys to tasks/<id>.output (or cwd-absolutized path) before counting; add Read+Bash harness case.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/hook-anti-read-poll.sh:52-65,183-186
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Bash classifier matches read verbs and task path substrings anywhere in the command string. echo or log lines mentioning cat …/tasks/id.output increment the counter without reading the file. Strip quoted strings before classification or require read verb and path on the same shell segment; add negative harness case.
- **Suggested revision**: Address the concern above.


### FINDING_3: correctness: scripts/hook-anti-read-poll.sh:88-111
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Single last_token slot per cwd cannot track two task output files concurrently Alternating reads of tasks/A.output and tasks/B.output each turn keeps both counters at 1 Use per-id state lines or document single-background-task assumption
- **Suggested revision**: Address the concern above.


### FINDING_33: **correctness** `scripts/hook-anti-read-poll.sh:57-58` — `bash_has_read_verb` treats any literal `-n` substring anywhere in the command as “`sed -n` read mode,” but the check is not anchored to `sed` or word boundaries. Common flags such as `find … -name`, `sort -n`, and `grep -rn` all contain `-n` immediately after `-`, so a compound command that includes `sed` for editing (not reading) plus one of those flags can satisfy the `sed` branch even when no line-oriented read is happening. That misclassifies non-polling work as a task-output poll (warn-only, but wrong signal). **Suggested fix:** Require `-n` only in the `sed` argument context, e.g. match `sed` then a bounded flag cluster like `sed` + `(-n|--quiet|-e …)` via a single ERE, or run a second pattern such as `(^|[^[:alnum:]_])sed([^[:alnum:]_]|$)[^|;&]*(\-n\b|--quiet)` instead of a global `grep -q '\-n'`.
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:57-58` — `bash_has_read_verb` treats any literal `-n` substring anywhere in the command as “`sed -n` read mode,” but the check is not anchored to `sed` or word boundaries. Common flags such as `find … -name`, `sort -n`, and `grep -rn` all contain `-n` immediately after `-`, so a compound command that includes `sed` for editing (not reading) plus one of those flags can satisfy the `sed` branch even when no line-oriented read is happening. That misclassifies non-polling work as a task-output poll (warn-only, but wrong signal). **Suggested fix:** Require `-n` only in the `sed` argument context, e.g. match `sed` then a bounded flag cluster like `sed` + `(-n|--quiet|-e …)` via a single ERE, or run a second pattern such as `(^|[^[:alnum:]_])sed([^[:alnum:]_]|$)[^|;&]*(\-n\b|--quiet)` instead of a global `grep -q '\-n'`.
- **Suggested revision**: Address the concern above.


### FINDING_34: **correctness** `scripts/hook-anti-read-poll.sh:48-64` — `bash_is_task_output_poll` ANDs `bash_has_read_verb` with `bash_has_task_output`, but `bash_has_task_output` only checks that `tasks/<id>.output` appears *anywhere* in the full multiline command string, with no requirement that the read verb’s operand is that path. A body like `OUT=tasks/foo.output` on one line and `cat notes.txt` on another (or a comment containing `tasks/foo.output` above an unrelated `cat`) still matches both predicates, so the hook can warn on non-polling Bash even though the read verb never targets the task file. **Suggested fix:** Tie path detection to the read verb (e.g. extract the operand after the matched `cat`/`tail`/… token, or require `tasks/…\.output` within a bounded window after the read verb), or require the normalized token from `extract_task_output_token` to appear in the same “command segment” as the read verb before counting.
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:48-64` — `bash_is_task_output_poll` ANDs `bash_has_read_verb` with `bash_has_task_output`, but `bash_has_task_output` only checks that `tasks/<id>.output` appears *anywhere* in the full multiline command string, with no requirement that the read verb’s operand is that path. A body like `OUT=tasks/foo.output` on one line and `cat notes.txt` on another (or a comment containing `tasks/foo.output` above an unrelated `cat`) still matches both predicates, so the hook can warn on non-polling Bash even though the read verb never targets the task file. **Suggested fix:** Tie path detection to the read verb (e.g. extract the operand after the matched `cat`/`tail`/… token, or require `tasks/…\.output` within a bounded window after the read verb), or require the normalized token from `extract_task_output_token` to appear in the same “command segment” as the read verb before counting.
- **Suggested revision**: Address the concern above.


### FINDING_35: **correctness** `scripts/hook-anti-read-poll.sh:71-76` — `extract_task_output_token`’s absolute-path `grep -oE` starts at the *first* `/` and uses `[^[:space:]"';|&()]*` up to `tasks/…`, so for a relative Read path such as `foo/bar/tasks/id.output` it normalizes to `/bar/tasks/id.output`, dropping the `foo/` prefix. A later Bash poll with the fully expanded absolute path (`/tmp/…/foo/bar/tasks/id.output`) produces a different state key, so the 600s / threshold-2 counter does not accumulate across the Read↔Bash shapes the plan says must share one normalized token—real per-turn polling can evade the reminder until each form hits threshold separately. **Suggested fix:** Prefer the longest (or rightmost) `tasks/<id>.output` match, include the full prefix back to the previous path separator without stopping at the first `/`, or normalize only to the stable `tasks/<id>.output` tail for *all* branches (Read and Bash) when the plan allows that weaker key.
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:71-76` — `extract_task_output_token`’s absolute-path `grep -oE` starts at the *first* `/` and uses `[^[:space:]"';|&()]*` up to `tasks/…`, so for a relative Read path such as `foo/bar/tasks/id.output` it normalizes to `/bar/tasks/id.output`, dropping the `foo/` prefix. A later Bash poll with the fully expanded absolute path (`/tmp/…/foo/bar/tasks/id.output`) produces a different state key, so the 600s / threshold-2 counter does not accumulate across the Read↔Bash shapes the plan says must share one normalized token—real per-turn polling can evade the reminder until each form hits threshold separately. **Suggested fix:** Prefer the longest (or rightmost) `tasks/<id>.output` match, include the full prefix back to the previous path separator without stopping at the first `/`, or normalize only to the stable `tasks/<id>.output` tail for *all* branches (Read and Bash) when the plan allows that weaker key.
- **Suggested revision**: Address the concern above.


### FINDING_39: **correctness** `scripts/hook-anti-read-poll.sh:67-82,84-122` — `extract_task_output_token` prefers an absolute path when present (`/…/tasks/<id>.output`) but falls back to the relative tail (`tasks/<id>.output`). That string is stored verbatim in `state-taskout-*.tsv` and compared with `[ "$token" = "$last_token" ]`, so two polls of the same task that differ only in absolute vs relative spelling (e.g. first `cat /tmp/proj/tasks/foo.output`, later `cat tasks/foo.output`, or `Read` with a full path vs `Bash` with a relative fragment) land on **different state keys** and never reach `count -eq 2`. The sibling doc at `scripts/hook-anti-read-poll.md:14-15` says counting uses a normalized `tasks/<id>.output` token, which the implementation does not enforce. **Suggested fix:** Always normalize the state key to the captured `tasks/<id>.output` tail (regex capture group or strip through the last `/tasks/`), use that for read/write/compare in `handle_task_output_poll`, and add a harness case that alternates absolute and relative forms and expects the second poll to fire.
- **Reviewer**: dyn-state-counter-transitions-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:67-82,84-122` — `extract_task_output_token` prefers an absolute path when present (`/…/tasks/<id>.output`) but falls back to the relative tail (`tasks/<id>.output`). That string is stored verbatim in `state-taskout-*.tsv` and compared with `[ "$token" = "$last_token" ]`, so two polls of the same task that differ only in absolute vs relative spelling (e.g. first `cat /tmp/proj/tasks/foo.output`, later `cat tasks/foo.output`, or `Read` with a full path vs `Bash` with a relative fragment) land on **different state keys** and never reach `count -eq 2`. The sibling doc at `scripts/hook-anti-read-poll.md:14-15` says counting uses a normalized `tasks/<id>.output` token, which the implementation does not enforce. **Suggested fix:** Always normalize the state key to the captured `tasks/<id>.output` tail (regex capture group or strip through the last `/tasks/`), use that for read/write/compare in `handle_task_output_poll`, and add a harness case that alternates absolute and relative forms and expects the second poll to fire.
- **Suggested revision**: Address the concern above.


### FINDING_8: risk-integration: hooks/hooks.json:37
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] hooks.json Read|Bash matcher is not CI-pinned alongside hook-anti-read-poll.sh registration Matcher reverted to Read-only while script Bash branch remains; production #3175 fix dead but test-hook-anti-read-poll.sh stays green Add harness grep that hooks.json entry for hook-anti-read-poll.sh uses matcher Read|Bash
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: scripts/test-hook-anti-read-poll.sh:147-157
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No cross-tool Read-then-Bash counter-sharing test despite plan requiring shared normalized token state Regression splitting Read/Bash state would not be caught by current harness Add Read then Bash cat on same TASK_OUT and cwd; second call should fire reminder
- **Suggested revision**: Address the concern above.


