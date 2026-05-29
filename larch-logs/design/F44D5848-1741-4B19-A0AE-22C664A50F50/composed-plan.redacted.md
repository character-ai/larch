## Plan

UX-only change to one Gate B branch. When `plan-review-loop.sh` ends with `LOOP_STATUS=converged|cap-hit` and `manual_gate_b=false`, Gate B (Step 3.5) currently prints the `## Multi-round loop result` table and then fires a two-option `AskUserQuestion` (**Continue to Step 3.6 and Gate C** / **Switch to discussion mode**). The findings were already auto-applied inside the loop, and both outcomes are available (more richly) at Gate C. Make that branch a **non-blocking print-and-auto-continue** summary and update the structural harness that pins the old prompt wording.

### UPDATED: `skills/design/references/approval-gates.md`

Single normative source for Gate B. Two edits:

1. **Passive-summary mode section** (the paragraph beginning "After parsing `.step3-plan-review-result.env` as data ...", currently ~line 100). Keep the section heading `#### Gate B passive-summary mode (`LOOP_STATUS=converged|cap-hit`)`, the table/column description, and the closing line `End with: "All accepted findings were auto-applied across N rounds; `plan.txt` reflects the final state."` byte-stable. Then **replace** the sentence:

   > Then fire `AskUserQuestion` with exactly two options: **Continue to Step 3.6 and Gate C** (Recommended) / **Switch to discussion mode**. On Continue, proceed to Step 3.6, then Step 3b, then Step 4, then Gate C.

   **with**:

   > This summary is **non-blocking**: do **not** fire an `AskUserQuestion` here — auto-continue to Step 3.6, then Step 3b, then Step 4, then Gate C, and do **not** halt the turn on the printed table. Gate C (Step 4b) is the single decision point; its **Discuss further** option covers the old switch-to-discussion intent.

   Keep the trailing two sentences, changing only the first leading phrase (`Passive-summary Continue routes through ...` → `Passive-summary auto-continue routes through ...`):

   > Passive-summary auto-continue routes through Step 3.6 before Step 3b / the next Step 3 entry. Do **not** re-apply findings or run the shared post-apply pipeline — the loop already revised `plan.txt`.

2. **Gate C "When" routing arrow** (currently ~line 168): change `passive-summary Continue → Step 3.6 → Step 3b → Step 4 → Step 4b` to `passive-summary auto-continue → Step 3.6 → Step 3b → Step 4 → Step 4b`. Leave the other arrows (auto-apply, Apply all, Go through each, zero-findings short-circuit) untouched.

Do NOT touch the `**Switch to discussion mode**` options inside the `manual_gate_b=true` 3-option prompt and the one-by-one iteration prompt (~lines 124, 143) — those remain in manual mode.

### UPDATED: `skills/design/SKILL.md`

Reword `passive-summary Continue` → `passive-summary auto-continue` in three routing references, for consistency with approval-gates.md. No behavioral text beyond these phrases changes.

- Post-loop branch matrix bullet (~line 1106): `... do not re-apply them at Gate B). Passive-summary Continue routes through Step 3.6 before Step 3b.` → `... Passive-summary auto-continue routes through Step 3.6 before Step 3b.` Keep the pinned prefix `` `LOOP_STATUS=converged|cap-hit` — proceed to Gate B **passive-summary mode** `` byte-stable.
- main-agent-vote path (~line 1117): `... including zero-findings and passive-summary Continue, proceed through Step 3.6 before Step 3b.` → `... including zero-findings and passive-summary auto-continue, proceed through Step 3.6 before Step 3b.`
- Step 3.5 prose (~line 1145): `... non-exiting path (passive-summary Continue, auto-apply, Apply all, or full one-by-one without abort) ...` → `... non-exiting path (passive-summary auto-continue, auto-apply, Apply all, or full one-by-one without abort) ...`. Leave the line-597-pinned sentence (`When Gate B resolves `manual_gate_b=false` ... routes through the warning/manual handling branch.`) and the `On Switch-to-discussion-mode (or per-finding Switch), re-enter Step 1e Gate A.` clause byte-stable.

### UPDATED: `scripts/test-design-structure.sh`

Update the five `contains` assertions that pin the old wording (the only harness pins on the prompt; verified by repo-wide grep). Keep each `# shellcheck disable=SC2016` comment above its assertion.

- ~Line 90 (was the two-option prompt pin): replace the literal `Then fire `AskUserQuestion` with exactly two options: **Continue to Step 3.6 and Gate C** (Recommended) / **Switch to discussion mode**.` with `do **not** fire an `AskUserQuestion` here — auto-continue to Step 3.6, then Step 3b, then Step 4, then Gate C`; change the failure message to `approval-gates.md passive-summary must be non-blocking auto-continue (no AskUserQuestion)`.
- ~Line 92: `passive-summary Continue → Step 3.6 → Step 3b → Step 4 → Step 4b` → `passive-summary auto-continue → Step 3.6 → Step 3b → Step 4 → Step 4b` (message unchanged).
- ~Line 842: `passive-summary Continue, auto-apply, Apply all, or full one-by-one without abort` → `passive-summary auto-continue, auto-apply, Apply all, or full one-by-one without abort` (message unchanged).
- ~Line 843: `Passive-summary Continue routes through Step 3.6 before Step 3b` → `Passive-summary auto-continue routes through Step 3.6 before Step 3b`; message `... passive-summary Continue Step 3.6 routing pin` → `... passive-summary auto-continue Step 3.6 routing pin`.
- ~Line 848: same literal swap for `$APPROVAL_MD`; message `... passive-summary Continue Step 3.6 routing pin` → `... passive-summary auto-continue Step 3.6 routing pin`.

