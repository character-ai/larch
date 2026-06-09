# Approval Gates Reference

**MANDATORY — READ ENTIRE FILE before composing Gate A discussion prose, Gate B findings presentation and apply-all rewrite, or Gate C approval prose: `skills/design/references/readability-style.md`.**

**Consumer**: `/design` Step 1e (Gate A — discussion-mode loop), Step 3.5 (Gate B — post-review chooser), and Step 4b (Gate C — final-approval loop).

**Contract**: owns the three user-facing approval gates that bracket the design review pipeline. Gate A is the **post-plan re-entry** discussion prompt, Gate C is the final approval prompt, and Gate B applies accepted in-scope findings — by default **auto-applying** with no prompt (`approve_requested=false`), or via a 3-option `AskUserQuestion` (Apply all / Go through each / Switch to discussion mode) when `--per-round-approval` is set (`approve_requested=true`). Gate A and Gate C use `AskUserQuestion` on their reachable paths (Gate C asks only when `skip_approve_requested=false`; see **Gate C** below); Gate B uses `AskUserQuestion` on its non-empty-findings path only under `--per-round-approval`. Reviewers always see the latest plan with all user-approved or operator-approved/applied prior feedback applied.

**When to load**: before executing Step 1e, Step 3.5, or Step 4b.

**Binding convention**: single normative source for the three gate prompts, their per-tier behavior, the severity-classification rubric used in Gate B, and the loop semantics between A/B/C.

**Cross-tier invariant**: Gates apply uniformly across SIMPLE and HARD tiers. Gate B reads `accepted-plan-findings.md` produced by the full `plan-review.md` panel on both tiers. The Gate B apply-UX behavior (auto-apply by default, explicit under `--per-round-approval`) applies uniformly across both tiers.

## Review-round cap

Gate C reads `$DESIGN_TMPDIR/review-round-count.txt` (treat missing/empty/non-numeric as 0; log Warning if non-numeric) and `design_classification` via `read-design-classification.sh`. Cap: 5 (both tiers). When counter >= cap, the "Re-run review panel" option is omitted from the Gate C `AskUserQuestion`; only Approve final design / See full plan / Discuss further remain. Any Gate C re-prompt after `Other` must preserve those three at-cap options (Approve final design / See full plan / Discuss further), while a `See full plan` pick at cap re-fires the same prompt minus the `See full plan` option (leaving Approve final design / Discuss further). Step 3 also enforces the cap at every entry (initial, Gate C re-run, Gate A "Ready for review" post-discussion) and short-circuits with the breadcrumb `**⚠ Step 3: review-round cap (<cap>) reached for <tier>; skipping panel and continuing to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4, then Gate C.**` when counter >= cap. SKILL.md Step 3 is the sole writer of the counter; `plan-review-loop.sh` is stateless w.r.t. the file. Gate A "Discuss more" loops remain uncapped.

---

## Gate A — Discussion Mode Loop (Step 1e)

**When**: **Re-entry-only**. Gate A is reached **only** from Gate B option (c) "switch to discussion mode" or Gate C option (b) "discuss further" (post-plan). First-time entry from Step 1d / Step 1d.5 is replaced by the **Step 1d.7 outline-approval gate** — see `${CLAUDE_PLUGIN_ROOT}/skills/design/references/design-outline.md`.

**Behavior**: when the orchestrator believes the open scope/requirements questions are discussed on a post-plan re-entry, prompt the user via `AskUserQuestion`.

**First-time entry**: handled by Step 1d.7 outline-approval, not by Gate A. See `design-outline.md` for the Approve/Refine/Cancel prompt.

**Shape 2 — re-entry from Gate B(c) or Gate C(b) (post-plan)**: exactly three options.

- **See full plan** — re-display the current `$DESIGN_TMPDIR/plan.txt` under a `## Latest Design Plan` header (verbatim, no diff vs. prior version) and re-fire the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). This option never advances state; it loops back to the prompt.
- **Ready for review** — write `: > "$DESIGN_TMPDIR/.step3-reentry"` and proceed directly to Step 3 with the current `$DESIGN_TMPDIR/plan.txt` (Step 2a sketches and Step 2a.5 dialectic are NOT re-run on re-entry per the existing loop-exit semantics below). Step 3 consumes the marker to restore the direct-review bypass package and clear stale review/final-approval sentinels before pause-check.
- **Discuss more** — remain in Gate A; conduct another discussion sub-round, then re-prompt.

The trigger for Shape 2 is exactly "Gate A entered from Gate B(c) or Gate C(b)" — the same trigger that already routes the discussion sub-round body to `discussion-round2.md`.

