### FINDING_1: code-quality: scripts/hook-anti-read-poll.sh:68-122
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] extract_task_output_token prefers absolute paths over the tasks/<id>.output tail so Read and Bash can use different state keys for the same task. An orchestrator polls via Read on /…/tasks/id.output then Bash cat tasks/id.output (or vice versa); each tool stays at count 1 and no reminder fires despite per-turn polling. Always canonicalize the state key to the tasks/<id>.output tail; add a harness case alternating Read+Bash paths for one id.
- **Suggested revision**: Address the concern above.

### FINDING_2: correctness: scripts/hook-anti-read-poll.sh:68-82,97-111
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] State key prefers absolute path when present so Read (full path) and Bash (relative tasks/id.output) do not share a counter Turn 1 Read /…/tasks/id.output then turn 2 Bash cat tasks/id.output resets count; sustained polling may never trigger the turn-2 reminder Normalize state key to canonical tasks/<id>.output tail for all branches
- **Suggested revision**: Address the concern above.

### FINDING_3: correctness: scripts/hook-anti-read-poll.sh:88-111
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Single last_token slot per cwd cannot track two task output files concurrently Alternating reads of tasks/A.output and tasks/B.output each turn keeps both counters at 1 Use per-id state lines or document single-background-task assumption
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: scripts/hook-anti-read-poll.sh:52-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] bash_has_read_verb matches read verbs anywhere in the command string including inside echo strings Two diagnostic echoes containing cat and tasks/foo.output within 600s emit a spurious reminder Tighten verb matching to compound-command boundaries or ignore quoted segments
- **Suggested revision**: Address the concern above.

### FINDING_5: correctness: scripts/hook-anti-read-poll.sh:119-121
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reminder fires only when count equals 2; later polls in the same window are silent After turn-2 warning orchestrator may poll dozens more times with no further hook output (plan-accepted) Optional: fire on count ge 2 with rate limit if stronger deterrence is needed
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] correctness: scripts/hook-anti-read-poll.sh:52-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Bash branch omits grep awk python and non-verb reads on task output Those poll shapes still bypass the hook entirely Accept for warn-only scope or extend verb/path detection later
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] architecture: hooks/hooks.json:37
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Hook runs on every Bash PostToolUse with early exit for non-matches Extra jq/grep work per Bash call; not a functional regression Acceptable tradeoff unless perf becomes an issue
- **Suggested revision**: Address the concern above.

### FINDING_8: risk-integration: hooks/hooks.json:37
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] hooks.json Read|Bash matcher is not CI-pinned alongside hook-anti-read-poll.sh registration Matcher reverted to Read-only while script Bash branch remains; production #3175 fix dead but test-hook-anti-read-poll.sh stays green Add harness grep that hooks.json entry for hook-anti-read-poll.sh uses matcher Read|Bash
- **Suggested revision**: Address the concern above.

### FINDING_9: risk-integration: scripts/test-hook-anti-read-poll.sh:147-157
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No cross-tool Read-then-Bash counter-sharing test despite plan requiring shared normalized token state Regression splitting Read/Bash state would not be caught by current harness Add Read then Bash cat on same TASK_OUT and cwd; second call should fire reminder
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/hook-anti-read-poll.sh:68-82
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Absolute vs relative task-output tokens may not share counter Alternating /tmp/proj/tasks/id.output and tasks/id.output reads could evade threshold 2 Normalize to tasks/<id>.output tail only or add mixed-path harness case
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-hook-anti-read-poll.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No task-output 600s window expiry test unlike generic Read 30s expiry case Polls spaced >600s apart reset counter silently until two reads fall within window Add task-output expiry harness case or document blind spot in hook-anti-read-poll.md
- **Suggested revision**: Address the concern above.

### FINDING_12: risk-integration: scripts/test-hook-anti-read-poll.sh:121-145
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New Bash poll cases only check additionalContext not reminder message text Wrong reminder string on Bash path would pass tests Assert Task-output poll detected or task-notification in Bash poll cases
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/relevant-checks.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Hook and AGENTS.md edits not mapped to harness in local relevant-checks Local edits may skip harness until full make lint Pre-existing; optional mapping for hook-anti-read-poll and AGENTS.md paths
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] correctness: scripts/hook-anti-read-poll.sh:52-65
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Bash classifier may match quoted cat plus tasks path without real read echo cat tasks/foo.output twice could warn incorrectly Warn-only; acceptable per plan exotic-form scope
- **Suggested revision**: Address the concern above.