Keep ~lines 60 (`... — proceed to Gate B **passive-summary mode**`), 88 (section heading), 89 (`zero-findings short-circuit → Step 3.6 ...`), and 597 byte-stable.

### Files verified to need NO change

- `skills/design/references/plan-review.md` (~line 58) references only `Gate B passive-summary reads round-summary.env when LOOP_STATUS=converged|cap-hit`; that data read is unchanged. No prompt/chooser reference.
- `scripts/test-design-multi-round-integration.sh` and `skills/design/scripts/test-step3-review-cap.sh` assert only `LOOP_STATUS=converged`/`cap-hit` *status* values, which this change does not alter.
- SKILL.md anti-halt continuation reminder — its `Gate B(c) → Step 1e` clause stays accurate for `manual_gate_b=true` mode.
- `CHANGELOG.md` and `larch-logs/**` references are historical records — not edited.

### Approach

Minimum-change, surgical. The behavior change lives entirely in the one approval-gates.md paragraph (delete the prompt; print-and-auto-continue, explicitly non-halting). Everything else is a consistency reword of the path label `Continue` → `auto-continue` (it was the now-removed option name) plus the matching harness-pin updates. No script logic changes: `plan-review-loop.sh` already emits `LOOP_STATUS=converged|cap-hit` and already auto-applies findings between rounds; only the orchestrator's Gate B presentation prose changes.

### Edge cases

- `manual_gate_b=true` on a converged/cap-hit run: unchanged — the loop exits after one round with `LOOP_STATUS=complete REASON=manual-gate-b`, so passive-summary mode is never entered; the full 3-option prompt still fires.
- `LOOP_STATUS=revision-failed|emit-plan-failed`: unchanged — still routed to the warning + manual-handling branch.
- `LOOP_STATUS=zero-findings-degraded-panel` and the zero-findings short-circuit: unchanged — still print-and-continue through Step 3.6.
- Gate-B-bypass short-circuits (`cap-reached`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `panel-failed`): unchanged — still skip Gate B and Step 3.6.
- HARD vs SIMPLE: passive-summary auto-continue still routes through Step 3.6 (HARD-only assessor) before Step 3b.

### Failure modes

- **Harness drift (most likely):** editing prose without updating the five `test-design-structure.sh` pins (or vice-versa) breaks CI. Signal: `bash scripts/test-design-structure.sh` fails with one of the five `contains` messages. Mitigation: edit prose and pins in the same change; run the harness before commit.
- **Orchestrator halts on the printed summary:** mitigated by the new explicit "auto-continue ... and do **not** halt the turn on the printed table" text.
- **Dangling `Continue` reference:** mitigated by enumerating all five prose spots (approval-gates 100/168, SKILL 1106/1117/1145).

### Testing strategy

- `bash scripts/test-design-structure.sh` — must pass with the updated assertions.
- `bash scripts/test-design-multi-round-integration.sh` and `bash skills/design/scripts/test-step3-review-cap.sh` — must still pass unchanged.
- `bash scripts/relevant-checks.sh` (or `make lint`) — markdown/agent-lint + full pre-commit sweep.
- Grep gate: `grep -rn "Continue to Step 3.6 and Gate C" skills/ scripts/` returns no hits; `grep -rn "passive-summary Continue" skills/ scripts/` returns no hits (all reworded to `auto-continue`).

## Acceptance

- In `skills/design/references/approval-gates.md`, the "Gate B passive-summary mode (`LOOP_STATUS=converged|cap-hit`)" section no longer fires an `AskUserQuestion`; it prints the `## Multi-round loop result` table + the "auto-applied across N rounds; `plan.txt` reflects the final state" line, then auto-continues (non-blocking, explicitly non-halting) to Step 3.6 → Step 3b → Step 4 → Gate C.
- The new section text states Gate C is the single decision point and its **Discuss further** option covers the old switch-to-discussion intent.
- No `Continue to Step 3.6 and Gate C` literal remains in `skills/` or `scripts/` (historical `larch-logs/**` and `CHANGELOG.md` excluded).
- No `passive-summary Continue` literal remains in `skills/` or `scripts/`; all five prose spots (approval-gates ~100/168, SKILL ~1106/1117/1145) read `passive-summary auto-continue`.
- `manual_gate_b=true`, `revision-failed`, `emit-plan-failed`, the zero-findings short-circuit, and the legacy non-loop auto-apply path are all unchanged.
- The five updated `scripts/test-design-structure.sh` `contains` assertions match the new prose; `bash scripts/test-design-structure.sh` passes.
- `bash scripts/test-design-multi-round-integration.sh` and `bash skills/design/scripts/test-step3-review-cap.sh` pass unchanged.
- `bash scripts/relevant-checks.sh` (or `make lint`) passes.

diff_lines: 30
