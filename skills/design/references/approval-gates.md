# Approval Gates Reference

**Consumer**: `/design` Step 1e (Gate A — discussion-mode loop), Step 3.5 (Gate B — post-review chooser), and Step 4b (Gate C — final-approval loop).

**Contract**: owns the three user-facing approval gates that bracket the design review pipeline. Gate A (scope discussion) and Gate C (final approval) always prompt the user. Gate B's behavior depends on `manual_gate_b` (set via `--manual` / `-m`): when `true`, the existing 3-option `AskUserQuestion` fires; when `false` (default), Gate B auto-applies every accepted in-scope finding after printing a compact findings list and an auto-apply breadcrumb. Gate A and Gate C always use `AskUserQuestion`; Gate B uses `AskUserQuestion` only in manual mode and may otherwise auto-apply. Reviewers always see the latest plan with all user-approved or auto-applied prior feedback applied.

**When to load**: before executing Step 1e, Step 3.5, or Step 4b.

**Binding convention**: single normative source for the three gate prompts, their per-tier behavior, the severity-classification rubric used in Gate B, and the loop semantics between A/B/C.

**Cross-tier invariant**: the gates apply uniformly across `--trivial`, `--simple`, and `--hard`. In `--trivial` and `--simple`, Gate A short-circuits on the first prompt (one round of "ready for review?"); in `--hard`, Gate A may iterate. Gate B and Gate C apply identically in all three tiers — the only difference is the source of findings (Gate B reads `accepted-plan-findings.md` produced by either `plan-review.md` full panel or `plan-review-quick.md` self-review). The auto-apply default and the `--manual` opt-out apply uniformly across `--trivial`, `--simple`, and `--hard`. In `--trivial` the source of `accepted-plan-findings.md` is the quick self-review (`plan-review-quick.md`); in `--simple` and `--hard` it is the full 10-reviewer panel. Gate B's mode branch reads `manual_gate_b` identically in all three tiers.

---

## Gate A — Discussion Mode Loop (Step 1e)

**When**: after Step 1d Round 1 settles (decisions recorded to `$DESIGN_TMPDIR/discussion-round1.md`, or the short-circuit breadcrumb printed). Also re-entered from Gate B option (c) and Gate C option (b).

**Behavior**: when the orchestrator believes the open scope/requirements questions are discussed, prompt the user via `AskUserQuestion`. The prompt has **two shapes** depending on entry path:

**Shape 1 — first-time entry (from Step 1d)**: exactly two options.

- **Ready for review** — exit Gate A; proceed to Step 2a (collaborative sketches → plan → Step 3 review).
- **Discuss more** — remain in Gate A; conduct another discussion sub-round, then re-prompt.

The **Show latest design proposal** option is **absent on first-time Gate A** because `$DESIGN_TMPDIR/plan.txt` does not yet exist (Step 2b has not run).

**Shape 2 — re-entry from Gate B(c) or Gate C(b) (post-plan)**: exactly three options.

- **Show latest design proposal** — re-display the current `$DESIGN_TMPDIR/plan.txt` under a `## Latest Design Plan` header (verbatim, no diff vs. prior version) and re-fire the same 3-option Gate A `AskUserQuestion`. This option never advances state; it loops back to the prompt.
- **Ready for review** — exit Gate A; proceed directly to Step 3 with the current `$DESIGN_TMPDIR/plan.txt` (Step 2a sketches and Step 2a.5 dialectic are NOT re-run on re-entry per the existing loop-exit semantics below).
- **Discuss more** — remain in Gate A; conduct another discussion sub-round, then re-prompt.

The trigger for Shape 2 is exactly "Gate A entered from Gate B(c) or Gate C(b)" — the same trigger that already routes the discussion sub-round body to `discussion-round2.md`.

Question text (both shapes): `"All open design questions appear discussed. Ready to launch the design review, or would you like to discuss more first?"` Header: `"Design discussion"`.

### Discussion sub-round body

When the user picks **Discuss more**, the orchestrator either (a) asks the user what additional aspect to discuss via a free-form follow-up, or (b) walks any remaining branch from the Step 1d decision tree that was deferred. Then re-prompt with the **same Gate A shape as the prior prompt**: Shape 1 uses the same two-option `AskUserQuestion` (Ready for review / Discuss more); Shape 2 uses the same three-option `AskUserQuestion` (Show latest design proposal / Ready for review / Discuss more). Append resolved decisions to `$DESIGN_TMPDIR/discussion-round1.md` (or `discussion-round2.md` when re-entered post-review — see "Re-entry from Gate B/C" below) using the existing Q&A schema in `discussion-rounds.md`.

