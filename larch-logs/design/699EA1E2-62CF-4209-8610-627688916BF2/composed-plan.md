## Plan

## Files to modify/create

### UPDATED: `skills/design/SKILL.md`

- Gate Step 5b.5 `readability-style.md` on `DIAGRAM_REQUIRED=true`.
  - Keep the false path as: skip, continue to Step 5c, no diagram prose.
  - Move the read directive into the `DIAGRAM_REQUIRED=true` branch only.
- Narrow the downgrade rule to **small always-needed references** and **explicit readability / load-timing sites** only.
  - Downgrade all-caps `MANDATORY — READ ENTIRE FILE` to plain `Read` where the active step always needs the file (for example Step 2b `readability-style.md` before drafting).
  - Pin the Step 2b replacement line exactly (plain `Read`, no `readability-style.md`.**` anchor):
    - `Read `skills/design/references/readability-style.md` before drafting the implementation plan.`
  - **Do not** downgrade branch-critical normative full-file reads: `flags.md`, `approval-gates.md`, `decompose-panel.md`, `plan-review.md`, `discussion-rounds.md`, and similar normative branch-entry references stay `MANDATORY — READ ENTIRE FILE`.
  - Preserve the same order and same target paths within each edited site.
  - Do not weaken conditional fail-closed routing language.
- Make duplicate-load hedges consistent.
  - Keep existing `(if not already loaded at Step 1e)` language.
  - Add the same style where Gate A / Gate B settle dispatch can reuse an already loaded `settle-rc-dispatch.md`.
  - Pin the two SKILL settle item-1 replacements exactly:
    - Gate A (Step 1e): `1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at discussion-round2).`
    - Gate B (Step 3.5): `1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at Step 1e).`
  - Keep item 2 branch directives unchanged immediately after each hedged item 1.
- Gate Step 1d.5 `brainstorm.md` load on a firm non-skip signal **before** removing the unconditional read.
  - Run `step1d5 --mode entry` first.
  - Remove the unconditional `MANDATORY — READ ENTIRE FILE` for `brainstorm.md` that currently fires before the in-file entry guard.
  - **Immediately after** the entry fence, apply a prompt-side guard that does **not** depend on nonexistent entry KVs:
    - Read `$DESIGN_TMPDIR/run-params.json` and bind `brainstorm_requested` (default `false` when absent).
    - If `brainstorm_requested` is not `true`, or `$DESIGN_TMPDIR/.brainstorm-done` exists: print the existing skip breadcrumb, run `step1d5 --mode complete`, and continue to Step 1d.7 without reading `brainstorm.md`.
    - Only on the run path (`brainstorm_requested=true` and `.brainstorm-done` absent): **MANDATORY — READ ENTIRE FILE** `brainstorm.md` and execute the Step 1d.5 body per that reference.
  - Do not rely on `step1d5 --mode entry` emitting skip/run KVs unless this plan also updates `python/design_lifecycle.py` to emit them (out of scope).
- Keep Step 2b direct-drafting inputs unchanged.
  - `approach-synthesis.txt=NO_SKETCHES` still means draft from direct inspection.
  - Approved outline and brainstorm inputs remain conditional exactly as documented.

### UPDATED: `skills/design/references/settle-rc-dispatch.md`

- Remove the top-level `readability-style.md` force-read.
- Do not replace it with another style load.
- Rationale: this reference branches on wrapper rc / KVs and emits no new user-facing prose.

### UPDATED: `skills/design/references/oos-step5b-dispatch.md`

- Remove the top-level `readability-style.md` `MANDATORY — READ ENTIRE FILE` line.
- Rationale: same as `settle-rc-dispatch.md`; this reference only branches on `NEXT_ACTION` / `FILE_DESIGN_OOS_STATUS` KVs and emits no new user-facing prose.

### UPDATED: `skills/design/references/design-outline.md`

- Downgrade the `readability-style.md` all-caps `MANDATORY` line to plain `Read`.
- Pin the replacement line exactly (plain `Read`, no `readability-style.md`.**` anchor):
  - `Read `skills/design/references/readability-style.md` before composing the outline.`