Question text: `"All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?"` Header: `"Design discussion"`.

### Discussion sub-round body

When the user picks **Discuss more**, the orchestrator either (a) asks the user what additional aspect to discuss via a free-form follow-up, or (b) walks any remaining branch from the Step 1d decision tree that was deferred. Then re-prompt with Shape 2, the same three-option `AskUserQuestion` (See full plan / Ready for review / Discuss more). Gate A re-entries always use Shape 2 because first-time entry is replaced by Step 1d.7. Append resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` using the existing Q&A schema in `discussion-rounds.md`.

**Per-tier behavior**: Gate A fires only on re-entry. First-time entry across both tiers (SIMPLE / HARD) is handled by Step 1d.7 outline-approval.

### Re-entry from Gate B(c) or Gate C(b)

When Gate A is re-entered from Gate B option (c) ("switch to discussion mode") or Gate C option (b) ("discuss further"), the orchestrator is now post-plan. Write any new resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` rather than `discussion-round1.md` (Round 1 is closed once Step 2a begins). On a Gate B(c) / Gate C(b) re-entry to Gate A, `discussion-round2.md` is evidence for the user-approved discussion outcome, not a patch instruction file. Gate A may revise `plan.txt` directly only for user-resolved design decisions recorded during that discussion flow (per `discussion-rounds.md`); Gate B remains the only place that applies accepted review findings. Do not run a separate rollback pass inside Gate B based on `discussion-round2.md`. If the discussion changes the plan after a prior explicit apply or changes whether an earlier finding should still stand, proceed through Gate A's normal "Ready for review" exit so Step 3 re-runs against the revised plan and regenerates `accepted-plan-findings.md` before any later Gate B entry.

**See full plan branch (re-entry only)**: when the user picks See full plan on Shape 2, the orchestrator reads `$DESIGN_TMPDIR/plan.txt` and prints its content under a `## Latest Design Plan` header, then re-fires the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). The See-full-plan branch performs no state mutation and writes nothing to `discussion-round2.md`. If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.

### Loop exit

When the user picks **Ready for review**:
- First-time entry: handled by Step 1d.7 outline-approval; Approve → Step 2a, Cancel → exit, Refine → loop.
- Re-entry (from Gate B or Gate C): write `: > "$DESIGN_TMPDIR/.step3-reentry"` and proceed directly to Step 3 (plan review) with the current `$DESIGN_TMPDIR/plan.txt`. Do NOT re-run sketches or dialectic.

---

## Gate B — Post-Review Chooser (Step 3.5)

**When**: after Step 3 review completes or when the script-internal Step 3 loop bails out. On the happy path, `review-design-step3-loop.sh` applies accepted findings in-loop via `revise-plan-with-waterfall.sh --patch-format file-replacement`; prompt-side Gate B is the fallback body for `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` and the explicit operator body for `per-round-approval-required`. Gate-B-bypass short-circuits (`cap-hit`, `tally-error`, `degraded-empty-collector`, `panel-failed`) bypass Step 3.5 before Step 3b (see SKILL.md post-loop branch matrix).

### Severity classification rubric

**All-or-nothing precedence**: inspect every accepted in-scope `### FINDING_N:` block in `$DESIGN_TMPDIR/accepted-plan-findings.md`. When **every** block carries a `- **Severity**:` line whose value is `important`, `latent`, or `nit`, Gate B presentation uses the structured mapping below for the **entire** findings set (no per-finding hybrid):

- `important → High`
- `latent → Medium`
- `nit → Low`

When **any** accepted finding lacks that structured `- **Severity**:` line (or the value is not one of `important|latent|nit`), fall back to the Concern-text rubric below for **all** findings in the set.

**Concern-text rubric** (legacy fallback — applies to the whole set when the structured field is absent on any accepted finding): for each finding, assign one bucket based on the finding's `**Concern**:` text:

- **Critical** — would cause data loss, security breach, build/CI breakage on landing, or a regression a downstream consumer would detect within one release.
- **High** — would cause functional incorrectness in a primary code path, missing required documentation contract, or violates a stated invariant in the plan.
- **Medium** — improves robustness or clarity in a secondary path; addresses a real but recoverable edge case.
- **Low** — style, naming, or future-proofing; no functional change implied.

When the concern text is ambiguous, prefer the lower bucket and surface the ambiguity in the displayed description. Never invent severity for findings not present in the file.

### Zero-findings short-circuit

