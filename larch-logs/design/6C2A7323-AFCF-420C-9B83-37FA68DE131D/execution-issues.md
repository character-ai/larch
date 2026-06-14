### External Reviewer Issues

- **Step design Step 3 — collect-agent-results.sh cursor NOT_SUBSTANTIVE failed (exit 0)**:
  ```
## Structured collector record

REVIEWER_FILE=<TMPDIR>/cursor-plan-requirements-output.txt|TOOL=cursor|STATUS=NOT_SUBSTANTIVE|EXIT_CODE=0|FAILURE_REASON=structured records not found after repair

## Reviewer output (<TMPDIR>/cursor-plan-requirements-output.txt)

schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix
1	in_scope	important	completeness	skills/design/SKILL.md:395-401	Step 1d.5 SKILL edits omit explicit removal of the post-entry prose that still mandates `--mode complete` on skip paths	The plan removes the unconditional `design-step1d5.sh --mode complete` fence but leaves the adjacent "When Step 1d.5 finishes or is skipped by its entry guard, run … `--mode complete` … before continuing to Step 1e" block unless implementers delete it too; brainstorm-off then makes two Bash calls and routes toward Step 1e instead of Step 1d.7, violating brainstorm-off one-call acceptance	In the Step 1d.5 SKILL.md section, delete that prose block and replace it with: skip paths end after `--mode entry` (sentinel already written); active brainstorm paths call `--mode complete` only from `brainstorm.md` after `.brainstorm-done`; then continue to Step 1d.7
2	in_scope	important	completeness	skills/design/SKILL.md:932	Validator Override branch lacks a concrete launcher invocation for `--record-override`	The plan says Override should use a wrapper-owned record path and adds `--record-override` to `design-step-validator-autofix.sh`, but unlike the documented `--operator-cancel` launcher line it does not spell the Override fence; prompt prose can keep the raw `run-log append-failure` command at line 932, missing the validator-autofix raw-Bash sweep goal	In the validator-autofix SKILL.md Override bullet, replace the raw append command with a one-line launcher example mirroring `--operator-cancel`, e.g. `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step-validator-autofix.sh --record-override --site "<SITE>"` (plus the same validate log args the wrapper needs), and state that prompt prose must not spell `run-log append-failure`

### Findings

1. **completeness** — `skills/design/SKILL.md:395-401`: The plan removes the unconditional `--mode complete` fence but does not require deleting the prose that still tells the orchestrator to run `design-step1d5.sh --mode complete` when Step 1d.5 is skipped and before Step **1e**. That breaks brainstorm-off **one Bash call** acceptance and misroutes first-time flow (should go to Step **1d.7**). Delete the block and document: skip paths stop after `--mode entry`; `--mode complete` runs only from `brainstorm.md` on the active terminal path.

2. **completeness** — `skills/design/SKILL.md:932`: Validator Override still documents a full raw `run-log append-failure` command while the plan only says "wrapper-owned record path." Without a pinned launcher line (like `--operator-cancel` at line 933), the validator-autofix sweep can leave raw append prose in SKILL.md. Replace the Override bullet with an explicit `design-step-validator-autofix.sh --record-override` launcher invocation.

### [OUT_OF_SCOPE]

3. **risk-integration** — `scripts/test-design-structure.sh`: No structural pin asserts that `skills/design/SKILL.md` Step 1d.5 no longer unconditionally invokes `--mode complete` immediately after `--mode entry`. Worth a follow-up issue; not required for minimum correct implementation if finding 1 is fixed in prose.

## Reviewer stderr (<TMPDIR>/cursor-plan-requirements-output.txt.diag)

(empty: <TMPDIR>/cursor-plan-requirements-output.txt.diag)

## Failed-agent stderr tail (<TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

(file missing: <TMPDIR>/cursor-plan-requirements-output.txt.stderr-tail)

## Launcher stderr (<TMPDIR>/cursor-plan-requirements-output.txt.launch-stderr)

timing: WARNING: unknown task-kind: cursor-phase1-cursor-plan-requirements
  ```
### Warnings

- **Step design Step 2b.5 — python plan check-size failed (exit 2)**:
  ```
PLAN_SIZE_STATUS=invalid-mechanical-churn
  ```