### FINDING_15: **Trust boundary:** The hook is warn-only (`exit 0` everywhere, no `set -e`, PostToolUse). It parses Claude Code hook JSON via `jq` and never `eval`s or executes `tool_input.command`. That matches the intended trust model in `SECURITY.md` (plugin hooks inside the operator’s Claude Code boundary).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Trust boundary:** The hook is warn-only (`exit 0` everywhere, no `set -e`, PostToolUse). It parses Claude Code hook JSON via `jq` and never `eval`s or executes `tool_input.command`. That matches the intended trust model in `SECURITY.md` (plugin hooks inside the operator’s Claude Code boundary).
- **Suggested revision**: Address the concern above.

### FINDING_16: **Injection / prompt reflection:** Reminders are built from fixed templates plus numeric `count`/`age`; paths and command bodies are not echoed into `additionalContext`, consistent with the existing `SECURITY.md` “Read-poll reminder output” note (`SECURITY.md:123`). `emit_reminder` uses `jq --arg`, which is appropriate for embedding text in JSON.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Injection / prompt reflection:** Reminders are built from fixed templates plus numeric `count`/`age`; paths and command bodies are not echoed into `additionalContext`, consistent with the existing `SECURITY.md` “Read-poll reminder output” note (`SECURITY.md:123`). `emit_reminder` uses `jq --arg`, which is appropriate for embedding text in JSON.
- **Suggested revision**: Address the concern above.

### FINDING_17: **Command handling:** The new Bash branch classifies with `grep -E` over the full command string only; it does not pass attacker/orchestrator-controlled strings to the shell beyond `printf`/`grep` data arguments. Task-output tokens are regex-bounded (`tasks/[A-Za-z0-9._-]+\.output`); `file_path` for Read strips tabs/newlines before use.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Command handling:** The new Bash branch classifies with `grep -E` over the full command string only; it does not pass attacker/orchestrator-controlled strings to the shell beyond `printf`/`grep` data arguments. Task-output tokens are regex-bounded (`tasks/[A-Za-z0-9._-]+\.output`); `file_path` for Read strips tabs/newlines before use.
- **Suggested revision**: Address the concern above.

### FINDING_18: **State persistence:** State under `${TMPDIR:-/tmp}/larch-read-poll/` uses `chmod 700` on the directory and `chmod 600` on TSV files. Stored keys are path fragments (`tasks/<id>.output` or an absolute prefix), not full Bash commands, so widening to Bash does not add a new “secrets in state file” surface beyond what generic Read polling already stored.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **State persistence:** State under `${TMPDIR:-/tmp}/larch-read-poll/` uses `chmod 700` on the directory and `chmod 600` on TSV files. Stored keys are path fragments (`tasks/<id>.output` or an absolute prefix), not full Bash commands, so widening to Bash does not add a new “secrets in state file” surface beyond what generic Read polling already stored.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Denial of service:** Every Bash PostToolUse now runs several `grep`s over the full command (5s hook timeout). That increases hook work but remains bounded, fail-open, and non-blocking — acceptable for this mitigation tier.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Denial of service:** Every Bash PostToolUse now runs several `grep`s over the full command (5s hook timeout). That increases hook work but remains bounded, fail-open, and non-blocking — acceptable for this mitigation tier.
- **Suggested revision**: Address the concern above.

### FINDING_20: **False positives (e.g. `echo 'cat tasks/foo.output'`)** are correctness/UX, not a security elevation; the hook cannot block tools.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **False positives (e.g. `echo 'cat tasks/foo.output'`)** are correctness/UX, not a security elevation; the hook cannot block tools. Prose-only changes (`AGENTS.md`, `orchestrator-never.md`, test pins) have no runtime security impact.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/hook-anti-read-poll.sh:113,152` — State files are still written with `printf … > "$taskout_file"` / `> "$state_file"` without verifying the target is a regular file (no `O_NOFOLLOW` / non-symlink check). A same-UID attacker who can plant a symlink under `${TMPDIR}/larch-read-poll/` before the hook runs could redirect writes; this pattern predates #3195 and is only slightly more exercised now because Bash PostToolUse triggers more updates. **Suggested fix:** (if hardening is ever desired) open state files with a symlink-safe write helper, matching patterns used elsewhere in the repo (e.g. stall-recovery’s non-symlink path checks in `SECURITY.md:56`).
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

