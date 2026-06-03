# Approval Gates Reference

**MANDATORY — READ ENTIRE FILE before composing Gate A discussion prose, Gate B findings presentation and apply-all rewrite, or Gate C approval prose: `skills/design/references/readability-style.md`.**

**Consumer**: `/design` Step 1e (Gate A — discussion-mode loop), Step 3.5 (Gate B — post-review chooser), and Step 4b (Gate C — final-approval loop).

**Contract**: owns the three user-facing approval gates that bracket the design review pipeline. Gate A is the **post-plan re-entry** discussion prompt, Gate C is the final approval prompt, and Gate B's behavior depends on `manual_gate_b` (set via `--manual` / `-m`): when `true`, the existing 3-option `AskUserQuestion` fires; when `false` (default), Gate B auto-applies every accepted in-scope finding after printing a compact findings list. Gate A and Gate C use `AskUserQuestion` on their reachable paths; Gate B uses `AskUserQuestion` only in manual mode and may otherwise auto-apply. Reviewers always see the latest plan with all user-approved or auto-applied prior feedback applied.

**When to load**: before executing Step 1e, Step 3.5, or Step 4b.

**Binding convention**: single normative source for the three gate prompts, their per-tier behavior, the severity-classification rubric used in Gate B, and the loop semantics between A/B/C.

**Cross-tier invariant**: Gates apply uniformly across SIMPLE and HARD tiers. Gate B reads `accepted-plan-findings.md` produced by the full `plan-review.md` panel on both tiers. The auto-apply default and the `--manual` opt-out apply uniformly across both tiers. Gate B's mode branch reads `manual_gate_b` identically in both tiers.

## Per-tier review-round cap

Gate C reads `$DESIGN_TMPDIR/review-round-count.txt` (treat missing/empty/non-numeric as 0; log Warning if non-numeric) and `design_classification` via `read-design-classification.sh`. Cap: SIMPLE = 3, HARD = 5. When counter >= cap, the "Re-run review panel" option is omitted from the Gate C `AskUserQuestion`; only Approve final design / See full plan / Discuss further remain. Any Gate C re-prompt after `Other` must preserve those three at-cap options (Approve final design / See full plan / Discuss further), while a `See full plan` pick at cap re-fires the same prompt minus the `See full plan` option (leaving Approve final design / Discuss further). Step 3 also enforces the cap at every entry (initial, Gate C re-run, Gate A "Ready for review" post-discussion) and short-circuits with the breadcrumb `**⚠ Step 3: review-round cap (<cap>) reached for <tier>; skipping panel and continuing to Step 3b, Step 4, then Gate C.**` when counter >= cap. Step 3.6 is skipped on that path. SKILL.md Step 3 is the sole writer of the counter; `plan-review-loop.sh` is stateless w.r.t. the file. Gate A "Discuss more" loops remain uncapped.

---

## Gate A — Discussion Mode Loop (Step 1e)

**When**: **Re-entry-only**. Gate A is reached **only** from Gate B option (c) "switch to discussion mode" or Gate C option (b) "discuss further" (post-plan). First-time entry from Step 1d / Step 1d.5 is replaced by the **Step 1d.7 outline-approval gate** — see `${CLAUDE_PLUGIN_ROOT}/skills/design/references/design-outline.md`.

**Behavior**: when the orchestrator believes the open scope/requirements questions are discussed on a post-plan re-entry, prompt the user via `AskUserQuestion`.

**First-time entry**: handled by Step 1d.7 outline-approval, not by Gate A. See `design-outline.md` for the Approve/Refine/Cancel prompt.

**Shape 2 — re-entry from Gate B(c) or Gate C(b) (post-plan)**: exactly three options.

- **See full plan** — re-display the current `$DESIGN_TMPDIR/plan.txt` under a `## Latest Design Plan` header (verbatim, no diff vs. prior version) and re-fire the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). This option never advances state; it loops back to the prompt.
- **Ready for review** — exit Gate A; proceed directly to Step 3 with the current `$DESIGN_TMPDIR/plan.txt` (Step 2a sketches and Step 2a.5 dialectic are NOT re-run on re-entry per the existing loop-exit semantics below).
- **Discuss more** — remain in Gate A; conduct another discussion sub-round, then re-prompt.

