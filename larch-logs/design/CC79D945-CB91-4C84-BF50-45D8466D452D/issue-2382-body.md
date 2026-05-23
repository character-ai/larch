## Problem: review is a script, yet it dominates main-agent Claude $

`/implement` Step 5 ultimately dispatches `scripts/run-step5-review.sh`, which calls `skills/review-and-fix/scripts/review-and-fix.sh`. Codex/Cursor handle fix application (`apply_findings_with_coder`), and `flush_review_batches` writes `code-review-tally` + `review-findings-full` larch-log batches internally. So at first glance, the main agent should pay almost nothing during Step 5.

In practice, Step 5 is consistently the #1 Claude cost driver across `/implement` runs. Recent committed run-log analysis (`/larch:report-tokens`):

| Issue | Workflow | Step 5 Claude $ | cache_read | cache_create | output |
| --- | --- | ---: | ---: | ---: | ---: |
| #2231 | SIMPLE | $37.52 | 55.1M | 5.1M | 129k |
| #2253 | SIMPLE | $13.41 | 13.9M | 2.4M | 16k |
| #2263 | SIMPLE | $6.24 | 9.3M | 0.9M | 17k |
| #2274 | HARD | $17.93 | 18.5M | 3.1M | 39k |

Output is small ($0.23–$1.94). The Claude $ is almost entirely cache_read + cache_create on the main agent's session transcript.

## Why this happens

`run-step5-review.sh` and `review-and-fix.sh:run_implement_round` are designed to process **exactly one round per invocation** and return. The round loop lives in the main agent's SKILL.md prose (`skills/implement/SKILL.md` "Step 5 — Code Review"):

> Track `round_num` from 1. For each round, run one foreground Bash call: `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --round-num "$round_num"`

For N rounds, the main agent issues N bash calls and N+ API turns happen between them. While each bash call runs, the main agent is idle and pays nothing — but at every gap between bash calls, an API turn fires and re-reads the entire accumulated transcript as cache_read. By Step 5 the transcript already carries design plan, implementation output, Step 3 checks loop, and SKILL.md prose.

Per-round main-agent work between bash calls (each is a separate API turn or a few):

1. Parse `REVIEW_AND_FIX_STATUS` / `ACCEPTED_COUNT` / `CODER_STATUS` from `run-step5-review.sh` stdout, branch on status
2. Run `run-relevant-checks-captured.sh --site step5-review-fixes`; parse `STATUS` and `REDACTED_LOG_FILE`
3. If checks failed: dispatch `lint-fix-loop.sh --site step5`; parse `LINT_FIX_STATUS`; possibly re-run checks
4. Substantiality classification (mechanical criteria: ≥2 high-severity, OR ≥100 LOC structural, OR ≥8 accepted)
5. Bulk-skip-ratio gate (`SKIPPED_FINDING_COUNT / FIX_COUNT >= LARCH_SKIP_RATIO_THRESHOLD`)
6. Loop or exit decision

That is ~6 API turns per round minimum. With round caps of 5 (SIMPLE) / 7 (HARD) plus an occasional Step 5 restart, you get 20–40 turns each replaying a ~100K-token transcript = tens of millions of cache_read tokens at $0.30/M = double-digit dollars per Step 5.

For #2231 specifically: ~4 rounds plus a full Step 5 restart (Step 5 → Step 6 → Step 5 again) doubled the cache_read for the second phase, producing the $37.52 outlier.

## Proposal: absorb the Step 5 round loop into review-and-fix.sh

Rearchitect so that one main-agent Bash call covers all rounds of Step 5, instead of N bash calls with N main-agent decision gaps between them.

Concretely, the script (`review-and-fix.sh` or a new wrapper) would internalize:

- The round-loop iteration up to `round_cap` (5 / 7 by panel)
- Calling the relevant-checks helper between rounds (or equivalent inline lint enforcement)
- Dispatching `lint-fix-loop.sh` on failed checks
- The substantiality classification gate
- The bulk-skip-ratio gate
- The "stall to Step 16" early-exit conditions (`coder-failed`, `submodule-violation`, `panel-failed`, `bulk-skip-ratio cap`)
- The main-agent-vote-required fallback only when *all 3* judges fail (rare; can stay as an exception path that still returns to the main agent)

