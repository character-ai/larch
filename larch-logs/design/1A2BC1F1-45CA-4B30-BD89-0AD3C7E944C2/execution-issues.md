### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-innovation-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 71s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-innovation-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/design/references/discussion-rounds.md:27-48	Sprawl Override audit omits the full append-tool-failure.sh contract	On Override, prose only says append a Warnings entry; append-tool-failure.sh requires --log, --site, --tool, --exit-code, --category, and --output-file (file must exist). A minimal implementation can skip the write or call the helper without a log file and get exit 2; audit is lost despite || true	Mirror the existing plan-command Override pattern in skills/design/SKILL.md (~1401): write $DESIGN_TMPDIR/operator-override-sprawl.log first, then append with --site design Step 1c sprawl heuristic or design Step 1d sprawl heuristic, --tool operator-override-sprawl, --exit-code 0, --category Warnings, --redact
2	in_scope	important	correctness	skills/design/SKILL.md:63-68	Hard-branch On-Override bullet abbreviates append-tool-failure flags	The bullet lists --category/--exit-code/--tool/--redact only; the helper also requires --log, --site, and --output-file. Implementers who follow only that bullet can produce a no-op audit	Match the validator Override block (~1398-1401): require --log $DESIGN_TMPDIR/execution-issues.md, --site design Step 2b.5, --output-file $DESIGN_TMPDIR/operator-override-hard-trigger.log (after writing TRIGGER_REASONS/PLAN_LINES/DIFF_* into that file)
3	in_scope	important	risk-integration	skills/design/scripts/plan-review-loop.sh:575	Mechanical-churn advisory still says Split/Cancel after SKILL.md changes	The plan updates the Step 2b.5 soft-advisory string to Split / Override / Cancel but does not list plan-review-loop.sh. Mid-review runs still print plan-body gate still requires Split/Cancel right before LOOP_STATUS=plan-size-trigger, contradicting the new three-option gate	One-line printf change to the same Split / Override / Cancel wording (or drop the gate requirement clause); optional grep pin in scripts/test-design-structure.sh if you want CI to catch drift
4	in_scope	important	architecture	skills/design/references/flags.md:19	Partition bullet hard-prompt sentence stays Split/Cancel-only	Plan updates README and the Hard trigger section but forbids editing the --partition bullet, which still says Hard plans still show the hard Split/Cancel prompt. Consumer docs disagree after the PR	Allow a one-clause fix inside that bullet only (e.g. Split/Override/Cancel) without changing partition routing prose
5	in_scope	nit	correctness	skills/design/SKILL.md:1008	plan-size-trigger branch still names Split-path / Cancel handler	Plan adds only an Override parenthetical; the matrix line still says run the Step 2b.5 Split-path / Cancel AskUserQuestion handler, which mislabels Override (return-to-caller, not Split-path)	Rename to hard-branch AskUserQuestion handler (Split / Override / Cancel) in the same edit pass

1. **[correctness]** `skills/design/references/discussion-rounds.md:27-48` — Sprawl **Override** audit is underspecified relative to `scripts/append-tool-failure.sh` (required `--log`, `--site`, `--output-file`). Copy the validator **Override** block pattern from `skills/design/SKILL.md` (~1401) with sprawl-specific `--site` / `--tool` / log path.

2. **[correctness]** `skills/design/SKILL.md:63-68` — Hard-trigger **On-Override** lists a truncated `append-tool-failure.sh` invocation. Spell out the same full flag set as the validator override so implementers do not ship a broken audit call.

3. **[risk-integration]** `skills/design/scripts/plan-review-loop.sh:575` — Plan updates the orchestrator advisory in `SKILL.md` but not this script’s matching `printf`; post-PR mid-review breadcrumbs will still say Split/Cancel only.

4. **[architecture]** `skills/design/references/flags.md:19` — The plan’s “do not touch `--partition` bullet” rule leaves an embedded hard-prompt sentence inaccurate vs README and the updated Hard trigger section.

5. **[correctness]** `skills/design/SKILL.md:1008` — `LOOP_STATUS=plan-size-trigger` prose should name the three-option hard handler, not “Split-path / Cancel” only.

[OUT_OF_SCOPE] `skills/design/references/flags.md:19` — `docs/skills.md` does not mention the new option; low drift risk if README is updated as planned.

[OUT_OF_SCOPE] Non-sticky re-prompt on every hard re-emit is explicit product intent; not a plan gap.

[OUT_OF_SCOPE] Self-attested `mechanical_churn` / trailer bypass paths predate this PR; adding script enforcement would be scope creep.

## Reviewer stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.diag)

Failed with exit code 1 after 71s. Output size: 0 bytes.

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-innovation-output.txt.stderr-tail)

Reading additional input from stdin...
⏳ codex agent: still running (1m elapsed)
2026-05-30T22:51:14.702946Z ERROR codex_core::session: failed to record rollout items: thread 019e7b14-d4ca-75c2-8d24-07021a617434 not found
❌ codex agent: FAILED (exit code 1, 71s elapsed, output 0 bytes)