### FINDING_25: architecture: scripts/hook-anti-read-poll.sh:119-121
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Reminder fires only when count equals exactly 2. Orchestrator ignores the first warning and polls the task output dozens more times with no further hook output. Re-fire every Nth read or escalate message while keeping PostToolUse warn-only.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/hook-anti-read-poll.sh:113-114
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] State TSV updated without file locking. Concurrent PostToolUse events can lose count increments or duplicate reminders. Wrap RMW in flock or atomic mv from a temp file.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/hook-anti-read-poll.sh:178-186
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Bash branch misses non-verb read forms. Orchestrator polls via python -c open(…) or awk without cat/tail/head. Accept for this PR or extend matchers in a follow-up.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/hook-anti-read-poll.sh:48-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Bash task-output regex is substring-based. cat tasks/foo.output.bak can be treated as a task-output poll. Tighten pattern after .output for Bash branch.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] architecture: scripts/test-hook-anti-read-poll.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Harness checks mode 600 only on generic state file not state-taskout. New task-output state files might regress permissions unnoticed. Add find -perm 600 assertion for state-taskout files in harness.
- **Suggested revision**: Address the concern above.

### FINDING_30: `3c762ac1d` — design run log flush (out of feature scope)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `3c762ac1d` — design run log flush (out of feature scope)
- **Suggested revision**: Address the concern above.

### FINDING_31: `2dccee2fa` — **Close orchestrator per-turn task-output polling gap (#3195)** (feature)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `2dccee2fa` — **Close orchestrator per-turn task-output polling gap (#3195)** (feature)
- **Suggested revision**: Address the concern above.

### FINDING_32: `e70ac8e6b` — implement run log flush (out of feature scope)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `e70ac8e6b` — implement run log flush (out of feature scope) Feature work is in `2dccee2fa`; the precomputed diff covers the ten planned files. Post-#3119 scope (prose + hook only; no breadcrumb/sentinel changes) matches the plan. ### Requirement traceability | Plan requirement | Status | |------------------|--------| | `AGENTS.md` — new bullet after polling bullet, before `/review --subagent`; pinned substring `poll the task output file once per turn`; existing polling/ScheduleWakeup bullets untouched | Met — verbatim bullet at line 58 | | `skills/shared/orchestrator-never.md` — rule #3 appended; rules #1–#2 unchanged | Met | | `scripts/test-design-structure.sh` — Check-17 grep for rule #3 opening sentence | Met | | `scripts/test-design-structure.md` — sibling sentence | Met | | `scripts/test-implement-anti-polling-rule.sh` + `.md` — fourth `check` + invariant note | Met | | `hooks/hooks.json` — `matcher: "Read|Bash"` | Met | | `scripts/hook-anti-read-poll.sh` — remove Read-only gate; Read/Bash branches; end-anchored Read classifier; suffix-tolerant Bash classifier; read-verb + full-command matching; task-output mode (token key, 600s, threshold 2, separate state file); generic Read preserved; fail-open | Met | | `scripts/test-hook-anti-read-poll.sh` — all seven new cases + generic regression | Met | | `scripts/hook-anti-read-poll.md` — documented behavior + fail-open | Met | | Rejected alternatives (sentinel pre-touch, breadcrumb NEVER, competing-monitor lint, PreToolUse block) | Correctly omitted | | `skills/implement/SKILL.md` not edited | Correct per plan | Hook behavior aligns with FINDING_1 (suffix-tolerant Bash path match, not full-command `$`) and FINDING_2 (Read-only gate removed; `case Read|Bash` at lines 16–19). Harness cases cover Bash poll, multiline Bash, suffix-appended commands, wrapper-variant shared counter, slow Read task-output, offset-ignore, `cat notes.txt` false-positive guard, and generic Read regression. CI pin literals match plan prose (grep opening sentence and apostrophe-free AGENTS substring).
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

