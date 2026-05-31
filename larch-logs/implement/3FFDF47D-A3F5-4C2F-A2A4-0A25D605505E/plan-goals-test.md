## Goal
Implement issue #3250: [IMPLEMENTING] Add "override and proceed" option to /design Step 2b.5 hard-trigger prompt\n\n## Summary.

## Implementation Plan
## Plan

Add a third option — **Override and proceed (advised against)** — to the two `/design`
prompt that gates an oversized plan at Step 2b.5: the plan-size **Hard branch**
`AskUserQuestion`. The option carries a prominent anti-recommendation,
sits **next-to-last** (Split / Override / Cancel), proceeds without a second confirmation, and
writes a Warnings audit entry to the run log. Thresholds and the `--partition` flow do not change.
Step 1c/1d semantic-sprawl heuristics remain Split/Cancel-only (**out of scope** here; file a
follow-up if sprawl Override is desired).

## Scope

- **In scope**: Step 2b.5 hard branch in `skills/design/SKILL.md`; matching soft-advisory
  breadcrumb in `skills/design/scripts/plan-review-loop.sh` (+ sibling `plan-review-loop.md`);
  hard-branch cross-references in `references/approval-gates.md`, `references/flags.md`
  (including the hard-trigger clause inside the `--partition` bullet), `README.md`; structure
  pins in `scripts/test-design-structure.sh`.
- **Out of scope (this PR)**: Step 1c/1d semantic-sprawl Override in
  `references/discussion-rounds.md` — `discussion-rounds.md`, Step 1c/1d sprawl prose, and any
  `DISCUSSION_MD` Override pin stay unchanged.

## Approach

The override behaves exactly like the existing **No-trigger branch**: it logs an audit note and
**returns to the caller**. The caller's existing routing then decides where to go next:

- Initial Step 2b -> Step 2b.5 hard override -> return -> Step 3 (plan review).
- Gate B re-emit -> Step 2b.5 hard override -> return -> Step 3b (per Gate B flow).
- Step 3 `LOOP_STATUS=plan-size-trigger` -> hard handler override -> return -> the existing
  "short-circuit to Step 3b".

Reusing "return to caller" keeps the change small and uniform: the override sets no
`SUMMARY_OUTCOME` and never exits, so no new cancellation outcome is introduced and
`render-final-summary.sh` (and its test) stay untouched.

On **Override**, write trigger context (`TRIGGER_REASONS`, `PLAN_LINES`, `DIFF_LINES`,
`DIFF_ADDED`, `DIFF_DELETED`) to `$DESIGN_TMPDIR/operator-override-hard-trigger.log`
(create/overwrite), then append a `### Warnings` entry to `$DESIGN_TMPDIR/execution-issues.md`
via `"${CLAUDE_PLUGIN_ROOT}/scripts/append-tool-failure.sh" --log "$DESIGN_TMPDIR/execution-issues.md" --site "design Step 2b.5" --tool "operator-override-hard-trigger" --exit-code 0 --category Warnings --output-file "$DESIGN_TMPDIR/operator-override-hard-trigger.log" --redact`
(mirror the validate-plan-commands **Override** block at `SKILL.md` ~1401). The audit write is
best-effort (`|| true`) and never blocks the operator's chosen action.

The new option is always shown when the prompt fires; the prominent warning is the only
guardrail (no flag, no second confirmation). `--partition` still cannot auto-downgrade a hard
trigger — the override is an explicit, loudly-discouraged operator escape hatch, a different
thing from a `--partition` downgrade.

## Option wording (load-bearing)

Hard-branch prompt only (sprawl prompts unchanged).

- Label (both prompts): `Override and proceed (advised against)`
- Hard-branch description: `STRONGLY DISCOURAGED. Proceeding with this oversized plan is quite
  likely to SEVERELY degrade the quality of the reviews and the resulting design. We advise
  against it. Pick this only if you knowingly accept that risk; splitting is almost always
  better. The override is recorded in the run log.`