The trigger for Shape 2 is exactly "Gate A entered from Gate B(c) or Gate C(b)" — the same trigger that already routes the discussion sub-round body to `discussion-round2.md`.

Question text: `"All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?"` Header: `"Design discussion"`.

### Discussion sub-round body

When the user picks **Discuss more**, the orchestrator either (a) asks the user what additional aspect to discuss via a free-form follow-up, or (b) walks any remaining branch from the Step 1d decision tree that was deferred. Then re-prompt with Shape 2, the same three-option `AskUserQuestion` (See full plan / Ready for review / Discuss more). Gate A re-entries always use Shape 2 because first-time entry is replaced by Step 1d.7. Append resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` using the existing Q&A schema in `discussion-rounds.md`.

**Per-tier behavior**: Gate A fires only on re-entry. First-time entry across both tiers (SIMPLE / HARD) is handled by Step 1d.7 outline-approval.

### Re-entry from Gate B(c) or Gate C(b)

When Gate A is re-entered from Gate B option (c) ("switch to discussion mode") or Gate C option (b) ("discuss further"), the orchestrator is now post-plan. Write any new resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` rather than `discussion-round1.md` (Round 1 is closed once Step 2a begins). On a Gate B(c) / Gate C(b) re-entry to Gate A, `discussion-round2.md` is evidence for the user-approved discussion outcome, not a patch instruction file. Gate A may revise `plan.txt` directly only for user-resolved design decisions recorded during that discussion flow (per `discussion-rounds.md`); Gate B remains the only place that applies accepted review findings. Do not run a separate rollback pass inside Gate B based on `discussion-round2.md`. If the discussion changes the plan after a prior auto-apply or changes whether an earlier finding should still stand, proceed through Gate A's normal "Ready for review" exit so Step 3 re-runs against the revised plan and regenerates `accepted-plan-findings.md` before any later Gate B entry.

**See full plan branch (re-entry only)**: when the user picks See full plan on Shape 2, the orchestrator reads `$DESIGN_TMPDIR/plan.txt` and prints its content under a `## Latest Design Plan` header, then re-fires the same Gate A `AskUserQuestion` minus the `See full plan` option, leaving exactly two options (`Ready for review` / `Discuss more`). The See-full-plan branch performs no state mutation and writes nothing to `discussion-round2.md`. If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt with the two-option shape anyway.

### Loop exit

When the user picks **Ready for review**:
- First-time entry: handled by Step 1d.7 outline-approval; Approve → Step 2a, Cancel → exit, Refine → loop.
- Re-entry (from Gate B or Gate C): proceed directly to Step 3 (plan review) with the current `$DESIGN_TMPDIR/plan.txt`. Do NOT re-run sketches or dialectic.

---

## Gate B — Post-Review Chooser (Step 3.5)

**When**: after Step 3 review completes — `accepted-plan-findings.md` (and `rejected-findings.md`, `oos.md`) have been written by the tally script. In legacy single-pass/manual branches the plan has **not** been revised yet; in multi-round `LOOP_STATUS=converged|cap-hit` branches the loop already revised `plan.txt` between rounds and Gate B is passive-summary only. Gate-B-bypass short-circuits (`LOOP_STATUS=cap-reached`, `TALLY_PLAN_REVIEW_STATUS=skipped-cap-reached`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `panel-failed`) bypass Step 3.5 and Step 3.6 before Step 3b (see SKILL.md post-loop branch matrix).

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

When `$DESIGN_TMPDIR/accepted-plan-findings.md` is empty (no accepted in-scope findings — either no reviewer raised any, or voting rejected all), Gate B prints `⏩ 3.5: Gate B — no accepted findings; nothing to apply` and proceeds to Step 3.6 (HARD-only plan-quality assessor; see `assessor.md`) before Step 3b. This short-circuit fires before Gate B mode resolution, presentation, any prompt, or any plan-apply path. Step 3.6 → Step 3b → Step 4 → Step 4b (Gate C) run in normal sequence on HARD runs, including `LOOP_STATUS=zero-findings-degraded-panel`.

#### Gate B mode (auto-apply vs manual)

