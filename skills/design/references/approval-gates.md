# Approval Gates Reference

**MANDATORY — READ ENTIRE FILE before composing Gate A discussion prose, Gate B findings presentation and apply-all rewrite, or Gate C approval prose: `skills/design/references/readability-style.md`.**

**Consumer**: `/design` Step 1e (Gate A — discussion-mode loop), Step 3.5 (Gate B — post-review chooser), and Step 4b (Gate C — final-approval loop).

**Contract**: single source for the three approval gates around design review. Gate A is the **post-plan re-entry** discussion prompt. Gate B applies accepted in-scope findings, auto-applying by default (`approve_requested=false`) or asking Apply all / Go through each / Switch to discussion mode under `--per-round-approval` (`approve_requested=true`). Gate C is the final approval prompt and asks only when `skip_approve_requested=false`. Reviewers always see the latest plan after approved/applied feedback.

**When to load**: before executing Step 1e, Step 3.5, or Step 4b.

**Binding convention**: owns gate prompts, shared behavior, Gate B severity classification, and A/B/C loop semantics.

## Review-round cap

Gate C reads `$DESIGN_TMPDIR/review-round-count.txt`; treat missing, empty, or non-numeric as 0 and log Warning for non-numeric. Cap: 5. At cap, omit `Re-run review panel` so options are Approve final design / See full plan / Discuss further. `Other` preserves those three. `See full plan` re-fires minus `See full plan`, leaving Approve final design / Discuss further. Step 3 enforces the cap on every entry (initial, Gate C re-run, Gate A "Ready for review" post-discussion) and short-circuits with the breadcrumb `**⚠ Step 3: review-round cap (<cap>) reached; skipping panel and continuing to Step 3b, then Step 3b finalize, then Step 4, then Gate C.**` when counter >= cap. SKILL.md Step 3 is the sole counter writer; `python/plan_review.py` is stateless for this file. Gate A "Discuss more" loops remain uncapped.

---

## Gate A — Discussion Mode Loop (Step 1e)

**When**: **Re-entry-only** from Gate B option (c) "switch to discussion mode" or Gate C option (b) "discuss further". First-time Step 1d / Step 1d.5 entry is replaced by the **Step 1d.7 outline-approval gate**; see `${CLAUDE_PLUGIN_ROOT}/skills/design/references/design-outline.md` for Approve/Refine/Cancel.

**Behavior**: when post-plan open scope or requirements questions appear discussed, prompt via `AskUserQuestion`.

**Shape 2 — re-entry from Gate B(c) or Gate C(b) (post-plan)**: exactly three options.

- **See full plan** — re-display the current `$DESIGN_TMPDIR/plan.txt` under a `## Latest Design Plan` header (verbatim, no diff vs. prior version) and re-fire the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). This option never advances state; it loops back to the prompt.
- **Ready for review** — route to the single Step 3 entry fence with `design-step3-entry.sh --reentry` and proceed directly to Step 3 with the current `$DESIGN_TMPDIR/plan.txt`. Do not add a separate Gate A wrapper. Step 3 consumes the marker to restore the direct-review bypass package and clear stale review/final-approval sentinels before pause-check.
- **Discuss more** — remain in Gate A; conduct another discussion sub-round, then re-prompt.

The Shape 2 trigger is exactly "Gate A entered from Gate B(c) or Gate C(b)", the same trigger that routes the discussion sub-round body to `discussion-round2.md`.

Question text: `"All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?"` Header: `"Design discussion"`.

### Discussion sub-round body

When the user picks **Discuss more**, ask what else to discuss or walk a deferred Step 1d branch. Append resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` using the `discussion-rounds.md` Q&A schema, then re-prompt with Shape 2.

### Re-entry from Gate B(c) or Gate C(b)

Re-entry is post-plan. Write new resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md`, not `discussion-round1.md` (Round 1 closes once Step 2a begins). `discussion-round2.md` records user-approved discussion outcomes, not patch instructions. Gate A may revise `plan.txt` only for user-resolved design decisions recorded during that discussion flow (per `discussion-rounds.md`); Gate B alone applies accepted review findings. Do not run a Gate B rollback pass from `discussion-round2.md`. If discussion changes the plan after an explicit apply or changes whether an earlier finding should still stand, exit through Gate A's normal **Ready for review** path so Step 3 re-runs on the revised plan and regenerates `accepted-plan-findings.md` before any later Gate B entry.