- Preserve the requirement to read style before composing the outline.
- Do not alter the outline schema, entry guard, approval sentinel, or output contract.

### UPDATED: `skills/design/references/brainstorm.md`

- Move the `brainstorm-prompts.md` `MANDATORY — READ ENTIRE FILE` directive below the **Entry guard** section.
- Read `brainstorm-prompts.md` only after guards pass and brainstorm will run (not on `brainstorm_requested=false` or `.brainstorm-done` skip paths).
- Preserve brainstorm synthesis, external slot launch, and discussion-loop contracts.
- Keep the post-guard `readability-style.md` load for prompt substitution and synthesis prose unchanged in strength; only relocate `brainstorm-prompts.md` relative to the entry guard.

### UPDATED: `skills/implement/SKILL.md`

- Replace the `Execution Issues Tracking` section-level mandatory load with an index / reachability note.
- Move load responsibility to active call sites:
  - OOS triage policy: read `execution-issues-tracking.md` only when an OOS candidate must be triaged.
  - `Pre-existing Code Issues` dual-write: read it only when a pre-existing-code issue is being recorded or triaged.
  - Self-review OOS handling: add a **new numbered self-review step 3** immediately after step 2 (diff capture) and **before** the review pass:
    - **MANDATORY — READ ENTIRE FILE** `execution-issues-tracking.md`.
    - Renumber the live self-review block with this explicit post-insert map (preserve fractional step 4.5):
      - **1** plan read (unchanged)
      - **2** diff capture (unchanged)
      - **3** policy read (`execution-issues-tracking.md`) — **new**
      - **4** review pass (former step 3)
      - **4.5** `write-pre-self-review-snapshot` fence (former step 3.5; keep the same Bash fence and `review-and-fix write-pre-self-review-snapshot` call)
      - **5** apply fixes / disposition (former step 4)
      - **6** rejected findings (former step 5)
      - **7** run checks (former step 6)
      - **8** commit-route (former step 7)
      - **9** log completion (former step 8)
      - **10** write-self-review-tally (former step 9)
      - **11** proceed to Step 6 chain (former step 10)
    - **Remove** the parenthetical `MANDATORY — READ ENTIRE FILE` from the renumbered review step 4(f); that bullet references the policy loaded at step 3 only.
    - Step 5 disposition (former step 4) keeps triage references pointing at the step 3 load; do not add a second full-file read there.
  - Step 8 `NEXT_ACTION=oos-pipeline`: **MANDATORY — READ ENTIRE FILE** `execution-issues-tracking.md` immediately before following `oos-pipeline.md`.
- Keep all current execution behavior.
  - Do not change categories, schemas, OOS disposition rules, or dual-write outcomes.
  - Do not change external implementer envelope validation.
- Remove the `summary-comment-template.md` mandatory read from Step 2.5 entirely.
  - Step 2.5 only appends inline Q/A rows to `execution-issues.md`; it does not compose `upsert-summary` publication text.
  - **Do not** add new orchestrator `summary-comment-template.md` reads at Step 0, Step 9a.1, Step 18, or other script-owned publication fences (`post-tracking-issue.sh`, `python/cli.py execution-issues refresh` under Step 8+, `python/cli.py final-report write`).
  - Upsert-summary bodies are composed by scripts/Python, not prompt-side prose at those steps; adding orchestrator preloads would recreate the Step 2.5 waste.

### UPDATED: `skills/implement/references/summary-comment-template.md`

- Fix the **When to load** contract:
  - Remove the nonexistent **Step 11** anchor.
  - State that orchestrator prompt-side composition does not load this reference on normal runs.
  - Pin maintainers to load when editing script-owned publication surfaces: `post-tracking-issue.sh`, `python/cli.py execution-issues refresh` (Step 8+ `execution-issues refresh` fence), and `python/cli.py final-report write` / Step 16–17 final-report paths.
  - Do not add SKILL-level orchestrator mandatory reads for those fences.

### UPDATED: `skills/implement/references/phantom-probe.md`