## Launcher stderr (<TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-innovation-output.txt.launch-stderr)

  ```

- **Step design Step 3 — collect-agent-results.sh codex FAILED failed (exit 1)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/codex-primary-plan-pragmatic-output.txt|TOOL=codex|STATUS=FAILED|EXIT_CODE=1|FAILURE_REASON=Failed with exit code 1 after 120s. Output size: 0 bytes.

## Reviewer output (<TMPDIR>/codex-primary-plan-pragmatic-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	correctness	skills/design/SKILL.md:781-779 (proposed On-Override)	Hard-trigger audit uses abbreviated append-tool-failure.sh flags	Plan cites only --category, --exit-code, --tool, and --redact; append-tool-failure.sh requires --log, --site, and --output-file (scripts/append-tool-failure.sh:68-73). With || true the override still proceeds but run-log audit may be missing while copy promises recording	Match the full invocation pattern at skills/design/SKILL.md:1401 (--log, --site design Step 2b.5, --output-file for the trigger-context log, then --redact)
2	in_scope	important	correctness	skills/design/references/discussion-rounds.md:27-28 (proposed sprawl Override)	Sprawl Override audit contract underspecified vs hard branch	Hard branch specifies trigger context file plus append-tool-failure; sprawl only says append Warnings. Implementer may omit --site/--tool/--output-file or skip capture, weakening sprawl audit parity	Spell the same append-tool-failure.sh shape for Step 1c/1d (--site design Step 1c sprawl heuristic or design Step 1d sprawl heuristic, --tool operator-override-sprawl-heuristic, context log file) in discussion-rounds.md
3	in_scope	important	correctness	skills/design/references/flags.md:19	--partition bullet left saying Split/Cancel after hard section gains Override	Plan rewords Hard trigger in flags.md but forbids editing the --partition bullet, which still says hard plans show Split/Cancel. Same file will contradict the new three-option gate	Allow a one-clause fix on line 19 only (Split/Override/Cancel) or add a cross-reference in the Hard trigger section; do not leave stale Split/Cancel-only text beside updated thresholds

**1. [correctness]** Hard-trigger `append-tool-failure.sh` invocation in the plan (SKILL.md On-Override) omits required `--log`, `--site`, and `--output-file`. The script fails usage without them; with `|| true` the operator proceeds but the promised run-log entry may never be written.

**2. [correctness]** Sprawl Override in `discussion-rounds.md` only says “append Warnings audit entry” without the concrete `append-tool-failure.sh` contract used elsewhere (e.g. validator Override at `skills/design/SKILL.md:1401`), so sprawl bypasses may not be logged consistently.

**3. [correctness]** `flags.md:19` will remain inaccurate if only the Hard trigger paragraph is reworded: it still says hard plans show a **Split/Cancel** prompt while the plan explicitly says not to edit that `--partition` bullet.

**[OUT_OF_SCOPE] [risk-integration]** `skills/design/scripts/plan-review-loop.sh:575` duplicates the soft-advisory string `plan-body gate still requires Split/Cancel`; the plan updates SKILL.md but not this printf, so mid-review breadcrumbs can drift after the change. Consider aligning that line when touching plan-size prose (not required for the prompt-side gate to work).

## Reviewer stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.diag)

Failed with exit code 1 after 120s. Output size: 0 bytes.

## Failed-agent stderr tail (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.stderr-tail)

Reading additional input from stdin...
⏳ codex agent: still running (1m elapsed)
2026-05-30T22:51:54.379358Z ERROR codex_core::session: failed to record rollout items: thread 019e7b14-d4dc-79b0-a501-37ab6316bc5a not found
⏳ codex agent: still running (2m elapsed)
❌ codex agent: FAILED (exit code 1, 120s elapsed, output 0 bytes)

## Launcher stderr (<TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

(empty: <TMPDIR>/codex-primary-plan-pragmatic-output.txt.launch-stderr)

  ```

### Warnings

- **Step design Step 3 (plan review) — plan-review-loop.sh (operator abort; codex CLI bug) failed (exit 1)**:
  ```
Operator aborted the Step 3 plan-review loop after round 1.

Root cause: the codex reviewer CLI repeatedly failed (exit 1) with
"failed to record rollout items: thread <id> not found" and produced 0-byte output,
so the per-slot waterfall kept retrying, making the loop run for hours (bug).

Round 1 DID complete with a valid tally (degraded panel: codex down; Claude + Cursor voted):
  ACCEPTED_COUNT=4 (all important, unanimous), TALLY_PLAN_REVIEW_STATUS=ok, REVISE_STATUS=ok,
  COLLECT_OK_COUNT=12, COLLECT_FAILURE_COUNT=2.
All 4 accepted findings (plan-review-loop.sh breadcrumb sync; full append-tool-failure.sh
audit contract; narrow scope to Step 2b.5 only; flags.md --partition hard-trigger clause) are
reflected in the finalized plan.txt. Rounds 2+ were not run.
  ```