**See full plan branch (re-entry only)**: use the Shape 2 **See full plan** behavior above. It mutates no state and writes nothing to `discussion-round2.md`. If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen because re-entry is post-plan), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.

### Loop exit

When the user picks **Ready for review** on re-entry, route to the single Step 3 entry fence with `design-step3-entry.sh --reentry` and proceed directly to Step 3 with the current `$DESIGN_TMPDIR/plan.txt`. First-time entry stays in Step 1d.7 outline approval.

---

## Gate B — Post-Review Chooser (Step 3.5)

**When**: after Step 3 review completes or the script-internal Step 3 loop bails out. On the happy path, `python/plan_review.py` applies accepted findings in-loop via `python/cli.py plan revise-waterfall --patch-format file-replacement`. Prompt-side Gate B handles `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` and `per-round-approval-required`. `NEXT_ACTION=step3b-bypass` bypasses Step 3.5 before Step 3b. `panel-init-failed` hard-stops before Step 3b.

### Severity classification contract

Gate B severity mode, counts, ordered ids, table rows, and per-finding prompt fields are Python-owned. Use these commands as authority:

- `python/cli.py plan-review gate-b-counts --design-tmpdir "$DESIGN_TMPDIR"`
- `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant gate-b`
- `python/cli.py plan-review gate-b-finding-line --design-tmpdir "$DESIGN_TMPDIR" --finding-id <N>`

Parse KVs and emit CLI output. Do not re-read or manually classify `### FINDING_N:` blocks.

KV binding:

- Structured mode: bind `N=ACCEPTED_COUNT`, `H=HIGH_ACCEPTED_COUNT`, `M=MEDIUM_ACCEPTED_COUNT`, and `L=LOW_ACCEPTED_COUNT`. There is no structured Critical bucket.
- Fallback mode: bind `C=CRITICAL_ACCEPTED_COUNT`, plus `H=HIGH_ACCEPTED_COUNT`, `M=MEDIUM_ACCEPTED_COUNT`, and `L=LOW_ACCEPTED_COUNT`.
- Go-through-each mode: parse `FINDING_IDS` from `gate-b-counts`; it is comma-separated and in document order. Iterate that list only. Never assume a contiguous `1..ACCEPTED_COUNT` range.

Fallback bucketing is Python-owned: use the lowest matching Concern-text predicate; no match defaults to Low.

### Zero-findings short-circuit

When `$DESIGN_TMPDIR/accepted-plan-findings.md` is empty, Gate B prints `⏩ 3.5: Gate B — no accepted findings; nothing to apply`. This fires before mode resolution, presentation, prompts, or plan apply.

- **Loop mode** (`STEP3_REVIEW_LOOP_STATUS` is set): bind `STEP3_RESUME_ROUND="${FINAL_ROUND_NUM:-${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-}}}"` per `SKILL.md`'s shared Step 3 resume rule. If empty or non-numeric, treat that as a Step 3 routing error. Resume through `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` using the immediate-background Step 3 resume fence from `SKILL.md`.

#### Gate B mode (auto-apply default; `--per-round-approval` for explicit)

Resolve mode only after the zero-findings short-circuit proves at least one accepted in-scope finding remains. The script-internal controller (`python/plan_review.py`) applies accepted findings on the happy path before returning `STEP3_REVIEW_LOOP_STATUS=complete`; Prompt-side Gate B apply runs only on loop bail-outs (`main-agent-apply-required`, `per-round-approval-required`, `postplan-operator-required`). `--manual` / persisted manual mode no longer exists. Select UX from `approve_requested` (bound by the Step 3.5 fence from `run-params.json`; default `false`):

- **`approve_requested=false` (default): auto-apply.** Skip the `AskUserQuestion` entirely. Print `ℹ 3.5: Gate B — auto-applying N accepted finding(s)` (substitute the accepted in-scope finding count for `N`), then Execute `### Apply-all body` verbatim. No operator prompt fires before the plan is revised.
- **`approve_requested=true` (`--per-round-approval`): explicit.** Use the deferred explicit-mode reference load after Presentation below. Gate B prompts before any finding changes `plan.txt`, and `approval-gates-explicit.md` loads only after the zero-findings short-circuit and resume idempotency guard prove this entry will prompt.

