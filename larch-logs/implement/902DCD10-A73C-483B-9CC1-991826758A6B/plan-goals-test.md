## Goal
Implement issue #5274: [IMPLEMENTING] md-to-py-V: dedup implement checks-failure + durable-bail-to-Step-18 prose.

## Implementation Plan
## Plan

## Inputs read

- `approach-synthesis.txt`: `NO_SKETCHES`; draft from direct inspection.
- `discussion-round1.md`: prose-only dedup in `skills/implement/SKILL.md`; no Python changes; no new reference files beyond section 4 edit to existing `checks-repair-loop.md`.
- `design-outline.md`: not present; no approved outline scope.
- `brainstorm.md`: not present.

## Approach

- **Merge precondition:** Implement only after commit-route (#5271) is merged. Start from a tree where the three absorbed commit-route envelope sites already use commit-route durable seeding, not prompt-side `STALL_TRACKING` when seed is absent.
- Make the minimum prose-only change in `skills/implement/SKILL.md` plus a **section 4-only** alignment edit in `skills/implement/references/checks-repair-loop.md`.
- Add a named **Checks Failure Entry Macro** near the existing macro section (parallel to **Rebase Checkpoint Macro**).
  - Macro owns post-`STATUS=fail` routing after the mandatory `checks-repair-loop.md` read: pinned `--site` / `--checks-site` lookup, `NEXT_ACTION=continue`, `NEXT_ACTION=main-agent-edit`, and `NEXT_ACTION=stall`, anti-halt wording, and site-specific success continuations.
  - **Do not** replace harness-pinned local blockquote tokens at `run-step-checks.sh` call sites (see **Preserved local contract**).
  - Keep `skills/implement/references/checks-repair-loop.md` authoritative for pinned site pairs, `NEXT_ACTION` semantics, and the full `main-agent-edit` repair contract (escalation recording, tail reads, Edit/Write, capture rerun, same-site-pair re-entry).
  - **Single execution owner for Step 5 MAV/coder terminal stall:** both the macro and `checks-repair-loop.md` §4 must agree that terminal `NEXT_ACTION=stall` at MAV/coder sites is a **routing summary only**; do not record-only or durable-seed inline. Execution defers to the main-agent handoff paragraph and fence (~639–642).
- Shorten the five `STATUS=fail` entry blockquotes by moving shared post-read routing into the macro while **retaining** the harness-required opener and token set in each local blockquote.
- Add a named **Durable Bail to Step 18 Macro** near **Rebase Checkpoint Macro**.
  - Delegate durable-state semantics to `skills/implement/references/step5-review-branches.md` `stall` section (lint-fix bail-value subset, empty bail otherwise, present-state key rewrite for `STALL_TRACKING` / `STALL_STEP` / `BAIL_REASON` and existing `IMPLEMENT_BAIL_REASON` stale-clearing, create-if-absent vs present-state branch).
  - **Do not** describe `--bail-reason` as a passthrough of orchestrator `$STALL_REASON`.
  - **Pin `STALL_STEP=5` / `--stall-step 5` for every Step 5 durable-bail invocation.** Call sites supply only bail-derivation inputs (`$STALL_REASON` for lint-fix token lookup); the step number is not a call-site delta.
  - **Force prompt-side `STALL_TRACKING=true` immediately before durable seeding or key rewrite** at every macro execution site. Do not reuse the earlier parsed Step 5 envelope `STALL_TRACKING` value (e.g. `false` from `main-agent-vote-required` or `coder-main-agent-required`). Persist `STALL_TRACKING=true` in both prompt-side state and durable `ship-pr-state.sh`.
  - Create-if-absent seeding uses the existing one-line `larch-run.sh` `step-8-seed-initial.sh` pattern from `step5-review-branches.md`; cross-ref **Initial state seeder contract** (Step 8) and `step-8-seed-initial.md`. **Do not** add new Bash fences or inline seeder argv assembly in the macro body.
  - Present-state rule unchanged: key-based rewrite without sourcing `ship-pr-state.sh`.
  - Step 18 recovery ordering unchanged: stall recovery before final report.
- **Single execution owner for Step 5 durable bail:** MAV/coder pre-fence blockquote terminal-stall lines are **routing summaries only**; they must defer to the main-agent handoff paragraph and fence (~639–642) without restating `step-5-resume.sh --record-only` or seeder steps. The handoff paragraph plus the `--record-only` fence is the **sole execution site** for record-only timing capture followed by defensive `STALL_TRACKING=true` and **Durable Bail to Step 18 Macro**. Do not inline seeding or record-only in blockquotes before checks complete; do not double-invoke record-only plus durable bail across both layers.
- **Align `checks-repair-loop.md` §4 with the same single-owner rule:** replace the current MAV/coder site override (inline `step-5-resume.sh --record-only` and durable-bail routing) with defer-to-handoff wording that names the main-agent handoff paragraph (~639) as the sole record-only + durable-bail execution site. Keep pinned `--site step5-mav --checks-site step5-review-fixes` and the full `main-agent-edit` contract unchanged.
- Apply **Durable Bail to Step 18 Macro** only at the main-agent handoff terminal stall path (~639): after `step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only` (fence ~642; both flags required), set `STALL_TRACKING=true` (defensive, default true), then invoke the macro with pinned `STALL_STEP=5`.
- **Do not** apply the durable-bail macro at the `stall` branch stub (`STEP5_REVIEW_STATUS=stall`). That stub already mandates **MANDATORY — READ ENTIRE FILE** `step5-review-branches.md`; authority stays there.
- At the `stall` stub only: delete the redundant seed-only inline sentence (current partial seeder prose at ~SKILL.md:623). Keep a single delegation line: follow the `stall` branch body in the Step 5 review-branches reference; skip to Step 18.
- **Out of scope** for durable-bail macro replacement (commit-route already owns durable seeding):
  - Step 5 self-review invalid commit-route envelope (~SKILL.md:584).
  - Step 5 resume lacks-envelope / invalid commit-route paths (~SKILL.md:657).
  - Step 7 invalid commit-route envelope (~SKILL.md:708).
- Keep Step 5 self-review post-repair-loop terminal stall (~SKILL.md:576) **separate**: default `STALL_TRACKING=true`, skip to Step 18 per `checks-repair-loop.md` section 4, **no** durable-bail macro and **no** `ship-pr-state.sh` seeding.
- Do not move logic into Python. Do not add a new reference file.
- Avoid adding, removing, or converting Bash fences. If fence count changes anyway, update fence-shape test counts.

## Preserved local contract (harness-pinned)

`skills/implement/scripts/test-implement-relevant-checks-anti-halt.sh` scans the **five physical lines** immediately before each `run-step-checks.sh` invocation. Each of the **four** launcher sites must keep in that window (typically one compact local blockquote line plus site deltas):

- `> **Continue after child returns.**`
- The literal token `RELEVANT_CHECKS_SKIPPED=true` (harness-required; `RELEVANT_CHECKS_OK=true` may remain only when `RELEVANT_CHECKS_SKIPPED=true` is also present in the same five-line window)
- `REDACTED_LOG_FILE` (checks failure, NOT raw `LOG_FILE`) when present
- `NOT raw \`LOG_FILE\``

The **Checks Failure Entry Macro** lives in the macro section and governs post-read routing only. After the local line references the macro and site token, call sites still state where `NEXT_ACTION=continue` goes. Do not change the harness; do not broaden to macro-only pointers at fence boundaries.

**MAV blockquote outside harness window (~626):** The MAV `main-agent-vote-required` blockquote sits **before** the shared `run-step-checks.sh --site step5-review-fixes` fence (~635) and is **not** scanned by the five-line anti-halt harness. It must **independently** retain the full checks-failure entry contract even though only the coder blockquote (~630) is harness-adjacent:

- Success guidance including MAV success log and `RELEVANT_CHECKS_SKIPPED=true` (and `RELEVANT_CHECKS_OK=true` only if skipped token is also present)
- On `STATUS=fail`, `REDACTED_LOG_FILE` (checks failure, NOT raw `LOG_FILE`) when present
- **MANDATORY — READ ENTIRE FILE**: `checks-repair-loop.md`
- Reference to **Checks Failure Entry Macro** with pinned `--site step5-mav --checks-site step5-review-fixes`
- `NEXT_ACTION=continue` -> deferred record->commit->resume
- `NEXT_ACTION=main-agent-edit` delegation via macro/reference
- Terminal `NEXT_ACTION=stall` -> routing summary only (defer to handoff ~639); **no** inline `step-5-resume.sh --record-only` or seeder prose

Shortening the MAV blockquote must not strip checks-failure entry to success-log plus stall deferral only.

**Four `run-step-checks.sh` sites / five `STATUS=fail` entries:**

| Site | Fence `--site` | Local deltas to keep after macro reference |
|------|----------------|--------------------------------------------|
| Step 3 | `step3` | Step 4 commit (impl) success; in-Step-3 anti-halt |
| Step 5 self-review | `step5-self-review` | continue self-review flow; keep line 576 post-repair stall handler separate (below) |
| Step 5 MAV | `step5-review-fixes` (capture); blockquote ~626 **outside** harness window | **Full checks-failure opener/token set + macro reference required independently** (see MAV row above); MAV success log; `NEXT_ACTION=continue` -> deferred record->commit->resume; terminal `NEXT_ACTION=stall` -> routing summary only: defer to main-agent handoff terminal-stall path (~639) for record-only + durable bail (`STALL_STEP=5`, forced `STALL_TRACKING=true`); do not re-invoke Step 5 loop wrapper; repair-loop re-entry always `--site step5-mav --checks-site step5-review-fixes` |
| Step 5 coder | `step5-review-fixes` (shared fence); blockquote ~630 **in** harness window | Coder success log; same continue/terminal-stall deferral as MAV row; harness must include literal `RELEVANT_CHECKS_SKIPPED=true` |
| Step 6 | `step6` | Step 7 commit (review) success; in-Step-6 anti-halt |

## Files to modify/create

### UPDATED: skills/implement/SKILL.md

**Checks Failure Entry Macro** should document:

- Entry on `STATUS=fail` after local harness tokens are satisfied.
- Mandatory full read of `skills/implement/references/checks-repair-loop.md`.
- Pinned site lookup from that reference (including MAV/coder capture vs repair-loop site pair).
- `NEXT_ACTION=continue` returning to the call-site success path.
- `NEXT_ACTION=main-agent-edit`: delegate to `checks-repair-loop.md` section 4 for the full in-step contract -- escalation recording when `LINT_FIX_LEDGER_READY=true`, tail reads, main-agent Edit/Write repair, rerun `run-step-checks.sh` at the capture site, re-invoke `checks repair-loop` with the same pinned `--site` / optional `--checks-site` pair, repeat until `continue` or `stall`; preserve section 1 structural handling on each re-entry.
- `NEXT_ACTION=stall` routing: Step 3 / Step 6 / Step 5 self-review -> default section 4 stall (`STALL_TRACKING=true`, skip to Step 18, no durable seeding at self-review post-repair handler); Step 5 MAV/coder terminal checks -> **routing summary only** deferring to main-agent handoff terminal-stall execution path (~639): record-only, forced `STALL_TRACKING=true`, **Durable Bail to Step 18 Macro** with pinned `STALL_STEP=5`. Do not record-only or durable-seed at the blockquote layer; `checks-repair-loop.md` §4 MAV/coder override is superseded by this handoff deferral.
- No halt or summary on checks-failure paths.

Then shorten the five `STATUS=fail` sites per **Preserved local contract**: compact local blockquote + macro reference + site token + site-specific success/terminal deltas.

**MAV blockquote (~626):** Even though outside the harness five-line window, retain the full checks-failure opener, `REDACTED_LOG_FILE` / NOT raw `LOG_FILE`, mandatory `checks-repair-loop.md` read, macro reference, pinned `--site step5-mav --checks-site step5-review-fixes`, and `NEXT_ACTION=main-agent-edit` delegation. Only terminal-stall record-only/seeder prose moves to the handoff execution path.

**Keep separate (do not fold into checks-failure macro):**

```text
On terminal NEXT_ACTION=stall, set STALL_TRACKING=true and skip to Step 18 ...
```

after Step 5 self-review `run-step-checks.sh` (~line 576).

**Durable Bail to Step 18 Macro** should document:

- **Authority:** same durable-state contract as `step5-review-branches.md` `stall` after `step-5-resume.sh --record-only` when required by the call site.
- **Pinned step:** always `STALL_STEP=5` / `--stall-step 5` for Step 5 durable-bail invocations; call sites do not vary the step number.
- **Forced tracking:** before durable seeding or key rewrite, set prompt-side `STALL_TRACKING=true` and persist `STALL_TRACKING=true` in durable state. Ignore earlier parsed Step 5 envelope `STALL_TRACKING` (including `false` from MAV/coder handoff statuses).
- **Lint-fix bail computation:** durable bail value is `$STALL_REASON` only when it is one of the lint-fix stall tokens listed in `step5-review-branches.md`; otherwise empty. Never pass raw `$STALL_REASON` (e.g. `panel-failed`) as `--bail-reason`.
- **Present-state branch:** if `$IMPLEMENT_TMPDIR/ship-pr-state.sh` exists and is non-empty, key-based rewrite (do not source): persist `STALL_TRACKING=true`, set `STALL_STEP=5`, set `BAIL_REASON` to computed durable lint-fix bail, apply same rule to `IMPLEMENT_BAIL_REASON` when that key already exists.
- **Create-if-absent branch:** if missing or empty, seed via the existing one-line `bash "$IMPLEMENT_TMPDIR/larch-run.sh" skills/implement/scripts/step-8-seed-initial.sh ...` pattern from `step5-review-branches.md` with `--stall-step 5`, computed `--bail-reason`, `--stall-tracking true`, and documented fixed args; do not duplicate argv or add macro-local fences. Cross-ref Step 8 **Initial state seeder contract**.
- Call sites supply bail-derivation inputs only (`$STALL_REASON` for lint-fix token lookup); macro or explicit **MANDATORY READ** of `step5-review-branches.md` owns bail derivation.
- Skip to Step 18 (stall recovery before final report).

**Apply macro at one execution site only:**

- Main-agent handoff terminal stall paragraph (~639): replace `seed or key-rewrite` wording with explicit ordering: invoke `step-5-resume.sh` via fence ~642 with **both** required flags `--final-round-num "$FINAL_ROUND_NUM"` and `--record-only` (do not reduce to bare `--record-only`), then set `STALL_TRACKING=true` (defensive, default true), then invoke **Durable Bail to Step 18 Macro** with pinned `STALL_STEP=5`. Macro adoption replaces only the seed/key-rewrite prose after the fence; fence argv is unchanged.

**MAV/coder blockquote terminal-stall clauses:** shorten to routing summaries that defer to the handoff execution path above. Remove inline `step-5-resume.sh --record-only` and seeder prose from blockquotes; retain success logs, full checks-failure entry (MAV independently), `NEXT_ACTION=continue` destinations, `NEXT_ACTION=main-agent-edit` delegation via macro/reference, and deferral wording only.

**`stall` branch stub (~623):**

- Remove redundant seed-only second sentence.
- Keep: follow `stall` branch body in `step5-review-branches.md`; skip to Step 18.
- Do **not** reference **Durable Bail to Step 18 Macro** here.

### UPDATED: skills/implement/references/checks-repair-loop.md

**Section 4 only** (`NEXT_ACTION=stall` site overrides):

- Replace the Step 5 MAV and coder-main-agent-required bullet (current line ~81: inline `step-5-resume.sh --record-only`, durable-bail / Step 18 routing) with defer-to-handoff wording aligned to the SKILL single-execution-owner contract:
  - On terminal `NEXT_ACTION=stall`, do **not** invoke `step-5-resume.sh --record-only` or durable-seed inline at the repair-loop site.
  - Name the outcome (terminal checks stall) and defer record-only timing capture (`step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only` at fence ~642), forced `STALL_TRACKING=true`, and **Durable Bail to Step 18 Macro** execution to the main-agent handoff paragraph and `--record-only` fence (~639-642) in `skills/implement/SKILL.md`.
  - Retain: do not re-invoke the Step 5 loop wrapper.
- Leave section 4 `NEXT_ACTION=continue`, `NEXT_ACTION=main-agent-edit`, default stall routing, and section 2 pinned site pairs unchanged.

### MAY_UPDATE: scripts/test-implement-fence-shape.sh

Only if implementation changes Bash fence count or shape in `skills/implement/SKILL.md`. Update `EXPECTED_OLD` / `EXPECTED_NEW` and run `make test-implement-fence-shape`.

## Edge cases

- Step 5 MAV and coder use capture site `step5-review-fixes` but repair-loop site `step5-mav --checks-site step5-review-fixes`. Do not collapse that distinction; repeat the pair on every repair-loop re-entry per `checks-repair-loop.md` section 2 and section 4 `main-agent-edit`.
- Structural checks failures may lack `REDACTED_LOG_FILE`. Macro preserves existing fail-closed stall path via reference default routing.
- **`NEXT_ACTION=main-agent-edit` loops:** macro and local blockquotes must not shortcut the section 4 escalation -> Edit/Write -> capture rerun -> same-site-pair re-entry chain; only terminal `continue` or `stall` exits the loop.
- **Durable-bail execution owner:** only the main-agent handoff paragraph (~639) plus its `--record-only` fence executes record-only timing capture and durable bail. MAV/coder blockquote terminal-stall lines and `checks-repair-loop.md` §4 MAV/coder override both name the outcome and defer; they must not duplicate record-only or seeding steps before the shared `run-step-checks.sh` fence returns.
- **MAV outside harness window:** stripping the ~626 blockquote to macro-only deferral passes coder-adjacent harness lint but leaves MAV without checks-failure entry; both blockquotes must retain full entry contracts.
- **Reference vs SKILL precedence:** after the §4 edit, mandatory reads of `checks-repair-loop.md` before the shared fence must not reintroduce inline record-only or durable-bail execution at the blockquote layer.
- **Handoff ordering:** after `--record-only` (with required `--final-round-num "$FINAL_ROUND_NUM"`), always set `STALL_TRACKING=true` (defensive) before invoking **Durable Bail to Step 18 Macro**; macro then forces `STALL_TRACKING=true` into durable state regardless of earlier parsed envelope values.
- **Parsed envelope override:** when `review-and-fix` emitted `STALL_TRACKING=false` for `main-agent-vote-required` or `coder-main-agent-required`, terminal checks stalls must still force `STALL_TRACKING=true` at durable-bail execution; never seed or rewrite `ship-pr-state.sh` with the stale parsed `false`.
- Commit-route `NEXT_ACTION=stall` paths and the three out-of-scope invalid-envelope sites already seed durable state. Do not reintroduce prompt-side seeding there.
- Closeout grep: `seed or key-rewrite` must be zero in `skills/implement/SKILL.md` on the post-commit-route base (macro + reference delegation only).
- Do not let macro text hide success paths; each call site states `NEXT_ACTION=continue` destination.

## Failure modes

- Macro-only call sites without harness tokens fail `make lint` (`test-implement-relevant-checks-anti-halt.sh`).
- OK-only success guidance without literal `RELEVANT_CHECKS_SKIPPED=true` in the five-line harness window fails `make lint` even when the plan allows OK wording elsewhere.
- Too-generic checks-failure macro could cause orchestrator halt after child returns; keep anti-halt wording in macro and local blockquotes.
- Omitting `NEXT_ACTION=main-agent-edit` from the macro skips the repairable checks-failure path and leaves lint failures unaddressed.
- Stripping MAV blockquote (~626) to success-log plus stall deferral leaves the sole MAV path without checks-failure entry while coder-adjacent harness lint still passes.
- Wrong Step 5 site pair could run repair checks under wrong lint site; keep pair delegated to `checks-repair-loop.md`.
- Treating `$STALL_REASON` as direct `--bail-reason` misclassifies Step 18a or leaves stale lint-fix tokens.
- Applying durable-bail macro at `stall` stub duplicates `step5-review-branches.md` authority and invites oversimplified seeding.
- Collapsing self-review line 576 into checks-failure macro wrongly attaches durable seeding to self-review checks stalls.
- Implementing before commit-route merge leaves ambiguous seed wording at absorbed envelope sites.
- **Dual-layer execution:** leaving `checks-repair-loop.md` §4 inline record-only plus SKILL handoff execution, or editing MAV/coder blockquotes and handoff both with record-only/seeder steps, causes double record-only or premature seeding before checks complete.
- **Bare `--record-only` handoff fence:** omitting `--final-round-num "$FINAL_ROUND_NUM"` breaks `step-5-resume.sh` (exits 2) before durable bail runs.
- **Stale `STALL_TRACKING`:** reusing parsed envelope `STALL_TRACKING=false` at durable-bail execution skips Step 18a stall recovery.
- **Unpinned step:** omitting `STALL_STEP=5` at durable-bail sites misroutes Step 18a recovery.

## Testing strategy

- Confirm commit-route (#5271) is merged on the implementation branch before editing.
- Run `make lint` (includes `test-implement-relevant-checks-anti-halt`).
- Run `make test-implement-fence-shape` if fence counts change.
- Grep the five checks-failure sites in `skills/implement/SKILL.md`:
  - **Harness-adjacent (four fences):** each local blockquote within five lines of its `run-step-checks.sh` fence references **Checks Failure Entry Macro**, retains harness tokens, and includes the literal `RELEVANT_CHECKS_SKIPPED=true`.
  - **MAV blockquote (~626, `main-agent-vote-required` branch):** grep by anchor (MAV success log / `main-agent-vote-required`) separately from the shared-fence window; assert full checks-failure opener (`On STATUS=fail`, `REDACTED_LOG_FILE`, NOT raw `LOG_FILE`, mandatory `checks-repair-loop.md` read, macro reference, pinned `--site step5-mav --checks-site step5-review-fixes`, `NEXT_ACTION=main-agent-edit` delegation) even though outside the five-line scan.
- Grep for `seed or key-rewrite`; expect zero hits in `skills/implement/SKILL.md` after edit.
- Grep `skills/implement/references/checks-repair-loop.md` section 4; confirm MAV/coder terminal stall text no longer instructs inline `step-5-resume.sh --record-only` or inline durable-bail execution; expect defer-to-handoff wording naming the main-agent handoff paragraph (~639).
- Confirm **Checks Failure Entry Macro** documents `NEXT_ACTION=main-agent-edit` and delegates to section 4 for the full repair loop.
- Confirm `stall` stub has no redundant seed-only sentence and no durable-bail macro reference.
- Confirm line ~576 post-repair self-review stall remains separate from checks-failure macro.
- Confirm MAV and coder blockquotes retain distinct success logs and defer terminal-stall to handoff (~639) without inline record-only or seeder steps.
- Confirm handoff paragraph and fence ~642 preserve `step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only` (both flags); macro replaces only post-fence seed/key-rewrite prose; `STALL_TRACKING=true` before macro; macro pins `STALL_STEP=5`.
- Confirm three commit-route envelope sites are untouched by durable-bail dedup.

## Acceptance

- `make lint` passes (including `test-implement-relevant-checks-anti-halt.sh`).
- `make test-implement-fence-shape` passes (or fence count updated and verified).
- `seed or key-rewrite` grep returns zero hits in `skills/implement/SKILL.md`.
- Five checks-failure entry sites each reference **Checks Failure Entry Macro** with site token plus local harness tokens preserved.
- MAV blockquote (~626) retains full checks-failure entry contract independently.
- Handoff ~639 uses `step-5-resume.sh --final-round-num "$FINAL_ROUND_NUM" --record-only` (both flags) then `STALL_TRACKING=true` then **Durable Bail to Step 18 Macro** with `STALL_STEP=5`.
- `checks-repair-loop.md` §4 MAV/coder stall override defers to handoff (~639) without inline record-only or durable-bail execution.

diff_lines: 183

## Test plan
(no test plan section in plan-file)
