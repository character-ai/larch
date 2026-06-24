# Approval Gates Reference

**MANDATORY — READ ENTIRE FILE before composing Gate A discussion prose, Gate B findings presentation and apply-all rewrite, or Gate C approval prose: `skills/design/references/readability-style.md`.**

**Consumer**: `/design` Step 1e (Gate A — discussion-mode loop), Step 3.5 (Gate B — post-review chooser), and Step 4b (Gate C — final-approval loop).

**Contract**: owns the three user-facing approval gates that bracket the design review pipeline. Gate A is the **post-plan re-entry** discussion prompt, Gate C is the final approval prompt, and Gate B applies accepted in-scope findings — by default **auto-applying** with no prompt (`approve_requested=false`), or via a 3-option `AskUserQuestion` (Apply all / Go through each / Switch to discussion mode) when `--per-round-approval` is set (`approve_requested=true`). Gate A and Gate C use `AskUserQuestion` on their reachable paths (Gate C asks only when `skip_approve_requested=false`; see **Gate C** below); Gate B uses `AskUserQuestion` on its non-empty-findings path only under `--per-round-approval`. Reviewers always see the latest plan with all user-approved or operator-approved/applied prior feedback applied.

**When to load**: before executing Step 1e, Step 3.5, or Step 4b.

**Binding convention**: single normative source for the three gate prompts, their shared behavior, the severity-classification rubric used in Gate B, and the loop semantics between A/B/C.

**All gates apply uniformly.**

## Review-round cap

Gate C reads `$DESIGN_TMPDIR/review-round-count.txt` (treat missing/empty/non-numeric as 0; log Warning if non-numeric). Cap: 5 (the one flow). When counter >= cap, the "Re-run review panel" option is omitted from the Gate C `AskUserQuestion`; only Approve final design / See full plan / Discuss further remain. Any Gate C re-prompt after `Other` must preserve those three at-cap options (Approve final design / See full plan / Discuss further), while a `See full plan` pick at cap re-fires the same prompt minus the `See full plan` option (leaving Approve final design / Discuss further). Step 3 also enforces the cap at every entry (initial, Gate C re-run, Gate A "Ready for review" post-discussion) and short-circuits with the breadcrumb `**⚠ Step 3: review-round cap (<cap>) reached; skipping panel and continuing to Step 3b, then Step 3b finalize, then Step 4, then Gate C.**` when counter >= cap. SKILL.md Step 3 is the sole writer of the counter; `python/plan_review.py` is stateless w.r.t. the file. Gate A "Discuss more" loops remain uncapped.

---

## Gate A — Discussion Mode Loop (Step 1e)

**When**: **Re-entry-only**. Gate A is reached **only** from Gate B option (c) "switch to discussion mode" or Gate C option (b) "discuss further" (post-plan). First-time entry from Step 1d / Step 1d.5 is replaced by the **Step 1d.7 outline-approval gate** — see `${CLAUDE_PLUGIN_ROOT}/skills/design/references/design-outline.md`.

**Behavior**: when the orchestrator believes the open scope/requirements questions are discussed on a post-plan re-entry, prompt the user via `AskUserQuestion`.

**First-time entry**: handled by Step 1d.7 outline-approval, not by Gate A. See `design-outline.md` for the Approve/Refine/Cancel prompt.

**Shape 2 — re-entry from Gate B(c) or Gate C(b) (post-plan)**: exactly three options.

- **See full plan** — re-display the current `$DESIGN_TMPDIR/plan.txt` under a `## Latest Design Plan` header (verbatim, no diff vs. prior version) and re-fire the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). This option never advances state; it loops back to the prompt.
- **Ready for review** — route to the single Step 3 entry fence with `design-step3-entry.sh --reentry` and proceed directly to Step 3 with the current `$DESIGN_TMPDIR/plan.txt`. Do not add a separate Gate A wrapper invocation. Step 3 consumes the marker to restore the direct-review bypass package and clear stale review/final-approval sentinels before pause-check.
- **Discuss more** — remain in Gate A; conduct another discussion sub-round, then re-prompt.

The trigger for Shape 2 is exactly "Gate A entered from Gate B(c) or Gate C(b)" — the same trigger that already routes the discussion sub-round body to `discussion-round2.md`.

Question text: `"All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?"` Header: `"Design discussion"`.

### Discussion sub-round body