The main agent then sees Step 5 as **one bash call**, parses the final summary KVs, and proceeds to Step 6.

Out of scope for the initial cut: changes to `/review` standalone diff mode, to `/review-and-fix` findings-mode dispatch, to the panel/voting internals, or to per-round `larch-log` batch flushing (these are already inside the script and unaffected).

## Why this will notably reduce costs

The cost mechanism is: `Step 5 Claude $ ≈ (# of API turns in Step 5) × (transcript size × cache_read_rate) + small output term`.

By collapsing N rounds × M gaps into 1 bash call, the number of API turns inside Step 5 drops from roughly 20–40 to roughly 2–4 (one to dispatch, one to parse the final result, plus any post-loop tally-batch composition still in the main agent — itself a candidate for cleanup since `flush_review_batches` already writes the canonical batches).

Order-of-magnitude estimate on observed runs:

- #2231 ($37.52 today): expected drop to roughly $3–$6 (≈85% reduction). The restart, if it happened at all under the new architecture, would also be much cheaper because the second phase would again be a single bash call rather than another N-round loop.
- #2253 ($13.41 today): expected drop to ~$1–$2.
- #2263 ($6.24 today): expected drop to ~$1.
- #2274 HARD ($17.93 Claude part today): expected drop to ~$2–$3. Codex part ($37.67) is unchanged — those are external reviewer dispatch costs the architecture doesn't touch.

Across the recent 9-day window with 184 SIMPLE runs at median $11.31 ($2,685 total) and 9 HARD runs at median $42.02 ($451 total), Step 5 is the modal contributor and cache_read is 50–67% of Claude cost. If 80% of Step 5 Claude $ is removed, total spend drops by an estimated 25–35% just from this one change, with no impact on review thoroughness (same panel, same voting, same coder dispatch — only the loop controller moves from prose to bash).

## Notes for the implementing session

- The substantiality and bulk-skip-ratio gates are already mechanical; their criteria are documented in `skills/implement/SKILL.md` Step 5 prose ("Re-review gate" and "Bulk-skip-ratio gate" subsections). Port the rules into bash with `LARCH_SKIP_RATIO_THRESHOLD` honored.
- The script must emit a final summary KV block that lets the main agent move directly to Step 6 — including `STALL_TRACKING=true` for early-exit conditions so Step 16 routing still works.
- Post-loop tally batch composition: `flush_review_batches` already writes both `code-review-tally` and `review-findings-full`. The SKILL.md's instructions for the main agent to compose those batches appear to duplicate this work; verify and remove the duplicate path in the same cleanup.
- Preserve existing harness coverage: `skills/review-and-fix/scripts/test-review-and-fix.sh`, `skills/implement/scripts/test-implement-review-token-propagation.sh`, and Step 5 lint-fix-loop tests should keep passing; add new assertions for the absorbed loop.
- This change is `/implement`-only. `/review` standalone (`--diff` mode) keeps its own round loop in `skills/review/SKILL.md` Step 3.

<!-- larch:plan:start -->
## Plan

**This is the FINAL implementation plan** — post-review and Gate B revisions applied (27 accepted findings incorporated; 2 exonerated; 1 OOS accepted as a follow-up). The 10-reviewer plan-review panel (5 Cursor × Arch/Edge/Innovation/Pragmatic/Requirements + 5 Codex × same archetypes) and 3-voter adjudication panel (Claude + Codex + Cursor) signed off on this revision. The implementor should execute this plan exactly; intermediate sketches, the dialectic resolution on hosting, and the original first-pass draft are not authoritative and exist only in the run-log artifacts for audit.

### Goal

