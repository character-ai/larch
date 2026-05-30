### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	AGENTS.md:61-62 / skills/shared/orchestrator-never.md:8-9	Proposed prose tells orchestrators to end the turn and wait on `<task-notification>` for every backgrounded task, with no carve-out for same-Bash-message blocking still required today	Until #3119 lands, Family B flows still require `run_in_background` plus a foreground blocking call in the same Bash message (`AGENTS.md:57-58`, `skills/implement/SKILL.md:66`, `BASH_AUTHORING.md:81`). An implementer can read the new unconditional “end the turn” / “every backgrounded task” lines as permission to background long scripts and exit the turn immediately—reintroducing the #2454-class turn-boundary break the adjacent bullets exist to prevent	Mirror `AGENTS.md:57`’s structure: ban per-turn output polling, but qualify completion with “unless the skill keeps a blocking Bash invocation open until the script finishes; otherwise end the turn for `<task-notification>`.” Use the same qualification in orchestrator-never rule #3—no breadcrumb tokens needed

1. **[correctness]** `AGENTS.md` (proposed bullet after line 61) / `skills/shared/orchestrator-never.md` (proposed rule #3): The verbatim additions tell the orchestrator to “end the turn” and rely on `<task-notification>` for “every” / “any” backgrounded task. That conflicts with the still-active Family B contract at `AGENTS.md:57-58`, `skills/implement/SKILL.md:66`, and `BASH_AUTHORING.md:81`, which require staying in the launching Bash message with a foreground blocking wait until the long script finishes. **Suggested revision:** Keep the per-turn-read ban, but add a machinery-independent exception such as “unless the skill keeps a blocking Bash invocation open until the script completes; otherwise end the turn for `<task-notification>`,” in both prose sites.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-harness-grep-fidelity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-harness-grep-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-grep-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-harness-grep-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-harness-grep-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-agents-md-pin-gap-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-agents-md-pin-gap-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-agents-md-pin-gap-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-agents-md-pin-gap-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-implement-anti-polling-rule.sh:57-60	Proposed third `check` uses single quotes around a literal containing `task's`	In bash, `'do not poll the task's output file once per turn'` terminates the quoted string at `task's`, so the harness fails to parse or never runs the intended grep	Use double quotes for the literal (mirror `scripts/test-design-structure.sh:323`), e.g. `"do not poll the task's output file once per turn"`

**1. correctness** — `scripts/test-implement-anti-polling-rule.sh` (proposed insertion after line 48): The verbatim `check` uses `'do not poll the task's output file once per turn'`. The apostrophe in `task's` ends the single-quoted string early, so the script is a syntax error or runs the wrong grep. **Suggested revision:** Use double quotes for that literal, matching the existing sub-skill pin in `scripts/test-design-structure.sh:323`.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-implement-anti-polling-rule.sh:57-60	Planned fourth `check` wraps the grep literal in single quotes while the substring contains `task's`	The apostrophe in `task's` terminates the single-quoted word in bash, so the script fails `bash -n`/parse or greps the wrong fragment; the new pin never guards AGENTS.md	Use the same quoting pattern as the existing Monitor check: double-quote the literal, e.g. `"do not poll the task's output file once per turn"` (still byte-identical to the AGENTS.md phrase)

**1. [correctness] `scripts/test-implement-anti-polling-rule.sh` (planned ~lines 57–60)** — The verbatim harness addition uses `'do not poll the task's output file once per turn'`. In bash, the `'` before `s` ends the quoted string, so the script is not syntactically valid (or does not grep the intended phrase). The file already handles `Don't` with double quotes on line 42. **Suggested revision:** pass the third `check` argument as `"do not poll the task's output file once per turn"` so it stays byte-identical to the new `AGENTS.md` bullet while parsing correctly.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-implement-anti-polling-rule.sh:58-60	Planned `check` literal uses single quotes around a string containing `task's`	The apostrophe in `task's` terminates the single-quoted word early; bash fails to parse the script (or the literal is wrong) before any assertion runs	Use a double-quoted third argument, mirroring the apostrophe-safe pattern already used in `scripts/test-design-structure.sh` Check 17 (`grep -Fq "NEVER treat a sub-skill's terminal output..."`)

**1. [correctness]** `scripts/test-implement-anti-polling-rule.sh:58-60` — The verbatim harness addition wraps `do not poll the task's output file once per turn` in single quotes. The possessive apostrophe ends the single-quoted span after `task`, so the script will not parse. The AGENTS.md bullet correctly needs that substring (it contains `task's`), and the sibling harness already solves the same problem with double quotes in Check 17 of `scripts/test-design-structure.sh` (line 323). Use `"do not poll the task's output file once per turn"` as the third `check` argument.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-implement-anti-polling-rule.sh:58-60	Verbatim `check` third argument uses single quotes around a literal containing `task's`	ASCII `'` inside `'do not poll the task's output file once per turn'` terminates the single-quoted string at `task`, so Bash fails to parse the script before any assertion runs; CI/`make test-implement-anti-polling-rule` stays red and the #1011 `/implement` pin never executes	Use a double-quoted literal for the third `check` argument (same pattern as `scripts/test-design-structure.sh:323` for `sub-skill's`), e.g. `"do not poll the task's output file once per turn"`, and keep it byte-identical to the new `AGENTS.md` bullet phrase

1. **correctness** — `scripts/test-implement-anti-polling-rule.sh:58-60` — The proposed fourth `check` wraps `do not poll the task's output file once per turn` in single quotes; the apostrophe in `task's` ends the quoted string early and breaks script parsing. **Suggested revision:** pass that substring as a double-quoted third argument, matching the existing apostrophe-bearing pin in `scripts/test-design-structure.sh:323`.

Everything else in the plan lines up with issue #3195 Part 2 (name the per-turn output-file read shape, bind to `<task-notification>`, drop Fix A/C, zero breadcrumb tokens, dual harness after FINDING_2, and the listed test commands). FINDING_2’s `/implement` delivery pin is covered; the transitional Family-B carve-out from rejected FINDING_1 is intentionally out of scope for this minimum-change lane.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-grep-literal-sync-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-grep-literal-sync-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-implement-anti-polling-rule.sh:58-61	Proposed `check` third argument uses single quotes around a literal containing ASCII apostrophe in `task's`	With U+0027 in `task's`, the opening `'` after `task` terminates the single-quoted string; the script fails bash parse (or never passes the intended substring to `grep -qF`), so the AGENTS pin does not run as designed	Use double quotes for the literal, matching `scripts/test-design-structure.sh:323` (`grep -Fq "NEVER treat a sub-skill's terminal output..."`)

1. **[correctness]** `scripts/test-implement-anti-polling-rule.sh:58-61` (proposed) — The verbatim `check` uses `'do not poll the task's output file once per turn'`. Plan prose at `plan.txt:23` and the pin substring both use ASCII `'` (U+0027) in `task's` (not U+2019). That byte inside a single-quoted shell argument ends the quoted span at `task`, so the third argument is not the intended grep needle. **Revision:** Use `"do not poll the task's output file once per turn"` (same bytes as the `AGENTS.md` bullet at `plan.txt:23`).

**Exonerated (grep-literal sync):**

- **orchestrator-never.md / `test-design-structure.sh`:** Proposed grep `NEVER poll a background task by reading its output file once per turn` (`plan.txt:43`) is byte-identical to the core of rule #3’s opening (`plan.txt:33`); `-Fq` substring match is consistent with Check 17’s existing sub-skill pin at `scripts/test-design-structure.sh:323-324`.
- **Curly apostrophe:** Plan instances of `task's` at lines 5, 23, 33, 60, and 65 all match `task\x27s`; no smart-apostrophe drift vs the AGENTS pin phrase.
- **HTML entities:** `<task-notification>` appears only in prose (`plan.txt:23`, `33`); neither harness grep literal includes angle brackets, so `&lt;`/`&gt;` issue-body rendering does not affect the proposed pins.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-grep-literal-sync-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-grep-literal-sync-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-scope-compat-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-scope-compat-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/test-implement-anti-polling-rule.sh:58-60	Verbatim fourth check uses single quotes around a literal containing ASCII apostrophe in task's	Bash parses 'do not poll the task' as one quoted word; the remainder is a syntax error so the script fails at source or the assertion never runs; FINDING_2 pin is a false guard	Use double quotes for the third check argument (mirror Check 17 in test-design-structure.sh:323) or another apostrophe-safe quoting form while keeping byte identity with AGENTS.md

**1. [correctness]** `scripts/test-implement-anti-polling-rule.sh` (proposed lines 58–60): The planned `check` call uses `'do not poll the task's output file once per turn'`. The apostrophe in `task's` terminates the single-quoted string early (same pattern already avoided in `test-design-structure.sh:323`, which uses double quotes for `sub-skill's`). **Suggested revision:** use `"do not poll the task's output file once per turn"` for the literal argument.

**Scope-compat checks (no additional in-scope findings):**

- **Breadcrumb-token scan:** All verbatim prose/harness insertions (AGENTS bullet, `orchestrator-never.md` rule #3, both grep pins) contain none of: `breadcrumb-monitor.sh`, `LARCH_DONE_SENTINEL`, `LARCH_BREADCRUMB`, `LARCH_STATUS_FILE`, `LARCH_PAIRED_PID_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, `BASH_AUTHORING.md` §4, or `Family B`.
- **#3119 file overlap:** `AGENTS.md` is in Stage 4 scope (breadcrumb trims at `AGENTS.md:57-58`); `orchestrator-never.md` has no breadcrumb machinery today; `test-design-structure.sh` / `test-implement-anti-polling-rule.sh` are audited in the Stage 3/4 rip-out but the proposed hunks are additive pins away from breadcrumb harness blocks. Insertion is after `AGENTS.md:61` (ScheduleWakeup), not inside `57-58` deletion targets — line-adjacency conflict with #3119 is unlikely; same-file merge is ordinary, not structurally conflict-prone.
- **Anchors verified:** ScheduleWakeup bullet at `AGENTS.md:61`; `orchestrator-never.md` ends at rule 2 (`:7-8`) for append-as-#3; `test-design-structure.sh:323-324` sub-skill `grep` pair with insertion before `:325`; `test-implement-anti-polling-rule.sh:46-48` three existing `check` calls with insertion after the `sleep` check.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-scope-compat-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-scope-compat-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	risk-integration	hooks/hooks.json:36-45; scripts/hook-anti-read-poll.sh:13-14	PostToolUse registration is Read-only but the plan’s primary mechanical fix is a new Bash branch	The #3175 incident polled via Bash `cat` of `…/tasks/<id>.output`. `hooks/hooks.json` only registers `hook-anti-read-poll.sh` under `matcher: "Read"`, so Claude Code never invokes the hook after Bash tool use. Script-only hardening plus `test-hook-anti-read-poll.sh` (stdin injection) can pass while production still never warns on the incident shape.	Add `hooks/hooks.json` to the change set: widen the matcher to `Read|Bash` (or add a second PostToolUse entry with `matcher: "Bash"` pointing at the same script). Update `scripts/hook-anti-read-poll.md` registration prose accordingly. Keep the harness cases; optionally assert the matcher in a small pin test so registration cannot drift again.

**1. risk-integration — `hooks/hooks.json` omits Bash from the PostToolUse matcher (important)**

The plan’s mechanical layer centers on extending `scripts/hook-anti-read-poll.sh` with a `Bash` branch for `cat`/`tail`/… of `…/tasks/<id>.output` paths (plan lines 80–82). Shipped registration is Read-only:

```36:44:hooks/hooks.json
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/hook-anti-read-poll.sh",
            "timeout": 5
          }
        ]
      }
```

The hook script itself exits immediately unless `tool_name == "Read"` today (`scripts/hook-anti-read-poll.sh:13-14`). Even after the planned refactor, **the host will not call the hook on Bash completions** unless `hooks.json` is updated. That leaves the stated “primary #3175 fix” inactive in real sessions while offline tests (piping JSON into the script) still pass.

**Suggested revision:** Add `### UPDATED: hooks/hooks.json`** with `matcher: "Read|Bash"` (same pattern as `Edit|Write|NotebookEdit` elsewhere). Bump the file count in the diff estimate. No other material gaps found for SIMPLE-tier scope: prose/harness layering is consistent, task-output path regex matches observed harness paths (`…/tasks/<id>.output`), dual pins (`test-design-structure.sh` + `test-implement-anti-polling-rule.sh`) close the AGENTS vs orchestrator-never split, and #3119/#3120 avoidance (no breadcrumb tokens, hook outside their edit set) is sound.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	hooks/hooks.json:36-45; plan.txt:72-88	Bash branch in hook script is not registered for PostToolUse	The plan’s primary mechanical fix targets #3175’s Bash `cat`/`tail` of `…/tasks/<id>.output`, but `hooks/hooks.json` only invokes `hook-anti-read-poll.sh` on `matcher: "Read"`. Claude Code never runs the hook after Bash tool use; `test-hook-anti-read-poll.sh` pipes JSON directly into the script and can pass while production never warns on the incident shape.	Add `### UPDATED: hooks/hooks.json` to the file list: widen the existing matcher to `Read|Bash` (same pattern as `startup|resume|clear|compact` on SessionStart) or add a parallel PostToolUse entry with `matcher: "Bash"`. Update `scripts/hook-anti-read-poll.md` registration prose and the testing strategy; optionally pin the matcher in a harness grep so registration cannot drift.

**1. [correctness]** `hooks/hooks.json:36-45` — The plan hardens `scripts/hook-anti-read-poll.sh` with a **Bash** branch for read commands against `…/tasks/<id>.output` (the #3175 shape), but shipped registration only wires the hook on **Read**:

```36:44:hooks/hooks.json
      {
        "matcher": "Read",
        "hooks": [
          {
            "type": "command",
            "command": "${CLAUDE_PLUGIN_ROOT}/scripts/hook-anti-read-poll.sh",
            "timeout": 5
          }
        ]
      }
```

Script-only changes plus offline harness cases cannot deliver the stated “primary #3175 fix” until `hooks.json` includes Bash in the matcher (minimal change: `Read|Bash` on the existing entry, following the pipe-union style already used for SessionStart).

**Suggested revision:** Add `hooks/hooks.json` to `### Files to modify/create`, bump the file count, and document the matcher in `hook-anti-read-poll.md` / testing strategy.

**Exonerated (SIMPLE / minimum-change):** Prose duplication (`AGENTS.md` + `orchestrator-never.md` rule #3) is intentional defense-in-depth; the planned `check` literal is apostrophe-free (`task output file`, per plan lines 23 and 65), so the `test-implement-anti-polling-rule.sh` pin is valid shell; task-output regex matches observed harness paths; warn-only scope and rejected blocking PreToolUse alternative match the tier.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	hooks/hooks.json:36-45; plan.txt:72-88	Primary #3175 Bash-path hook hardening is not wired in shipped hooks.json	PostToolUse only registers hook-anti-read-poll.sh under matcher Read, so production never invokes the hook on Bash cat/tail/head of tasks/*.output; offline test-hook-anti-read-poll.sh pipes JSON directly and will pass while the incident shape stays unwarned in real sessions	Add ### UPDATED hooks/hooks.json with a second PostToolUse entry (matcher Bash, same command/timeout as Read); update hook-anti-read-poll.md registration line; extend testing strategy to note hooks.json is part of the delivery surface

1. **correctness** — `hooks/hooks.json:36-45` (plan `### UPDATED: scripts/hook-anti-read-poll.sh` only): The plan’s mechanical layer centers on a **Bash** branch for `cat`/`tail`/… of `…/tasks/<id>.output` (#3175), but shipped registration still invokes `hook-anti-read-poll.sh` only on **Read** PostToolUse. Bash poll-reads never reach the hook at runtime; `test-hook-anti-read-poll.sh` exercises the script in isolation and will not catch the gap. **Suggested revision:** Add `hooks/hooks.json` to the file list with a parallel `matcher: "Bash"` PostToolUse entry (same command as Read), document it in `hook-anti-read-poll.md`, and treat hooks.json as part of the validation surface in the testing strategy.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-migration-compat-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-migration-compat-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-migration-compat-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-migration-compat-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-migration-compat-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-migration-compat-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-migration-compat-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-migration-compat-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-migration-compat-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-migration-compat-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-ci-pin-integrity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-ci-pin-integrity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-ci-pin-integrity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-ci-pin-integrity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-ci-pin-integrity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-ci-pin-integrity-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-ci-pin-integrity-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-ci-pin-integrity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-ci-pin-integrity-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-ci-pin-integrity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/hook-anti-read-poll.sh:75-87 (planned Bash branch)	Bash matcher underspecified for multiline/compound commands	Plan says detect a read when the command is cat/tail/head/… whose argument matches the classifier; #3175 polling often used multiline Bash with leading assignments and embedded `cat …/tasks/<id>.output` (not cat as argv[0]). A literal argv-only matcher passes the planned single-line harness but misses the incident shape.	Specify matching against the full `tool_input.command` string: require a read-verb token and a `tasks/<id>.output` path match anywhere in the body (newlines/pipelines/`&&` OK); add one multiline `Bash` harness case mirroring incident transcripts.

1. **correctness** — `scripts/hook-anti-read-poll.sh:75-87` (planned Bash branch): Bash matcher underspecified for multiline/compound commands. Plan text ties detection to a read command whose argument matches the classifier; #3175 transcripts routinely poll via multiline Bash (`IMPLEMENT_TMPDIR=…` then embedded `cat …/tasks/<id>.output`), so argv-only parsing can pass the planned single-line `cat` test yet miss production polling. **Suggested revision:** Match read verb + `tasks/<id>.output` anywhere in the full `tool_input.command`; add a multiline `Bash` case to `scripts/test-hook-anti-read-poll.sh`.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

{"no_issues_found": true}


## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-literal-contract-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-literal-contract-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-literal-contract-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-literal-contract-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-hook-wire-up-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-hook-wire-up-output.txt)

{"no_issues_found": true}


## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-hook-wire-up-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-hook-wire-up-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-edge-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-edge-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/hook-anti-read-poll.sh:79-83; scripts/test-hook-anti-read-poll.sh:93-99	Task-output classifier uses end-anchored `.output$` on the full Bash command string	Item 1 defines `(^|/)tasks/[A-Za-z0-9._-]+\.output$` and item 2(b) applies that classifier to the entire `tool_input.command`. Incident transcripts use `cat …/tasks/<id>.output 2>/dev/null`, `… | head -5`, and `|| echo` suffixes, so the command does not end at `.output` and the Bash branch stays silent while polling continues. Planned harness cases use bare `cat …/tasks/<id>.output` only, so CI can pass while production misses #3175.	Split path vs command matching: keep `$` only for `Read` `file_path`. For Bash, match `tasks/<id>.output` with a suffix-tolerant pattern (e.g. allow trailing whitespace, `2>`, `|`, `;`, `&&`, `||`) or extract the path token first. Add a harness case mirroring transcript suffixes (`2>/dev/null`, `| head -5`).

1. **correctness** — `scripts/hook-anti-read-poll.sh:79-83`, `scripts/test-hook-anti-read-poll.sh:93-99`: The task-output classifier’s `\.output$` anchor is applied to the full Bash `command` string, but #3175 polling commands almost always append redirects or pipes after `.output`. The Bash branch would not fire; harness cases that use bare `cat …/tasks/<id>.output` would still pass. **Suggested revision:** use an end anchor only for `Read` paths; for Bash, use a suffix-tolerant match or path extraction, and add harness coverage for `2>/dev/null` and `| head` suffixes seen in run logs.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-token-pin-fidelity-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-token-pin-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-token-pin-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-token-pin-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-token-pin-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-token-pin-fidelity-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-token-pin-fidelity-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-token-pin-fidelity-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-token-pin-fidelity-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-token-pin-fidelity-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-hook-mechanics-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-hook-mechanics-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/hook-anti-read-poll.sh:14; plan.txt:71-87	hooks.json widens to Read|Bash but the plan never requires replacing the script's Read-only tool_name gate	After hooks.json changes, every Bash PostToolUse still hits [ "$tool_name" = "Read" ] || exit 0 at line 14 and exits before the new Bash branch runs — the #3175 fix is dead in production	Add an explicit plan step: replace the single-tool guard with Read|Bash branching (e.g. case on tool_name) before classifier/Bash logic; mirror in hook-anti-read-poll.md
2	in_scope	important	correctness	plan.txt:81-82	Task-output classifier uses ERE end anchor $ while Bash matching is against the full tool_input.command string	Incident transcripts use cat …/tasks/<id>.output with trailing 2>/dev/null, || echo, or | head (see larch-logs/implement/* session-transcript.jsonl); anchored (^|/)tasks/…\.output$ on the whole command misses the primary #3175 shape	For Bash, match task-output with a substring ERE without $ (or grep -Eo and test -n); keep $ only when classifying Read tool_input.file_path; add a harness case with cat …/tasks/<id>.output 2>/dev/null

1. **[correctness]** `scripts/hook-anti-read-poll.sh:14` / plan `hooks.json` + hook section — The plan widens `hooks/hooks.json` to `"matcher": "Read|Bash"` (consistent with existing pipe unions at `hooks/hooks.json:60` `startup|resume|clear|compact` and `docs/dev-hook-audit.md:29` `Edit|Write`), but it does not list updating the script’s `[ "$tool_name" = "Read" ] || exit 0` guard. Without that change, the new Bash branch never runs despite registration.

2. **[correctness]** plan classifier `plan.txt:81-82` — Item 1 defines the classifier as `(^|/)tasks/[A-Za-z0-9._-]+\.output$`, while item 2 applies it as a substring of the full Bash command. The `$` anchor rejects common post-`.output` suffixes (`2>/dev/null`, `| head`, `|| echo`) seen in real `tasks/*.output` Bash reads. Read-path classification of `file_path` can keep `$`; Bash-body detection should not.

**Verified (no finding):** `Read|Bash` matches in-repo matcher style; one PostToolUse block is enough. `state-taskout-${cwd_hash}.tsv` vs `state-${cwd_hash}.tsv` cannot collide (distinct prefixes under `larch-read-poll/`). Fail-open contract (`set -e` omitted, `exit 0` early paths, final `exit 0`) is preserved in the plan. Bash 3.2 constraint is stated; word-boundary/`sed -n` implementation detail is left to the implementer (acceptable for warn-only). Separate task-output state + threshold 2 / 600s window aligns with harness goals.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-hook-mechanics-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-hook-mechanics-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-arch-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-arch-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-arch-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-arch-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-edge-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-edge-output.txt)

{"no_issues_found": true}

## Reviewer stderr (<TMPDIR>/codex-primary-plan-edge-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-edge-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex SENTINEL_TIMEOUT failed (exit 124)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=SENTINEL_TIMEOUT|EXIT_CODE=124|FAILURE_REASON=Process did not complete (sentinel file missing — possible crash or system kill)

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	scripts/hook-anti-read-poll.sh:86-88	Task-output counter keys by path but plan never defines Bash canonical path extraction	Item 3 says key task-output state by path only; Bash branch only classifies via suffix-tolerant match in the full command string. If implementer keys state by the entire tool_input.command (or by unstable prefixes), incident-shaped variants (sleep && cat …/tasks/id.output 2>/dev/null vs bare cat …/tasks/id.output) never share a counter and slow per-turn Bash polling can evade threshold 2	Specify in hook changes: capture the matched tasks/<id>.output token (prefer full absolute path when present in command, else tasks/<id>.output) and use that normalized string as the task-output state key for both Read and Bash branches; add harness case with two Bash payloads that differ only in leading wrappers/suffixes but share the same task id

1. **correctness** — `scripts/hook-anti-read-poll.sh:86-88` — Task-output counting mode says “key state by path only” but the plan does not say how to derive that path from a Bash `tool_input.command`. If the implementer uses the full command string as the state key, #3175-shaped variants (`sleep 5 && cat …/tasks/<id>.output 2>/dev/null` vs `cat …/tasks/<id>.output`) will not accumulate toward threshold 2 and the primary mechanical fix stays ineffective. **Suggested revision:** Document that both Read and Bash branches normalize to the same key (matched `tasks/<id>.output`, using the absolute path when the command contains one), and add a harness case with two syntactically different Bash commands targeting the same task output file.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-pragmatic-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-requirements-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-pin-drift-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-pin-drift-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-pin-drift-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-pin-drift-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-pin-drift-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-dyn-pin-drift-output-phase3.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/codex-primary-plan-dyn-pin-drift-output-phase3.txt)

(file missing: <TMPDIR>/codex-primary-plan-dyn-pin-drift-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/codex-primary-plan-dyn-pin-drift-output-phase3.txt.diag)

(file missing: <TMPDIR>/codex-primary-plan-dyn-pin-drift-output-phase3.txt.diag)

  ```

- **Step design Step 3 — collect-agent-results.sh cursor FAILED failed (exit 2)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-dyn-hook-gate-composition-output-phase3.txt|TOOL=cursor|STATUS=FAILED|EXIT_CODE=2|FAILURE_REASON=Process failed with exit code 2

## Reviewer output (<TMPDIR>/cursor-plan-dyn-hook-gate-composition-output-phase3.txt)

(file missing: <TMPDIR>/cursor-plan-dyn-hook-gate-composition-output-phase3.txt)

## Reviewer stderr (<TMPDIR>/cursor-plan-dyn-hook-gate-composition-output-phase3.txt.diag)

(file missing: <TMPDIR>/cursor-plan-dyn-hook-gate-composition-output-phase3.txt.diag)

  ```