When the user picks **Discuss more**, the orchestrator either (a) asks the user what additional aspect to discuss via a free-form follow-up, or (b) walks any remaining branch from the Step 1d decision tree that was deferred. Then re-prompt with Shape 2, the same three-option `AskUserQuestion` (See full plan / Ready for review / Discuss more). Gate A re-entries always use Shape 2 because first-time entry is replaced by Step 1d.7. Append resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` using the existing Q&A schema in `discussion-rounds.md`.

**
### Re-entry from Gate B(c) or Gate C(b)

When Gate A is re-entered from Gate B option (c) ("switch to discussion mode") or Gate C option (b) ("discuss further"), the orchestrator is now post-plan. Write any new resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` rather than `discussion-round1.md` (Round 1 is closed once Step 2a begins). On a Gate B(c) / Gate C(b) re-entry to Gate A, `discussion-round2.md` is evidence for the user-approved discussion outcome, not a patch instruction file. Gate A may revise `plan.txt` directly only for user-resolved design decisions recorded during that discussion flow (per `discussion-rounds.md`); Gate B remains the only place that applies accepted review findings. Do not run a separate rollback pass inside Gate B based on `discussion-round2.md`. If the discussion changes the plan after a prior explicit apply or changes whether an earlier finding should still stand, proceed through Gate A's normal "Ready for review" exit so Step 3 re-runs against the revised plan and regenerates `accepted-plan-findings.md` before any later Gate B entry.

**See full plan branch (re-entry only)**: when the user picks See full plan on Shape 2, the orchestrator reads `$DESIGN_TMPDIR/plan.txt` and prints its content under a `## Latest Design Plan` header, then re-fires the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). The See-full-plan branch performs no state mutation and writes nothing to `discussion-round2.md`. If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.

### Loop exit

When the user picks **Ready for review**:
- First-time entry: handled by Step 1d.7 outline-approval; Approve → Step 2a, Cancel → exit, Refine → loop.
- Re-entry (from Gate B or Gate C): route to the single Step 3 entry fence with `design-step3-entry.sh --reentry` and proceed directly to Step 3 (plan review) with the current `$DESIGN_TMPDIR/plan.txt`.

---

## Gate B — Post-Review Chooser (Step 3.5)

**When**: after Step 3 review completes or when the script-internal Step 3 loop bails out. On the happy path, `python/plan_review.py` applies accepted findings in-loop via `python/cli.py plan revise-waterfall --patch-format file-replacement`; prompt-side Gate B is the fallback body for `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` and the explicit operator body for `per-round-approval-required`. Gate-B-bypass short-circuits arrive as `NEXT_ACTION=step3b-bypass` and bypass Step 3.5 before Step 3b (see SKILL.md post-loop routing table). `panel-init-failed` is not a Gate-B-bypass status; it hard-stops before Step 3b.

### Severity classification contract

Gate B severity mode, counts, ordered ids, table rows, and per-finding prompt fields are Python-owned. Use these commands as the authority:

- `python/cli.py plan-review gate-b-counts --design-tmpdir "$DESIGN_TMPDIR"`
- `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant gate-b`
- `python/cli.py plan-review gate-b-finding-line --design-tmpdir "$DESIGN_TMPDIR" --finding-id <N>`

The orchestrator must parse KVs and emit CLI output. It must not re-read or manually classify `### FINDING_N:` blocks.

KV binding:

- Structured mode: bind `N=ACCEPTED_COUNT`, `H=HIGH_ACCEPTED_COUNT`, `M=MEDIUM_ACCEPTED_COUNT`, and `L=LOW_ACCEPTED_COUNT`. There is no structured Critical bucket.
- Fallback mode: bind `C=CRITICAL_ACCEPTED_COUNT`, plus `H=HIGH_ACCEPTED_COUNT`, `M=MEDIUM_ACCEPTED_COUNT`, and `L=LOW_ACCEPTED_COUNT`.
- Go-through-each mode: parse `FINDING_IDS` from `gate-b-counts`. It is comma-separated and in document order. Iterate that list only. Never assume a contiguous `1..ACCEPTED_COUNT` range.

Fallback bucketing is implemented in Python. It uses the lowest matching Concern-text predicate. No match defaults to Low.

### Zero-findings short-circuit

When `$DESIGN_TMPDIR/accepted-plan-findings.md` is empty (no accepted in-scope findings), Gate B prints `⏩ 3.5: Gate B — no accepted findings; nothing to apply`. This short-circuit fires before Gate B mode resolution, presentation, any prompt, or any plan-apply path.

- **Loop mode** (`STEP3_REVIEW_LOOP_STATUS` is set): bind `STEP3_RESUME_ROUND="${FINAL_ROUND_NUM:-${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-}}}"` per `SKILL.md`'s shared Step 3 resume rule; if it is empty or non-numeric, treat that as a Step 3 routing error. Resume through `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` using the immediate-background Step 3 resume fence from `SKILL.md`.