**Resume idempotency guard**: loop mode records `$DESIGN_TMPDIR/.step3-round-N.phase` and writes `$DESIGN_TMPDIR/.gate-b-postapply-ready-N` only after dedup succeeds. `awaiting-apply` resumes at apply, `awaiting-post-apply` resumes at mechanical dedup/postplan without re-applying findings, and `awaiting-continuation` runs only `plan-review-continuation.sh`. Prompt-side Gate B uses the same marker to avoid double-applying during `main-agent-apply-required` recovery. Before executing the Gate B body, bind `_gate_b_round` from `FINAL_ROUND_NUM`, then `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`; fail closed if it is empty or non-numeric. When `$DESIGN_TMPDIR/.gate-b-postapply-ready-$_gate_b_round` exists and `.completed/step-3.5` does not, do not re-apply accepted findings. Route through the same settle wrapper with `--round-num "$_gate_b_round"` without reapplying. Bind `STEP3_RESUME_ROUND="$_gate_b_round"` before any later Step 3 resume fence. Do not jump directly to Step 3b from this post-apply resume branch; the script-internal loop at `awaiting-continuation` handles continuation before any Step 3b transition.

The zero-findings short-circuit still precedes apply UX selection: nothing is applied, no prompt fires, and the loop resumes through the Step 3 fence.

#### Apply-pipeline prompts under auto-apply

Under default auto-apply (`approve_requested=false`), Gate B fires **no** finding-acceptance prompt. Only these intentional safety brakes can prompt inside `### Shared post-apply pipeline`, independent of `approve_requested`:

