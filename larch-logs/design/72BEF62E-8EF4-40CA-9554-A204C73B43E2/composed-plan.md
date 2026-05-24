## Plan

# Implementation Plan — Refactor /design Step 3 into plan-review-loop.sh (#2676) — Revised after Plan Review Round 1

## Approach

Replace `/design` Step 3's orchestrator-side single-round plan-review flow (currently inlined in `skills/design/SKILL.md`) with a single-pass driver script `skills/design/scripts/plan-review-loop.sh` that owns: scout → panel dispatch → reviewer collection → ballot construction → aggregation → voting → tally. The script is a narrow /design-specific coordinator wrapping existing primitives — NOT a wrapper around `review-core.sh`, which is code-review-shaped. Voter 1 (Claude) moves from the `SKILL.md` Agent-tool subagent path to `launch-claude-review.sh` subprocess, by extending `scripts/dispatch-plan-voters.sh` in-place to mirror `scripts/dispatch-code-voters.sh`'s pattern (Round 1 user decision overrides the issue's "no launcher change"). `aggregate-findings.sh` is absorbed into /design (the user-confirmed #2644 R1/FINDING_27 lesson) via a new `--input-mode plan` flag that relaxes the `block_has_severity` check on **merged-output blocks** (line 628 in `main()`, NOT the input-side line 245-248). All six session-root artifact paths (`ballot.txt`, `accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md`) remain identical in name and parse contract. The 10 focus-area enum anchor comments survive in SKILL.md as no-op bash comments. The script accepts `--round-num <N>` (default 1) as forward-compat for the multi-round companion.

**Scope-of-work clarification (Round 1 findings F_12, F_13, F_61, F_62)**: this is NOT a pure no-behavior-change refactor. It absorbs three orthogonal changes that the dialectic confirmed are tightly coupled to the refactor: (1) aggregate-findings.sh introduction into /design (R1/FINDING_27), (2) `--input-mode plan` flag on aggregate-findings.sh (dialectic DECISION_1), (3) Voter 1 mechanism change to `launch-claude-review.sh` subprocess (user Round 1 override). The acceptance criterion is **session-root artifact contract equivalence** (same six file names, same parse contracts, same downstream consumers), NOT byte-identical ballots. The PR description should call this out explicitly.

## Files to modify/create

### NEW: `skills/design/scripts/plan-review-loop.sh`

Single-pass /design plan-review driver (~300 lines after Round 1 revisions). Bash 3.2 portable (no associative arrays, no namerefs, no mapfile, no `${var^^}`, no `&>>`, no coproc; use indexed arrays + newline temp files + `while IFS= read -r`).

Argv (parsed via `case`):
- `--design-tmpdir DIR` (required)
- `--plan-file PATH` (required; canonical `$DESIGN_TMPDIR/plan.txt`)
- `--feature-file PATH` (optional; defaults to `${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt`)
- `--round-num N` (optional, default `1`; forward-compat surface; emitted verbatim as `ROUNDS_COMPLETED=$N`)
- `--codex-present true|false` (required)
- `--cursor-present true|false` (required)
- `--timeout SEC` (optional, default `1860` — matches plan-review.md spec, NOT 1800; F_2, F_36, F_66, F_92)
- `--help`

Steps:
1. Sanity-check argv + readable files. Resolve `$DESIGN_TMPDIR` via `cd … && pwd -P`.
2. Run `scout-plan-archetypes-wrapper.sh` to populate `$DESIGN_TMPDIR/scout-plan-manifest.json` (fail-open).
3. Run `dispatch-plan-review-panel.sh` (already from #2665; no fallback needed when absent — F_45/F_48/F_52/F_54). Capture stdout into a local var. Parse `DISPATCH_OK` into local `PANEL_DISPATCH_OK` (use a distinct local-variable name from `VOTER_DISPATCH_OK` to prevent collision — F_9), plus `PANEL_PATHS_FILE`, `ALL_OUTPUT_FILES_PATH`, `STATIC_DISPATCH_OK`, `FALLBACK_COUNT`, `DEGRADED_ROUND`, `DYNAMIC_SLOT_COUNT`, and forward `WARN=` lines.
4. **Panel-failed early exit (F_10, F_27, F_35)**: when `PANEL_PATHS_FILE` is empty or missing OR points at an empty file, do NOT invoke `collect-agent-results.sh` (it exits with error on empty paths-file). Emit `LOOP_STATUS=panel-failed` + `ACCEPTED_COUNT=0` + `DEGRADED_PANEL=1` + `ROUNDS_COMPLETED=$ROUND_NUM`, write empty session-root artifacts (`accepted-plan-findings.md`, `rejected-findings.md`, `oos.md`, `oos-accepted-design.md`, `voting-tally.md`) so downstream `finalize-plan.sh` (Step 4) sees the required files; exit 1.
5. **Collect with full validation contract (F_2, F_22, F_36, F_66, F_68, F_75, F_92, F_93)**: `collect-agent-results.sh --timeout 1860 --substantive-validation --validation-mode --structured-reviewer-validation --paths-file "$PANEL_PATHS_FILE"`. Foreground call; no `run_in_background`. **Parse each collector record (F_16, F_22, F_96)**: read `REVIEWER_FILE`, `TOOL`, `STATUS`, `EXIT_CODE`, `STRUCTURED_SIDECAR`, `FAILURE_REASON` for each result block. For every non-OK record, route through `compose-collector-failure-log.sh --reviewer-file "$REVIEWER_FILE" --structured-record "REVIEWER_FILE=…|TOOL=…|STATUS=…|EXIT_CODE=…|FAILURE_REASON=…" --output "$DESIGN_TMPDIR/<slot>-collector.failure.log"` then `append-tool-failure.sh --log "$DESIGN_TMPDIR/execution-issues.md" --site "design Step 3" --tool "collect-agent-results.sh <tool> <status>" --exit-code "<EXIT_CODE-or-1>" --category "External Reviewer Issues" --output-file "$DESIGN_TMPDIR/<slot>-collector.failure.log" --redact`. Continue with OK reviewers only.
6. **Mid-run dirty-tree probe (F_17, F_25, F_30, F_69, F_76, F_95)**: invoke `check-mid-run-dirty-tree.sh --mode checkpoint` immediately after the collection boundary. On `STATUS=dirty` or `STATUS=unknown`, write `$DESIGN_TMPDIR/dirty-tree-detected.env` (per the existing convention) and emit `WARN=plan-review-collection: dirty tree detected` — the caller (SKILL.md) handles the AskUserQuestion recovery, NOT this script.
7. **Build pre-aggregation findings.md from TSV sidecars (F_1, F_14, F_21, F_28, F_33)**: for each OK reviewer's `REVIEWER_FILE`, locate the structured sidecar at `${REVIEWER_FILE}.tsv` (written by `--structured-reviewer-validation`). Parse each TSV row's columns (`schema_version`, `scope`, `severity`, `focus_area`, `location`, `what`, `scenario_or_breakage`, `suggested_fix`). For each row:
   - Derive reviewer slot name from the manifest (`Cursor-Arch`, `Codex-Edge`, `Cursor-dyn-<slug>`, etc.) — stamped from the dispatcher manifest, NOT reviewer self-reported.
   - When `scope=in_scope` (or absent/empty), emit a `### FINDING_N:` block with `- **Reviewer(s)**: <slot>` + `- **Severity**: <important|latent|nit>` + `- **Focus area**: <focus_area>` + `- **Location**: <location>` + `- **Concern**: <what>. Scenario: <scenario_or_breakage>` + `- **Proposed resolution**: <suggested_fix>`. The Severity line ensures the aggregator's validator passes (and lets `--input-mode plan` be an opt-out for ballots that DON'T carry severity, e.g. on quick-review paths — see aggregate-findings.sh update).
   - When `scope=out_of_scope` (or `[OUT_OF_SCOPE]` prose tag in the reviewer body, detected via secondary text-scan), emit an `### OOS_N:` block with `- **Description**: <what>. Scenario: <scenario_or_breakage>` + `- **Reviewer**: <slot>` + `- **Severity**: <severity>` + `- **Focus area**: <focus_area>` + `- **Location**: <location>` + `- **Phase**: design`. **Preserve any `focus-area=security` lines from the TSV verbatim (F_20)** — `tally-plan-review.sh`'s `is_security_block` check requires the canonical literal token.
   - **Renumber globally**: assign `FINDING_1`...`FINDING_N` for in-scope, `OOS_1`...`OOS_M` for OOS, ordered by manifest spawn order (cursor-arch, codex-arch, cursor-edge, codex-edge, … static → dynamic).
   - **Dedup in-scope and OOS separately (F_73, F_80)**: simple token-overlap dedup on the `what` field (Jaccard > 0.6 → merge; concatenate `Reviewer(s)` lists). In-scope-wins-OOS: if the same `what` text appears in both an in-scope FINDING and an OOS block (rare; only when one reviewer flags as in-scope and another as OOS), keep only the in-scope FINDING and drop the OOS duplicate.
   - **Empty-findings short-circuit (F_34, F_41, F_67, F_74, F_87, F_94)**: when 0 FINDING + 0 OOS blocks survive after dedup, do NOT launch voters. Emit `LOOP_STATUS=complete` + `ACCEPTED_COUNT=0` + `DEGRADED_PANEL=0` + `ROUNDS_COMPLETED=$ROUND_NUM` + `AGGREGATOR_STATUS=skipped-empty-input`, write empty session-root artifacts (matching the existing SKILL.md zero-findings prose), and exit 0.
   Write the combined ballot to `$DESIGN_TMPDIR/findings.md`.
8. **Aggregate in-scope only (F_3, F_15, F_23, F_29)**: `aggregate-findings.sh` splits on `### FINDING_[0-9]+:` only — it drops OOS blocks. Split `findings.md` into `$DESIGN_TMPDIR/findings-in-scope.md` (FINDING blocks only) and `$DESIGN_TMPDIR/findings-oos.md` (OOS blocks only). Then if `LARCH_AGGREGATOR_DISABLED=1` is set, skip aggregation (set `AGGREGATOR_STATUS=disabled`). Otherwise run `aggregate-findings.sh --findings-file "$DESIGN_TMPDIR/findings-in-scope.md" --review-tmpdir "$DESIGN_TMPDIR" --codex-present "$CODEX_PRESENT" --cursor-present "$CURSOR_PRESENT" --mode description --plan-file "$PLAN_FILE" --session-env-path "$DESIGN_TMPDIR/source-env.sh" --input-mode plan`. Parse `AGGREGATED`, `MERGED_COUNT`, `INPUT_COUNT`, `REASON`. On `AGGREGATED=false`, fall back to the pre-aggregation `findings-in-scope.md` unchanged. Emit `AGGREGATOR_STATUS=$REASON` for the test harness.
9. **Compose ballot.txt**: concatenate the (possibly aggregated) `findings-in-scope.md` followed by the unchanged `findings-oos.md` into `$DESIGN_TMPDIR/ballot.txt`. This ensures OOS blocks survive aggregation and the canonical ballot path stays at `ballot.txt`.
10. **Dispatch voters (F_40, F_89, F_99)**: `dispatch-plan-voters.sh --ballot-file "$DESIGN_TMPDIR/ballot.txt" --design-tmpdir "$DESIGN_TMPDIR" --codex-available "$CODEX_PRESENT" --cursor-available "$CURSOR_PRESENT" --session-env-path "$DESIGN_TMPDIR/source-env.sh"`. This dispatcher is updated by this PR to launch Voter 1 in addition to Voter 2/3, to emit `VOTER_1_PATH`/`VOTER_1_TOOL`/`VOTER_1_STATUS`/`VOTER_1_PARSE_RATE_STATUS` KVs, and to flip its own `DISPATCH_OK` to false when `VOTER_1_STATUS=failed` (mirroring `dispatch-code-voters.sh:450-451`). Capture stdout into a separate local var; parse into a separate local `VOTER_DISPATCH_OK` (NOT overwriting `PANEL_DISPATCH_OK` from Step 3 — F_9). Parse `VOTER_1_PATH`, `VOTER_1_TOOL`, `VOTER_1_STATUS`, `VOTER_1_PARSE_RATE_STATUS`, `VOTER_2_*`, `VOTER_3_*`, `VOTER_PATHS_FILE`. Forward `WARN=` lines.
11. Run `check-mid-run-dirty-tree.sh --mode checkpoint` after the voter collection boundary (matches existing dirty-tree probe placement in SKILL.md).
12. Collect into a newline temp file the subset of voter output paths whose `VOTER_*_STATUS != failed`.
13. Run `tally-plan-review.sh --ballot-file "$DESIGN_TMPDIR/ballot.txt" --voter-files <paths> --design-tmpdir "$DESIGN_TMPDIR"` (DIRECT call, NOT via `design-driver.sh ACTION=TALLY`). Capture stdout; parse `TALLY_PLAN_REVIEW_STATUS`, `VOTING_TALLY_FILE`. Forward `WARN=` lines.
14. Compute `ACCEPTED_COUNT` from `### FINDING_N:` blocks in `$DESIGN_TMPDIR/accepted-plan-findings.md`. Compute `DEGRADED_PANEL` (boolean 0/1): set 1 when `STATIC_DISPATCH_OK=false` OR `FALLBACK_COUNT > floor(slot_count/2)` OR fewer than 2 non-failed voters reached tally.
15. Decide `LOOP_STATUS`:
    - `panel-failed` — already handled in Step 4 (early exit).
    - `main-agent-vote-required` — propagated when `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` (0-judge fallback per dialectic DECISION_2).
    - `complete` — otherwise (the happy path).
16. Emit stdout KVs (F_8, F_56, F_58, F_99):
    - `LOOP_STATUS=<complete|panel-failed|main-agent-vote-required>`
    - `ACCEPTED_COUNT=<int>`
    - `DEGRADED_PANEL=<0|1>`
    - `ROUNDS_COMPLETED=$ROUND_NUM`
    - `AGGREGATOR_STATUS=<ok|disabled|insufficient-input|validation-failed|skipped-empty-input|…>`
    - `TALLY_PLAN_REVIEW_STATUS=…` (passed through verbatim from tally — this is the variable SKILL.md branches on for its existing main-agent-vote-required prose; emitting both `LOOP_STATUS=main-agent-vote-required` and `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` is intentional — different consumers parse different variables, but both are byte-equivalent so there is no ambiguity)
    - `VOTING_TALLY_FILE=…` (passed through from tally)
    - `VOTER_1_PARSE_RATE_STATUS=…` (passed through from dispatch-plan-voters.sh; the test harness asserts this KV — F_40, F_99)

Exit codes:
- `0` on `LOOP_STATUS=complete` or `main-agent-vote-required` (both normal terminal states; SKILL.md handles MAV with its existing prose).
- `2` on argv / file errors (exit before any external dispatch).
- `1` on `LOOP_STATUS=panel-failed` (Phase 3 collapse OR empty paths-file).

The script does NOT revise `plan.txt` — that authority belongs to Gate B (Step 3.5).

### NEW: `skills/design/scripts/plan-review-loop.md`

Sibling spec per `.claude/rules/script-md-siblings.md`. Documents:
- Purpose, primary callers (`skills/design/SKILL.md` Step 3), invariants (six session-root artifacts; never revises plan.txt; honors `LARCH_AGGREGATOR_DISABLED=1` per dialectic DECISION_4).
- Argv summary.
- 16-step outline matching the script body.
- Stdout KV protocol enumeration.
- Scope-of-work statement: this script is the consequence of the #2676 refactor + #2644 R1/FINDING_27 aggregator absorption + dialectic DECISION_1 (`--input-mode plan`).
- Makefile wiring: `test-plan-review-loop`.
- Harness: `skills/design/scripts/test-plan-review-loop.sh`.
- Edit-in-sync rules.

### NEW: `skills/design/scripts/test-plan-review-loop.sh`

Hermetic regression harness (~250 lines, Bash 3.2 portable). Stub-based: `PATH` injection with stubs for `codex`, `cursor`, `claude` binaries plus stubs for `scout-plan-archetypes-wrapper.sh`, `dispatch-plan-review-panel.sh`, `collect-agent-results.sh`, `aggregate-findings.sh`, `dispatch-plan-voters.sh`, `tally-plan-review.sh`, `check-mid-run-dirty-tree.sh`. Coverage:
1. **Happy path**: 2 reviewers produce 2 findings + 1 OOS each (4 in-scope + 2 OOS pre-dedup); aggregator merges to 3 unique in-scope; OOS unchanged (2 blocks); voters all return parseable; tally produces 2 accepted, 1 rejected, 1 OOS accepted. Asserts: all 6 session-root files exist; `LOOP_STATUS=complete`; `ACCEPTED_COUNT=2`; `DEGRADED_PANEL=0`; `ROUNDS_COMPLETED=1`; `AGGREGATOR_STATUS=ok`; `VOTING_TALLY_FILE` non-empty.
2. **`--round-num 3` forward-compat**: same fixtures; asserts `ROUNDS_COMPLETED=3`.
3. **Aggregator-failure fallback**: stub aggregator to exit 0 with `AGGREGATED=false REASON=validation-failed`. Asserts: ballot.txt contains pre-aggregation in-scope concatenated with OOS unchanged; `AGGREGATOR_STATUS=validation-failed`.
4. **`LARCH_AGGREGATOR_DISABLED=1` kill switch**: env var set; asserts aggregator NOT invoked AND `AGGREGATOR_STATUS=disabled` AND tally still runs.
5. **0-judge fallback (DECISION_2)**: stub `dispatch-plan-voters.sh` so all three `VOTER_*_STATUS=failed`. Asserts: `LOOP_STATUS=main-agent-vote-required` AND `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required`; exit 0.
6. **Panel-failed (empty paths-file)**: stub `dispatch-plan-review-panel.sh` to return `DISPATCH_OK=false` + empty paths-file. Asserts: `collect-agent-results.sh` NOT invoked, `LOOP_STATUS=panel-failed`, empty session-root artifacts written, exit 1.
7. **Empty-findings short-circuit (F_34 etc.)**: stub reviewers to return zero findings + zero OOS. Asserts: voters NOT launched; `LOOP_STATUS=complete`; `ACCEPTED_COUNT=0`; empty session-root artifacts; exit 0.
8. **Severity-absent ballot proof (DECISION_1)**: validates that `aggregate-findings.sh --input-mode plan` succeeds when the input findings.md lacks Severity lines (assert `AGGREGATED=true`).
9. **Collector failure routing (F_16, F_96)**: stub one reviewer to return STATUS=FAILED; assert `compose-collector-failure-log.sh` invoked and `append-tool-failure.sh` appended an entry to `execution-issues.md`.
10. **TSV sidecar parsing (F_1 etc.)**: write a fixture TSV alongside a stub reviewer output; assert the inline helper produces correct `### FINDING_N:` and `### OOS_N:` blocks from the TSV rows, with reviewer attribution stamped from the dispatcher manifest.
11. **`PANEL_DISPATCH_OK` vs `VOTER_DISPATCH_OK` isolation (F_9)**: stub both dispatchers to emit DISPATCH_OK=false; assert plan-review-loop.sh distinguishes the two and emits the panel value as the source of truth for panel-failed classification.
12. **VOTER_1_PARSE_RATE_STATUS pass-through (F_40, F_99)**: stub dispatch-plan-voters.sh to emit `VOTER_1_PARSE_RATE_STATUS=OK`; assert plan-review-loop.sh emits it on its own stdout.
13. **Dedup in-scope vs OOS (F_73, F_80)**: fixture with the same finding appearing as in-scope from reviewer A and OOS from reviewer B. Asserts: only one in-scope block survives; OOS is dropped (in-scope-wins).
14. **Argv errors**: missing required flags, unreadable files, unknown flag — all exit 2 before any external dispatch.

### NEW: `skills/design/scripts/test-plan-review-loop.md`

Sibling spec stub: purpose, primary script under test, Makefile target name, list of 14 covered scenarios.

### UPDATED: `skills/design/SKILL.md`

Step 3 (the `review_budget=full` branch) is collapsed. Before this PR, the full branch contains the IMPORTANT banner, the MANDATORY `plan-review.md` load, the External Reviewer Setup paragraph, the inline scout + dispatch-plan-review-panel Bash block, the "Collecting, Voting, Finalize" prose, the `printf 'ACTION=TALLY ARGS=…'` block, and the `TALLY_PLAN_REVIEW_STATUS` parsing prose.

After this PR:
- KEEP: the `## Plan Candidate for Review` pre-print Bash block (`emit-design-plan-preview.sh --variant step3`).
- KEEP: the `review_budget=quick` branch and its MANDATORY load of `plan-review-quick.md`.
- KEEP: the IMPORTANT banner.
- KEEP: the MANDATORY load of `references/plan-review.md` (contents updated; see below).
- KEEP: the 10 focus-area enum anchor comments as no-op bash comments inside or beside the new invocation block (`scripts/test-design-structure.sh` Check 14a counts the literal string).
- KEEP: the `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required` prose paragraph (which handles the MAV synthetic-ballot write + re-tally) — this fires when the parsed `TALLY_PLAN_REVIEW_STATUS` from the loop's stdout equals `main-agent-vote-required` (F_58: the LOOP_STATUS/TALLY_PLAN_REVIEW_STATUS pair are byte-equivalent on this branch, not contradictory).
- REPLACE all inline orchestration with one foreground Bash block, **with exit-status capture and explicit panel-failed handling (F_5, F_11, F_18, F_24, F_30, F_31, F_57)**:

  ```bash
  [ -f ~/.cache/larch/sessions/current-design-env-$PPID.sh ] && source ~/.cache/larch/sessions/current-design-env-$PPID.sh
  # Foreground required: see BASH_AUTHORING.md §4
  set +e
  _plan_review_out=$("${CLAUDE_PLUGIN_ROOT}/skills/design/scripts/plan-review-loop.sh" \
    --design-tmpdir "$DESIGN_TMPDIR" \
    --plan-file "$DESIGN_TMPDIR/plan.txt" \
    --feature-file "${IMPLEMENT_TMPDIR:-$DESIGN_TMPDIR}/feature-description.txt" \
    --codex-present "$CODEX_PRESENT" \
    --cursor-present "$CURSOR_PRESENT" \
    --round-num 1)
  _plan_review_rc=$?
  set -e
  LOOP_STATUS=""; ACCEPTED_COUNT=""; DEGRADED_PANEL=""; ROUNDS_COMPLETED=""
  TALLY_PLAN_REVIEW_STATUS=""; AGGREGATOR_STATUS=""; VOTING_TALLY_FILE=""
  VOTER_1_PARSE_RATE_STATUS=""
  while IFS= read -r _line || [[ -n "$_line" ]]; do
    _key="${_line%%=*}"; _value="${_line#*=}"
    case "$_key" in
      LOOP_STATUS|ACCEPTED_COUNT|DEGRADED_PANEL|ROUNDS_COMPLETED|TALLY_PLAN_REVIEW_STATUS|AGGREGATOR_STATUS|VOTING_TALLY_FILE|VOTER_1_PARSE_RATE_STATUS)
        printf -v "$_key" '%s' "$_value" ;;
      WARN) printf '%s\n' "WARN=$_value" ;;
    esac
  done <<<"$_plan_review_out"
  if [[ "$_plan_review_rc" -ne 0 && "$LOOP_STATUS" != "panel-failed" && "$LOOP_STATUS" != "main-agent-vote-required" ]]; then
    printf '%s\n' "**⚠ plan-review-loop.sh exited with rc=$_plan_review_rc and unexpected LOOP_STATUS=$LOOP_STATUS**"
  fi
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  # Focus area enum anchor for CI: code-quality / risk-integration / correctness / architecture / security
  ```

Mechanical deletions in SKILL.md Step 3:
- The `printf 'ACTION=TALLY ARGS=%s …'` block.
- The `dispatch-plan-review-panel.sh` invocation block (the inline `DISPATCH_OK` / `PANEL_PATHS_FILE` parsing loop and the post-collect dirty-tree sentinel checks).
- The `scout-plan-archetypes-wrapper.sh` invocation block.
- The "Collecting, Voting, Finalize, Track Rejected" orchestration prose paragraph.
- **The stale narrative prose at SKILL.md:632-634 about inline scout+dispatch-plan-review-panel-sh (F_42, F_100) — replaced with a single sentence pointing at `plan-review-loop.sh`.**
- **The stale narrative prose at SKILL.md:689-693 about parsing PANEL_PATHS_FILE from an inline loop (F_88) — deleted entirely.**

### UPDATED: `scripts/dispatch-plan-voters.sh`

Extend to launch Voter 1 (Claude) before Voter 2/3, mirroring `scripts/dispatch-code-voters.sh:285-301`. New behavior:
- Source the shared parse-rate library `scripts/lib-voter-parse-rate.sh` AFTER the helpers from `dispatch-code-voters.sh` (`check_voter_parse_rate`, `check_and_retry_voter_parse_rate`, `parse_rate_status_from_output`) are moved into it (see lib-voter-parse-rate.sh UPDATED entry below). **The "library already exists; just source it" wording in Round 1 plan was wrong (F_46, F_53)**: the library currently has only 3 diagnostic helpers (`voter_parse_rate_diag_path`, `voter_output_sha256`, `voter_parse_rate_diag_matches_output`); the parse-rate logic lives in dispatch-code-voters.sh and must be physically MOVED into the lib as part of this PR.
- Before the existing Voter 2/3 manifest construction, add:
  - Build Voter 1 prompt via `skills/shared/scripts/render-voter-prompt.sh` (correct path — F_81, F_85, F_98; NOT `scripts/render-voter-prompt.sh`) with the same `--panel-role` / `--id-grammar finding-oos` / `--verification-context plan` as today's Voter 2/3 prompts.
  - Set `VOTER_1_PATH="$DESIGN_TMPDIR/claude-vote-output.txt"`.
  - `set +e; "$PLUGIN_ROOT/scripts/launch-claude-review.sh" --output "$VOTER_1_PATH" --prompt-file "$claude_prompt" --mode description --role voter --timeout 1200 --timing-task-kind claude-plan-voter …; voter1_rc=$?; set -e`.
  - Diagnostic capture on `voter1_rc != 0` or empty `$VOTER_1_PATH`: write a `voter1-diag.txt` and append to `execution-issues.md` via `append-tool-failure.sh` — same pattern as `dispatch-code-voters.sh:304-347`.
  - `VOTER_1_TOOL="claude"`; `VOTER_1_STATUS="launched"`; downgrade to `failed` when `voter1_rc != 0` or output is empty.
- After Voter 2/3 collection and parse-rate retry checks, run `check_and_retry_voter_parse_rate` on Voter 1 (now available from the shared lib).
- **Flip DISPATCH_OK to false when VOTER_1_STATUS=failed (F_89)**: mirror `dispatch-code-voters.sh:450-451`.
- Update the `plan-voter-paths.txt` writer to include `VOTER_1_PATH` first when status != failed.
- **Emit VOTER_1_PARSE_RATE_STATUS, VOTER_2_PARSE_RATE_STATUS, VOTER_3_PARSE_RATE_STATUS KVs (F_40, F_99)** — mirroring dispatch-code-voters.sh's behavior.
- Add `--timing-task-kind claude-plan-voter` at the Voter 1 launch; register `claude-plan-voter` in `scripts/lib-timing-kinds.sh`.
- **Existing argv unchanged** — no new required flags; backward compatible.

### UPDATED: `scripts/dispatch-plan-voters.md`

Document the Voter 1 launch (`launch-claude-review.sh` subprocess; `--timing-task-kind claude-plan-voter`). Update Primary callers to add `skills/design/scripts/plan-review-loop.sh`. Document the new KVs (`VOTER_1_*`, `VOTER_*_PARSE_RATE_STATUS`). Note the DISPATCH_OK=false on Voter 1 failure. Cross-reference `scripts/lib-voter-parse-rate.sh` as the home of the shared parse-rate helpers (the move is documented in the lib's own .md).

### UPDATED: `scripts/test-dispatch-plan-voters.sh`

Add stubs for `launch-claude-review.sh` (or PATH-stubbed `claude` binary). Three new test cases on top of the existing voters:
1. Voter 1 happy path — assert `VOTER_1_PATH` / `VOTER_1_TOOL=claude` / `VOTER_1_STATUS=launched`; `VOTER_1_PARSE_RATE_STATUS=OK`; `plan-voter-paths.txt` contains 3 paths in order.
2. Voter 1 fail — assert `VOTER_1_STATUS=failed`, `DISPATCH_OK=false`, diagnostic appended.
3. Voter 1 parse-rate retry — narrative first call, parseable second; assert retry succeeded and `VOTER_1_PARSE_RATE_STATUS=OK`.

Existing tests (codex/cursor) continue passing.

### UPDATED: `scripts/lib-voter-parse-rate.sh`

**Move (not copy) the following functions from `scripts/dispatch-code-voters.sh` into this shared library (F_4, F_6, F_19, F_26, F_44, F_46, F_53, F_71, F_78, F_84, F_91)**:
- `check_voter_parse_rate`
- `check_and_retry_voter_parse_rate`
- `parse_rate_status_from_output`
- `launch_voter_retry`
- `make_voter_retry_prompt_file` (or split into the dispatcher-specific prompt construction + shared retry orchestration; pragmatic decision at implementation time)
- `should_suppress_parse_rate_issue_append`
- `is_harness_review_path` (keep here since suppress_parse_rate uses it)
- `parse_rate_check_tool_label`

The shared checker must count BOTH `FINDING_N` AND `OOS_N` IDs from the ballot when computing parse-rate (today it only counts `FINDING_N` for code-review). Add an optional `--id-grammar finding-only|finding-oos` parameter to the helpers, defaulting to `finding-only` for backward compat with dispatch-code-voters.sh. dispatch-plan-voters.sh passes `--id-grammar finding-oos`.

### UPDATED: `scripts/lib-voter-parse-rate.md`

Sibling spec stub. Document the moved functions, the `--id-grammar` parameter, and callers (`dispatch-code-voters.sh`, `dispatch-plan-voters.sh`).

### UPDATED: `scripts/dispatch-code-voters.sh`

Source `scripts/lib-voter-parse-rate.sh` to gain the moved helpers. Remove the local copies. No behavior change for /implement.

### UPDATED: `scripts/test-dispatch-code-voters.sh`

No behavior change required; existing tests should pass because the helpers now come from the lib but the contract is unchanged. May need one minor update to confirm OOS-grammar fallback works.

### UPDATED: `skills/review/scripts/aggregate-findings.sh`

Add `--input-mode plan|code` flag (default `code` — current strict behavior). When `--input-mode plan`:
- The Python validator's `block_has_severity` check **on merged-output blocks at line 628** (NOT on input blocks at line 245-248, which do not run the check — F_13, F_70, F_77) is gated on `INPUT_MODE`. Pass `INPUT_MODE` to the embedded Python via `os.environ["LARCH_AGGREGATE_INPUT_MODE"]`. The validator reads `os.environ.get("LARCH_AGGREGATE_INPUT_MODE", "code")` and gates the line 628 `if not block_has_severity(b): return 1` check on `input_mode == "code"`.
- All other validations continue to fire unchanged.
- The aggregator's merge prompt is unchanged; the orchestrator-aggregator subagent simply won't be required to emit severity lines for plan-review-mode input.

### UPDATED: `skills/review/scripts/aggregate-findings.md`

Document the new `--input-mode plan|code` flag, its default (`code`), and the dialectic linkage to /design DECISION_1.

### UPDATED: `skills/review/scripts/test-aggregate-findings.sh`

Add one new test: invoke `aggregate-findings.sh` with `--input-mode plan` on a fixture findings.md whose merged-output blocks lack severity lines; assert `AGGREGATED=true`. Existing `--input-mode code` (default) tests continue to fail-shut on missing-severity merged output.

### UPDATED: `skills/design/references/plan-review.md`

Rewrite the Voter 1 prose:
- Voter 1 launch is owned by `scripts/dispatch-plan-voters.sh` via `launch-claude-review.sh` subprocess (NOT Agent tool).
- The Voter 1 prompt is rendered by `skills/shared/scripts/render-voter-prompt.sh` (same as Voter 2/3) with `--panel-role` / `--id-grammar finding-oos` / `--verification-context plan` — there is no separate inline Voter 1 prompt in SKILL.md.
- Update the "Voter Composition" section.

Update the "Collecting External Reviewer Results" section:
- The `collect-agent-results.sh` invocation block in the doc is now an INVARIANT specification, not a Step 3 inline call. plan-review-loop.sh implements this invariant (same flags, same timeout 1860). **Update Check 7 of test-design-structure.sh accordingly (F_93)** — the check now confirms the invariant lives in plan-review-loop.sh OR plan-review.md (whichever location CI prefers).
- Cross-reference: "/design Step 3's panel + voting + tally is owned by `skills/design/scripts/plan-review-loop.sh`. Plan-review-loop.sh implements the collect-agent-results contract specified here."
- **Update the dedup rules section** to clarify that plan-review-loop.sh implements `in-scope wins OOS` dedup with the schema documented here (F_73, F_80).

### UPDATED: `skills/design/scripts/design-driver.md`

Add: "`ACTION=TALLY` is retained for backward compatibility with older callers. The current Step 3 entrypoint is `skills/design/scripts/plan-review-loop.sh`, which calls `tally-plan-review.sh` directly. No code change to `design-driver.sh`'s `TALLY` case; the case stays callable for any out-of-tree caller."

### UPDATED: `scripts/test-design-structure.sh`

Pin additions (new checks):
- `skills/design/scripts/plan-review-loop.sh` exists and is executable.
- `skills/design/scripts/plan-review-loop.md` exists.
- `skills/design/scripts/test-plan-review-loop.sh` exists and is executable.
- `skills/design/scripts/test-plan-review-loop.md` exists.
- `plan-review-loop.sh` body greps for `aggregate-findings.sh` AND `--input-mode plan` (F_97 — the literal `--input-mode plan` token pin).
- `plan-review-loop.sh` body greps for `tally-plan-review.sh` (DIRECT call, NOT via design-driver.sh).
- `plan-review-loop.sh` body greps for `dispatch-plan-voters.sh`.
- `plan-review-loop.sh` body greps for `dispatch-plan-review-panel.sh`.
- `plan-review-loop.sh` body greps for `scout-plan-archetypes-wrapper.sh`.
- `plan-review-loop.sh` body greps for `collect-agent-results.sh` AND `--substantive-validation` AND `--validation-mode` AND `--structured-reviewer-validation` AND `--timeout 1860` (F_93).
- `plan-review-loop.sh` body greps for `check-mid-run-dirty-tree.sh` (F_17 etc.).
- `plan-review-loop.sh` body greps for `compose-collector-failure-log.sh` (F_96).
- `plan-review-loop.sh` body greps for `launch-claude-review.sh` via dispatch-plan-voters.sh (sanity check).
- SKILL.md Step 3 greps `plan-review-loop.sh` (single invocation block).
- The 10 focus-area enum anchor comments remain (Check 14a — unchanged).

Pin removals (stale after plan deletions in SKILL.md):
- Check 14b2 (`grep -Fq 'ACTION=TALLY' "$SKILL_MD"`) REMOVED.
- **Checks 14c1, 14c2, 14c3 (F_38, F_43, F_50, F_59)**: review their current grep targets. If they require literal tokens `scout-plan-archetypes-wrapper.sh`, `dispatch-plan-review-panel.sh`, or `PANEL_PATHS_FILE` in SKILL.md, REMOVE or RELOCATE them — those tokens move into plan-review-loop.sh. New pin: `plan-review-loop.sh` body contains the same literal tokens.

### UPDATED: `Makefile`

- Add `test-plan-review-loop` phony target running `bash scripts/harness-timer.sh $@ bash skills/design/scripts/test-plan-review-loop.sh`.
- Wire into the same umbrella that runs `test-tally-plan-review` / `test-dispatch-plan-review-panel`. **Do NOT introduce a `test-design` umbrella target (F_83, F_90 — it doesn't exist)** — use the existing harness shard convention.

### UPDATED: `agent-lint.toml`

Register the four new files (`plan-review-loop.sh`, `plan-review-loop.md`, `test-plan-review-loop.sh`, `test-plan-review-loop.md`). If the lint expects caller-graph rows, add `dispatch-plan-voters.sh` as a primary caller of `launch-claude-review.sh` and `plan-review-loop.sh` as primary caller of `dispatch-plan-voters.sh`, `dispatch-plan-review-panel.sh`, `aggregate-findings.sh`, `tally-plan-review.sh`, `collect-agent-results.sh`, `check-mid-run-dirty-tree.sh`, `compose-collector-failure-log.sh`.

### UPDATED: `scripts/lib-timing-kinds.sh`

Add `claude-plan-voter` to `TIMING_TASK_KINDS_ALLOWED` (per `.claude/rules/timing-task-kind-allowlist.md`).

### UPDATED: `SECURITY.md`

Add a brief note in the threat-model section (F_64 / OOS_3): the /design plan-review panel now uses `launch-claude-review.sh` subprocess for Voter 1 (previously an Agent-tool subagent). This is a security-equivalent boundary (same trust model as the existing Voter 1 in /implement's review loop, which already uses this pattern via `dispatch-code-voters.sh`) but it should be documented for completeness. Cross-reference `scripts/lib-voter-parse-rate.sh` as the shared parse-rate boundary.

## Edge cases

- **Aggregator disabled / failed → ballot still valid**: when `LARCH_AGGREGATOR_DISABLED=1` is in env, OR `aggregate-findings.sh` exits 0 with `AGGREGATED=false`, the script preserves pre-aggregation `findings-in-scope.md` and concatenates it with `findings-oos.md` to form `ballot.txt`. Tally still runs.
- **Empty ballot (0 findings + 0 OOS) → empty-findings short-circuit**: no voters launched; emit `LOOP_STATUS=complete`, `ACCEPTED_COUNT=0`, write empty session-root artifacts. Matches plan-review.md:108 zero-findings short-circuit (F_34, F_41, F_67, F_74, F_87, F_94).
- **Empty PANEL_PATHS_FILE (Phase 3 collapse) → panel-failed early exit**: do not invoke `collect-agent-results.sh` (it would error on empty paths). Emit `LOOP_STATUS=panel-failed`, write empty session-root artifacts, exit 1 (F_10, F_27, F_35).
- **Voter 1 launch failure**: `dispatch-plan-voters.sh` writes diagnostic, sets `VOTER_1_STATUS=failed`, flips `DISPATCH_OK=false`. Loop proceeds with Voter 2/3 (effective panel size 2). Threshold rules in `tally-plan-review.sh` handle 2-voter tallies.
- **All 3 voters fail → `LOOP_STATUS=main-agent-vote-required`**: tally emits `TALLY_PLAN_REVIEW_STATUS=main-agent-vote-required`. Loop propagates BOTH KVs to SKILL.md, which handles the synthetic-ballot write + re-tally with its existing prose. SKILL.md branches on `TALLY_PLAN_REVIEW_STATUS` (the existing variable) — `LOOP_STATUS` is informational pass-through (F_58 is not a contradiction; both KVs carry the same value).
- **Aggregator validation-failed**: e.g. when the LLM merge drops a reviewer slot. Loop falls back to pre-aggregation `findings-in-scope.md` unchanged. `AGGREGATOR_STATUS=validation-failed` (test 3 covers this).
- **OOS-only ballot**: 0 in-scope findings + N OOS blocks. Aggregator runs on the empty in-scope file (returns `INPUT_COUNT=0 REASON=insufficient-input`); the loop concatenates the empty in-scope output with the OOS file. Voters see only OOS items. tally writes oos.md and empty accepted-plan-findings.md. `LOOP_STATUS=complete`.
- **`--round-num 2+` in this single-pass refactor**: accepted; behavior identical to `--round-num 1` other than the emitted `ROUNDS_COMPLETED` KV. Multi-round companion adds per-round routing.
- **Reviewer TSV sidecar missing or malformed**: when `${REVIEWER_FILE}.tsv` is absent or unreadable, fall back to text-pattern extraction (look for prose `[OUT_OF_SCOPE]` tags and numbered prose findings). When that also fails for a reviewer, log the reviewer as contributing 0 findings via a `WARN=…` line. The dispatch-plan-review-panel test must ensure --structured-reviewer-validation actually writes sidecars; the collector contract already guarantees this when STATUS=OK.

## Failure modes

1. **Aggregator schema validator regression**: a future change to `aggregate-findings.sh` could re-tighten the severity check past the `--input-mode plan` gate. **Earliest warning**: `test-aggregate-findings.sh`'s new `--input-mode plan` no-severity fixture fails. **Mitigation**: pin the flag's existence and behavior in `test-design-structure.sh` (grep `plan-review-loop.sh` for `--input-mode plan`, per F_97 fix).

2. **Voter 1 silent failure**: `launch-claude-review.sh` returns exit 0 but with an empty `claude-vote-output.txt` (truncation upstream). **Earliest warning**: dispatch-plan-voters.sh detects empty output, flips `VOTER_1_STATUS=failed` and `DISPATCH_OK=false`; `effective_judges < 3` warning fires. **Mitigation**: parse-rate retry (now in shared lib) runs on Voter 1; diagnostic written to execution-issues.md.

3. **plan-review-loop.sh exit-status drift**: a future SKILL.md edit that breaks the `set +e; _rc=$?; set -e` capture could silently swallow `panel-failed`. **Earliest warning**: test-design-structure.sh greps SKILL.md for `set +e` AND `_plan_review_rc=$?` adjacent to the plan-review-loop.sh invocation. **Mitigation**: add that grep pin to test-design-structure.sh.

## Testing strategy

- **New harness**: `skills/design/scripts/test-plan-review-loop.sh` covers 14 scenarios (see NEW entry).
- **Updated harnesses**:
  - `scripts/test-dispatch-plan-voters.sh` gains 3 cases for Voter 1 (happy, fail, parse-rate retry).
  - `scripts/test-dispatch-code-voters.sh` runs unchanged after the lib move (sources the lib instead of declaring functions locally).
  - `skills/review/scripts/test-aggregate-findings.sh` gains 1 case for `--input-mode plan`.
- **Structural pins**: `scripts/test-design-structure.sh` Check 14a (10 enum anchors) is preserved; Check 14b2 (`ACTION=TALLY` in SKILL.md) REMOVED; Checks 14c1-14c3 reviewed/relocated to plan-review-loop.sh; new pins enumerate every script + sibling .md, the literal token `--input-mode plan`, and the `set +e / _rc=$?` pattern in SKILL.md.
- **CI integration**: Makefile gains `test-plan-review-loop` under the existing design harness umbrella (NOT a new `test-design` umbrella — F_83); agent-lint.toml registers the new files.
- **Equivalence acceptance**: artifact-name + parse-contract equivalence, NOT byte-identical (F_12, F_13, F_61, F_62). Manual `/design --hard` on a test issue before+after the refactor; six session-root files compared for: (a) all six paths exist; (b) `accepted-plan-findings.md` blocks match the FINDING_N template; (c) `voting-tally.md` has the same column shape; (d) tally counts are within ±1 (aggregator dedup may merge near-duplicates that the previous orchestrator-side dedup did not).
- **No regression**: `make lint` continues to pass; the existing design harness shard passes including the new and updated harnesses.

diff_lines: 850

## Acceptance

- `skills/design/scripts/plan-review-loop.sh` + sibling `.md` created.
- `skills/design/SKILL.md` Step 3 replaced with single invocation of the new script; explicit deletions of inline `ACTION=TALLY`, `TALLY_PLAN_REVIEW_STATUS` parsing, scout + dispatch-plan-review-panel inline blocks, and the stale prose at SKILL.md:632-634 and :689-693.
- `/design --hard` and `/design --simple` on a test issue produce the same six session-root artifact NAMES with equivalent PARSE CONTRACTS (NOT byte-identical ballots — aggregator absorption changes dedup shape; per dialectic DECISION_1 and Round 1 findings F_12/F_13/F_61/F_62).
- `/design --trivial` is unchanged (does not invoke `plan-review-loop.sh`).
- `plan-review-loop.sh` emits stdout KVs: `LOOP_STATUS`, `ACCEPTED_COUNT`, `DEGRADED_PANEL`, `ROUNDS_COMPLETED`, `AGGREGATOR_STATUS`, `TALLY_PLAN_REVIEW_STATUS` (pass-through), `VOTING_TALLY_FILE` (pass-through), `VOTER_1_PARSE_RATE_STATUS` (pass-through).
- `scripts/dispatch-plan-voters.sh` launches Voter 1 (Claude) via `launch-claude-review.sh` subprocess; emits `VOTER_1_*` KVs; flips `DISPATCH_OK=false` when `VOTER_1_STATUS=failed`.
- `scripts/lib-voter-parse-rate.sh` hosts shared parse-rate helpers (`check_voter_parse_rate`, `check_and_retry_voter_parse_rate`, etc.) moved from `dispatch-code-voters.sh`; `--id-grammar finding-only|finding-oos` parameter; both dispatchers source from it.
- `skills/review/scripts/aggregate-findings.sh` accepts `--input-mode plan|code` (default `code`); plan mode bypasses the merged-output severity check at line 628.
- `skills/design/references/plan-review.md` Voter 1 prose rewritten to describe `launch-claude-review.sh` subprocess (not Agent tool).
- `scripts/test-design-structure.sh` Check 14b2 (`ACTION=TALLY` grep) REMOVED; Checks 14c1-14c3 (scout/dispatch-plan-review-panel/PANEL_PATHS_FILE) RELOCATED to target `plan-review-loop.sh`; new pins for every NEW file + literal `--input-mode plan` token + `set +e / _plan_review_rc=$?` in SKILL.md.
- New harness `skills/design/scripts/test-plan-review-loop.sh` covers 14 scenarios (happy path, --round-num forward compat, aggregator-fallback, LARCH_AGGREGATOR_DISABLED kill switch, 0-judge fallback, panel-failed early exit, empty-findings short-circuit, severity-absent aggregator pass, collector-failure routing, TSV sidecar parsing, dispatch_ok isolation, VOTER_1_PARSE_RATE_STATUS pass-through, dedup in-scope-wins, argv errors).
- `scripts/test-dispatch-plan-voters.sh` gains 3 Voter 1 cases (happy/fail/parse-rate-retry).
- `skills/review/scripts/test-aggregate-findings.sh` gains 1 `--input-mode plan` case.
- `SECURITY.md` updated with the subprocess-voter boundary note (OOS_3 / F_64).
- Two follow-up OOS issues filed: #2720 (finalize-plan.sh empty voting-tally.md guard), #2721 (SECURITY.md subprocess voter note). Both blocked by this issue.
- `make lint` passes; design harness shard passes including the new and updated tests.

diff_lines: 850