### FINDING_36: **correctness** `scripts/hook-anti-read-poll.sh:48-64,178-185` — When the orchestrator polls via `cat "$VAR"` / `cat ${TASK_OUT}` and the literal `tasks/…\.output` never appears in `tool_input.command`, both `bash_has_task_output` and `extract_task_output_token` miss the #3175 pattern entirely (the hook exits silently on the Bash branch). The harness only covers literal-path `cat $TASK_OUT` expansions in the test script, not variable-only command text. **Suggested fix:** Document as an accepted blind spot, or add a softer heuristic (e.g. warn on repeated Bash `cat`/`tail` of any `*.output` under a `tasks/` parent directory when `jq` exposes expanded paths elsewhere)—only if product wants broader coverage than literal-string matching.
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:48-64,178-185` — When the orchestrator polls via `cat "$VAR"` / `cat ${TASK_OUT}` and the literal `tasks/…\.output` never appears in `tool_input.command`, both `bash_has_task_output` and `extract_task_output_token` miss the #3175 pattern entirely (the hook exits silently on the Bash branch). The harness only covers literal-path `cat $TASK_OUT` expansions in the test script, not variable-only command text. **Suggested fix:** Document as an accepted blind spot, or add a softer heuristic (e.g. warn on repeated Bash `cat`/`tail` of any `*.output` under a `tasks/` parent directory when `jq` exposes expanded paths elsewhere)—only if product wants broader coverage than literal-string matching.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** (plan-accepted) `scripts/hook-anti-read-poll.sh:52-60` — Polling via `awk`, `python -c`, process substitution, or `sed` without `-n` is still invisible to `bash_has_read_verb`; the plan explicitly treats that as acceptable for a warn-only hook.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **code-quality** `scripts/hook-anti-read-poll.sh:43-50` — `is_read_task_output_path` is end-anchored on `file_path` while `bash_has_task_output` is intentionally substring-based; suffix-appended incident commands (`2>/dev/null`, `| head`) are covered for Bash. No wrapped-grep violation in this script context.
- **Suggested revision**: Address the concern above.

### FINDING_39: **correctness** `scripts/hook-anti-read-poll.sh:67-82,84-122` — `extract_task_output_token` prefers an absolute path when present (`/…/tasks/<id>.output`) but falls back to the relative tail (`tasks/<id>.output`). That string is stored verbatim in `state-taskout-*.tsv` and compared with `[ "$token" = "$last_token" ]`, so two polls of the same task that differ only in absolute vs relative spelling (e.g. first `cat /tmp/proj/tasks/foo.output`, later `cat tasks/foo.output`, or `Read` with a full path vs `Bash` with a relative fragment) land on **different state keys** and never reach `count -eq 2`. The sibling doc at `scripts/hook-anti-read-poll.md:14-15` says counting uses a normalized `tasks/<id>.output` token, which the implementation does not enforce. **Suggested fix:** Always normalize the state key to the captured `tasks/<id>.output` tail (regex capture group or strip through the last `/tasks/`), use that for read/write/compare in `handle_task_output_poll`, and add a harness case that alternates absolute and relative forms and expects the second poll to fire.
- **Reviewer**: dyn-state-counter-transitions-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:67-82,84-122` — `extract_task_output_token` prefers an absolute path when present (`/…/tasks/<id>.output`) but falls back to the relative tail (`tasks/<id>.output`). That string is stored verbatim in `state-taskout-*.tsv` and compared with `[ "$token" = "$last_token" ]`, so two polls of the same task that differ only in absolute vs relative spelling (e.g. first `cat /tmp/proj/tasks/foo.output`, later `cat tasks/foo.output`, or `Read` with a full path vs `Bash` with a relative fragment) land on **different state keys** and never reach `count -eq 2`. The sibling doc at `scripts/hook-anti-read-poll.md:14-15` says counting uses a normalized `tasks/<id>.output` token, which the implementation does not enforce. **Suggested fix:** Always normalize the state key to the captured `tasks/<id>.output` tail (regex capture group or strip through the last `/tasks/`), use that for read/write/compare in `handle_task_output_poll`, and add a harness case that alternates absolute and relative forms and expects the second poll to fire.
- **Suggested revision**: Address the concern above.