Determine Gate B mode only after the zero-findings short-circuit above proves there is at least one accepted in-scope finding to handle.

**Multi-round loop outcomes** (read `$DESIGN_TMPDIR/.step3-plan-review-result.env` when present; see `plan-review.md` § Multi-round loop):

- When `LOOP_STATUS` is `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, `panel-failed`, or `cap-reached`, Gate B is **bypassed** — Step 3 already routed to Step 3b or the Step 2b.5 handler; Step 3.6 is skipped too on those short-circuits. Step 3 prints the matching skip breadcrumb: `⏩ 3.6: assessor — skipped (Step 3 tally-error short-circuit)`, `⏩ 3.6: assessor — skipped (Step 3 degraded-empty-collector short-circuit)`, `⏩ 3.6: assessor — skipped (Step 3 panel-failed short-circuit)`, `⏩ 3.6: assessor — skipped (Step 3 cap-reached short-circuit)`, `⏩ 3.6: assessor — skipped (Step 3 plan-size-trigger short-circuit)`, or `⏩ 3.6: assessor — skipped (Step 3 plan-validator-defects short-circuit)`.
- When `LOOP_STATUS` is `converged` or `cap-hit` and `manual_gate_b=false`, enter **passive-summary mode** (below) instead of the auto-apply path — findings were already applied inside `plan-review-loop.sh`.
- When `LOOP_STATUS` is `revision-failed`, `emit-plan-failed`, or `optional-trailer-dedup-loss`, use the full 3-option `AskUserQuestion` form so the operator can apply or inspect the final-round findings manually. Gate-B-settled paths `complete|revision-failed|emit-plan-failed|optional-trailer-dedup-loss` proceed through Step 3.6 after Gate B and any Step 2b.5 return.
- When `LOOP_STATUS` is `main-agent-vote-required`, after successful MainAgent adjudication and re-tally, parse the re-tally output and refresh the active Step 3 result state (including `.step3-plan-review-result.env`) before continuing to Gate B as complete-equivalent. The re-tally must pass `--findings-classification-out "$DESIGN_TMPDIR/plan-review/round-${ROUNDS_COMPLETED:-$ROUND_NUM}/findings-classification.tsv"` before refreshing the active state. Settled Gate B paths proceed through Step 3.6. If re-tally emits `tally-error`, use that short-circuit.
- When `manual_gate_b=true`, always use the full 3-option form regardless of `LOOP_STATUS` (the loop exits after one round with `LOOP_STATUS=complete REASON=manual-gate-b` and does not auto-apply).

#### Gate B passive-summary mode (`LOOP_STATUS=converged|cap-hit`)

After parsing `.step3-plan-review-result.env` as data (read line-by-line and accept only the documented `KEY=value` schema; do not shell-source it), print `## Multi-round loop result` as a table with one row per `$DESIGN_TMPDIR/plan-review/round-N/round-summary.env` (columns: `ROUND_NUM`, `ACCEPTED_COUNT`, `IMPORTANT_ACCEPTED_COUNT`, `DEGRADED_PANEL`, `REVISE_STATUS`, `LOOP_STATUS`). End with: "All accepted findings were auto-applied across N rounds; `plan.txt` reflects the final state." This summary is **non-blocking**: do **not** fire an `AskUserQuestion` here — auto-continue to Step 3.6, then Step 3b, then Step 4, then Gate C, and do **not** halt the turn on the printed table. Gate C (Step 4b) is the single decision point; its **Discuss further** option covers the old switch-to-discussion intent. Passive-summary auto-continue routes through Step 3.6 before Step 3b / the next Step 3 entry. Do **not** re-apply findings or run the shared post-apply pipeline — the loop already revised `plan.txt`.