Option order on both prompts (next-to-last placement): Split / Override / Cancel. The Split and
Cancel labels and their existing on-select behavior are preserved verbatim.

## Files to modify/create

### UPDATED: `skills/design/SKILL.md`
- Step 2b.5 **Hard branch** (the `## Plan Size — Hard Trigger` paragraph): change "exactly two
  options" to three options; add the **Override and proceed (advised against)** option as the
  next-to-last choice (Split / Override / Cancel); keep the `## Plan Size — Hard Trigger`
  header, the Split label, and the Cancel branch (`SUMMARY_OUTCOME=cancelled-plan-size-hard`)
  unchanged.
- Replace the stale parenthetical "(no **Continue** option — hard triggers are never
  downgradeable by `--partition`)" with: hard triggers are never downgradeable by `--partition`;
  **Override and proceed** is an explicit, loudly-discouraged operator escape hatch, not a
  `--partition` downgrade. This sentence is the pinned invariant (see test below).
- Add the On-**Override** behavior: write the trigger context (`TRIGGER_REASONS`, `PLAN_LINES`,
  `DIFF_LINES`, `DIFF_ADDED`, `DIFF_DELETED`) to a small log file, append it to
  `execution-issues.md` via the full `append-tool-failure.sh` invocation above (`--log`,
  `--site "design Step 2b.5"`, `--tool operator-override-hard-trigger`, `--exit-code 0`,
  `--output-file` pointing at the capture log, `--category Warnings`, `--redact`; best-effort
  `|| true`), print a loud `**⚠ 2b.5: operator
  overrode plan-size hard trigger; review quality may be severely degraded.**` breadcrumb, then
  **return to the caller** like the No-trigger branch (step 6). Note it sets no `SUMMARY_OUTCOME`
  and re-prompts on every subsequent firing (not sticky).
- Soft-advisory line (`HARD_TRIGGER_FIRED=true` + `SOFT_ADVISORY=true`): change "plan-body gate
  still requires Split/Cancel" to "plan-body gate still requires the Split / Override / Cancel
  prompt". (Coupled with the test pin at the `plan-body gate still requires` line.)
- Step 3 post-loop branch matrix, `LOOP_STATUS=plan-size-trigger` line: add a short parenthetical
  that Override returns and the existing "short-circuit to Step 3b" continues. Behavior is
  already correct because Override returns; this is a clarity-only edit.

### UPDATED: `skills/design/scripts/plan-review-loop.sh`
- Soft-advisory printf (~line 575): change `plan-body gate still requires Split/Cancel` to
  `plan-body gate still requires the Split / Override / Cancel prompt` (match SKILL.md).

### UPDATED: `skills/design/scripts/plan-review-loop.md`
- Sibling sync for the same soft-advisory phrase per
  `${CLAUDE_PLUGIN_ROOT}/.claude/rules/script-md-siblings.md`.

### UPDATED: `skills/design/references/approval-gates.md`
- The Gate B / Step 2b.5 cross-reference that reads "fires an `AskUserQuestion` with Split /
  Cancel only (no Continue option) when `HARD_TRIGGER_FIRED=true`": reword to include the
  Override option. Keep the `Step 2b.5` token (a separate structure-test pin depends on it).