**Per-tier behavior** (the prompt is always fired at least once before sketches/review; further iterations follow the user's **Discuss more** choice):
- `--trivial`: after Step 1d's short-circuit (`⏩ 1d: discussion r1 — no scope decisions require discussion`) prints, the user typically picks **Ready for review** on the first prompt. The loop still accommodates **Discuss more** if the user wants to add context.
- `--simple`: fire after Step 1d. Users typically pick **Ready for review** on the first prompt; the loop accommodates iteration without forcing it.
- `--hard`: same prompt; users are more likely to iterate.

### Re-entry from Gate B(c) or Gate C(b)

When Gate A is re-entered from Gate B option (c) ("switch to discussion mode") or Gate C option (b) ("discuss further"), the orchestrator is now post-plan. Write any new resolved decisions to `$DESIGN_TMPDIR/discussion-round2.md` rather than `discussion-round1.md` (Round 1 is closed once Step 2a begins). On a Gate B(c) / Gate C(b) re-entry to Gate A, the plan-modification authority depends on Gate B mode. In manual mode (`--manual`), `plan.txt` is revised only when the user picks Apply all or per-finding Apply on the next Gate B entry. In default auto-apply mode, `plan.txt` was already revised when Gate B last fired; Gate A re-entries do NOT silently revise `plan.txt` themselves in either mode. If the user agrees during discussion that a specific Gate B finding should now be applied (manual mode) or rolled back (auto-apply mode), record the agreement in `discussion-round2.md` and adjust during the subsequent Gate B iteration.

**Show latest design proposal branch (re-entry only)**: when the user picks Show latest design proposal on Shape 2, the orchestrator reads `$DESIGN_TMPDIR/plan.txt` and prints its content under a `## Latest Design Plan` header, then immediately re-fires the same 3-option Gate A `AskUserQuestion` until the user picks Ready for review or Discuss more. The Show-plan branch performs no state mutation and writes nothing to `discussion-round2.md`. If `$DESIGN_TMPDIR/plan.txt` is missing or empty on re-entry (should not happen — re-entry is post-plan by definition), print `**⚠ plan.txt missing or empty; nothing to show.**` and re-prompt anyway.

### Loop exit

When the user picks **Ready for review**:
- First-time entry (from Step 1d): proceed to Step 2a (sketches).
- Re-entry (from Gate B or Gate C): proceed directly to Step 3 (plan review) with the current `$DESIGN_TMPDIR/plan.txt`. Do NOT re-run sketches or dialectic.

---

## Gate B — Post-Review Chooser (Step 3.5)

**When**: after Step 3 review completes — `accepted-plan-findings.md` (and `rejected-findings.md`, `oos.md`) have been written by the tally script. **The plan has NOT been revised yet** (Gate B is the only path that revises `plan.txt` from review findings).

### Severity classification rubric

For each accepted in-scope finding in `$DESIGN_TMPDIR/accepted-plan-findings.md`, the orchestrator assigns one severity bucket based on the finding's `**Concern**:` text:

- **Critical** — would cause data loss, security breach, build/CI breakage on landing, or a regression a downstream consumer would detect within one release.
- **High** — would cause functional incorrectness in a primary code path, missing required documentation contract, or violates a stated invariant in the plan.
- **Medium** — improves robustness or clarity in a secondary path; addresses a real but recoverable edge case.
- **Low** — style, naming, or future-proofing; no functional change implied.

When the concern text is ambiguous, prefer the lower bucket and surface the ambiguity in the displayed description. Never invent severity for findings not present in the file.

### Presentation

When Gate B is in manual mode, print a table under the header `## Plan Review Findings — Review` listing every accepted finding, in `FINDING_N` order, with columns: ID, Severity, Reviewer(s), Concern. The Concern column is a 1-10 line description drawn from the finding's `**Concern**:` field (truncate to 10 lines max; never paraphrase the concern text). After the table, also print the rejected and OOS sections for context (read from `rejected-findings.md` and `oos.md`).

In default auto-apply mode, do **not** print the full review table above. The compact findings list in the auto-apply path below is the visibility surface for accepted findings on that branch; print rejected/OOS sections there once.

### Prompt

#### Gate B mode (auto-apply vs manual)

Determine Gate B mode defensively. If the in-memory boolean `manual_requested` from Step 0b is still bound, let `manual_requested=true` force `manual_gate_b=true` without consulting `run-params.json`; otherwise read `manual_gate_b` from `$DESIGN_TMPDIR/run-params.json` using `jq -r '.manual_gate_b // false'` so missing/null coerces to `false`. If `run-params.json` cannot be read, or `jq` is unavailable, print `**⚠ 3.5: Gate B — could not read manual_gate_b from run-params.json (<reason>).**`, append that warning under `Warnings` in `$DESIGN_TMPDIR/execution-issues.md` via `append-tool-failure.sh` when possible, and use `manual_gate_b=true` when `manual_requested=true`; otherwise use `manual_gate_b=false`.

When `manual_gate_b=false`, execute the auto-apply path:

1. Print `> **🔶 /design 3.5: gate B (auto-apply N findings)**` (substitute `N` with the accepted in-scope finding count).
2. Print a compact findings list under `## Plan Review Findings — Auto-applying`: one row per finding showing `FINDING_N | Severity | Reviewer(s) | <1-line concern excerpt>`. Use the same severity rubric and the same concern text source as the review table; truncate to the first 1-2 lines or 200 characters, whichever is shorter. Never paraphrase.
3. Also print the rejected and OOS sections for context (same reads from `rejected-findings.md` / `oos.md` as the presentation table).
4. Execute `### Apply-all body` verbatim.

When `manual_gate_b=true`, fire the `AskUserQuestion` block below verbatim.

`AskUserQuestion` with exactly three options:

- **Apply all** — Execute `### Apply-all body` verbatim. The dedup-sweep, `dedup-sweep:` breadcrumb, `ACTION=EMIT_PLAN`, validator invocation, and Step 2b.5 all run there.
- **Go through each** — Iterate findings in `FINDING_N` order. For each, fire `AskUserQuestion` (batch up to 4 findings per call) with three options: apply / skip / switch to discussion mode. After all findings resolved, revise `plan.txt` to incorporate only the applied subset. Before re-emitting `ACTION=EMIT_PLAN`, perform a duplicate-content sweep on the freshly revised `plan.txt`: re-read the file, use your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once — not just byte-identical text). Preserve intentional repetition where the same content appears in distinct context sections (e.g., a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section. Rewrite `plan.txt` via the Write tool with duplicates removed. Then print exactly one breadcrumb of the shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (use `0` when none were found — the breadcrumb always fires so operators see the sweep ran). Only after the breadcrumb proceed to `ACTION=EMIT_PLAN`, then when `review_budget` is `full` run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/invoke-plan-validator-if-not-quick.sh" "$DESIGN_TMPDIR/plan.txt"` as above, then run **Step 2b.5** as above, then proceed to Step 3b when Step 2b.5 returns. The Step 2b.5 call fires **once** per Gate B settled path (after the batch `EMIT_PLAN`), not once per per-finding apply. If at any per-finding prompt the user picks "switch to discussion mode", stop the iteration immediately, discard any unapplied per-finding intent, and exit to Gate A (no plan revision occurs on this exit path).
- **Switch to discussion mode** — Skip plan revision entirely. Exit to Gate A. `plan.txt` remains as it was before Step 3.
Question text: `"Plan review returned N findings (C critical / H high / M medium / L low). How would you like to handle them?"` Header: `"Plan findings"`. Substitute the actual counts before asking.

### Apply-all body

Apply every accepted in-scope finding to `$DESIGN_TMPDIR/plan.txt`, write the revised plan via the Write tool (full file replacement, preserving `diff_lines: <N>`). Before re-emitting `ACTION=EMIT_PLAN`, perform a duplicate-content sweep on the freshly revised `plan.txt`: re-read the file, use your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once — not just byte-identical text). Preserve intentional repetition where the same content appears in distinct context sections (e.g., a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section. Rewrite `plan.txt` via the Write tool with duplicates removed. Then print exactly one breadcrumb of the shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (use `0` when none were found — the breadcrumb always fires so operators see the sweep ran). Only after the breadcrumb proceed to `ACTION=EMIT_PLAN` so `diff-lines.txt` reflects the final plan. When `review_budget` is `full`, immediately run `"${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/invoke-plan-validator-if-not-quick.sh" "$DESIGN_TMPDIR/plan.txt"` (pipes `ACTION=VALIDATE_PLAN_COMMANDS` into `design-driver.sh`; same mechanical dispatch as `SKILL.md` Step 2b). Then run the **Step 2b.5 — Plan-size threshold check** procedure from `SKILL.md`. Only when Step 2b.5 returns to caller (no Split or Cancel selected) proceed to Step 3b (architecture diagram) — Step 4 (rejected-findings report) and Step 4b (Gate C) follow in normal sequence.

### One-by-one iteration prompt

For each finding when the user picks **Go through each**:

Question text: `"FINDING_<N> [<Severity>] — <reviewer>: <one-line concern summary>. Apply this finding to the plan?"` Header: `"Finding <N>/<total>"`. Options:
- **Apply** — record in the applied set.
- **Skip** — record in the skipped set; the finding moves from accepted to rejected.
- **Switch to discussion mode** — abort iteration; exit to Gate A; do NOT revise `plan.txt`.

After iteration completes (all findings answered without an early abort), the orchestrator revises `plan.txt` per the applied set only. Before re-emitting `ACTION=EMIT_PLAN`, perform a duplicate-content sweep on the freshly revised `plan.txt`: re-read the file, use your own reasoning to identify semantically duplicate lines or short blocks (the same constraint, requirement, or instruction stated more than once — not just byte-identical text). Preserve intentional repetition where the same content appears in distinct context sections (e.g., a constraint cited in both the Approach and Edge cases sections to reinforce it in each context); only remove duplicates that are truly redundant within or across the same section. Rewrite `plan.txt` via the Write tool with duplicates removed. Then print exactly one breadcrumb of the shape `dedup-sweep: removed <N> duplicate line(s) from plan.txt` (use `0` when none were found — the breadcrumb always fires so operators see the sweep ran). Only after the breadcrumb write the per-finding outcomes back to `$DESIGN_TMPDIR/accepted-plan-findings.md` (apply set retained) and `$DESIGN_TMPDIR/rejected-findings.md` (skip set appended with `Reason not implemented: rejected by user during one-by-one review`).

### Zero-findings short-circuit

When `$DESIGN_TMPDIR/accepted-plan-findings.md` is empty (no accepted in-scope findings — either no reviewer raised any, or voting rejected all), Gate B prints `⏩ 3.5: Gate B — no accepted findings; nothing to apply` and proceeds directly to Step 3b. This short-circuit fires before the mode branch: neither auto-apply nor the manual prompt runs. Step 3b → Step 4 → Step 4b (Gate C) run in normal sequence.

### Gate B plan revision and Step 2b.5

Gate B's plan revision may cause Step 2b.5 to branch: partition flag (`--partition`) routes directly to Split-path with no `AskUserQuestion`; hard trigger (`PLAN_LINES > 800` or `DIFF_LINES > 1500`) fires an `AskUserQuestion` with Split / Cancel only (no Continue option); otherwise Step 2b.5 returns silently. If Step 2b.5 exits the skill on **Cancel** (cost line + exit 0) or **Split** (Split-path: decomposition panel + exit 1), `$DESIGN_TMPDIR` is preserved and the operator can re-run after addressing sprawl.

---

## Gate C — Final-Approval Loop (Step 4b)

**When**: after Step 4 (rejected-findings report) completes. Step 4 is reached on every Gate B settled path: auto-apply → Step 3b → Step 4 → Step 4b; Apply all → Step 3b → Step 4 → Step 4b; Go through each (without abort) → Step 3b → Step 4 → Step 4b; zero-findings short-circuit → Step 3b → Step 4 → Step 4b. Gate B(c) "switch to discussion mode" exits to Gate A and never reaches Gate C until the user later picks "Ready for review" + the new review completes its own Gate B settled path. Gate C is also re-entered from Gate C(b) "discuss further" → Gate A loop → eventual re-review → Step 4 → Step 4b.

### Presentation

**Mandatory — immediately before the Prompt section below.** The executor MUST run the Step 4b `SKILL.md` fenced Bash block that invokes `emit-design-plan-preview.sh --variant gatec` (the shared large-plan summary path). When `$DESIGN_TMPDIR` is set to a directory and `$DESIGN_TMPDIR/plan.txt` is present and non-empty, that block emits the plan under a `## Final Design Plan` header (summary or full body per the threshold rules in the Large-plan summary mode subsection). **Defined exception — warning-only path:** when `$DESIGN_TMPDIR` is unset or not a directory, the block prints `**⚠ 4b: DESIGN_TMPDIR missing or invalid; cannot present final design plan**` and execution continues to the Prompt without a plan header/body. When `plan.txt` is missing or empty (should not happen on this path), the block prints `**⚠ 4b: plan.txt missing or empty; cannot present final design plan**` and execution continues to the Prompt the same way.

**Large-plan summary mode**: the shared Bash (`skills/design/scripts/emit-design-plan-preview.sh`) uses `LARCH_DESIGN_PLAN_SUMMARY_THRESHOLD` (default `120`, positive integers only; `0`, empty, non-numeric values, or values with a leading zero fall back to `120`; comparisons use base-10 integer coercion). The same threshold, strict `line_count > threshold` rule, outline cap (40 matching `##`/`###` lines via `grep -E '^#{2,3} '`), empty-outline fallback (first 30 lines of `plan.txt`), and bold-note behavior apply at Step 3's `## Plan Candidate for Review` emit and at Gate C's `## Final Design Plan` emit. When the plan's line count strictly exceeds the threshold, the block emits only the plan title (first line) plus a section outline plus a bold note pointing at the full plan; if the outline is empty, the block falls back to the first 30 lines of `plan.txt`. The outline is best-effort and may include `##`/`###` lines from inside fenced code blocks. When the user picks `Other` on the Prompt below and asks for the full plan, the executor MUST `cat` the full `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion` — including when the plan was already printed in full (non-summary path); the three primary options are unchanged after the re-prompt.

### Prompt

`AskUserQuestion` with three primary options plus the host's standard `Other` free-form channel:

- **Approve final design** — exit Gate C; proceed to Step 5b publish (compose `composed-plan.md`, write `larch:plan` block to issue, run `design-log-publish.sh`, rename tracking issue).
- **Discuss further** — re-enter Gate A (Step 1e) with the current plan; the discussion sub-round writes to `discussion-round2.md`.
- **Re-run review panel** — re-enter Step 3 with the current `plan.txt` (which already reflects all user-approved or auto-applied prior feedback). Do NOT re-run sketches or dialectic. Step 3.5 (Gate B) will fire again on the fresh findings. Findings from prior review runs are NOT preserved — each review is a fresh look at the latest plan.

Question text: `"Final design plan is ready. Approve, discuss further, or re-run the review panel against this plan?"` Header: `"Final design"`.

**Opt-in to see the full plan via `Other`**: the user may pick `Other` on this prompt and request the full plan (whether or not large-plan summary mode applied on the prior emit). The executor MUST `cat` `$DESIGN_TMPDIR/plan.txt` into chat and re-fire the same Gate C `AskUserQuestion`; the three primary options (Approve / Discuss further / Re-run review panel) are unchanged. This Gate C `Other` behavior is distinct from the Step 0 tier-gate `Other` (which is a terminal cancel) — Gate C `Other` never cancels `/design`; it only displays the full plan and re-prompts.

### Loop exit

When the user picks **Approve final design**, proceed to Step 5b. The skill no longer fires a separate accept/regenerate/cancel prompt in Step 5b — Gate C is the only final-approval gate.

---

## State invariants across gates

1. **Latest plan to reviewers**: Step 3 (whether first-time or re-entry from Gate C(c)) always reads `$DESIGN_TMPDIR/plan.txt` as written by the most recent of: Step 2b initial plan write, or Gate B applied-set revision. No "ghost" prior-version plan is ever submitted to reviewers.

2. **No preserved findings across review runs**: when Step 3 is re-entered from Gate C(c), the prior `accepted-plan-findings.md` / `rejected-findings.md` / `oos.md` / `voting-tally.md` are overwritten by the new run. Gate B operates on the latest run's artifacts only.

3. **Discussion outputs accumulate**: `discussion-round1.md` is written by Step 1d / Gate A on first-time entry. `discussion-round2.md` accumulates entries across all Gate A re-entries from Gate B(c) / Gate C(b). Both files remain readable inputs to subsequent plan revisions.

4. **Gate B apply contract**: in default auto-apply mode (no `--manual` flag), Gate B revises `plan.txt` by applying every accepted in-scope finding after the compact findings list and the auto-apply breadcrumb, with no user prompt. In manual mode (`--manual` set), Gate B revises `plan.txt` only when the user explicitly picks option (a) Apply all or option (b) per-finding Apply. Gate A and Gate C never auto-revise `plan.txt`. The plan-review tally script writes artifact files only; it does not revise `plan.txt`. The mode is sticky for the entire `/design` run and is read from `manual_gate_b` in `run-params.json` on every Gate B entry.