When `$DESIGN_TMPDIR/accepted-plan-findings.md` is empty (no accepted in-scope findings — either no reviewer raised any, or voting rejected all), Gate B prints `⏩ 3.5: Gate B — no accepted findings; nothing to apply` and returns to `SKILL.md`'s heuristic multi-round continuation check. This short-circuit fires before Gate B mode resolution, presentation, any prompt, or any plan-apply path. When the continuation check stops, Step 3b → Step 3b completion boundary → Step 4 → Step 4b (Gate C) run in normal sequence, including `LOOP_STATUS=zero-findings-degraded-panel`.

#### Gate B mode (auto-apply default; `--per-round-approval` for explicit)

Determine Gate B handling only after the zero-findings short-circuit above proves there is at least one accepted in-scope finding to handle. In **loop mode**, the script-internal controller (`review-design-step3-loop.sh`) applies accepted findings on the happy path before returning `STEP3_REVIEW_LOOP_STATUS=complete`; prompt-side Gate B apply runs only on loop bail-outs (`main-agent-apply-required`, `per-round-approval-required`, `postplan-operator-required`). Legacy **`--mode single`** harness callers still treat Gate B as the sole apply point when `LOOP_STATUS=complete` and the review pass has not modified `plan.txt`. `--manual` / persisted manual mode no longer exists. The apply UX is selected by `approve_requested` (bound by the Step 3.5 fence from `run-params.json`; default `false`):

- **`approve_requested=false` (default) — auto-apply.** Skip the `AskUserQuestion` entirely. Print `ℹ 3.5: Gate B — auto-applying N accepted finding(s)` (substitute the accepted in-scope finding count for `N`), then Execute `### Apply-all body` verbatim (which runs `### Shared post-apply pipeline`). No operator prompt fires before the plan is revised. This restores the pre-#3512 auto-apply behavior (issue #2930). The plan-size brakes and validator auto-fix escalation in `### Shared post-apply pipeline` still prompt when triggered (see **Apply-pipeline prompts under auto-apply** below).
- **`approve_requested=true` (`--per-round-approval`) — explicit.** Use the full Apply all / Go through each / Switch to discussion mode prompt below; Gate B prompts explicitly before any finding changes `plan.txt`. `Go through each` and `Switch to discussion mode` are reachable only on this path (discussion otherwise remains reachable via Gate C `Discuss further`).

**Resume idempotency guard**: loop mode records `$DESIGN_TMPDIR/.step3-round-N.phase` and writes `$DESIGN_TMPDIR/.gate-b-postapply-ready-N` only after dedup succeeds. `awaiting-apply` resumes at apply, `awaiting-post-apply` resumes at mechanical dedup/postplan without re-applying findings, and `awaiting-continuation` runs only `plan-review-continuation.sh`. Prompt-side Gate B uses the same marker to avoid double-applying during `main-agent-apply-required` recovery.

The zero-findings short-circuit above is unchanged in both modes (nothing to apply, no prompt either way).

#### Apply-pipeline prompts under auto-apply

Under default auto-apply (`approve_requested=false`), Gate B fires **no** finding-acceptance prompt. The only operator prompts that can still fire inside the apply pipeline are the intentional safety brakes in `### Shared post-apply pipeline`, and they are unchanged by `--approve`:

1. **Plan-size HARD trigger** (`design-postplan-emit.sh` rc=12 → Split / Override / Cancel).
2. **Plan-command validator escalation** (rc=10): defects are first auto-corrected cross-vendor (see `SKILL.md` **### Plan command validator failure (shared)**); the helper enforces target-file-only writes, repo dirty-tree checks, per-site evidence, and optional-trailer preservation before the postplan fence is re-entered. The Fix-and-retry / Override / Cancel prompt fires only after auto-fix is exhausted.

Plan drift (`DRIFT_TRIGGER_FIRED=true`) no longer halts: the driver records a warning in `execution-issues.md` and exits `0`. These size brakes are the only automatic halt on the apply path.

**Step 3 outcomes** (read `$DESIGN_TMPDIR/.step3-review-result.env` and `STEP3_REVIEW_LOOP_STATUS` when present):

- When `STEP3_REVIEW_LOOP_STATUS=complete`, the in-loop controller has already applied accepted findings, run postplan, and continuation; Gate B is skipped unless a legacy `--mode single` caller still routes here with unset loop envelope.
- When `STEP3_REVIEW_LOOP_STATUS` is `main-agent-apply-required` or `per-round-approval-required`, prompt-side Gate B owns apply/postplan recovery before resuming the loop at the recorded phase.
- When `STEP3_REVIEW_LOOP_STATUS` is `main-agent-vote-required`, loop mode resumes after MainAgent re-tally via `run-step3-review.sh --mode loop --starting-round "$N"` (see `SKILL.md` post-loop branch matrix); legacy `--mode single` may still continue to Gate B after re-tally. For input/output isolation: bind `_RETALLY_SCOPE_ANCHOR_IN="$SCOPE_ANCHOR_FILE"` before launch, unset `_RETALLY_PARSED_SCOPE_ANCHOR_FILE` before parsing stdout (so re-tally stdout cannot corrupt the input anchor and re-tally's result is never confused with the pre-re-tally anchor).
- When `LOOP_STATUS` is `tally-error`, `degraded-empty-collector`, `panel-failed`, or `cap-reached`, Gate B is **bypassed** — Step 3 already routed to Step 3b.
- When `LOOP_STATUS` is `complete` or `zero-findings-degraded-panel` on a legacy `--mode single` path, Gate B follows the mode rules below; the review pass has not modified `plan.txt` on that path. After any non-exiting Gate B settled path, control returns to `SKILL.md`'s heuristic multi-round continuation check before Step 3b. That check may defer Gate C by launching another Step 3 review round when the disk-derived continuation predicates fire and the shared cap is not yet reached.

### Presentation

Print a compact findings list under `## Plan Review Findings — Review`: one row per accepted finding showing `FINDING_N | Severity | Reviewer(s) | <1-line concern excerpt>`. Use the same severity rubric and the same concern text source as the review table; truncate to the first 1-2 lines or 200 characters, whichever is shorter. Never paraphrase. Also print the rejected and OOS sections for context (read from `rejected-findings.md` and `oos.md`) once.

### Prompt

**Explicit mode only (`approve_requested=true`).** Under default auto-apply (`approve_requested=false`) this entire prompt is skipped — Gate B runs `### Apply-all body` directly after the `ℹ 3.5: Gate B — auto-applying N accepted finding(s)` breadcrumb (see **Gate B mode** above). When `--per-round-approval` is set, fire `AskUserQuestion` with exactly three options:

- **Apply all** — Execute `### Apply-all body` verbatim. The dedup-sweep and shared post-apply pipeline run there; the merged `design-postplan-emit.sh --with-plan-size` fence owns clean rc0/12/13 plan-size handling without a second standalone Step 2b.5 pass.
- **Go through each** — Iterate findings in `FINDING_N` order. For each, fire `AskUserQuestion` (batch up to 4 findings per call) with three options: apply / skip / switch to discussion mode. If at any per-finding prompt the user picks "switch to discussion mode", stop the iteration immediately, discard any unapplied per-finding intent, and exit to Gate A (no plan revision occurs on this exit path). Otherwise, after the iteration completes, run the single post-iteration apply/update path documented below; the merged post-plan fence fires **once** per Gate B settled path, not once per per-finding apply. When the loop bails out with `per-round-approval-required`, persist the operator decision to `$DESIGN_TMPDIR/.gate-b-per-round-approval-round-<N>.env` as `FINDINGS_FILE=<absolute-path>` (full `accepted-plan-findings.md` for Apply all, filtered findings file for Go through each); the loop consumes this file exactly once on resume at `awaiting-apply`.
- **Switch to discussion mode** — Skip plan revision entirely. Exit to Gate A. `plan.txt` remains as it was before Step 3.

Question text depends on which rubric applies (see **Severity classification rubric**):

- **Structured severity on every accepted finding** — `"Plan review returned N findings (H high / M medium / L low). How would you like to handle them?"` (counts map from `important`/`latent`/`nit`; there is no structured Critical bucket).
- **Concern-text fallback** (any accepted finding lacks structured `- **Severity**:`) — `"Plan review returned N findings (C critical / H high / M medium / L low). How would you like to handle them?"`

Header: `"Plan findings"`. Substitute the actual counts before asking.

### Apply-all body

Apply every accepted in-scope finding to `$DESIGN_TMPDIR/plan.txt`, write the revised plan via the Write tool (full file replacement, preserving `diff_lines: <N>` and any optional `diff_added:`, `diff_deleted:`, or `mechanical_churn:` trailers in the final contiguous metadata block immediately above `diff_lines:` — preserve or explicitly recompute them; do not drop mechanical/deletion-heavy estimates while retaining only the legacy total), then Execute `### Shared post-apply pipeline` verbatim.

### One-by-one iteration prompt

For each finding when the user picks **Go through each**:

Question text: `"FINDING_<N> [<Severity>] — <reviewer>: <one-line concern summary>. Apply this finding to the plan?"` Header: `"Finding <N>/<total>"`. Options:
- **Apply** — record in the applied set.
- **Skip** — record in the skipped set; the finding moves from accepted to rejected.
- **Switch to discussion mode** — abort iteration; exit to Gate A; do NOT revise `plan.txt`.

After iteration completes (all findings answered without an early abort), the orchestrator revises `plan.txt` per the applied set only, writes the per-finding outcomes back to `$DESIGN_TMPDIR/accepted-plan-findings.md` (apply set retained) and `$DESIGN_TMPDIR/rejected-findings.md` (skip set appended with `Reason not implemented: rejected by user during one-by-one review`), then Execute `### Shared post-apply pipeline` verbatim.

### Shared post-apply pipeline

In-loop apply takes a loop-owned `plan-pre-apply-round-N.txt` snapshot before `revise-plan-with-waterfall.sh`, then runs `gate-b-dedup-plan.sh --snapshot-trailers` and `gate-b-dedup-plan.sh --dedup` under `set +e`. A dedup failure restores the loop snapshot and returns `STEP3_REVIEW_LOOP_STATUS=main-agent-apply-required` with `DEDUP_RC`; `.gate-b-postapply-ready-N` is written only after dedup succeeds. Operator-brake resumes (`POSTPLAN_RC=10/12/13`) persist phase `awaiting-postplan-operator`. Non-plan-changing Override/Continue writes `$DESIGN_TMPDIR/.postplan-operator-continue-N` before resuming the script-internal loop; the loop consumes the marker, runs HARD snapshots when applicable, and promotes to `awaiting-continuation`. Plan-changing Fix-and-retry/autofix overwrites phase to `awaiting-post-apply` instead.

After the chosen findings have been applied to `plan.txt` (either the full accepted set or the one-by-one applied subset), run the same post-apply sequence for both Gate B branches:

1. **Optional trailer guard (direct rewrites)**: before any prompt-side `plan.txt` replacement or dedup rewrite, run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/gate-b-dedup-plan.sh" --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` to snapshot strict optional trailer keys and values (`diff_added`, `diff_deleted`, `mechanical_churn`) from the final metadata block into `$DESIGN_TMPDIR/.gate-b-optional-trailer-keys` (companion `.gate-b-optional-trailer-keys.values`). An empty snapshot forbids introducing new optional trailers on later validation.
2. Re-read the freshly revised `plan.txt` and perform a duplicate-content sweep using your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once — not just byte-identical text).
3. Preserve intentional repetition where the same content appears in distinct context sections (for example, a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section.
4. Rewrite `plan.txt` via the Write tool with duplicates removed.
5. Run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/gate-b-dedup-plan.sh" --design-tmpdir "$DESIGN_TMPDIR" --dedup` only after step 1 (mechanical section-aware dedup plus trailer key/value preservation — same `dedup_plan_preserve_optional_trailers` helper as `plan-review-loop.sh`). Missing `.gate-b-optional-trailer-keys` is exit **3** (fail closed). It prints exactly one breadcrumb of the shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (use `0` when none were found). On exit **1** (optional trailer keys/values lost or newly introduced), revise again rather than continuing with a legacy total-only estimate; on exit **2** (dedup failure), treat as a Gate B post-apply failure and stop for operator repair.
6. After step 5 succeeds and before the merged post-plan fence, the snapshotted keys are already validated by `gate-b-dedup-plan.sh`; do not skip step 5. Write/update the apply-ready marker path `$DESIGN_TMPDIR/.gate-b-postapply-ready-${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-current}}` only after the accepted findings have been applied and dedup has succeeded; this marker is the resume idempotency guard for pauses before Step 3b writes `.completed/step-3.5`.
7. Only after the breadcrumb, optional trailer guard, and apply-ready marker (when applicable) run the Gate B merged post-plan fence: `env LARCH_QUIET_DISABLE=1 "${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-postplan-emit.sh" --design-tmpdir "$DESIGN_TMPDIR" --with-plan-size` (initial snapshot suppressed) with the canonical session-env / pause prelude (`${REPO:+--repo "$REPO"}` on pause-save only), `set +e` capture, immediate `printf '%s\n' "${_postplan_out:-}"`, and the same `case` arms as `SKILL.md` Step 2b using `case "${_postplan_rc:-1}" in` (`0`, `10`, `11`, `12`, `13`, `2`, `1`, plus the default-abort `*` arm).
8. On `_postplan_rc=10`, read allowlisted validator keys (`VALIDATE_STATUS`, defect counts, log path) from `.design-postplan-emit-result.env` (never `source`) and execute **### Plan command validator failure (shared)** with `--site` context `design Step 3.5 / Gate B`; Fix-and-retry re-enters this same Gate B `--with-plan-size` fence. On **Override**, run retained **Step 2b.5** (Split / Override / Cancel hard prompt). On `_postplan_rc=0` (including drift-advisory path), write/update `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` then continue to step 9. On `_postplan_rc=12`, Gate B hard `AskUserQuestion` offers Split / Override / Cancel; **Override** writes `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` before continuing to step 9. On `_postplan_rc=13` or Split entry, run Split-path only (no standalone Step 2b.5 display after driver output). Non-exiting Split returns (Refine, no-split Continue) write/update `: > "$DESIGN_TMPDIR/.completed/step-2b.5"` before continuing to step 9. Driver exit `1` / `2` mirrors Step 2b.
9. Before returning to `SKILL.md`'s heuristic multi-round continuation check on any non-exiting post-apply path, derive `_gate_b_round="${STEP3_REVIEW_ROUND_NUM:-${ROUND_NUM:-}}"`; for HARD designs run `snapshot-plan-round.sh write-after --design-tmpdir "$DESIGN_TMPDIR" --round "$_gate_b_round"` and then `snapshot-plan-round.sh write-cursor --design-tmpdir "$DESIGN_TMPDIR" --value "$((_gate_b_round + 1))"`. This records the plan as it stands after the current round's Gate B application, so the next `run-step3-review.sh` entry receives the next `--round-num` and prior `plan-review/round-*` artifacts remain diagnosable. If the round value is missing or non-numeric, or either snapshot helper call fails, stop for operator repair rather than launching another automatic round.
10. Only when the merged fence settles clean (`_postplan_rc=0`), drift Continue settles, or a non-exiting Split/Override path completes without skill exit, return to `SKILL.md`'s heuristic multi-round continuation check. When that check stops, proceed to Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b); Step 4 and Gate C follow in normal sequence. When that check continues, it clears only `.step3-entry-plan-printed` and re-enters Step 3 without writing `.completed/step-3.5`, preserving the current Gate B apply sentinel hygiene.

### Gate B plan revision and Step 2b.5

Gate B's plan revision may cause the merged driver fence to branch: partition flag (`--partition`) maps to Split-path with no `AskUserQuestion`; hard trigger (plan body `> 800`, or `diff_added > 2000` when the trailer is present, else legacy `diff_lines > 1500`; deletions never trip; `mechanical_churn: true` downgrades only the diff trigger to `SOFT_ADVISORY`) fires an `AskUserQuestion` with Split / Override / Cancel (explicit, strongly-discouraged Override-and-proceed escape hatch; `--partition` still cannot auto-downgrade a hard trigger) when `HARD_TRIGGER_FIRED=true`; drift trigger (`DRIFT_TRIGGER_FIRED=true`) records a logged advisory in `execution-issues.md` and exits `0` without prompting; otherwise the merged fence returns to `SKILL.md`'s heuristic continuation check after writing `step-2b.5`. The standalone Step 2b.5 procedure is retained only for Override-after-defects and standalone recovery paths. Authoritative machine contract: `skills/design/scripts/check-plan-size.md`. If the split handler exits the skill on **Cancel** (cost line + exit 0) or **Split** (Split-path: decomposition panel + exit 1), `$DESIGN_TMPDIR` is preserved and the operator can re-run after addressing sprawl.

---

## Gate C — Final-Approval Loop (Step 4b)

**`--skip-approve` auto-approve carve-out**: when `skip_approve_requested=true` (read by the Step 4b dedicated read fence in `SKILL.md`), Gate C auto-approves the final plan without an `AskUserQuestion`: print `⏩ 4b: Gate C — auto-approved final plan (--skip-approve)` and proceed to Step 5 immediately. The Presentation block below (plan emit) still runs before the auto-approve decision so the operator sees the final plan in the transcript. The auto-approve path never fires the Prompt below. The Gate C "Never offers 'Discuss further'" invariant: under `--skip-approve`, Gate A re-entry from Gate C(b) is simply not taken — Gate A prompts are untouched on non-skip runs.

**When** (`skip_approve_requested=false`): after Step 4 (rejected-findings report) completes. Step 4 is reached on every Gate B settled path that continues the design and does not trigger automatic continuation: default auto-apply → heuristic stop → Step 3b → Step 3b completion boundary → Step 4 → Step 4b; explicit Apply all (`--approve`) → heuristic stop (`explicit-approve`) → Step 3b → Step 3b completion boundary → Step 4 → Step 4b; explicit Go through each (`--approve`, without abort) → heuristic stop (`explicit-approve`) → Step 3b → Step 3b completion boundary → Step 4 → Step 4b; zero-findings short-circuit → heuristic stop unless the disk-derived degraded-panel predicate asks for another round → Step 3b → Step 3b completion boundary → Step 4 → Step 4b. Gate B(c) "switch to discussion mode" is reachable only under `--approve`; it exits to Gate A and never reaches Gate C until the user later picks "Ready for review" and the new review completes its own Gate B settled path. On the default auto-apply path, post-review discussion is reached through Gate C's "Discuss further" option after the heuristic stops. Step 3 bypasses such as `LOOP_STATUS=cap-reached`, `tally-error`, `degraded-empty-collector` and `panel-failed` skip Gate B and the continuation check but still continue Step 3b → Step 3b completion boundary → Step 4 → Step 4b with the current plan and artifacts. Gate C is also re-entered from Gate C(b) "discuss further" → Gate A loop → eventual re-review → Step 3.5 → heuristic stop → Step 3b → Step 3b completion boundary → Step 4 → Step 4b.

### Presentation

**Mandatory — immediately before the Prompt section below.** The executor MUST run the Step 4b `SKILL.md` fenced Bash block that invokes `emit-design-plan-preview.sh --variant gatec` (the shared large-plan summary path). When `$DESIGN_TMPDIR` is set to a directory and `$DESIGN_TMPDIR/plan.txt` is present and non-empty, that block emits the plan under a `## Final Design Plan` header (summary or full body per the threshold rules in the Large-plan summary mode subsection). **Defined exception — warning-only path:** when `$DESIGN_TMPDIR` is unset or not a directory, the block prints `**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**` and execution continues to the Prompt without a plan header/body. When `plan.txt` is missing or empty (should not happen on this path), the block prints `**⚠ 4b: plan.txt missing or empty; cannot present final design plan**` and execution continues to the Prompt the same way.

**Large-plan summary mode**: the shared Bash (`skills/design/scripts/emit-design-plan-preview.sh`) uses `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` (default `120`, positive integers only; `0`, empty, non-numeric values, or values with a leading zero fall back to `120`; comparisons use base-10 integer coercion). The same threshold, strict `line_count > threshold` rule, outline cap (40 matching `##`/`###` lines via `grep -E '^#{2,3} '`), empty-outline fallback (first 30 lines of `plan.txt`), and bold-note behavior apply at Step 3's `## Plan Candidate for Review` emit and at Gate C's `## Final Design Plan` emit. When the plan's line count strictly exceeds the threshold, the block emits only the plan title (first line) plus a section outline plus a bold note pointing at the full plan; if the outline is empty, the block falls back to the first 30 lines of `plan.txt`. The outline is best-effort and may include `##`/`###` lines from inside fenced code blocks. When the user picks the structured `See full plan` option, the executor MUST `cat` the full `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option — including when the plan was already printed in full (non-summary path); the remaining options preserve their cap-aware shape (below cap: `Approve final design` / `Discuss further` / `Re-run review panel`; at cap: `Approve final design` / `Discuss further`). When the user picks `Other` and asks for the full plan, the executor MUST also `cat` the full plan and re-fire the same Gate C `AskUserQuestion`, but the `Other` re-prompt preserves the **same option set unchanged** (no option removed) and may be invoked repeatedly without mutating the option count.

### Prompt

`AskUserQuestion` with four primary options plus the host's standard `Other` free-form channel:

- **Approve final design** — exit Gate C; proceed to Step 5 finalize: Step 5b composes `composed-plan.md`; Step 5c writes the `larch:plan` block, best-effort upserts the architecture diagram, renames the tracking issue to `[DESIGNED]`, then runs `design-log-publish.sh`.
- **See full plan** — Print the current `$DESIGN_TMPDIR/plan.txt` into chat under a `## Final Design Plan` header (verbatim — same content the Gate C plan-emit produced or would produce in full mode), then re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. The remaining options preserve their cap-aware shape (Approve final design / Discuss further / Re-run review panel below cap, or Approve final design / Discuss further at cap). This option performs no state mutation and never advances control past Gate C.
- **Discuss further** — re-enter Gate A (Step 1e) with the current plan; the discussion sub-round writes to `discussion-round2.md`. When Gate A later exits via **Ready for review**, re-enter Step 3 with the revised current plan; any settled review path must continue through Step 3b, the Step 3b completion boundary (FINALIZE + step-3b), Step 4, and then back to Gate C.
- **Re-run review panel** — offer this option only when the current review-round count is still below the flattened cap of 5. Re-enter Step 3 with the current `plan.txt` (which already reflects all user-approved or operator-approved/applied prior feedback). Do NOT re-run sketches or dialectic. On HARD runs the round cursor advances at Step 3 entry when `plan-after-round-<cursor>.txt` already exists; Step 3.5 (Gate B), the heuristic continuation check, Step 3b, the Step 3b completion boundary (FINALIZE + step-3b), Step 4, and then Gate C fire again on the fresh findings. Findings from prior manual review runs are NOT preserved — each manual re-run is a fresh look at the latest plan.

When at the cap, omit `Re-run review panel` so three options remain (`Approve final design` / `See full plan` / `Discuss further`); after a `See full plan` pick at cap, the re-fired prompt has two options (`Approve final design` / `Discuss further`).

If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks the structured `See full plan` option (for example after the warning-only presentation path), print `**⚠ plan.txt missing or empty; nothing to show.**` and still re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. Preserve the same cap-aware remaining options as usual. This warning path performs no state mutation and does not advance control past Gate C.

Question text below cap: `"Final design plan is ready. Approve, see the full plan, discuss further, or re-run the review panel against this plan?"` At cap: `"Final design plan is ready. Approve, see the full plan, or discuss further?"` Header: `"Final design"`.

**Opt-in to see the full plan via `Other`**: `See full plan` is the preferred structured path for printing the full plan before deciding. The user may still pick `Other` on this prompt and request the full plan (whether or not large-plan summary mode applied on the prior emit). The executor MUST `cat` `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion` with the **same option set unchanged**; when `plan.txt` is missing or empty, print `**⚠ plan.txt missing or empty; nothing to show.**` instead and still re-fire the same prompt. The Other path does **not** mutate the option set on its re-prompt, so any number of repeat Other requests preserve the same option count. This differs from the structured `See full plan` option, which drops itself on its re-prompt. Gate C `Other` never cancels `/design`; it only displays the full plan when available and re-prompts.

### Loop exit

When the user picks **Approve final design**, proceed to Step 5b. The skill no longer fires a separate accept/regenerate/cancel prompt in Step 5b — Gate C is the only final-approval gate.

---

## State invariants across gates

1. **Latest plan to reviewers**: Step 3 (whether first-time or re-entry from Gate C(c)) always reads `$DESIGN_TMPDIR/plan.txt` as written by the most recent of: Step 2b initial plan write, or Gate B applied-set revision. No "ghost" prior-version plan is ever submitted to reviewers.

2. **No preserved findings across manual review runs**: when Step 3 is re-entered from Gate C(c), the prior `accepted-plan-findings.md` / `accepted-plan-findings-all.md` / `rejected-findings.md` / `oos.md` / `voting-tally.md` are overwritten by the new manual run. Gate B operates on the latest run's `accepted-plan-findings.md` only. During automatic continuation before Gate C, `accepted-plan-findings-all.md` accumulates accepted in-scope findings across the automatic rounds for final-summary reporting, while `accepted-plan-findings.md` remains the current Gate B apply set. `oos-accepted-design.md` is accumulated for the current automatic sequence before terminal status mapping — see `plan-review.md` § Single-pass review.

3. **Discussion outputs accumulate**: `discussion-round1.md` is written by Step 1d. Step 1d.7 writes the approved outline separately to `design-outline.md`. `discussion-round2.md` accumulates entries across all Gate A re-entries from Gate B(c) / Gate C(b). All three files remain readable inputs to subsequent plan revisions.

4. **Gate B apply contract**: by default (`approve_requested=false`) Gate B **auto-applies** every accepted in-scope finding with no prompt; under `--per-round-approval` (`approve_requested=true`) it prompts explicitly before revising `plan.txt` and the rewrite runs only after the operator chooses **Apply all** or applies individual findings in **Go through each**. In neither mode does it ask again for each already-approved apply action. Gate A and Gate C never auto-revise `plan.txt`; Gate A may still revise `plan.txt` directly for user-resolved discussion outcomes per `discussion-rounds.md`, but Gate B never treats `discussion-round2.md` as patch instructions. The plan-review tally script writes artifact files only; it does not revise `plan.txt`. **Loop mode**: the script-internal Step 3 loop applies accepted findings on the happy path via `revise-plan-with-waterfall.sh`; prompt-side Gate B is the apply surface only for loop bail-outs (`main-agent-apply-required`, `per-round-approval-required`). **Legacy `--mode single`**: Gate B remains the sole apply point between review rounds. There is no persisted mode state; the apply UX is recomputed from `approve_requested` at each Gate B entry.

<!-- loop-mode review contract -->
In loop mode, accepted findings are applied inside `review-design-step3-loop.sh` before `STEP3_REVIEW_LOOP_STATUS=complete`. Prompt-side Gate B applies only on loop bail-outs; under `--per-round-approval` it asks explicitly: Apply all / Go through each / Switch to discussion mode.