### UPDATED: `skills/design/references/flags.md`
- Plan-size thresholds section, the "**Hard trigger** — any one suffices (no operator Continue
  override in the hard `AskUserQuestion`)" line: reword the parenthetical to note the explicit,
  strongly-discouraged Override-and-proceed escape hatch and that `--partition` still cannot
  auto-downgrade a hard trigger. Do NOT touch the separate `--partition` bullet (its "no Continue
  option, no threshold inspection" describes the partition-only path). **Do** update the
  hard-trigger clause inside that same bullet: change "the hard **Split/Cancel** prompt" to "the
  hard **Split/Override/Cancel** prompt".

### UPDATED: `scripts/test-design-structure.sh`
- Replace the pin `grep -Fq '(no **Continue** option — hard triggers'` (and its FINDING_21 fail
  message) with a `grep -Fq` on the pinned invariant substring
  `**Override and proceed** is an explicit, loudly-discouraged operator escape hatch, not a \`--partition\` downgrade` in `$SKILL_MD`.
- Add a pin asserting the option label `Override and proceed (advised against)` appears in
  `$SKILL_MD`.
- Update the pin `grep -Fq 'plan-body gate still requires Split/Cancel'` to
  `plan-body gate still requires the Split / Override / Cancel prompt` in **both** `$SKILL_MD`
  and `$PLAN_LOOP_SH` (existing `$PLAN_LOOP_SH` variable at file top).
- Leave all unrelated pins untouched (`## Plan Size — Hard Trigger`, `Step 1c sprawl heuristic`,
  `semantic sprawl heuristic`, `per Step 1d invocation`, the `Step 2b.5` approval-gates pin, the
  `SOFT_ADVISORY=`/`DIFF_ADDED=`/`DIFF_DELETED=`/`MECHANICAL_CHURN=` parse pins, the sub-step
  transition string, the `cancelled-plan-size-hard` enum, and the Step 1d-sprawl-return pin).

### UPDATED: `README.md`
- The `/design` row that says "hard triggers still show the hard `Split`/`Cancel` prompt before
  that same Split-path": change to `Split`/`Override`/`Cancel` for accuracy. One-clause precision
  fix per the drift-prone-prose rule.

## Edge cases

- **Not sticky**: the hard prompt re-fires on every oversized re-emit (e.g. a Gate B revision
  that is still oversized). Each override re-prompts and logs its own audit entry.
- **`--partition` + hard trigger**: the hard branch still fires with all three options; Override
  proceeds, Split enters Split-path. The partition branch (partition set, no hard trigger) is
  unchanged — it routes straight to Split-path with no `AskUserQuestion`, so it gains no override.
- **`plan-size-trigger` mid-review**: Override returns from the hard handler and the existing
  "short-circuit to Step 3b" carries the run forward; no extra review round runs.
- **Audit-log helper fails or is absent**: the `append-tool-failure.sh` call is best-effort
  (`|| true`); the override still proceeds. Logging never blocks the operator's choice.
- **AskUserQuestion `Other` free-text**: unchanged — existing gate Other-handling applies.

## Failure modes

1. **Stale cross-reference drift.** Missing one of the prose surfaces (SKILL.md,
   plan-review-loop.sh/md, approval-gates, flags.md both hard-trigger and `--partition` clauses,
   README) leaves docs that contradict the new option.
   Earliest signal: the plan-review panel or a later run-log audit flags the contradiction.
   Mitigation: the file list enumerates every stale "no Continue / Split-Cancel-only" surface;
   structure-test pins lock the SKILL.md + discussion-rounds invariants.
2. **Coupled test pin not updated -> CI red.** Editing the SKILL.md "(no Continue ...)" prose or
   the soft-advisory line without updating the matching `test-design-structure.sh` pin fails CI.
   Earliest signal: `bash scripts/test-design-structure.sh` fails locally or in `/implement`
   Step 5 / CI. Mitigation: pair every pinned-prose edit with its pin update in the same commit.
3. **Override mistaken for a cancel/exit.** If implemented as setting `SUMMARY_OUTCOME` or
   exiting, the run aborts instead of proceeding. Earliest signal: the run ends after override
   rather than reaching Step 3 / Step 3b. Mitigation: spec Override to mirror the No-trigger
   branch — return to caller, no `SUMMARY_OUTCOME`, no exit.

## Testing strategy

- Update `scripts/test-design-structure.sh` pins as above; add the Override-label pin. Run
  `bash scripts/test-design-structure.sh` — must pass.
- Run `bash scripts/relevant-checks.sh` (or `make lint`) over the edited files: agent-lint,
  markdownlint (MD038 code-span whitespace), bash32, readability-preamble, bare-grep-probe,
  foreground-markers, and renderer-substitution checks must pass.
- `skills/design/scripts/check-plan-size.sh` is NOT modified (thresholds unchanged), so
  `test-check-plan-size.sh` stays green with no edits. `render-final-summary.sh` is untouched
  (no new outcome), so `test-render-final-summary.sh` stays green. Run both to confirm no
  regression.
- Limitation: the override routing is prompt-side (the orchestrator fires the `AskUserQuestion`
  and branches in prose), so there is no script unit test for the actual override path. The
  structure tests pin the prose contract; the behavior itself is verified by manual QA of a
  `/design` run that trips the hard trigger and picks Override.

## Out of scope

- Hard-trigger thresholds (`plan-body > 800`, `diff_added > 2000`, legacy `diff_lines > 1500`)
  and the `mechanical_churn` soft-advisory: unchanged.
- The `--partition` routing and the Split-path / decomposition panel: unchanged.
- Step 1c/1d semantic-sprawl `AskUserQuestion` prompts (`discussion-rounds.md`): unchanged;
  sprawl Override deferred to a follow-up issue.
- No new flag and no second confirmation gate.


## Acceptance

A correct implementation satisfies all of the following:

- The Step 2b.5 **Hard branch** `AskUserQuestion` in `skills/design/SKILL.md` offers exactly three options, in this order: (1) `Let my panel of agents split this feature for you`, (2) **Override and proceed (advised against)** (the next-to-last choice), (3) `Cancel`. The existing Split and Cancel labels and their on-select behavior are unchanged.
- The Override option's label/description prominently warns that proceeding is quite likely to SEVERELY degrade the quality of the reviews and the resulting design, and that it is advised against.
- On Override: the orchestrator writes the trigger context to a capture file and appends a `### Warnings` entry to `$DESIGN_TMPDIR/execution-issues.md` via the full `append-tool-failure.sh` contract (`--log`, `--site "design Step 2b.5"`, `--tool operator-override-hard-trigger`, `--exit-code 0`, `--output-file`, `--category Warnings`, `--redact`; best-effort `|| true`), prints a loud override breadcrumb, then returns to the caller exactly like the No-trigger branch. Override sets no `SUMMARY_OUTCOME`, never exits, and re-fires on every subsequent oversized re-emit (not sticky).
- The stale SKILL.md parenthetical `(no **Continue** option — hard triggers are never downgradeable by --partition)` is replaced by the pinned invariant sentence stating Override is an explicit, loudly-discouraged operator escape hatch and that `--partition` still cannot auto-downgrade a hard trigger.
- The SKILL.md soft-advisory line AND the `skills/design/scripts/plan-review-loop.sh` soft-advisory `printf` (plus the `plan-review-loop.md` sibling) read `the Split / Override / Cancel prompt` instead of `Split/Cancel`.
- `references/approval-gates.md`, `references/flags.md` (including the hard-trigger clause inside the `--partition` bullet), and `README.md` no longer describe the hard prompt as Split/Cancel-only.
- `scripts/test-design-structure.sh` pins are updated: the `(no **Continue** option …)` pin is replaced with the new invariant substring; a new pin asserts the `Override and proceed (advised against)` label appears in SKILL.md; the `plan-body gate still requires …` pin matches the new phrase in BOTH `$SKILL_MD` and `$PLAN_LOOP_SH`. `bash scripts/test-design-structure.sh` passes.
- Unchanged (regression guard): hard-trigger thresholds, the `--partition` routing/Split-path, the `mechanical_churn` soft-advisory, and the Step 1c/1d semantic-sprawl prompts in `references/discussion-rounds.md`.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes on every edited file.

diff_lines: 72

## Test plan
(no test plan section in plan-file)