Collapse the prose-owned Step 5 round loop in `skills/implement/SKILL.md` into a single foreground Bash call. The new wrapper internalizes the round loop, post-round `run-relevant-checks-captured.sh`, post-checks `lint-fix-loop.sh`, the substantiality + bulk-skip-ratio gates, and the next-round decision. The main agent sees Step 5 as one bash call, parses a final summary KV envelope, and proceeds to Step 6 or Step 16. Cost reduction expected: 80%+ of current Step 5 Claude cost across observed runs (#2231 $37.52 → ~$3-6, #2253 $13.41 → ~$1-2, #2274 HARD $17.93 Claude → ~$2-3, etc.).

### Files to create

1. **`scripts/lib-implement-round-cap.sh`** (NEW) — extract `count_prior_degraded_rounds` (currently only at `scripts/run-step5-review.sh:50-66`) into a sourced library. Single source of truth for cap-math.
2. **`scripts/lib-implement-round-cap.md`** (NEW) — sibling doc for the shared library: signature `count_prior_degraded_rounds(implement_tmpdir, current_round)`, read paths (`round-N/review-and-fix.env`), Bash 3.2 compatibility, validation behavior.
3. **`scripts/test-lib-implement-round-cap.sh`** (NEW) — pin the shared helper: `lib_helper_returns_zero_when_no_prior_rounds`, `lib_helper_counts_degraded_rounds_correctly`, `lib_helper_ignores_non_degraded_rounds`, `lib_helper_handles_missing_round_artifacts_gracefully`.

### Files to modify — runtime

4. **`skills/review-and-fix/scripts/review-and-fix.sh`**
   - Source `scripts/lib-implement-round-cap.sh` at the top of the file. Replace any duplicate inline cap-math with the helper call.
   - Add `--mode loop` and `--mode mav-apply` argv recognition (existing `--mode diff` and `--findings-file` paths remain unchanged for backward compatibility).
   - Add `--starting-round N` argv (default 1, used by `--mode loop`). Validation: when `N>1`, the wrapper checks that `$IMPLEMENT_TMPDIR/round-${N-1}/review-and-fix.env` exists; on missing artifact, exit with `STEP5_REVIEW_STATUS=stall STALL_REASON=starting-round-invalid`.
   - **Wrap top-level dispatch in `main "$@"` guard** so the script is source-safe for tests:
     ```bash
     main() {
       case "$MODE" in
         loop)   run_implement_loop ;;
         diff)   [[ -n "$IMPLEMENT_TMPDIR" ]] && run_implement_round ;;
         mav-apply) run_implement_mav_apply ;;
         *) [[ -n "$IMPLEMENT_TMPDIR" ]] && run_implement_round ;;
       esac
       [[ -n "$FINDINGS_FILE" && -z "$IMPLEMENT_TMPDIR" ]] && run_findings_mode
     }
     if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then main "$@"; fi
     ```
     Replace the current footer (`if [[ -n "$IMPLEMENT_TMPDIR" ]]; then run_implement_round; fi; run_findings_mode`) with this dispatch matrix.
   - **Exit audit**: convert every body-reachable `exit 2` inside `run_implement_round` and its helpers into a return-status path. Confirmed sites: `review-and-fix.sh:199-200` (apply_findings_with_coder failure), `:1129-1132` (security classifier failure), `:1237-1238` (review-and-fix.env write failure). Each conversion gets a regression test asserting the final envelope is still emitted.
   - Widen the `MODE` guard inside `run_implement_round` to accept the legacy explicit `--mode diff`; reject only unknown modes.
   - **Extract `_implement_round_body`**: pull the current `run_implement_round` body into a new private function that returns status via in-process variables. The existing `run_implement_round` becomes a thin wrapper that calls `_implement_round_body`, captures return code + emitted KVs, then `exit`s with the captured code (preserves single-round CLI contract).
   - **Per-round artifact contract**: `_implement_round_body` writes `$IMPLEMENT_TMPDIR/round-${round_num}/pre-coder-head.txt` (via `git rev-parse HEAD`) immediately before invoking `apply_findings_with_coder` for EVERY round (not just round 1). On `fix-applied`, write `$IMPLEMENT_TMPDIR/round-${round_num}/post-coder-head.txt`. The existing run-root `pre-review-head.txt` is unchanged.
   - **Gate input persistence**: after each round body completes, persist `HIGH_SEVERITY_COUNT` (count of Important/Critical/High-tagged accepted findings scanned from `round-N/accepted-findings.md` via the existing `important_findings_present` regex family at review-and-fix.sh:101-119), `FIX_COUNT`, and `SKIPPED_FINDING_COUNT` into `round-${N}/review-and-fix.env`.
   - **Add `run_implement_loop` function** (placement: next to `run_implement_round`):
     - Initialize `round_num` from `--starting-round N` (default 1).
     - Compute `effective_round_cap = ROUND_CAP + count_prior_degraded_rounds(IMPLEMENT_TMPDIR, $round_num)` using the shared library. ROUND_CAP comes from `--round-cap` (loop mode requires base value, NOT pre-inflated).
     - Emit per-round breadcrumb: `→ Step 5 round ${round_num}/${effective_round_cap}` via existing `emit_breadcrumb`.
     - For each iteration, call `_implement_round_body`. Capture round exit_code and parsed status keys (in-process, not via stdout).
     - **Status routing matrix**:
       - `REVIEW_AND_FIX_STATUS=main-agent-vote-required` → exit loop with `STEP5_REVIEW_STATUS=main-agent-vote-required`, `FINAL_ROUND_NUM=$round_num`, round artifacts intact.
       - `REVIEW_AND_FIX_STATUS=panel-failed` → `STEP5_REVIEW_STATUS=stall STALL_TRACKING=true STALL_REASON=panel-failed`.
       - `REVIEW_AND_FIX_STATUS=coder-failed`: check `CODER_STATUS` first. If `CODER_STATUS=submodule-violation`, exit with `STALL_REASON=submodule-violation`. Otherwise exit with `STALL_REASON=coder-failed`.
       - `REVIEW_AND_FIX_STATUS=converged-small-changes`/`no-changes`/`no-findings`/`in-scope-filtered-out` → exit loop with `STEP5_REVIEW_STATUS=complete` directly. **Do NOT run post-round checks/lint-fix/gates** — these statuses indicate no coder edits or filtered-out state.
       - `REVIEW_AND_FIX_STATUS=fix-applied` → continue to post-round helper dispatch.
       - Any other / unknown status → `STEP5_REVIEW_STATUS=stall STALL_REASON=round-failed-${REVIEW_AND_FIX_STATUS:-unknown}` (catch-all).
     - **Post-round helper dispatch** (only for `fix-applied`):
       - Dispatch `run-relevant-checks-captured.sh --tmpdir "$IMPLEMENT_TMPDIR" --site step5-review-fixes`. Parse with **token-aware splitter**: each line may carry multiple `KEY=value` tokens (e.g., `STATUS=fail FAILURE_REASON=...`); tokenize by whitespace and extract each independently.
       - If `STATUS=fail` AND `REDACTED_LOG_FILE` is empty/absent → structural stall: `STEP5_REVIEW_STATUS=stall STALL_REASON=relevant-checks-${FAILURE_REASON:-unknown}`. No lint-fix without a redacted log.
       - If `STATUS=fail` AND `REDACTED_LOG_FILE` is non-empty → enter lint-fix sub-loop with `lint_fix_attempts=0`, `lint_fix_max=${LARCH_STEP5_LINT_FIX_MAX_ATTEMPTS:-3}`:
         - Dispatch `lint-fix-loop.sh --tmpdir "$IMPLEMENT_TMPDIR" --site step5 --checks-log "$REDACTED_LOG_FILE"`. Parse `LINT_FIX_STATUS`.
         - `applied` → increment attempts. If at `lint_fix_max`, stall with `lint-fix-attempt-cap`. Otherwise re-dispatch checks; if pass, break to substantiality gate; if fail, repeat.
         - `main-agent-required` → stall with `lint-fix-main-agent-required`.
         - `failed` → stall with `lint-fix-failed`.
         - `no-changes` → re-invoke checks once; if still failing, treat as `failed` stall.
       - On checks pass (`RELEVANT_CHECKS_OK=true` or `RELEVANT_CHECKS_SKIPPED=true`), apply re-review gate.
     - **Re-review gate**:
       - Re-read `DEGRADED_ROUND` from `round-${N}/review-and-fix.env`; if `true`, increment `effective_round_cap` once for the current iteration.
       - Substantiality: substantial = (`HIGH_SEVERITY_COUNT >= 2`) OR (`structural_loc >= 100`) OR (`FIX_COUNT >= 8`). `structural_loc = git diff --numstat $(cat round-N/pre-coder-head.txt) $(cat round-N/post-coder-head.txt) | awk '{a+=$1; b+=$2} END {print a+b}'`. On numstat failure, structural_loc=0, log Warnings.
       - Bulk-skip-ratio gate: if `FIX_COUNT > 0`, `skip_ratio = SKIPPED_FINDING_COUNT / FIX_COUNT`; threshold default 0.5 (overridable via `LARCH_SKIP_RATIO_THRESHOLD`).
       - `skip_ratio >= threshold` AND `round_num < effective_round_cap` → log loop-trigger, increment `round_num`, continue.
       - `skip_ratio >= threshold` AND `round_num == effective_round_cap` → stall with `bulk-skip-ratio-cap`.
       - Substantial AND `round_num < effective_round_cap` → increment `round_num`, continue.
       - Substantial AND `round_num == effective_round_cap` AND bulk-skip didn't stall → exit with `STEP5_REVIEW_STATUS=cap-hit`.
       - Non-substantial AND bulk-skip didn't loop → exit with `STEP5_REVIEW_STATUS=complete`.
     - **Final KV envelope** (LAST lines of stdout, last-line discipline; fixed enums):
       - `STEP5_REVIEW_STATUS` ∈ {`complete`, `stall`, `cap-hit`, `main-agent-vote-required`, `mav-resume-past-cap`}
       - `STALL_TRACKING` ∈ {`true`, `false`}
       - `STALL_REASON` ∈ {`coder-failed`, `panel-failed`, `submodule-violation`, `lint-fix-failed`, `lint-fix-main-agent-required`, `lint-fix-attempt-cap`, `bulk-skip-ratio-cap`, `relevant-checks-<reason>`, `starting-round-invalid`, `round-failed-<status>`, `classifier-failed`, `env-write-failed`, `""`}
       - `ROUNDS_COMPLETED=N`
       - `FINAL_ROUND_NUM=N`
       - `FINAL_REVIEW_AND_FIX_STATUS=<last per-round status>`
       - `CODER_STATUS=<last per-round CODER_STATUS, or empty>`
       - `FILES_CHANGED_HINT=<best-effort coder commit info>`
       - `EFFECTIVE_ROUND_CAP=N`
     - **Exit code contract**: wrapper exits 0 for `complete`, `cap-hit`, `main-agent-vote-required`, `mav-resume-past-cap`; exits 2 for `stall` (any reason).
     - **`flush_review_batches` cadence**: each `_implement_round_body` call ends with `flush_review_batches` as today (gated on round exit_code=0). Additionally, after loop exits on stall paths, call `flush_review_batches` once with best-effort flag so stall paths still produce partial batches.
   - **Add `run_implement_mav_apply` function**: accepts `--findings-file`, `--implement-tmpdir`, `--round-num N`. Same commit/artifact contract as an ordinary review round (writes `round-N/pre-coder-head.txt`, dispatches coder, writes `round-N/post-coder-head.txt` on success, flushes batches).

5. **`scripts/run-step5-review.sh`**
   - Source `scripts/lib-implement-round-cap.sh` (replace the local `count_prior_degraded_rounds` definition).
   - Add `--starting-round N` argv (default 1, passthrough).
   - Add `--mode loop|single|mav-apply` argv (default `loop` when invoked from SKILL.md Step 5).
   - **Cap math ownership split**:
     - `--mode loop`: forward `--round-cap 5` (BASE cap, NOT pre-inflated) + `--mode loop --starting-round $STARTING_ROUND`. Loop wrapper inflates internally.
     - `--mode single`: existing dispatch unchanged. ROUND_CAP is pre-inflated by the launcher.
     - `--mode mav-apply`: forward `--mode mav-apply --round-num N --findings-file <path>`.
   - Backward compat: `--round-num N` without `--mode` → treat as `--mode single`.
   - When `--mode loop`, do NOT require `--round-num`.
   - Update `usage()` text to enumerate all new flags.

6. **`skills/implement/SKILL.md` — Step 5 prose (lines ~1198-1290) + early Step 5 bullets (line 42, lines 1200-1206)**
   - **Collapse the per-round loop prose (lines ~1208-1241)** into one Bash block:
     ```bash
     "${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh" \
       --implement-tmpdir "$IMPLEMENT_TMPDIR" \
       --mode loop \
       --starting-round 1
     ```
   - KV parser block (token-aware extractor, matching FINDING_22). Branch on `STEP5_REVIEW_STATUS`:
     - `complete` → continue to Step 6 via existing post-Step-5 chain (Cross-Skill Presence Propagation → `code-review-tally` reference (now informational; flush_review_batches already wrote the batch) → Track Rejected Code Review Findings → Step 6 breadcrumb).
     - `cap-hit` → print `**⚠ 5: code review hit $EFFECTIVE_ROUND_CAP-round cap without converging. Proceeding.**`, log to Warnings, then run the post-Step-5 chain.
     - `stall` → log `Step 5 — wrapper stalled: $STALL_REASON` to the appropriate category in `$IMPLEMENT_TMPDIR/execution-issues.md` (`Coder Issues` for coder-failed/submodule-violation/lint-fix-main-agent-required; `Tool Failures` for panel-failed/lint-fix-failed/lint-fix-attempt-cap/relevant-checks-*; `Tracking Issues` for starting-round-invalid; `Tool Failures` default). Set `STALL_TRACKING=true`. Skip to Step 16.
     - `main-agent-vote-required` → execute existing main-agent voting prose (read FINDINGS_FILE, cast YES/NO/EXONERATE per finding, write voter-main-agent.txt, re-tally). Dispatch `review-and-fix.sh --implement-tmpdir "$IMPLEMENT_TMPDIR" --mode mav-apply --round-num $FINAL_ROUND_NUM --findings-file "$ACCEPTED_FINDINGS_FILE"`. Run `run-relevant-checks-captured.sh`. Log `Step 5 — 0-judge panel: main-agent adjudication performed`. Re-invoke wrapper with `--starting-round $((FINAL_ROUND_NUM + 1))`. On resume, the loop runs substantiality+bulk-skip retroactively on round `FINAL_ROUND_NUM` artifacts before deciding the next round. If `FINAL_ROUND_NUM == EFFECTIVE_ROUND_CAP`, resume yields `STEP5_REVIEW_STATUS=mav-resume-past-cap`.
     - `mav-resume-past-cap` → main agent prints `**ℹ 5: MAV resume past cap; no additional review round executed.**` and routes as `complete`.
   - **Remove the duplicate prose (lines ~1245-1281)** for `### Larch-log batch — code-review-tally` and `### Larch-log batch — review-findings-full`. Replace with a brief note: `Note: review-and-fix.sh runs flush_review_batches at the end of every successful round (and best-effort once on stall paths), writing both code-review-tally and review-findings-full batches. compose_review_findings_output passes --issue 0 as the authoritative contract; downstream log consumers join records by RUN_ID. No additional main-agent composition is required.` Preserve `### Track Rejected Code Review Findings` (which documents the *format*, not a duplicate composition).
   - **Update the Step 5 banner** to reflect the new single-call shape: `> **🔶 /implement 5: code review — run-step5-review.sh --mode loop, up to $effective_round_cap rounds; 3-judge panel on round 1 (Claude+Codex+Cursor), 2-judge on rounds 2+ (Claude+Cursor); review panel: 6 Cursor specialists; dynamic-archetypes cap=$dynamic_archetypes_cap**`
   - **Update non-Step-5 SKILL.md bullets**: line 42 (early Step 5 reference) and lines 1200-1206 (per-round `run-step5-review.sh` argv derivation + "Track round_num from 1") MUST be rewritten to describe the new single-call shape. Grep SKILL.md for `run-step5-review` and `round_num` outside the Step 5 block; update each occurrence.

### Files to modify — script-md siblings (per `.claude/rules/script-md-siblings.md`)

7. **`scripts/run-step5-review.md`** — document new flags + dispatch modes + cap-math ownership + new shared library source.
8. **`skills/review-and-fix/scripts/review-and-fix.md`** — document `--mode loop`, `--mode mav-apply`, `--starting-round N`; `run_implement_loop` function; post-round helper dispatch; per-status routing matrix table; substantiality/bulk-skip gates (with the deterministic `git diff --numstat` proxy and `HIGH_SEVERITY_COUNT` scanner); stall-reason fixed enum; exit-code contract; `main "$@"` guard; per-round artifact contract; gate-input persistence; lint-fix attempt-cap; MAV apply path; final-summary KV envelope schema with examples.
9. **`scripts/larch-log-batches.md`** — document `--issue 0` as authoritative contract for in-process `review-findings-full` compose; consumers join by RUN_ID.

### Files to modify — tests

10. **`skills/review-and-fix/scripts/test-review-and-fix.sh`** — add 16 new test cases:
    - `loop_complete_after_non_substantial`
    - `loop_continues_after_substantial_round_below_cap`
    - `loop_iterates_to_cap`
    - `loop_stall_coder_failed`
    - `loop_stall_submodule_violation`
    - `loop_stall_panel_failed`
    - `loop_main_agent_vote_required_and_resume`
    - `loop_starting_round_validates_artifacts`
    - `loop_bulk_skip_ratio_stalls_at_cap`
    - `loop_relevant_checks_structural_fail_no_log`
    - `loop_lint_fix_attempt_cap`
    - `loop_catchall_unknown_status`
    - `loop_exit_audit_classifier_failure`
    - `loop_mav_resume_past_cap`
    - `loop_status_matrix_complete_short_circuits` (each of `converged-small-changes`, `no-changes`, `no-findings`, `in-scope-filtered-out` exits `complete` WITHOUT running checks)
    - `loop_high_severity_count_from_accepted_findings`
    - `loop_round_pre_post_coder_head`
    (Existing single-round cases stay green.)
11. **`scripts/test-run-step5-review.sh`** — add: `dispatch_loop_default`, `dispatch_loop_explicit_starting_round`, `dispatch_single_round_backward_compat`, `dispatch_mav_apply`.
12. **`skills/implement/scripts/test-implement-review-token-propagation.sh`** — extend with loop-mode propagation assertions.
13. **Structure tests**: update grep-assertions about Step 5 prose; assert duplicate tally prose removed; assert parser case-branch covers every `STEP5_REVIEW_STATUS` value (including `mav-resume-past-cap`); assert envelope-key coverage.

### Edge cases (must be handled)

- Restart at `--starting-round N>1` with missing `round-(N-1)/review-and-fix.env` → exit `STALL_REASON=starting-round-invalid`.
- Degraded round inflation accumulates across MAV-resume re-invocations (disk-derived via shared lib).
- `RELEVANT_CHECKS_SKIPPED=true` (no check script applicable) → treat as pass.
- MAV at round 5 (cap) + restart at `--starting-round 6` → `STEP5_REVIEW_STATUS=mav-resume-past-cap`; main agent prints info line, continues.
- Coder commits no changes after `fix-applied` → `structural_loc=0`; substantiality falls back to `HIGH_SEVERITY_COUNT` and `FIX_COUNT`.
- `LARCH_SKIP_RATIO_THRESHOLD` invalid decimal → log Warnings, use default 0.5.
- `git diff --numstat` fails → `structural_loc=0`, log Warnings.
- `run-relevant-checks-captured.sh` multi-KV-per-line → token-aware parser.
- `STATUS=fail` with empty `REDACTED_LOG_FILE` (log-dir-create-failed, log-allocation, etc.) → structural stall, no lint-fix.
- `lint-fix-loop.sh` returns `applied` repeatedly → capped at `LARCH_STEP5_LINT_FIX_MAX_ATTEMPTS` (default 3).
- Unknown `REVIEW_AND_FIX_STATUS` → catch-all `STALL_REASON=round-failed-<status>`.
- `run_implement_round` legacy CLI re-entry → existing `--mode diff --round-num N` still works.

### Failure modes (top 3)

1. **Contract drift between absorbed loop's KV envelope and SKILL.md parser.** Earliest warning: structure test asserting SKILL.md parser case-branches cover every `STEP5_REVIEW_STATUS` value. Mitigation: pin envelope shape in `test-review-and-fix.sh` per-exit-path + SKILL.md structure assertion.
2. **Exit-audit miss leaves an uncaught `exit 2` inside the loop body.** Earliest warning: each formerly-exit-2 path has a regression test asserting the final envelope is emitted (process did NOT die mid-loop). Mitigation: enumerate confirmed sites (review-and-fix.sh:199, :1131, :1238) + grep CI assertion that no new `exit 2` calls exist in functions called from `_implement_round_body` without corresponding regression coverage.
3. **Substantiality `HIGH_SEVERITY_COUNT` scanner false-positive/negative.** Earliest warning: unit test pinning the regex output against a corpus of known-tagged accepted findings. Mitigation: reuse existing `important_findings_present` regex family (already validated); document the regex as load-bearing in `review-and-fix.md`.

### Out-of-scope follow-ups (filed separately by /implement)

- `OOS_3`: numstat path/extension filtering for substantiality (filter `*.md`, vendored `*.json`, generated assets). Conservative threshold 100 stands for the first cut; refinement is a follow-up.

## Acceptance

This implementation is accepted when ALL of the following are true:

1. **Single-call dispatch verified**: `/implement` Step 5 invokes `scripts/run-step5-review.sh --mode loop` ONCE per Step 5 entry. Multi-round behavior happens entirely inside the wrapper. Observed Claude cost at Step 5 drops by ≥75% across a sampling of SIMPLE and HARD runs (target: 80%+).

2. **Existing single-round CLI unchanged**: `review-and-fix.sh --mode diff --round-num N` continues to work; `test-review-and-fix.sh` existing cases pass without input changes; `test-implement-review-token-propagation.sh` existing assertions stay green.

3. **All 16 new `test-review-and-fix.sh` loop cases pass** (each enumerated above), AND all 4 new `test-run-step5-review.sh` dispatch cases pass, AND the new `test-lib-implement-round-cap.sh` cases pass.

4. **KV envelope contract pinned**: structure tests assert SKILL.md parser handles every value `STEP5_REVIEW_STATUS` can emit (`complete`, `stall`, `cap-hit`, `main-agent-vote-required`, `mav-resume-past-cap`); envelope-key coverage assertion verifies every required key is present in every loop-exit path.

5. **Stall semantics preserved exactly**: each existing stall condition (panel-failed, coder-failed, submodule-violation, lint-fix-failed, lint-fix-main-agent-required, bulk-skip-ratio cap, round-cap-without-converge) routes to the same `execution-issues.md` category and Step 16 destination as today; the new `lint-fix-attempt-cap`, `starting-round-invalid`, and `round-failed-<status>` reasons route to `Tool Failures` (or `Tracking Issues` for starting-round-invalid).

6. **Duplicate tally-batch prose removed**: SKILL.md lines ~1245-1281 no longer contain the duplicated `### Larch-log batch — code-review-tally` / `### Larch-log batch — review-findings-full` composition steps. Replacement is a brief informational note.

7. **Non-Step-5 SKILL.md references updated**: SKILL.md line 42 and lines 1200-1206 no longer describe per-round `run-step5-review.sh` argv derivation or "Track round_num from 1." A grep for `round_num` outside the Step 5 block returns only context that is consistent with the single-call shape.

8. **Cap-math owner is the shared library**: `scripts/lib-implement-round-cap.sh` is the only definition of `count_prior_degraded_rounds`; both `run-step5-review.sh` and `review-and-fix.sh`'s loop source it. No double-inflation possible.

9. **Per-round artifacts present**: every round produces `round-N/pre-coder-head.txt` (before coder) AND `round-N/post-coder-head.txt` (after `fix-applied`), AND `round-N/review-and-fix.env` carries `HIGH_SEVERITY_COUNT`, `FIX_COUNT`, `SKIPPED_FINDING_COUNT` (in addition to existing keys).

10. **Source-safe testing**: `review-and-fix.sh` can be `source`d in a test without triggering top-level dispatch (the `main "$@"` guard contract); tests can stub `_implement_round_body` and `run_implement_mav_apply`.

11. **Exit audit complete**: confirmed `exit 2` sites at `review-and-fix.sh:199-200`, `:1129-1132`, `:1237-1238` are converted to in-process status returns; each former-`exit 2` path has a regression test that asserts the final envelope is emitted on its failure condition.

12. **`make lint` and `bash scripts/relevant-checks.sh` pass cleanly** on the resulting branch; no regression in existing harness coverage.

diff_lines: 1660
<!-- larch:plan:end -->