- Downgrade `When to load` from unconditional `MANDATORY — READ ENTIRE FILE`.
- State the actual trigger:
  - Read before parsing non-clean `PHANTOM_*` telemetry that requires orchestrator action.
  - Read before changing phantom-probe call sites.
  - Do not require a full-reference read when the already parsed macro path is a no-op, such as `PHANTOM_STATUS=clean`.
- Preserve the registry, six-site count, advisory-only semantics, and no-`eval` parsing rule.

### UPDATED: `scripts/lint-readability-preamble.tsv`

- Keep manifest counts aligned with `python/cli.py lint readability-preamble`, which counts orchestrator-inline matches of the substring `readability-style.md`.**` (plain `Read` lines without that suffix do not count).
- Apply these row updates in the same change:
  - `skills/design/references/settle-rc-dispatch.md`: `expected_count` `1` → `0` (remove the row or zero the count; smallest manifest-only change is fine).
  - `skills/design/references/design-outline.md`: `expected_count` `1` → `0` (downgraded plain `Read` line drops the anchor).
  - `skills/design/SKILL.md`: `expected_count` `3` → `2`; `step_markers` `2b,5` → `5` only (Step 2b loses the anchor; Step 5b.5 gated `DIAGRAM_REQUIRED=true` and Step 5c `MANDATORY` lines remain under `<!-- step:5 -->` and still satisfy per-step placement).
- Rationale: without these three adjustments, `make lint` fails after the downgrades even though the feature behavior is correct.

### UPDATED: `scripts/test-design-structure.sh`

- Update the two SKILL settle-dispatch `assert_followed_count_at_least` adjacency needles (current lines 248–249) to match the hedged item-1 text pinned in `skills/design/SKILL.md`.
- Pin the replacement first-needle literals exactly:
  - Gate A: `1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at discussion-round2).`
  - Gate B: `1. **MANDATORY — READ ENTIRE FILE**: Read `${CLAUDE_PLUGIN_ROOT}/skills/design/references/settle-rc-dispatch.md` completely (if not already loaded at Step 1e).`
- Keep each second needle (item 2 branch directive) unchanged.
- Do not alter the `approval-gates.md` or `discussion-rounds.md` settle needles unless their SKILL call-site item-1 text changes in the same PR (out of scope here).

### MAY_UPDATE: `skills/design/scripts/test-brainstorm-prompts.sh`

- If relocating `brainstorm-prompts.md` load below the entry guard changes the grep anchor, update the harness to assert the post-guard placement instead of the pre-guard position.
- Do not change prompt content contracts.

## Approach

- Keep this as a focused prompt-text sweep.
- Change load timing and directive strength only.
- Do not edit reference bodies except scoped `When to load` / readability directive lines, the brainstorm entry-guard ordering fix, the `summary-comment-template.md` maintainer contract fix, and the readability-preamble manifest rows for settle, design-outline, and SKILL.md.
- Prefer exact local rewrites over reorganizing sections.
- Preserve all sentinel, KV, branch, and artifact contracts.
- Apply the no-prose dispatch-table pattern consistently: `settle-rc-dispatch.md` and `oos-step5b-dispatch.md` both drop style preloads; do not extend that pattern to normative branch-entry references.
- For publication templates, delete orchestrator no-op preloads only; rely on script-maintainer `When to load` notes instead of new SKILL hot-path reads.
- Pin the self-review renumber as an explicit integer + fractional map so step 3.5 (`write-pre-self-review-snapshot`) becomes step 4.5 and no step numbers collide.
- When downgrading `MANDATORY` to plain `Read`, use the pinned one-line forms above and update `lint-readability-preamble.tsv` in the same PR; do not invent alternate wording that still accidentally includes `readability-style.md`.**` unless the manifest is updated to match.
- When adding settle duplicate-load hedges in `skills/design/SKILL.md`, update `scripts/test-design-structure.sh` adjacency literals in the same PR so `make lint` structure pins stay aligned with live orchestrator prose.

## Edge cases

