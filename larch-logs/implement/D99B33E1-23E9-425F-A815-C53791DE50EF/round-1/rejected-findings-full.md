### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/test-hook-anti-read-poll.sh:121-145
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] New Bash poll cases only check additionalContext not reminder message text Wrong reminder string on Bash path would pass tests Assert Task-output poll detected or task-notification in Bash poll cases
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Trust boundary:** The hook is warn-only (`exit 0` everywhere, no `set -e`, PostToolUse). It parses Claude Code hook JSON via `jq` and never `eval`s or executes `tool_input.command`. That matches the intended trust model in `SECURITY.md` (plugin hooks inside the operator’s Claude Code boundary).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Trust boundary:** The hook is warn-only (`exit 0` everywhere, no `set -e`, PostToolUse). It parses Claude Code hook JSON via `jq` and never `eval`s or executes `tool_input.command`. That matches the intended trust model in `SECURITY.md` (plugin hooks inside the operator’s Claude Code boundary).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **Command handling:** The new Bash branch classifies with `grep -E` over the full command string only; it does not pass attacker/orchestrator-controlled strings to the shell beyond `printf`/`grep` data arguments. Task-output tokens are regex-bounded (`tasks/[A-Za-z0-9._-]+\.output`); `file_path` for Read strips tabs/newlines before use.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Command handling:** The new Bash branch classifies with `grep -E` over the full command string only; it does not pass attacker/orchestrator-controlled strings to the shell beyond `printf`/`grep` data arguments. Task-output tokens are regex-bounded (`tasks/[A-Za-z0-9._-]+\.output`); `file_path` for Read strips tabs/newlines before use.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **State persistence:** State under `${TMPDIR:-/tmp}/larch-read-poll/` uses `chmod 700` on the directory and `chmod 600` on TSV files. Stored keys are path fragments (`tasks/<id>.output` or an absolute prefix), not full Bash commands, so widening to Bash does not add a new “secrets in state file” surface beyond what generic Read polling already stored.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **State persistence:** State under `${TMPDIR:-/tmp}/larch-read-poll/` uses `chmod 700` on the directory and `chmod 600` on TSV files. Stored keys are path fragments (`tasks/<id>.output` or an absolute prefix), not full Bash commands, so widening to Bash does not add a new “secrets in state file” surface beyond what generic Read polling already stored.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Denial of service:** Every Bash PostToolUse now runs several `grep`s over the full command (5s hook timeout). That increases hook work but remains bounded, fail-open, and non-blocking — acceptable for this mitigation tier.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Denial of service:** Every Bash PostToolUse now runs several `grep`s over the full command (5s hook timeout). That increases hook work but remains bounded, fail-open, and non-blocking — acceptable for this mitigation tier.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: **False positives (e.g. `echo 'cat tasks/foo.output'`)** are correctness/UX, not a security elevation; the hook cannot block tools.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **False positives (e.g. `echo 'cat tasks/foo.output'`)** are correctness/UX, not a security elevation; the hook cannot block tools. Prose-only changes (`AGENTS.md`, `orchestrator-never.md`, test pins) have no runtime security impact.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: architecture: scripts/hook-anti-read-poll.sh:119-121
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Reminder fires only when count equals exactly 2. Orchestrator ignores the first warning and polls the task output dozens more times with no further hook output. Re-fire every Nth read or escalate message while keeping PostToolUse warn-only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: correctness: scripts/hook-anti-read-poll.sh:113-114
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] State TSV updated without file locking. Concurrent PostToolUse events can lose count increments or duplicate reminders. Wrap RMW in flock or atomic mv from a temp file.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: risk-integration: scripts/hook-anti-read-poll.sh:178-186
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Bash branch misses non-verb read forms. Orchestrator polls via python -c open(…) or awk without cat/tail/head. Accept for this PR or extend matchers in a follow-up.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: correctness: scripts/hook-anti-read-poll.sh:48-50
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Bash task-output regex is substring-based. cat tasks/foo.output.bak can be treated as a task-output poll. Tighten pattern after .output for Bash branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_30: `3c762ac1d` — design run log flush (out of feature scope)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `3c762ac1d` — design run log flush (out of feature scope)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_31: `2dccee2fa` — **Close orchestrator per-turn task-output polling gap (#3195)** (feature)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `2dccee2fa` — **Close orchestrator per-turn task-output polling gap (#3195)** (feature)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_32: `e70ac8e6b` — implement run log flush (out of feature scope)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - `e70ac8e6b` — implement run log flush (out of feature scope) Feature work is in `2dccee2fa`; the precomputed diff covers the ten planned files. Post-#3119 scope (prose + hook only; no breadcrumb/sentinel changes) matches the plan. ### Requirement traceability | Plan requirement | Status | |------------------|--------| | `AGENTS.md` — new bullet after polling bullet, before `/review --subagent`; pinned substring `poll the task output file once per turn`; existing polling/ScheduleWakeup bullets untouched | Met — verbatim bullet at line 58 | | `skills/shared/orchestrator-never.md` — rule #3 appended; rules #1–#2 unchanged | Met | | `scripts/test-design-structure.sh` — Check-17 grep for rule #3 opening sentence | Met | | `scripts/test-design-structure.md` — sibling sentence | Met | | `scripts/test-implement-anti-polling-rule.sh` + `.md` — fourth `check` + invariant note | Met | | `hooks/hooks.json` — `matcher: "Read|Bash"` | Met | | `scripts/hook-anti-read-poll.sh` — remove Read-only gate; Read/Bash branches; end-anchored Read classifier; suffix-tolerant Bash classifier; read-verb + full-command matching; task-output mode (token key, 600s, threshold 2, separate state file); generic Read preserved; fail-open | Met | | `scripts/test-hook-anti-read-poll.sh` — all seven new cases + generic regression | Met | | `scripts/hook-anti-read-poll.md` — documented behavior + fail-open | Met | | Rejected alternatives (sentinel pre-touch, breadcrumb NEVER, competing-monitor lint, PreToolUse block) | Correctly omitted | | `skills/implement/SKILL.md` not edited | Correct per plan | Hook behavior aligns with FINDING_1 (suffix-tolerant Bash path match, not full-command `$`) and FINDING_2 (Read-only gate removed; `case Read|Bash` at lines 16–19). Harness cases cover Bash poll, multiline Bash, suffix-appended commands, wrapper-variant shared counter, slow Read task-output, offset-ignore, `cat notes.txt` false-positive guard, and generic Read regression. CI pin literals match plan prose (grep opening sentence and apostrophe-free AGENTS substring).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: **correctness** `scripts/hook-anti-read-poll.sh:48-64,178-185` — When the orchestrator polls via `cat "$VAR"` / `cat ${TASK_OUT}` and the literal `tasks/…\.output` never appears in `tool_input.command`, both `bash_has_task_output` and `extract_task_output_token` miss the #3175 pattern entirely (the hook exits silently on the Bash branch). The harness only covers literal-path `cat $TASK_OUT` expansions in the test script, not variable-only command text. **Suggested fix:** Document as an accepted blind spot, or add a softer heuristic (e.g. warn on repeated Bash `cat`/`tail` of any `*.output` under a `tasks/` parent directory when `jq` exposes expanded paths elsewhere)—only if product wants broader coverage than literal-string matching.
- **Reviewer**: dyn-bash-regex-classifiers-output.txt
- **Concern**: - **correctness** `scripts/hook-anti-read-poll.sh:48-64,178-185` — When the orchestrator polls via `cat "$VAR"` / `cat ${TASK_OUT}` and the literal `tasks/…\.output` never appears in `tool_input.command`, both `bash_has_task_output` and `extract_task_output_token` miss the #3175 pattern entirely (the hook exits silently on the Bash branch). The harness only covers literal-path `cat $TASK_OUT` expansions in the test script, not variable-only command text. **Suggested fix:** Document as an accepted blind spot, or add a softer heuristic (e.g. warn on repeated Bash `cat`/`tail` of any `*.output` under a `tasks/` parent directory when `jq` exposes expanded paths elsewhere)—only if product wants broader coverage than literal-string matching.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: correctness: scripts/hook-anti-read-poll.sh:52-65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] bash_has_read_verb matches read verbs anywhere in the command string including inside echo strings Two diagnostic echoes containing cat and tasks/foo.output within 600s emit a spurious reminder Tighten verb matching to compound-command boundaries or ignore quoted segments
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: correctness: scripts/hook-anti-read-poll.sh:119-121
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Reminder fires only when count equals 2; later polls in the same window are silent After turn-2 warning orchestrator may poll dozens more times with no further hook output (plan-accepted) Optional: fire on count ge 2 with rate limit if stronger deterrence is needed
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