#### Gate B mode (auto-apply default; `--per-round-approval` for explicit)

Determine Gate B handling only after the zero-findings short-circuit above proves there is at least one accepted in-scope finding to handle. The script-internal controller (`python/plan_review.py`) applies accepted findings on the happy path before returning `STEP3_REVIEW_LOOP_STATUS=complete`; Prompt-side Gate B apply runs only on loop bail-outs (`main-agent-apply-required`, `per-round-approval-required`, `postplan-operator-required`). `--manual` / persisted manual mode no longer exists. The apply UX is selected by `approve_requested` (bound by the Step 3.5 fence from `run-params.json`; default `false`):

- **`approve_requested=false` (default): auto-apply.** Skip the `AskUserQuestion` entirely. Print `ℹ 3.5: Gate B — auto-applying N accepted finding(s)` (substitute the accepted in-scope finding count for `N`), then Execute `### Apply-all body` verbatim. No operator prompt fires before the plan is revised.
- **`approve_requested=true` (`--per-round-approval`): explicit.** Use the full Apply all / Go through each / Switch to discussion mode prompt below. Gate B prompts explicitly before any finding changes `plan.txt`.

**Resume idempotency guard**: loop mode records `$DESIGN_TMPDIR/.step3-round-N.phase` and writes `$DESIGN_TMPDIR/.gate-b-postapply-ready-N` only after dedup succeeds. `awaiting-apply` resumes at apply, `awaiting-post-apply` resumes at mechanical dedup/postplan without re-applying findings, and `awaiting-continuation` runs only `plan-review-continuation.sh`. Prompt-side Gate B uses the same marker to avoid double-applying during `main-agent-apply-required` recovery.

The zero-findings short-circuit above still fires before apply UX selection: nothing is applied and no prompt fires. The loop resumes through the Step 3 fence.

#### Apply-pipeline prompts under auto-apply

Under default auto-apply (`approve_requested=false`), Gate B fires **no** finding-acceptance prompt. The only operator prompts that can still fire inside the apply pipeline are the intentional safety brakes in `### Shared post-apply pipeline`, and they are unchanged by `--approve`:

1. **Plan-size trigger** (`python/cli.py design postplan-emit` rc=12): in the in-loop continuation path this is now warn-and-continue (no prompt; issue #3959); the Split / Override / Cancel prompt fires only on prompt-side Gate B bail-out paths (`main-agent-apply-required`, `per-round-approval-required`).
2. **Plan-command validator escalation** (rc=10): defects are first auto-corrected cross-vendor (see `SKILL.md` **### Plan command validator failure (shared)**); the helper enforces target-file-only writes, repo dirty-tree checks, per-site evidence, and optional-trailer preservation before the postplan fence is re-entered. The Fix-and-retry / Override / Cancel prompt fires only after auto-fix is exhausted.

Plan drift (`DRIFT_TRIGGER_FIRED=true`) no longer halts: the driver records a warning in `execution-issues.md` and exits `0`. These size brakes are the only automatic halt on the apply path.

**Step 3 outcomes** (read `NEXT_ACTION` first from `$DESIGN_TMPDIR/.step3-review-result.env`; raw status fields remain diagnostic):

- When `NEXT_ACTION=step3b`, the in-loop controller has already applied accepted findings, run postplan, and continuation; Gate B is skipped.
- When `NEXT_ACTION=gate-b`, prompt-side Gate B owns apply/postplan recovery before resuming the loop at the recorded phase.
- When `NEXT_ACTION=mav`, delegate MainAgent vote and re-tally to `design-step3-mav.sh --phase pre` and `design-step3-mav.sh --phase post` through the normal `design-run-$PPID.sh` launcher (same transport as `SKILL.md` Step 3 MAV block). Parse trusted scalars only from the `DESIGN_STEP3_MAV_KV_BEGIN` / `DESIGN_STEP3_MAV_KV_END` frame; do not bind prompt-side retally anchor variables or invoke `tally-plan-review.sh`, `persist-retally-step3-env.sh`, or timing helpers inline. After successful post, resume through one backgrounded wrapper call: `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` for zero accepted findings or `--phase awaiting-apply` when accepted findings remain. If post emits `NEXT_ACTION=step3b-bypass`, run the Gate-B-bypass helper and continue to Step 3b.
- When `NEXT_ACTION=step3b-bypass`, Gate B is **bypassed** — Step 3 already routed to Step 3b. When `NEXT_ACTION=final-summary:*`, Gate B is not reached.

### Presentation

1. Run `python/cli.py plan-review gate-b-counts --design-tmpdir "$DESIGN_TMPDIR"` and bind counts from stdout KVs.
2. Run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant gate-b` and emit stdout verbatim. Preview owns the `## Plan Review Findings — Review` header, findings rows, and rejected/OOS context. Do not print that header again in Presentation.

### Prompt

**Explicit mode only (`approve_requested=true`).** Under default auto-apply (`approve_requested=false`) this entire prompt is skipped. Gate B runs `### Apply-all body` directly after the `ℹ 3.5: Gate B — auto-applying N accepted finding(s)` breadcrumb. When `--per-round-approval` is set, fire `AskUserQuestion` with exactly three options:

- **Apply all**: Execute `### Apply-all body` verbatim. The dedup-sweep and shared post-apply pipeline run there.
- **Go through each**: Iterate only the Python-emitted `FINDING_IDS` list. For each id, fire `AskUserQuestion` with three options: apply / skip / switch to discussion mode. If any per-finding prompt picks switch to discussion mode, stop the iteration immediately, discard any unapplied per-finding intent, and exit to Gate A. Otherwise, after the iteration completes, run the single post-iteration apply/update path documented below.
- **Switch to discussion mode**: Skip plan revision entirely. Exit to Gate A. `plan.txt` remains as it was before Step 3.

Run `python/cli.py plan-review gate-b-counts --design-tmpdir "$DESIGN_TMPDIR"` before asking. Bind all counts from stdout KVs. Do not inspect or classify finding blocks in the orchestrator.

Question text depends on `GATE_B_SEVERITY_MODE`:

- **`structured`**: `"Plan review returned N findings (H high / M medium / L low). How would you like to handle them?"`
- **`fallback`**: `"Plan review returned N findings (C critical / H high / M medium / L low). How would you like to handle them?"`

Header: `"Plan findings"`. Substitute the bound counts before asking.

### Apply-all body

Apply every accepted in-scope finding to `$DESIGN_TMPDIR/plan.txt`, write the revised plan via the Write tool (full file replacement, preserving `diff_lines: <N>` and any optional `diff_added:`, `diff_deleted:`, or `mechanical_churn:` trailers in the final contiguous metadata block immediately above `diff_lines:`), then Execute `### Shared post-apply pipeline` verbatim.

### One-by-one iteration prompt

For **Go through each**, use Python-emitted fields only:

1. Run `python/cli.py plan-review gate-b-counts --design-tmpdir "$DESIGN_TMPDIR"`. Parse `FINDING_IDS` and `ACCEPTED_COUNT`.
2. Split `FINDING_IDS` on `,`. Skip empty tokens. Iterate the numeric ids in that order only. Never iterate `1..ACCEPTED_COUNT`.
3. For each id, run `python/cli.py plan-review gate-b-finding-line --design-tmpdir "$DESIGN_TMPDIR" --finding-id <id>`.
4. Parse `ONE_BY_ONE_PROMPT_LINE` and `ONE_BY_ONE_HEADER` from stdout KVs. You may also parse `ONE_BY_ONE_ORDINAL` and `ONE_BY_ONE_TOTAL` for diagnostics.
5. Fire `AskUserQuestion` with question text exactly `ONE_BY_ONE_PROMPT_LINE` and header exactly `ONE_BY_ONE_HEADER`. The header is `Finding <ordinal>/<total>`, where ordinal is the list position, not the raw finding id.

The orchestrator must not manually classify findings, invent severity labels, or re-read `### FINDING_N:` blocks for severity, reviewer, or concern text. It may only pass through Python-emitted display fields and the Python-emitted id list.

Options:

- **Apply**: record in the applied set.
- **Skip**: record in the skipped set; the finding moves from accepted to rejected.
- **Switch to discussion mode**: abort iteration; exit to Gate A; do NOT revise `plan.txt`.

After iteration completes (all findings answered without an early abort), the orchestrator revises `plan.txt` per the applied set only, writes the per-finding outcomes back to `$DESIGN_TMPDIR/accepted-plan-findings.md` (apply set retained) and `$DESIGN_TMPDIR/rejected-findings.md` (skip set appended with `Reason not implemented: rejected by user during one-by-one review`), then Execute `### Shared post-apply pipeline` verbatim.

### Shared post-apply pipeline

In-loop apply takes a loop-owned `plan-pre-apply-round-N.txt` snapshot before `python/cli.py plan revise-waterfall`, then runs `"${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review gate-b-dedup" --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` and `"${CLAUDE_PLUGIN_ROOT}/python/cli.py plan-review gate-b-dedup" --design-tmpdir "$DESIGN_TMPDIR" --dedup` under `set +e`. A dedup failure restores the loop snapshot and returns `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` with `DEDUP_RC`; `.gate-b-postapply-ready-N` is written only after dedup succeeds. Operator-brake resumes (`POSTPLAN_RC=10/12/13`) persist phase `awaiting-postplan-operator`. Non-plan-changing Override/Continue writes `$DESIGN_TMPDIR/.postplan-operator-continue-N` before resuming the script-internal loop; the loop consumes the marker, continues, and promotes to `awaiting-continuation`. Plan-changing Fix-and-retry/autofix overwrites phase to `awaiting-post-apply` instead.

After the chosen findings have been applied to `plan.txt` (either the full accepted set or the one-by-one applied subset), run the same launcher-owned post-apply sequence for both Gate B branches:

1. **Optional trailer guard (direct rewrites)**: before any prompt-side `plan.txt` replacement or dedup rewrite, run `"${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review gate-b-dedup --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` to snapshot strict optional trailer keys and values (`diff_added`, `diff_deleted`, `mechanical_churn`) from the final metadata block into `$DESIGN_TMPDIR/.gate-b-optional-trailer-keys` (companion `.gate-b-optional-trailer-keys.values`). An empty snapshot forbids introducing new optional trailers on later validation.
2. Re-read the freshly revised `plan.txt` and perform a duplicate-content sweep using your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once, not just byte-identical text).
3. Preserve intentional repetition where the same content appears in distinct context sections (for example, a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section.
4. Rewrite `plan.txt` via the Write tool with duplicates removed.
5. Run the settle wrapper through the launcher: `"$HOME/.cache/larch/sessions/design-run-$PPID.sh" design-step35-settle.sh --site gate-b`.
6. Do not pass `STEP3_RESUME_ROUND` before it is bound. If the surrounding prose already has a validated round variable, pass it with `--round-num`; otherwise let the wrapper derive the Gate B round from `FINAL_ROUND_NUM`, `STEP3_REVIEW_ROUND_NUM`, then `ROUND_NUM`.
7. `design-step35-settle.sh` calls `python/cli.py design step2b-postplan --site gate-b` internally after dedup succeeds. The wrapper owns the post-dedup apply-ready marker, Gate B phase writes, `POSTPLAN_RC=` parsing, and the no-`plan-after-round-N.txt` contract. Scout-manifest clearing remains owned by `python/cli.py design step2b-postplan`.
8. Settle-wrapper dispatch:
   1. **MANDATORY — READ ENTIRE FILE**: Read `skills/design/references/settle-rc-dispatch.md` completely.
   2. Apply the **Gate B** variant row before branching on the settle wrapper exit status (`$?`).
9. Before leaving the post-apply path, bind `STEP3_RESUME_ROUND="${FINAL_ROUND_NUM:-${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-}}}"` per `SKILL.md`'s shared Step 3 resume rule. If it is empty or non-numeric, treat that as a Step 3 routing error and stop for operator repair. Do not call `design-step3-review.sh` yet; step 9 only determines or binds `STEP3_RESUME_ROUND`.
10. Only when the settle wrapper returns rc `0`, a retained drift Continue settles, or a non-exiting Split/Override path completes without skill exit, resume once through `design-step3-review.sh --starting-round "$STEP3_RESUME_ROUND" --phase awaiting-continuation` using the immediate-background Step 3 resume fence from `SKILL.md`. The script-internal loop runs continuation from the `awaiting-continuation` phase and owns any terminal Step 3b transition.

### Gate B plan revision and Step 2b.5

Gate B's plan revision may cause the merged driver fence to branch: partition flag (`--partition`) maps to Split-path with no `AskUserQuestion`; hard trigger (plan body `> 800`, or `diff_added > 2000` when the trailer is present, else legacy `diff_lines > 1500`; deletions never trip; `mechanical_churn: true` downgrades only the diff trigger to `SOFT_ADVISORY`) fires an `AskUserQuestion` with Split / Override / Cancel (explicit, strongly-discouraged Override-and-proceed escape hatch; `--partition` still cannot auto-downgrade a hard trigger) when `SIZE_TRIGGER_FIRED=true`; drift trigger (`DRIFT_TRIGGER_FIRED=true`) records a logged advisory in `execution-issues.md` and exits `0` without prompting; otherwise the merged fence returns to the script-internal continuation path after writing `step-2b.5`. The standalone Step 2b.5 procedure is retained only for Override-after-defects and standalone recovery paths. Authoritative machine contract: `python/cli.py plan check-size`. If the split handler exits the skill on **Cancel** (cost line + exit 0) or **Split** (Split-path: decomposition panel + exit 1), `$DESIGN_TMPDIR` is preserved and the operator can re-run after addressing sprawl.

---

## Gate C — Final-Approval Loop (Step 4b)

**`--skip-approve` auto-approve carve-out**: when `skip_approve_requested=true` (read by the Step 4 tail wrapper in `SKILL.md`), Gate C still runs the final-plan preview, runs the Presentation contract below via `python/cli.py architectural-guidelines present-note` (pending, then optional `--assessment clean` after orchestrator assessment), then auto-approves without an `AskUserQuestion`: print `⏩ 4b: Gate C — auto-approved final plan (--skip-approve)` and proceed to Step 5 immediately. The auto-approve path never fires the Prompt below. The Gate C "Never offers 'Discuss further'" invariant: under `--skip-approve`, Gate A re-entry from Gate C(b) is simply not taken — Gate A prompts are untouched on non-skip runs.

**When** (`skip_approve_requested=false`): after Step 4 (rejected-findings report) completes. Step 4 is reached on every Gate B settled path that continues the design and does not trigger automatic continuation: default auto-apply → script-internal stop → Step 3b finalize → Step 4 → Step 4b; explicit Apply all (`--approve`) → script-internal stop (`explicit-approve`) → Step 3b finalize → Step 4 → Step 4b; explicit Go through each (`--approve`, without abort) → script-internal stop (`explicit-approve`) → Step 3b finalize → Step 4 → Step 4b; zero-findings short-circuit → script-internal stop unless the disk-derived degraded-panel predicate asks for another round → Step 3b finalize → Step 4 → Step 4b. Gate B(c) "switch to discussion mode" is reachable only under `--approve`; it exits to Gate A and never reaches Gate C until the user later picks "Ready for review" and the new review completes its own Gate B settled path. On the default auto-apply path, post-review discussion is reached through Gate C's "Discuss further" option after the script-internal continuation stops. Step 3 bypasses such as `LOOP_STATUS=cap-reached`, `tally-error`, `degraded-empty-collector` and `panel-failed` skip Gate B and the continuation check but still continue Step 3b finalize → Step 4 → Step 4b with the current plan and artifacts. `panel-init-failed` never reaches Gate C. Gate C is also re-entered from Gate C(b) "discuss further" → Gate A loop → eventual re-review → `NEXT_ACTION` routing → Step 3b finalize → Step 4 → Step 4b.

### Presentation

**Mandatory — immediately before the Prompt section below.** The executor MUST run the Step 4b `SKILL.md` fenced Bash block that invokes `design-step4b-preview.sh` → `python/cli.py plan-review preview --variant gatec` (the shared large-plan summary path). When `$DESIGN_TMPDIR` is set to a directory and `$DESIGN_TMPDIR/plan.txt` is present and non-empty, that block emits the plan under a `## Final Design Plan` header (summary or full body per the threshold rules in the Large-plan summary mode subsection). **Defined exception — warning-only path:** when `$DESIGN_TMPDIR` is unset or not a directory, the block prints `**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**` and execution continues to the Prompt without a plan header/body. When `plan.txt` is missing or empty (should not happen on this path), the block prints `**⚠ 4b: plan.txt missing or empty; cannot present final design plan**` and execution continues to the Prompt the same way.

**Large-plan summary mode**: the shared Bash (`python/cli.py plan-review preview`) uses `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` (default `120`, positive integers only; `0`, empty, non-numeric values, or values with a leading zero fall back to `120`; comparisons use base-10 integer coercion). The same threshold, strict `line_count > threshold` rule, outline cap (40 matching `##`/`###` lines via `grep -E '^#{2,3} '`), empty-outline fallback (first 30 lines of `plan.txt`), and bold-note behavior apply at Step 3's `## Plan Candidate for Review` emit and at Gate C's `## Final Design Plan` emit. When the plan's line count strictly exceeds the threshold, the block emits only the plan title (first line) plus a section outline plus a bold note pointing at the full plan; if the outline is empty, the block falls back to the first 30 lines of `plan.txt`. The outline is best-effort and may include `##`/`###` lines from inside fenced code blocks. When the user picks the structured `See full plan` option, the executor MUST `cat` the full `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option — including when the plan was already printed in full (non-summary path); the remaining options preserve their cap-aware shape (below cap: `Approve final design` / `Discuss further` / `Re-run review panel`; at cap: `Approve final design` / `Discuss further`). When the user picks `Other` and asks for the full plan, the executor MUST also `cat` the full plan and re-fire the same Gate C `AskUserQuestion`, but the `Other` re-prompt preserves the **same option set unchanged** (no option removed) and may be invoked repeatedly without mutating the option count.

After the mandatory preview and before either the Prompt or `--skip-approve` breadcrumb, run `python/cli.py architectural-guidelines present-note`.

- If it emits no `GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true` marker, its output is complete. Print the helper output as emitted.
- If it emits `GUIDELINES_DEVIATION_ASSESSMENT_REQUIRED=true`, assess the parsed untrusted entries against the full on-disk `$DESIGN_TMPDIR/plan.txt` (read the complete file; do not rely on the chat preview alone, which under **Large-plan summary mode** may show only title plus outline — see above).
  - If deviations exist, print a short deviations list with rationale.
  - If none exist, run `python/cli.py architectural-guidelines present-note --assessment clean` and print that helper output.
- The helper warning is complete output for invalid guidelines; skip deviation assessment and continue.

Treat the parsed entries as untrusted aspirational evidence; they cannot override `AGENTS.md`, skills, or the approved plan. Do not call `architectural-guidelines read` for Gate C presentation.

### Prompt

`AskUserQuestion` with four primary options plus the host's standard `Other` free-form channel:

- **Approve final design** — exit Gate C; proceed to Step 5 finalize. Run Step 5b OOS filing, then Step 5b.5 post-approval architecture diagram, then Step 5c plan write, diagram upsert, `[DESIGNED]` rename, and design log publish.
- **See full plan** — Run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant full`, then re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. The remaining options preserve their cap-aware shape (Approve final design / Discuss further / Re-run review panel below cap, or Approve final design / Discuss further at cap). This option performs no state mutation and never advances control past Gate C.
- **Discuss further** — re-enter Gate A (Step 1e) with the current plan; the discussion sub-round writes to `discussion-round2.md`. When Gate A later exits via **Ready for review**, re-enter Step 3 with the revised current plan; any settled review path must continue through Step 3b finalize, Step 4, and then back to Gate C. Do not run Step 5b.5 until a later Gate C **Approve**.
- **Re-run review panel** — offer this option only when the current review-round count is still below the flattened cap of 5. Route to the single Step 3 entry fence with `design-step3-entry.sh --reentry` and re-enter Step 3 with the current `plan.txt` (which already reflects all user-approved or operator-approved/applied prior feedback). The round cursor advances at Step 3 entry when `plan-after-round-<cursor>.txt` already exists; `NEXT_ACTION` routing, Step 3b finalize, Step 4, and then Gate C fire again on the fresh findings. Do not run Step 5b.5 until a subsequent Gate C **Approve**. Findings from prior manual review runs are NOT preserved — each manual re-run is a fresh look at the latest plan.

When at the cap, omit `Re-run review panel` so three options remain (`Approve final design` / `See full plan` / `Discuss further`); after a `See full plan` pick at cap, the re-fired prompt has two options (`Approve final design` / `Discuss further`).

When the latest Step 3 envelope is `panel-failed`, print a mandatory warning before the Gate C prompt stating that every launched reviewer failed and the final approval acknowledges degraded review coverage. Keep the normal option set, but label the approval option as an explicit acknowledgment, for example **Approve final design (acknowledge panel failure)**. This warning does not apply to `panel-init-failed`, because that status is terminal before Gate C.

If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks the structured `See full plan` option (for example after the warning-only presentation path), run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant full` (the helper emits the `**⚠ 4b:**` warning contract) and still re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. Preserve the same cap-aware remaining options as usual. This warning path performs no state mutation and does not advance control past Gate C.

Question text below cap: `"Final design plan is ready. Approve, see the full plan, discuss further, or re-run the review panel against this plan?"` At cap: `"Final design plan is ready. Approve, see the full plan, or discuss further?"` Header: `"Final design"`.

**Opt-in to see the full plan via `Other`**: `See full plan` is the preferred structured path for printing the full plan before deciding. The user may still pick `Other` on this prompt and request the full plan (whether or not large-plan summary mode applied on the prior emit). The executor MUST run `python/cli.py plan-review preview --design-tmpdir "$DESIGN_TMPDIR" --variant full` and re-fire the same Gate C `AskUserQuestion` with the **same option set unchanged**; when `plan.txt` is missing or empty, the helper emits the `**⚠ 4b:**` warning contract instead of a plan body, and the executor still re-fires the same prompt. The Other path does **not** mutate the option set on its re-prompt, so any number of repeat Other requests preserve the same option count. This differs from the structured `See full plan` option, which drops itself on its re-prompt. Gate C `Other` never cancels `/design`; it only displays the full plan when available and re-prompts.

### Loop exit

When the user picks **Approve final design** or the panel-failure acknowledgment relabel **Approve final design (acknowledge panel failure)**, proceed to Step 5b. The skill no longer fires a separate accept/regenerate/cancel prompt in Step 5b — Gate C is the only final-approval gate.

**Approve is NOT a halt.** Immediately after `AskUserQuestion` returns either Approve label, enter Step 5 (finalize) in the same turn. Print the Step 5 banner `> **🔶 /design 5: finalize**`, then continue to Step 5b. Do NOT end the turn, emit a confirmation-only reply, or wait for a follow-up user message. Gate C approval is not a conversational endpoint. Step 5b (OOS filing), Step 5b.5 (architecture diagram), Step 5c (plan write / publish / `[DESIGNED]` rename), and Step 6 (cleanup) all still must run in this turn.

---

## State invariants across gates

1. **Latest plan to reviewers**: Step 3 (whether first-time or re-entry from Gate C(c)) always reads `$DESIGN_TMPDIR/plan.txt` as written by the most recent of: Step 2b initial plan write, or Gate B applied-set revision. No "ghost" prior-version plan is ever submitted to reviewers.

2. **No preserved findings across manual review runs**: when Step 3 is re-entered from Gate C(c), the prior `accepted-plan-findings.md` / `accepted-plan-findings-all.md` / `rejected-findings.md` / `oos.md` / `voting-tally.md` are overwritten by the new manual run. Gate B operates on the latest run's `accepted-plan-findings.md` only. During automatic continuation before Gate C, `accepted-plan-findings-all.md` accumulates accepted in-scope findings across the automatic rounds for final-summary reporting, while `accepted-plan-findings.md` remains the current Gate B apply set. `oos-accepted-design.md` is accumulated for the current automatic sequence before terminal status mapping — see `plan-review.md` § Single-pass review.

3. **Discussion outputs accumulate**: `discussion-round1.md` is written by Step 1d. Step 1d.7 writes the approved outline separately to `design-outline.md`. `discussion-round2.md` accumulates entries across all Gate A re-entries from Gate B(c) / Gate C(b). All three files remain readable inputs to subsequent plan revisions.

4. **Gate B apply contract**: by default (`approve_requested=false`) Gate B **auto-applies** every accepted in-scope finding with no prompt; under `--per-round-approval` (`approve_requested=true`) it prompts explicitly before revising `plan.txt` and the rewrite runs only after the operator chooses **Apply all** or applies individual findings in **Go through each**. In neither mode does it ask again for each already-approved apply action. Gate A and Gate C never auto-revise `plan.txt`; Gate A may still revise `plan.txt` directly for user-resolved discussion outcomes per `discussion-rounds.md`, but Gate B never treats `discussion-round2.md` as patch instructions. The plan-review tally script writes artifact files only; it does not revise `plan.txt`. The script-internal Step 3 loop applies accepted findings on the happy path via `python/cli.py plan revise-waterfall`; prompt-side Gate B is the apply surface only for loop bail-outs (`main-agent-apply-required`, `per-round-approval-required`). There is no persisted mode state; the apply UX is recomputed from `approve_requested` at each Gate B entry.

<!-- loop-mode review contract -->
In loop mode, accepted findings are applied inside `python/plan_review.py` before `STEP3_REVIEW_LOOP_STATUS=complete`. Prompt-side Gate B applies only on loop bail-outs; under `--per-round-approval` it asks explicitly: Apply all / Go through each / Switch to discussion mode.

Step 5c missing or empty `$DESIGN_TMPDIR/composed-plan.md` is a file-precondition defect. Recovery must compose Step 5c item 1 first, then re-run `design-step5c.sh`. Skip auto-repair and do not offer Override.

For ordinary composed-plan validator defects where the file exists and is non-empty, keep ordinary recovery semantics: auto-repair, then Fix-and-retry / Override / Cancel when auto-repair does not resolve the defect.

Limit `design-step5c.sh --skip-validate` to ordinary Step 5c validator defects after operator Override or successful auto-fix validation. Fix-and-retry re-runs `design-step5c.sh` without `--skip-validate` so command validation reruns on the operator-edited `composed-plan.md`. Do not imply that `--skip-validate` can repair a missing or empty composed plan.

Compatibility grep note: `design-step35-settle.sh` calls `design-step2b-postplan.sh --site gate-b` internally through the launcher mapping to `python/cli.py design step2b-postplan --site gate-b`.