- If a reference is needed to decide a branch, keep the read before that branch.
- If a branch is already known as a no-op from a wrapper macro key, do not force-read the routing reference solely for confirmation.
- If `brainstorm_requested=false` or `.brainstorm-done` exists, Step 1d.5 must not force-read `brainstorm.md` or `brainstorm-prompts.md`; the prompt-side guard after `step1d5 --mode entry` must use `run-params.json` and `.brainstorm-done`, not absent entry KVs.
- If Q/A does not occur, Step 2.5 must not preload the summary template.
- If Q/A occurs but no `upsert-summary` publication runs, keep `execution-issues.md` schema intact; orchestrator does not load `summary-comment-template.md`.
- If `DIAGRAM_REQUIRED=false`, Step 5b.5 must not load style or compose diagram prose.
- Self-review must load OOS triage policy at new step 3 before the review pass; renumbered step 4(f) must not retain a duplicate inline `MANDATORY` read.
- Self-review step 4.5 must remain the `write-pre-self-review-snapshot` fence between review (step 4) and apply/disposition (step 5); do not fold 4.5 into an integer step or drop the snapshot.
- Review-only or implement runs that reach Step 8 `oos-pipeline` without hitting earlier OOS call sites must still load `execution-issues-tracking.md` on that branch.
- Plain `Read` downgrades for Step 2b and `design-outline.md` must not leave `lint-readability-preamble.tsv` expecting the old `readability-style.md`.**` counts or the old `2b` step-marker placement.
- If discussion-round2 already loaded `settle-rc-dispatch.md`, Gate A Step 1e may skip the duplicate read via the discussion-round2 hedge; Gate B must still read when Step 1e did not run on that path.

## Failure modes

- **Over-conditioning a policy read**: the agent may skip needed OOS or dual-write policy.
  - Warning signal: instructions ask for triage or filing without first reading `execution-issues-tracking.md`.
  - Mitigation: keep explicit reads at each active OOS / pre-existing-code / self-review step 3 / Step 8 `oos-pipeline` call site.
- **Duplicate self-review policy load**: adding step 3 without removing the inline step 4(f) `MANDATORY` forces two full reads per `--self-review` run.
  - Warning signal: both step 3 and step 4(f) carry `MANDATORY — READ ENTIRE FILE` for `execution-issues-tracking.md`.
  - Mitigation: one read at step 3 only; step 4(f) references that load.
- **Self-review step-number collision**: integer-only renumbering can orphan step 3.5, duplicate numbers, or leave snapshot prose on the wrong step.
  - Warning signal: live block still shows `3.5` after insert, or `write-pre-self-review-snapshot` is missing between review and apply.
  - Mitigation: apply the pinned map (3 → policy read; old 3 → 4; old 3.5 → 4.5; old 4–10 → 5–11) verbatim.
- **Changing behavior while changing wording**: a branch may move or lose fail-closed semantics.
  - Warning signal: route predicates, rc handling, or artifact names change in the diff.
  - Mitigation: review the diff for non-wording changes to KVs, paths, and branch tables.
- **Over-broad downgrade in design SKILL**: downgrading normative branch-entry reads weakens prompt contracts without reducing no-op loads.
  - Warning signal: `flags.md`, `approval-gates.md`, `decompose-panel.md`, or `plan-review.md` lose `MANDATORY`.
  - Mitigation: restrict downgrades to small always-needed refs and explicit readability/load-timing sites only.
- **Recreating template preload waste**: adding orchestrator `summary-comment-template.md` reads at script-owned publication fences.
  - Warning signal: SKILL gains new `MANDATORY` template lines at Step 0 / 9a.1 / 18 / Step 8+ refresh without prompt-side composition.
  - Mitigation: delete Step 2.5 preload only; fix `summary-comment-template.md` **When to load** for script maintainers.
- **Stale readability-preamble manifest**: removing or downgrading orchestrator-inline style directives without updating `lint-readability-preamble.tsv` leaves false-positive lint expectations.
  - Warning signal: `make lint` fails on `readability-preamble` for `settle-rc-dispatch.md`, `design-outline.md`, or `skills/design/SKILL.md` after the edits.
  - Mitigation: zero settle and design-outline counts; set SKILL.md `expected_count` to `2` and `step_markers` to `5` only in the same change.
- **Step-marker placement drift**: lowering SKILL.md count without dropping `2b` from `step_markers` fails placement lint even when the file-level count is correct.
  - Warning signal: `skills/design/SKILL.md: step "2b": expected >=1 orchestrator-inline readability-style directive in step body, found 0`.
  - Mitigation: change `step_markers` from `2b,5` to `5` when Step 2b uses plain `Read`.
- **Stale structure-test settle needles**: adding duplicate-load hedges to SKILL settle item 1 without updating `test-design-structure.sh` adjacency literals.
  - Warning signal: `make lint` fails on `SKILL Gate A guard must load settle dispatch immediately before branch directive` or the Gate B sibling assertion.
  - Mitigation: update lines 248–249 needles to the pinned hedged item-1 literals in the same PR.
- **Lint expecting literal anchors**: `agent-lint` may pin some paths or wording.
  - Warning signal: `make lint` fails on S030 or prompt-shape checks.
  - Mitigation: keep literal paths in `SKILL.md` and update only directive wording; adjust `test-brainstorm-prompts.sh` if brainstorm placement moves.

## Testing strategy

- Run `grep -RIn "MANDATORY .*READ ENTIRE FILE" skills/design skills/implement`.
- Manually inspect each remaining hit across both skills.
  - It should be branch-critical, truly always required, or outside this feature's scope.
  - Confirm `settle-rc-dispatch.md` and `oos-step5b-dispatch.md` no longer preload `readability-style.md`.
  - Confirm `brainstorm-prompts.md` load sits after the brainstorm entry guard.
  - Confirm Step 1d.5 SKILL prose gates `brainstorm.md` on `run-params.json` + `.brainstorm-done`, not on absent entry KVs.
  - Confirm normative branch-entry reads (`flags.md`, `approval-gates.md`, `decompose-panel.md`, `plan-review.md`) remain `MANDATORY`.
  - Confirm self-review has exactly one `execution-issues-tracking.md` full read at new step 3; renumbered step 4(f) has no inline `MANDATORY`.
  - Confirm self-review step 4.5 still runs `write-pre-self-review-snapshot` between step 4 review and step 5 apply/disposition.
  - Confirm disposition prose references **step 5 (former step 4)**, not step 4.
  - Confirm `summary-comment-template.md` has no new orchestrator reads in `skills/implement/SKILL.md`; Step 2.5 preload is gone; **When to load** no longer cites Step 11.
  - Confirm Step 2b and `design-outline.md` use the pinned plain `Read` lines (no `readability-style.md`.**` suffix).
  - Confirm SKILL Gate A and Gate B settle item-1 lines carry the pinned duplicate-load hedges and `test-design-structure.sh` lines 248–249 needles match them verbatim.