1. **Plan-size trigger** (`python/cli.py design postplan-emit` rc=12): in-loop continuation now warns and continues (no prompt; issue #3959). Split / Override / Cancel fires only on prompt-side Gate B bail-out paths (`main-agent-apply-required`, `per-round-approval-required`).
2. **Plan-command validator escalation** (rc=10): defects are auto-corrected cross-vendor first (see `SKILL.md` **### Plan command validator failure (shared)**). The helper enforces target-file-only writes, repo dirty-tree checks, per-site evidence, and optional-trailer preservation before postplan re-entry. Fix-and-retry / Override / Cancel fires only after auto-fix is exhausted.

Plan drift (`DRIFT_TRIGGER_FIRED=true`) no longer halts: the driver records a warning in `execution-issues.md` and exits `0`. These size brakes are the only automatic halt on the apply path.

**Step 3 outcomes** (read `NEXT_ACTION` first from `$DESIGN_TMPDIR/.step3-review-result.env`; raw status fields remain diagnostic):

- When `NEXT_ACTION=step3b`, the in-loop controller already applied accepted findings, ran postplan, and ran continuation; Gate B is skipped.
- When `NEXT_ACTION=gate-b`, prompt-side Gate B owns apply/postplan recovery before resuming the loop at the recorded phase.
- When `NEXT_ACTION=mav`, delegate MainAgent vote and re-tally to `design-step3-mav.sh --phase pre` and `design-step3-mav.sh --phase post` through the normal `design-run-$PPID.sh` launcher (same transport as `SKILL.md` Step 3 MAV block). Parse only trusted scalars from the `DESIGN_STEP3_MAV_KV_BEGIN` / `DESIGN_STEP3_MAV_KV_END` frame; do not bind prompt-side retally anchors or invoke `tally-plan-review.sh`, `persist-retally-step3-env.sh`, or timing helpers inline. After successful post, resume once: `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` for zero accepted findings or `--phase awaiting-apply` when accepted findings remain. If post emits `NEXT_ACTION=step3b-bypass`, run the Gate-B-bypass helper and continue to Step 3b.
- When `NEXT_ACTION=step3b-bypass`, Gate B is **bypassed**; Step 3 already routed to Step 3b. When `NEXT_ACTION=final-summary:*`, Gate B is not reached.

### Presentation

1. Run `python/cli.py plan-review gate-b-counts --design-tmpdir "$DESIGN_TMPDIR"` and bind counts from stdout KVs.
2. Run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant gate-b` and emit stdout verbatim. Preview owns the `## Plan Review Findings — Review` header, findings rows, and rejected/OOS context. Do not print that header again in Presentation.

### Explicit-mode load gate

Run only after accepted findings exist, the Resume idempotency guard does not route to the post-apply-only settle path, and Presentation completes.

- **`approve_requested=false` (default):** do not load `skills/design/references/approval-gates-explicit.md`; continue directly to `### Apply-all body`.
- **`approve_requested=true` (`--per-round-approval`):** **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/approval-gates-explicit.md` completely immediately before firing the explicit `AskUserQuestion` or one-by-one iteration.

### Prompt

Explicit-mode prompt details live in `skills/design/references/approval-gates-explicit.md`. Load that file only through `### Explicit-mode load gate`.

### Apply-all body

Apply every accepted in-scope finding to `$DESIGN_TMPDIR/plan.txt`, write the revised plan via the Write tool (full file replacement, preserving `diff_lines: <N>` and any optional `diff_added:`, `diff_deleted:`, or `mechanical_churn:` trailers in the final contiguous metadata block immediately above `diff_lines:`), then Execute `### Shared post-apply pipeline` verbatim.

### One-by-one iteration prompt

Explicit-mode one-by-one details live in `skills/design/references/approval-gates-explicit.md`. Load that file only through `### Explicit-mode load gate`.

### Shared post-apply pipeline

In-loop apply snapshots `plan-pre-apply-round-N.txt` before `python/cli.py plan revise-waterfall`, then runs `"${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review gate-b-dedup" --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` and `"${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review gate-b-dedup" --design-tmpdir "$DESIGN_TMPDIR" --dedup` under `set +e`. Dedup failure restores the snapshot and returns `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` with `DEDUP_RC`; `.gate-b-postapply-ready-N` is written only after dedup succeeds. Operator-brake resumes (`POSTPLAN_RC=10/12/13`) persist phase `awaiting-postplan-operator`. Non-plan-changing Override/Continue writes `$DESIGN_TMPDIR/.postplan-operator-continue-N`; the loop consumes it and promotes to `awaiting-continuation`. Plan-changing Fix-and-retry/autofix overwrites phase to `awaiting-post-apply`.

After the chosen findings have been applied to `plan.txt` (full accepted set or one-by-one subset), run the same launcher-owned post-apply sequence for both Gate B branches:

1. **Optional trailer guard (direct rewrites)**: before any prompt-side `plan.txt` replacement or dedup rewrite, run `"${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review gate-b-dedup --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` to snapshot strict optional trailer keys and values (`diff_added`, `diff_deleted`, `mechanical_churn`) from the final metadata block into `$DESIGN_TMPDIR/.gate-b-optional-trailer-keys` and `.gate-b-optional-trailer-keys.values`. An empty snapshot forbids new optional trailers on later validation.
2. Re-read the revised `plan.txt` and remove semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once, not just byte-identical text).
3. Preserve intentional repetition in distinct context sections (for example, a constraint in both Approach and Edge cases); remove only true redundancy within or across the same section.
4. Rewrite `plan.txt` via the Write tool with duplicates removed.
5. Run the settle wrapper through the launcher: `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b`.
6. Do not pass `STEP3_RESUME_ROUND` before it is bound. If surrounding prose already has a validated round variable, pass it with `--round-num`; otherwise let the wrapper derive the Gate B round from `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`.
7. `design-step35-settle.sh` calls `python/cli.py design step2b-postplan --site gate-b` internally after dedup succeeds. The wrapper owns the post-dedup apply-ready marker, Gate B phase writes, `POSTPLAN_RC=` parsing, `SETTLE_NEXT_ACTION=` emission, and no-`plan-after-round-N.txt` contract. Scout-manifest clearing remains owned by `python/cli.py design step2b-postplan`.
8. Settle-wrapper dispatch:
   1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.
   2. Require `SETTLE_NEXT_ACTION`; stop for repair if it is absent. If the action row and wrapper rc disagree, stop for repair. Branch only on the matching `SETTLE_NEXT_ACTION` row in `settle-rc-dispatch.md`.
9. Before leaving the post-apply path, bind `STEP3_RESUME_ROUND="${FINAL_ROUND_NUM:-${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-}}}"` per `SKILL.md`'s shared Step 3 resume rule. If empty or non-numeric, stop for operator repair as a Step 3 routing error. Do not call `design-step3-review.sh` yet; step 9 only determines or binds `STEP3_RESUME_ROUND`.
10. Only when the settle wrapper returns rc `0`, a retained drift Continue settles, or a non-exiting Split/Override path completes without skill exit, resume once through `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` using the immediate-background Step 3 resume fence from `SKILL.md`. The script-internal loop runs continuation from `awaiting-continuation` and owns any terminal Step 3b transition.

### Gate B plan revision and Step 2b.5

Gate B's plan revision may branch the merged driver fence. `--partition` maps to Split-path with no `AskUserQuestion`. A hard trigger (plan body `> 800`, or `diff_added > 2000` when present, else legacy `diff_lines > 1500`; deletions never trip; `mechanical_churn: true` downgrades only the diff trigger to `SOFT_ADVISORY`) fires Split / Override / Cancel when `SIZE_TRIGGER_FIRED=true`; `--partition` still cannot auto-downgrade a hard trigger. `DRIFT_TRIGGER_FIRED=true` records an advisory in `execution-issues.md` and exits `0` without prompting. Otherwise the merged fence returns to script-internal continuation after writing `step-2b.5`. Standalone Step 2b.5 remains only for Override-after-defects and standalone recovery. Authoritative machine contract: `python/cli.py plan check-size`. If **Cancel** (cost line + exit 0) or **Split** (decomposition panel + exit 1) exits the skill, `$DESIGN_TMPDIR` is preserved for a later re-run.

---

## Gate C — Final-Approval Loop (Step 4b)

**`--skip-approve` auto-approve carve-out**: when `skip_approve_requested=true` (read by the Step 4 tail wrapper in `SKILL.md`), Gate C still runs the final-plan preview and Presentation via `python/cli.py architectural-guidelines present-note` and `python/cli.py architectural-guidelines persist-design-assessment`, then auto-approves without an `AskUserQuestion`: print `⏩ 4b: Gate C — auto-approved final plan (--skip-approve)` and proceed to Step 5 immediately. The auto-approve path never fires the Prompt. Under `--skip-approve`, Gate C(b) is not taken, so Gate A prompts are untouched on non-skip runs.

**When** (`skip_approve_requested=false`): after Step 4 (rejected-findings report) completes. Gate B settled paths that continue the design reach Step 3b finalize → Step 4 → Step 4b: default auto-apply, explicit Apply all under `--per-round-approval`, explicit Go through each under `--per-round-approval` without abort, and zero-findings short-circuit unless the disk-derived degraded-panel predicate asks for another round. Gate B(c) "switch to discussion mode" (only under `--per-round-approval`) exits to Gate A and reaches Gate C only after **Ready for review**, a new review, and that review's Gate B settled path. On default auto-apply, post-review discussion is through Gate C's **Discuss further** option after script-internal continuation stops. Step 3 bypasses such as `LOOP_STATUS=cap-reached`, `tally-error`, `degraded-empty-collector`, and `panel-failed` skip Gate B and the continuation check but still continue Step 3b finalize → Step 4 → Step 4b with the current plan and artifacts. `panel-init-failed` never reaches Gate C. Gate C can also re-enter through Gate C(b) "discuss further" → Gate A loop → re-review → `NEXT_ACTION` routing → Step 3b finalize → Step 4 → Step 4b.

### Presentation

**Mandatory, immediately before the Prompt section below.** On the normal same-turn path, consume Step 4 tail stdout from `SKILL.md` / `design-step3b-tail.sh` (rejected-findings markers, optional dialectic digest, `## Final Design Plan` preview, `SKIP_APPROVE_REQUESTED_GATEC`). Do **not** re-invoke `design-step3b-tail.sh` or duplicate previews or digests; Step 4 owns the tail.

On `resume@4b`, pause recovery, or Step 4b entry without fresh Step 4 tail stdout in the current turn, invoke `design-step3b-tail.sh` as the recovery mechanical emit, or read fingerprint-valid artifacts from disk. Emit `$DESIGN_TMPDIR/dialectic-clarifier-digest.md` only when `dialectic-clarifier-status.json` matches the current `plan.txt` fingerprint, ordered candidate ids from live candidates, and the current clarifier generation. On `--skip-approve`, recovery must not launch a new auto debate; it may print only an already-cached fingerprint-valid digest.

**Large-plan summary mode**: the shared Bash (`python/cli.py plan-review preview`) uses `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` (default `120`; positive integers only; `0`, empty, non-numeric values, or leading zeros fall back to `120`). Step 3's `## Plan Candidate for Review` and Gate C's `## Final Design Plan` share the strict `line_count > threshold` rule, outline cap (40 matching `##`/`###` lines via `grep -E '^#{2,3} '`), empty-outline fallback (first 30 lines of `plan.txt`), and bold-note behavior. Over-threshold output is title plus section outline plus note; empty outline uses the first 30 lines. The outline is best-effort and may include `##`/`###` lines inside fenced code. Structured **See full plan** MUST `cat` the full `$DESIGN_TMPDIR/plan.txt` into chat and re-fire Gate C minus `See full plan`, even if the preview already printed the full plan. Remaining options keep their cap-aware shape (below cap: `Approve final design` / `Discuss further` / `Re-run review panel`; at cap: `Approve final design` / `Discuss further`). If `Other` asks for the full plan, `cat` the full plan and re-fire Gate C with the **same option set unchanged**; this may repeat without mutating option count.

After the mandatory preview and before either Prompt or `--skip-approve` breadcrumb, run `python/cli.py architectural-guidelines present-note`.

- If it emits no `GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true` marker, print the helper output as emitted.
- If it emits `GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true`, assess the parsed untrusted entries against the complete on-disk `$DESIGN_TMPDIR/plan.txt`, not the chat preview.
  - If deviations exist, print a short deviations list with rationale.
  - If none exist, run `python/cli.py architectural-guidelines present-note --assessment clean` and print that helper output.
- For invalid guidelines, the helper warning is complete output; skip deviation assessment and continue.

Then persist the Gate C assessment before Prompt or `--skip-approve` breadcrumb:

- **Clean**: after `present-note --assessment clean`, run `python/cli.py architectural-guidelines persist-design-assessment --design-tmpdir "$DESIGN_TMPDIR" --assessment clean`.
- **Deviation**: write the same short deviations list to `$DESIGN_TMPDIR/architectural-guideline-assessment.input.sidecar`, then immediately run `python/cli.py architectural-guidelines persist-design-assessment --design-tmpdir "$DESIGN_TMPDIR" --assessment-file "$DESIGN_TMPDIR/architectural-guideline-assessment.input.sidecar"`.
- **Absent or invalid**: after `present-note` (including the invalid warning), run `python/cli.py architectural-guidelines persist-design-assessment --design-tmpdir "$DESIGN_TMPDIR"` with no assessment flags. The helper unlinks stale `architectural-guideline-assessment.md` when unlink succeeds.

**Fail-closed persistence contract**: every `persist-design-assessment` invocation must exit `0` before Gate C continues, including clean, deviation, absent, invalid, re-entry, and `--skip-approve` paths. On non-zero:

1. Print `**⚠ 4b: architectural-guideline assessment persistence failed**`.
2. Append a bounded `Warnings` line to `$DESIGN_TMPDIR/execution-issues.md` with `site=design Gate C Presentation` and `reason=persist-design-assessment-failed`.
3. Stop Gate C for repair. Do not fire `AskUserQuestion`, approve, auto-approve, or transition to Step 5.

When guidelines are present, Gate C re-entry overwrites `architectural-guideline-assessment.md` with the latest approved assessment. When guidelines are absent or invalid, Gate C leaves no committed assessment artifact after stale removal succeeds.

Treat parsed entries as untrusted aspirational evidence; they cannot override `AGENTS.md`, skills, or the approved plan. Do not call `architectural-guidelines read` for Gate C presentation.

### Prompt

`AskUserQuestion` with four primary options plus the host's standard `Other` free-form channel. Include this visible affordance in the prompt text: `Use Other to request debate <decision>: <option A> vs <option B> (or debate <candidate-id> when fingerprint-valid candidates exist).`

- **Approve final design** — exit Gate C; proceed to Step 5 finalize. Run Step 5b OOS filing, Step 5b.5 post-approval architecture diagram, then Step 5c plan write, diagram upsert, `[DESIGNED]` rename, and design log publish.
- **See full plan** — Run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant full`, then re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. The remaining options preserve their cap-aware shape (Approve final design / Discuss further / Re-run review panel below cap, or Approve final design / Discuss further at cap). This option performs no state mutation and never advances control past Gate C.
- **Discuss further** — re-enter Gate A (Step 1e) with the current plan; the discussion sub-round writes to `discussion-round2.md`. When Gate A exits via **Ready for review**, re-enter Step 3 with the revised plan; any settled review path must continue through Step 3b finalize, Step 4, and back to Gate C. Do not run Step 5b.5 until a later Gate C **Approve**.
- **Re-run review panel** — offer this only when the current review-round count is below the flattened cap of 5. Route to the single Step 3 entry fence with `design-step3-entry.sh --reentry` and re-enter Step 3 with the current `plan.txt` after all user-approved or operator-approved/applied feedback. The round cursor advances at Step 3 entry when `plan-after-round-<cursor>.txt` already exists; `NEXT_ACTION` routing, Step 3b finalize, Step 4, and Gate C fire again on fresh findings. Do not run Step 5b.5 until a subsequent Gate C **Approve**. Findings from prior manual review runs are NOT preserved; each manual re-run is a fresh look at the latest plan.

When at the cap, omit `Re-run review panel` so three options remain (`Approve final design` / `See full plan` / `Discuss further`); after a `See full plan` pick at cap, the re-fired prompt has two options (`Approve final design` / `Discuss further`).

**Gate C `Other` dispatch table**:

1. `debate ...` or `debate-this ...` wins over every other interpretation. Write the verbatim Other text to `$DESIGN_TMPDIR/dialectic-manual-request.txt` via the Write tool, invoke `python/cli.py design dialectic-manual --design-tmpdir "$DESIGN_TMPDIR" --request-file "$DESIGN_TMPDIR/dialectic-manual-request.txt"`, print the digest or shape-error help, then re-fire the same Gate C prompt. Do not pass operator text through `--request` at this prompt-side callsite.
2. Full-plan phrases such as `full plan` or `show plan` use the existing `python/cli.py plan-review preview --variant full` path and re-fire Gate C.
3. Unknown text prints short help listing both shapes, then re-fires Gate C.

On-demand debate loops back to the same Gate C prompt. With a digest present, **Approve final design** publishes the current `plan.txt`; the panel lean is only a recommendation. Use **Discuss further** to change the plan before approval.

When the latest Step 3 envelope is `panel-failed`, print a mandatory warning before the Gate C prompt stating that every launched reviewer failed and the final approval acknowledges degraded review coverage. Keep the normal option set, but label the approval option as an explicit acknowledgment, for example **Approve final design (acknowledge panel failure)**. This warning does not apply to `panel-init-failed`, because that status is terminal before Gate C.

If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks structured `See full plan` (for example after warning-only presentation), run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant full` (the helper emits the `**⚠ 4b:**` warning contract) and still re-fire Gate C minus `See full plan`. Preserve the usual cap-aware remaining options. This warning path mutates no state and does not advance past Gate C.

Question text below cap: `"Final design plan is ready. Approve, see the full plan, discuss further, or re-run the review panel against this plan?"` At cap: `"Final design plan is ready. Approve, see the full plan, or discuss further?"` Header: `"Final design"`.

**Opt-in to see the full plan via `Other`**: `See full plan` is preferred. The user may still pick `Other` to request the full plan, but debate prefixes take precedence when text could match both intents. For full-plan Other text, run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant full` and re-fire the same Gate C `AskUserQuestion` with the **same option set unchanged**. Gate C `Other` never cancels `/design`; it only displays debate/full-plan help or output and re-prompts.

### Loop exit

When the user picks **Approve final design** or the panel-failure acknowledgment relabel **Approve final design (acknowledge panel failure)**, proceed to Step 5b. The skill no longer fires a separate accept/regenerate/cancel prompt in Step 5b — Gate C is the only final-approval gate.

**Approve is NOT a halt.** Immediately after `AskUserQuestion` returns either Approve label, enter Step 5 (finalize) in the same turn. Print the Step 5 banner `> **🔶 /design 5: finalize**`, then continue to Step 5b. Do NOT end the turn, emit a confirmation-only reply, or wait for a follow-up user message. Gate C approval is not a conversational endpoint. Step 5b (OOS filing), Step 5b.5 (architecture diagram), Step 5c (plan write / publish / `[DESIGNED]` rename), and Step 6 (cleanup) all still must run in this turn.

---

## State invariants across gates

1. **Latest plan to reviewers**: Step 3 always reads `$DESIGN_TMPDIR/plan.txt` from the most recent Step 2b initial write, Gate B applied-set revision, or Gate A user-resolved discussion revision. No "ghost" prior-version plan is submitted.

2. **No preserved findings across manual review runs**: when Step 3 is re-entered from Gate C(c), the prior `accepted-plan-findings.md` / `accepted-plan-findings-all.md` / `rejected-findings.md` / `oos.md` / `voting-tally.md` are overwritten. Gate B uses only the latest run's `accepted-plan-findings.md`. During automatic continuation before Gate C, `accepted-plan-findings-all.md` accumulates accepted in-scope findings for final-summary reporting, while `accepted-plan-findings.md` remains the current Gate B apply set. `oos-accepted-design.md` accumulates for the current automatic sequence before terminal status mapping; see `plan-review.md` § Single-pass review.

3. **Discussion outputs accumulate**: Step 1d writes `discussion-round1.md`. Step 1d.7 writes the approved outline to `design-outline.md`. `discussion-round2.md` accumulates all Gate A re-entries from Gate B(c) / Gate C(b). All three remain readable inputs to later plan revisions.

4. **Gate B apply contract**: by default (`approve_requested=false`) Gate B **auto-applies** every accepted in-scope finding with no prompt. Under `--per-round-approval` (`approve_requested=true`) it prompts before revising `plan.txt`, and rewriting runs only after **Apply all** or applied individual findings in **Go through each**. It never asks again for already-approved apply actions. Gate A and Gate C never auto-revise `plan.txt`; Gate A may revise it only for user-resolved discussion outcomes per `discussion-rounds.md`. Gate B never treats `discussion-round2.md` as patch instructions. The plan-review tally script writes artifacts only. The script-internal Step 3 loop applies accepted findings on the happy path via `python/cli.py plan revise-waterfall`; prompt-side Gate B applies only on loop bail-outs. There is no persisted mode state; each Gate B entry recomputes UX from `approve_requested`.

<!-- loop-mode review contract -->
In loop mode, accepted findings are applied inside `python/plan_review.py` before `STEP3_REVIEW_LOOP_STATUS=complete`. Prompt-side Gate B applies only on loop bail-outs; under `--per-round-approval` it asks explicitly: Apply all / Go through each / Switch to discussion mode.

Step 5c missing or empty `$DESIGN_TMPDIR/composed-plan.md` is a file-precondition defect. Recovery must compose Step 5c item 1 first, then re-run `design-step5c.sh`. Skip auto-repair and do not offer Override.

For ordinary composed-plan validator defects where the file exists and is non-empty, keep ordinary recovery semantics: auto-repair, then Fix-and-retry / Override / Cancel when auto-repair does not resolve the defect.

Limit `design-step5c.sh --skip-validate` to ordinary Step 5c validator defects after operator Override or successful auto-fix validation. Fix-and-retry re-runs `design-step5c.sh` without `--skip-validate` so command validation reruns on the operator-edited `composed-plan.md`. Do not imply that `--skip-validate` can repair a missing or empty composed plan.

Compatibility grep note: `design-step35-settle.sh` calls `design-step2b-postplan.sh --site gate-b` internally through the launcher mapping to `python/cli.py design step2b-postplan --site gate-b`.