Resolve the mode defensively in this order: first, if sourced session env exports `MANUAL_REQUESTED=true`, set `manual_gate_b=true` immediately; second, if the in-memory boolean `manual_requested` from Step 0b is still bound, let `manual_requested=true` force `manual_gate_b=true` without consulting `run-params.json`; third, read `manual_gate_b` from `$DESIGN_TMPDIR/run-params.json` using `jq -r '.manual_gate_b // false'` so missing/null coerces to `false`. The persisted value follows one canonical write rule from Step 0b recovery: `partition_requested` / `brainstorm_requested` are true-only merges, but `manual_gate_b` is overwritten from the current run's `manual_requested` value so omitting `--manual` clears stale persisted manual mode instead of preserving it accidentally. Session env and in-memory state are true-only overrides; persisted `run-params.json` remains the canonical source for proving `manual_gate_b=false`. If `run-params.json` cannot be read, `jq` is unavailable, or the mode cannot otherwise be confirmed from persisted state, print `**⚠ 3.5: Gate B — could not confirm manual_gate_b from persisted state (<reason>); defaulting to auto-apply unless a true-only manual override is already present.**`, append that warning under `Warnings` in `$DESIGN_TMPDIR/execution-issues.md` via `append-tool-failure.sh` when possible, and continue with `manual_gate_b=false`.

### Presentation

When `manual_gate_b=true`, print a table under the header `## Plan Review Findings — Review` listing every accepted finding, in `FINDING_N` order, with columns: ID, Severity, Reviewer(s), Concern. The Concern column is a 1-10 line description drawn from the finding's `**Concern**:` field (truncate to 10 lines max; never paraphrase the concern text). After the table, also print the rejected and OOS sections for context (read from `rejected-findings.md` and `oos.md`).

When `manual_gate_b=false`, do **not** print the full review table above. The compact findings list in the auto-apply path below is the visibility surface for accepted findings on that branch; print rejected/OOS sections there once.

### Prompt

When `manual_gate_b=false` and `LOOP_STATUS` is neither `converged` nor `cap-hit`, execute the auto-apply path:

1. Print a compact findings list under `## Plan Review Findings — Auto-applying`: one row per finding showing `FINDING_N | Severity | Reviewer(s) | <1-line concern excerpt>`. Use the same severity rubric and the same concern text source as the review table; truncate to the first 1-2 lines or 200 characters, whichever is shorter. Never paraphrase.
2. Also print the rejected and OOS sections for context (same reads from `rejected-findings.md` / `oos.md` as the presentation table).
3. Execute `### Apply-all body` verbatim.

When `manual_gate_b=true`, fire the `AskUserQuestion` block below verbatim.

`AskUserQuestion` with exactly three options:

- **Apply all** — Execute `### Apply-all body` verbatim. The dedup-sweep, shared post-apply pipeline, `design-postplan-emit.sh`, and Step 2b.5 all run there.
- **Go through each** — Iterate findings in `FINDING_N` order. For each, fire `AskUserQuestion` (batch up to 4 findings per call) with three options: apply / skip / switch to discussion mode. If at any per-finding prompt the user picks "switch to discussion mode", stop the iteration immediately, discard any unapplied per-finding intent, and exit to Gate A (no plan revision occurs on this exit path). Otherwise, after the iteration completes, run the single post-iteration apply/update path documented below; the Step 2b.5 call fires **once** per Gate B settled path, not once per per-finding apply.
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

After the chosen findings have been applied to `plan.txt` (either the full accepted set or the one-by-one applied subset), run the same post-apply sequence for both Gate B branches:

1. **Optional trailer guard (direct rewrites)**: before any prompt-side `plan.txt` replacement or dedup rewrite, run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/gate-b-dedup-plan.sh" --design-tmpdir "$DESIGN_TMPDIR" --snapshot-trailers` to snapshot strict optional trailer keys and values (`diff_added`, `diff_deleted`, `mechanical_churn`) from the final metadata block into `$DESIGN_TMPDIR/.gate-b-optional-trailer-keys` (companion `.gate-b-optional-trailer-keys.values`). An empty snapshot forbids introducing new optional trailers on later validation.
2. Re-read the freshly revised `plan.txt` and perform a duplicate-content sweep using your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once — not just byte-identical text).
3. Preserve intentional repetition where the same content appears in distinct context sections (for example, a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section.
4. Rewrite `plan.txt` via the Write tool with duplicates removed.
5. Run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/gate-b-dedup-plan.sh" --design-tmpdir "$DESIGN_TMPDIR" --dedup` only after step 1 (mechanical section-aware dedup plus trailer key/value preservation — same `dedup_plan_preserve_optional_trailers` helper as `plan-review-loop.sh`). Missing `.gate-b-optional-trailer-keys` is exit **3** (fail closed). It prints exactly one breadcrumb of the shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (use `0` when none were found). On exit **1** (optional trailer keys/values lost or newly introduced), revise again rather than continuing with a legacy total-only estimate; on exit **2** (dedup failure), treat like `emit-plan-failed` manual handling.
6. After step 5 succeeds and before `ACTION=EMIT_PLAN` / Step 2b.5, the snapshotted keys are already validated by `gate-b-dedup-plan.sh`; do not skip step 5.
7. Only after the breadcrumb and optional trailer guard (when applicable) run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/design-postplan-emit.sh" --design-tmpdir "$DESIGN_TMPDIR"` (snapshot suppressed; no `--force-validate`) so the driver issues `ACTION=EMIT_PLAN`, refreshes `diff-lines.txt`, and applies the shared validator quick-skip contract. Use the canonical session-env / pause prelude, `set +e` capture, and the same file-first/stdout KV parse as `SKILL.md` Step 2b.
8. On driver exit `0` with `VALIDATE_STATUS=defects-found`, execute **### Plan command validator failure (shared)** with `--site` context `design Step 3.5 / Gate B`; on exit `0` otherwise, run the **Step 2b.5 — Plan-size threshold check** procedure from `SKILL.md`. Driver exit `1` / `2` handling mirrors Step 2b (`missing-diff-lines`, `snapshot-failed`, `validate-driver-failed`, or config error).
9. Only when Step 2b.5 returns to caller (no Split or Cancel selected) proceed to Step 3.6 (HARD-only plan-quality assessor; see `assessor.md`) then Step 3b (architecture diagram) — Step 4 (rejected-findings report) and Step 4b (Gate C) follow in normal sequence.

### Gate B plan revision and Step 2b.5

Gate B's plan revision may cause Step 2b.5 to branch: partition flag (`--partition`) routes directly to Split-path with no `AskUserQuestion`; hard trigger (plan body `> 800`, or `diff_added > 2000` when the trailer is present, else legacy `diff_lines > 1500`; deletions never trip; `mechanical_churn: true` downgrades only the diff trigger to `SOFT_ADVISORY`) fires an `AskUserQuestion` with Split / Override / Cancel (explicit, strongly-discouraged Override-and-proceed escape hatch; `--partition` still cannot auto-downgrade a hard trigger) when `HARD_TRIGGER_FIRED=true`; otherwise Step 2b.5 returns silently (possibly after a mechanical-churn advisory line). Authoritative machine contract: `skills/design/scripts/check-plan-size.md`. If Step 2b.5 exits the skill on **Cancel** (cost line + exit 0) or **Split** (Split-path: decomposition panel + exit 1), `$DESIGN_TMPDIR` is preserved and the operator can re-run after addressing sprawl.

---

## Gate C — Final-Approval Loop (Step 4b)

**When**: after Step 4 (rejected-findings report) completes. Step 4 is reached on every Gate B settled path that continues the design: auto-apply → Step 3.6 → Step 3b → Step 4 → Step 4b; Apply all → Step 3.6 → Step 3b → Step 4 → Step 4b; Go through each (without abort) → Step 3.6 → Step 3b → Step 4 → Step 4b; passive-summary auto-continue → Step 3.6 → Step 3b → Step 4 → Step 4b; zero-findings short-circuit → Step 3.6 → Step 3b → Step 4 → Step 4b. Gate B(c) "switch to discussion mode" exits to Gate A and never reaches Gate C until the user later picks "Ready for review" + the new review completes its own Gate B settled path. Step 3 bypasses such as `LOOP_STATUS=cap-reached`, `tally-error`, `degraded-empty-collector`, `plan-size-trigger`, `plan-validator-defects`, and `panel-failed` skip Gate B (and therefore Step 3.6) but still continue Step 3b → Step 4 → Step 4b with the current plan and artifacts. Gate C is also re-entered from Gate C(b) "discuss further" → Gate A loop → eventual re-review → Step 4 → Step 4b.

### Presentation

**Mandatory — immediately before the Prompt section below.** The executor MUST run the Step 4b `SKILL.md` fenced Bash block that invokes `emit-design-plan-preview.sh --variant gatec` (the shared large-plan summary path). When `$DESIGN_TMPDIR` is set to a directory and `$DESIGN_TMPDIR/plan.txt` is present and non-empty, that block emits the plan under a `## Final Design Plan` header (summary or full body per the threshold rules in the Large-plan summary mode subsection). **Defined exception — warning-only path:** when `$DESIGN_TMPDIR` is unset or not a directory, the block prints `**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**` and execution continues to the Prompt without a plan header/body. When `plan.txt` is missing or empty (should not happen on this path), the block prints `**⚠ 4b: plan.txt missing or empty; cannot present final design plan**` and execution continues to the Prompt the same way.

**Large-plan summary mode**: the shared Bash (`skills/design/scripts/emit-design-plan-preview.sh`) uses `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` (default `120`, positive integers only; `0`, empty, non-numeric values, or values with a leading zero fall back to `120`; comparisons use base-10 integer coercion). The same threshold, strict `line_count > threshold` rule, outline cap (40 matching `##`/`###` lines via `grep -E '^#{2,3} '`), empty-outline fallback (first 30 lines of `plan.txt`), and bold-note behavior apply at Step 3's `## Plan Candidate for Review` emit and at Gate C's `## Final Design Plan` emit. When the plan's line count strictly exceeds the threshold, the block emits only the plan title (first line) plus a section outline plus a bold note pointing at the full plan; if the outline is empty, the block falls back to the first 30 lines of `plan.txt`. The outline is best-effort and may include `##`/`###` lines from inside fenced code blocks. When the user picks the structured `See full plan` option, the executor MUST `cat` the full `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option — including when the plan was already printed in full (non-summary path); the remaining options preserve their cap-aware shape (below cap: `Approve final design` / `Discuss further` / `Re-run review panel`; at cap: `Approve final design` / `Discuss further`). When the user picks `Other` and asks for the full plan, the executor MUST also `cat` the full plan and re-fire the same Gate C `AskUserQuestion`, but the `Other` re-prompt preserves the **same option set unchanged** (no option removed) and may be invoked repeatedly without mutating the option count.

### Prompt

`AskUserQuestion` with four primary options plus the host's standard `Other` free-form channel:

- **Approve final design** — exit Gate C; proceed to Step 5b publish (compose `composed-plan.md`, write `larch:plan` block to issue, run `design-log-publish.sh`, rename tracking issue).
- **See full plan** — Print the current `$DESIGN_TMPDIR/plan.txt` into chat under a `## Final Design Plan` header (verbatim — same content the Gate C plan-emit produced or would produce in full mode), then re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. The remaining options preserve their cap-aware shape (Approve final design / Discuss further / Re-run review panel below cap, or Approve final design / Discuss further at cap). This option performs no state mutation and never advances control past Gate C.
- **Discuss further** — re-enter Gate A (Step 1e) with the current plan; the discussion sub-round writes to `discussion-round2.md`.
- **Re-run review panel** — offer this option only when the current review-round count is still below the tier cap. Re-enter Step 3 with the current `plan.txt` (which already reflects all user-approved or auto-applied prior feedback). Do NOT re-run sketches or dialectic. On HARD runs the round cursor advances at Step 3 entry when `plan-after-round-<cursor>.txt` already exists (see `assessor.md`); Step 3.5 (Gate B) and Step 3.6 (assessor) fire again on the fresh findings. Findings from prior review runs are NOT preserved — each review is a fresh look at the latest plan.

When at the tier cap, omit `Re-run review panel` so three options remain (`Approve final design` / `See full plan` / `Discuss further`); after a `See full plan` pick at cap, the re-fired prompt has two options (`Approve final design` / `Discuss further`).

If `$DESIGN_TMPDIR/plan.txt` is missing or empty when the user picks the structured `See full plan` option (for example after the warning-only presentation path), print `**⚠ plan.txt missing or empty; nothing to show.**` and still re-fire the same Gate C `AskUserQuestion` minus the `See full plan` option. Preserve the same cap-aware remaining options as usual. This warning path performs no state mutation and does not advance control past Gate C.

Question text below cap: `"Final design plan is ready. Approve, see the full plan, discuss further, or re-run the review panel against this plan?"` At cap: `"Final design plan is ready. Approve, see the full plan, or discuss further?"` Header: `"Final design"`.

**Opt-in to see the full plan via `Other`**: `See full plan` is the preferred structured path for printing the full plan before deciding. The user may still pick `Other` on this prompt and request the full plan (whether or not large-plan summary mode applied on the prior emit). The executor MUST `cat` `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion` with the **same option set unchanged**; when `plan.txt` is missing or empty, print `**⚠ plan.txt missing or empty; nothing to show.**` instead and still re-fire the same prompt. The Other path does **not** mutate the option set on its re-prompt, so any number of repeat Other requests preserve the same option count. This differs from the structured `See full plan` option, which drops itself on its re-prompt. Gate C `Other` never cancels `/design`; it only displays the full plan when available and re-prompts.

### Loop exit

When the user picks **Approve final design**, proceed to Step 5b. The skill no longer fires a separate accept/regenerate/cancel prompt in Step 5b — Gate C is the only final-approval gate.

---

## State invariants across gates

1. **Latest plan to reviewers**: Step 3 (whether first-time or re-entry from Gate C(c)) always reads `$DESIGN_TMPDIR/plan.txt` as written by the most recent of: Step 2b initial plan write, or Gate B applied-set revision. No "ghost" prior-version plan is ever submitted to reviewers.

2. **No preserved findings across review runs**: when Step 3 is re-entered from Gate C(c), the prior `accepted-plan-findings.md` / `rejected-findings.md` / `oos.md` / `voting-tally.md` are overwritten by the new run; `oos-accepted-design.md` and per-round forensics under `plan-review/round-<N>/` from the prior review run are overwritten as well. Gate B operates on the latest run's artifacts only. **Within-loop carve-out**: during a single multi-round `plan-review-loop.sh` invocation, `oos-accepted-design.md` accumulates across inner rounds and per-round forensics under `plan-review/round-<N>/` accumulate across those rounds — see `plan-review.md` § Multi-round loop.

3. **Discussion outputs accumulate**: `discussion-round1.md` is written by Step 1d. Step 1d.7 writes the approved outline separately to `design-outline.md`. `discussion-round2.md` accumulates entries across all Gate A re-entries from Gate B(c) / Gate C(b). All three files remain readable inputs to subsequent plan revisions.

4. **Gate B apply contract**: in default auto-apply mode (no `--manual` flag), Gate B revises `plan.txt` by applying every accepted in-scope finding after the compact findings list, with no user prompt. In manual mode (`--manual` set), Gate B revises `plan.txt` only when the user explicitly picks option (a) Apply all or option (b) per-finding Apply. Gate A and Gate C never auto-revise `plan.txt`; Gate A may still revise `plan.txt` directly for user-resolved discussion outcomes per `discussion-rounds.md`, but Gate B never treats `discussion-round2.md` as patch instructions. The plan-review tally script writes artifact files only; it does not revise `plan.txt`. **Loop-internal carve-out**: the multi-round plan-review loop auto-applies accepted findings between inner rounds via `revise-plan-with-waterfall.sh`, bounded by `LARCH_DESIGN_ROUND_CAP` and the hardcoded single-round convergence rule in `plan-review-loop.sh` (≤5 non-nit accepted, 0 important; nits excluded) — this mechanical loop-internal revision is distinct from Gate B's user-driven apply contract. The mode is sticky for the entire `/design` run with this precedence chain: sourced `MANUAL_REQUESTED=true` override, then in-memory `manual_requested=true` override, then persisted `run-params.json` as the authority when it is readable, else the default auto-apply contract (`manual_gate_b=false`) remains in force.

5. **Assessor Stop cancellation**: when Step 3.6 `AskUserQuestion` picks **Stop** on a WORSE-majority verdict, `/design` sets `SUMMARY_OUTCOME=cancelled-assessor-worse`, runs the Final summary block, preserves `$DESIGN_TMPDIR`, and skips `[DESIGNED]` rename and design-log publish (see `assessor.md`).