- Confirm `scripts/lint-readability-preamble.tsv` rows:
  - `settle-rc-dispatch.md` `expected_count=0`
  - `design-outline.md` `expected_count=0`
  - `skills/design/SKILL.md` `expected_count=2` and `step_markers=5` only
- Run `make lint`.
- Do not run Python-only tests unless Markdown lint points to a Python-rendered contract.

## Acceptance

- All 5 target files edited per the plan.
- `settle-rc-dispatch.md` and `oos-step5b-dispatch.md` have no `readability-style.md` load.
- `design-outline.md` uses the pinned plain `Read` form.
- `brainstorm.md` loads `brainstorm-prompts.md` only after its entry guard.
- `design/SKILL.md`: Step 1d.5 is gated on `run-params.json`; Step 5b.5 style load is gated on `DIAGRAM_REQUIRED=true`; settle item-1 at Gate A and Gate B carry duplicate-load hedges; Step 2b uses plain `Read` for `readability-style.md`.
- `implement/SKILL.md`: section-level MANDATORY removed; self-review has exactly one `execution-issues-tracking.md` read at new step 3 with explicit renumber map; Step 2.5 has no `summary-comment-template.md` load.
- `summary-comment-template.md` When to load updated.
- `phantom-probe.md` When to load updated.
- `lint-readability-preamble.tsv` rows corrected.
- `test-design-structure.sh` adjacency needles updated.
- `make lint` passes.

review_status: complete
rounds_completed: 5
diff_lines: 152
