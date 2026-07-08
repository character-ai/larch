## Goal
Implement issue #6576: [IMPLEMENTING] [BUG] Under-quorum degraded vote retries full panel; re-vote only affected items.

## Implementation Plan
## Plan

## Approach

Implement the fix in `/implement` review-and-fix only.

`round_runner._run_round` keeps the degraded banner as the entry point, but splits retry into a targeted under-quorum re-vote path and the existing full fresh-panel fallback. The targeted path must settle the same round artifacts and in-memory state as a normal `review_core_capture` tally pass.

### Round entry and resume idempotency

At round entry:

- Clear `degraded-retry.flag` only; **do not** unlink `degraded-retry.done` (preserves idempotency across resumed rounds).
- When `degraded-retry.done` already exists, **short-circuit before the first `review_core_capture`**: reload settled artifacts from `review-core.env`, `voting-tally.md`, and related round sinks instead of rerunning the round body. Parse `core` from disk, run `_core_round_state`, and skip both targeted and full retry paths. This prevents a resumed round from overwriting settled attempt-2 artifacts and then skipping retry because the done sentinel is already present.

Only when the done sentinel is absent run the normal first-pass `review_core_capture`.

### Pure under-quorum classification (fail closed)

Add `_pure_under_quorum_degradation(core, threshold_env, round_dir) -> bool` that returns true only when all are true:

1. `threshold_env` exists, is readable, and parses to a non-empty mapping.
2. Required threshold keys are present with parseable numeric values: `FAILED_SLOTS`, `NOT_SUBSTANTIVE_SLOTS`, `DYNAMIC_FAILED_SLOTS`, `DYNAMIC_DROPPED_SLOTS`. Do not treat absent keys as zero.
3. Required core keys are present with parseable numeric values: `UNDER_QUORUM_COUNT`, `PARSE_FAILED_COUNT`, `VOTER_COUNT`.
4. `UNDER_QUORUM_COUNT > 0`, `PARSE_FAILED_COUNT == 0`, `FAILED_SLOTS == 0`, `NOT_SUBSTANTIVE_SLOTS == 0`, `DYNAMIC_FAILED_SLOTS == 0`, `DYNAMIC_DROPPED_SLOTS == 0`.
5. No other panel-degradation signals in the first-pass tally snapshot:
   - Read `round_dir/review-core-tally.env` when present; if `ELIGIBLE_VOTER_COUNT` is present and `VOTER_COUNT` is present, require `ELIGIBLE_VOTER_COUNT >= VOTER_COUNT`.
   - Read `round_dir/dropped-reviewer-attempts.env` when present; require `STRAGGLER_DROPPED_COUNT == 0` (or key absent).
   - When `DROPPED_SLOTS_FILE` resolves via `_resolve_dropped_slots_file`, require no dynamic drop evidence (`_dynamic_evidence_in_dropped_file` / `_dynamic_evidence_in_manifest` must be false).
   - If the first-pass `voting-tally.md` contains the judge-availability banner (`judge(s) available`), the parse-failed banner, or the NOT_SUBSTANTIVE banner, return false even when under-quorum metadata is also present.

Any missing metadata, malformed env, mixed degradation, or dynamic slot failure/drop evidence → full fresh-panel retry.

### Targeted under-quorum re-vote

When pure under-quorum:

1. Preserve `voting-tally-degraded-attempt-1.md` before any retry work.
2. Snapshot original `VOTER_N_PATH` files from `review-core-voters.env` into `under-quorum-revote/original-voter-N.txt` before dispatch overwrites anything.
3. Build a restricted ballot from full `findings.md` for every id in `UNDER_QUORUM_ITEMS`:
   - Use `voting.BALLOT_HEADING_RE` to extract complete `### FINDING_N:` and `### OOS_N:` blocks.
   - Require every requested id to be found; if any id is missing or the restricted ballot would be empty, abort targeted path (return false) before replacing round artifacts.
4. Dispatch voters on the restricted ballot with `--review-tmpdir` set to `round_dir/under-quorum-revote/`, reusing first-pass optional context when round artifacts exist (`--session-env-path`, `--diff-file`, `--plan-file`) and always including the required `dispatch-voters` flags from `_run_round` / first-pass parity:
   - `--ballot-file` (restricted ballot path)
   - `--review-tmpdir`
   - `--codex-available`
   - `--cursor-available`
   - `--round-num`
   - `--site`
5. Merge voter outputs into new round-level voter files:
   - Keep the full original voter text.
   - Normalize each revote file with `voting._normalize_markdown_table_votes` before extracting vote lines.
   - Append only normalized revote lines whose ballot id is in `UNDER_QUORUM_ITEMS`, using case-insensitive `FINDING_N` / `OOS_N` matching consistent with `voting.parse_judge_vote` / `BALLOT_HEADING_RE`.
   - Do not append unrestricted revote output; untouched items must keep their first-pass votes.
   - If a revote file is missing for a slot, use the original snapshot for that slot.
6. Re-run full-ballot `tally-code-votes` with argv parity to `review_core_body._tally_voted_ballot`:
   - `--review-tmpdir` = `round_dir`
   - `--ballot-file` = `round_dir/findings.md` (full original ballot)
   - `--voter-files` / `--voter-tools` = merged round-level files and original tools from `review-core-voters.env`
   - Load `round_dir/review-core-gather.env` and pass `FILE_LIST_FILE` as `--scope-files` when that file exists and is non-empty.
   - Forward the same optional args from first-pass round artifacts when files exist: `--proposer-map-file` (`round_dir/proposer-map.tsv`), `--manifest-file` (`panel-manifest.ndjson`), `--collector-results-file` (`collector-results.env`), `--plan-file`, `--session-env-path`, `--not-substantive-count` (from parsed `review-core-threshold.env` only when `NOT_SUBSTANTIVE_SLOTS` key exists and value > 0), plus `--cursor-available` / `--codex-available` / `--round-num` from round context.
   - Write diagnostic stdout to `under-quorum-revote/review-core-targeted-tally.env`.
   - If `TALLY_STATUS=main-agent-vote-required`, return false before replacing round artifacts (hand control to full-panel fallback).
7. Only after `TALLY_STATUS` is present and not `main-agent-vote-required`, run the same `emit-tally` argv bundle `review_core_body` uses after a normal tally, through `_emit_tally_with_context` parity:
   - Read `mode`, `scout_status`, `dynamic_slots`, `static_slot_count` from first-pass `core` and/or `review-core-dispatch.env` / `review-core-emit.env`.
   - Forward `--session-env-path` from `args.session_env_path` and `--implement-tmpdir` from `IMPLEMENT_TMPDIR` / `args.implement_tmpdir` when set.
   - Write `under-quorum-revote/review-core-targeted-emit.env`.
   - Replace round-level `voting-tally.md`, accepted/rejected/OOS outputs, classification TSV path, and related tally sinks from the emit step.
8. Refresh settled state before any warning surfacing or downstream routing:
   - Merge tally + emit KVs into `core` (at minimum `UNDER_QUORUM_*`, `PARSE_FAILED_COUNT`, `VOTER_COUNT`, accepted/rejected/exonerated/neutral counts, classification path, `VOTING_TALLY_FILE`, `REVIEW_CORE_STATUS` when emitted).
   - Rewrite `review-core.env` from the merged `core`.
   - Re-run `_core_round_state(core=core, round_dir=round_dir)` and reassign `core_status`, `accepted_count`, `rejected_count`, `exonerated_count`, `neutral_count`, `accepted_file`, `rejected_file`.
   - Mirror `review_core_body` diff-mode status selection: when mode is `diff` and post-retally `ACCEPTED_COUNT > 0`, set `REVIEW_CORE_STATUS` to `fix-required` or `cap-reached` using the round cap already available to `_run_round` (`EFFECTIVE_ROUND_CAP` / tier ceiling from `core` or args).
   - When the final tally is clean (`degraded_this_round` cleared) and `not _reviewer_prune_status_records(core_status)`, call `_clear_reviewer_prune_round(ledger=prune_ledger, round_num=round_num, work_dir=round_dir)`.
   - When a valid final classification TSV exists, call `review_core_body._record_prune_round` with `prune_ledger`, `panel-manifest.ndjson`, and the final classification file so the reviewer-prune ledger reflects the retally.
9. Return true only when steps 3–8 complete without aborting artifact replacement.

### Retry control flow and sentinels

Refactor the degraded branch so targeted failure cannot skip the only full-panel retry:

```
if retry_degraded_panel:
    if degraded_retry_done.is_file():
        # Idempotent re-entry: retry already settled; skip re-running either path
        pass
    else:
        degraded_this_round = True
        preserve attempt-1
        touch degraded-retry.flag   # retry started, not "retry finished"
        targeted_ok = _pure_under_quorum_degradation(...) and _run_under_quorum_revote(...)
        if not targeted_ok:
            _append_round_oos_artifact(...)   # preserve pre-fallback OOS accumulation
            review_core_capture(...)          # existing full fresh-panel retry
            _merge_dropped_reviewer_attempt(...)
            re-parse core + _core_round_state(...)
            if not _reviewer_prune_status_records(core_status):
                _clear_reviewer_prune_round(...)
        touch degraded-retry.done
        preserve attempt-2 when still degraded and changed
        clear degraded_this_round when final tally is clean

Rules:

- Do not nest the only `review_core_capture` call inside `if not degraded_retry_flag`; fallback must run when `_run_under_quorum_revote` returns false even after `degraded-retry.flag` exists.
- Preserve `_append_round_oos_artifact` immediately before full-panel `review_core_capture`, unchanged from current `_run_round`.
- Full-panel fallback keeps today's `_merge_dropped_reviewer_attempt` path and reviewer-slot warning behavior.
- Zero-findings degraded banners keep current skip behavior.

Keep `/design` plan-review out of scope. Do not change quorum thresholds, voter prompts, dispatch policy, panel shape, or `review_tally.py` parsing.

## Files to modify/create

### UPDATED: python/larch/review/round_runner.py

Add private helpers near the degraded retry helpers:

- `_pure_under_quorum_degradation(core, threshold_env, round_dir) -> bool`
  - Fail closed on missing/unreadable `threshold_env` or absent required keys.
  - Use `_env_int` only after presence checks.
  - Require `DYNAMIC_FAILED_SLOTS == 0` and `DYNAMIC_DROPPED_SLOTS == 0` from threshold env.
  - Inspect first-pass `review-core-tally.env`, `dropped-reviewer-attempts.env`, resolved `DROPPED_SLOTS_FILE`, and `voting-tally.md` for mixed degradation banners and dynamic drop evidence.
- `_under_quorum_item_ids(core) -> list[str]`
  - Split `UNDER_QUORUM_ITEMS` on commas, trim, drop empties.
- `_extract_ballot_blocks(source: Path, item_ids: set[str]) -> tuple[str, bool]`
  - Walk `findings.md` with `voting.BALLOT_HEADING_RE`.
  - Collect full `### FINDING_N:` and `### OOS_N:` blocks for requested ids.
  - Return `(restricted_text, all_present)`; `all_present` is false when any requested id is missing.
- `_write_under_quorum_ballot(source, output, item_ids) -> bool`
  - Delegate to `_extract_ballot_blocks`; write output only when `all_present` and non-empty.
- `_review_voter_slots(round_dir) -> tuple[list[str], list[str], list[Path]] | None`
  - Parse `review-core-voters.env`.
  - Return original `VOTER_N_PATH`, `VOTER_N_TOOL`, and readable original file paths.
  - Return `None` when required metadata or files are missing.
- `_snapshot_original_voters(round_dir, revote_dir, slots) -> list[Path]`
  - Copy each original voter file into `revote_dir/original-voter-N.txt`.
- `_merge_targeted_voter_outputs(*, originals: list[Path], revote_files: list[str], under_quorum_ids: set[str], output_paths: list[str]) -> list[str]`
  - For each slot: start from full original text.
  - Run `voting._normalize_markdown_table_votes` on each revote file before line extraction.
  - Append only normalized revote lines matching `^{id}:` for ids in `under_quorum_ids` (case-insensitive, consistent with `parse_judge_vote`).
  - Write merged files to the round-level voter paths used by retally.
- `_build_targeted_dispatch_args(round_dir, args, restricted_ballot, revote_dir) -> list[str] | None`
  - Assemble required `dispatch-voters` argv: ballot, tmpdir, codex/cursor availability, round num, site.
  - Append optional `--session-env-path`, `--diff-file`, `--plan-file` from first-pass artifacts when present.
- `_build_targeted_tally_args(round_dir, core, args, merged_voter_files, voter_tools) -> list[str] | None`
  - Assemble the `_tally_voted_ballot`-parity argv from `round_dir` artifacts.
  - Load `review-core-gather.env` and pass `FILE_LIST_FILE` as `--scope-files` when present.
  - Return `None` when required proposer map or merged voter inputs are missing.
- `_build_targeted_emit_args(round_dir, core, tally_env_path, args) -> list[str] | None`
  - Mirror `review_core_body` emit argv and route through `_emit_tally_with_context` parity (`--session-env-path`, `--implement-tmpdir`).
- `_apply_targeted_retally_outputs(round_dir, core_out: Path, core: dict[str, str], tally: dict[str, str], emit: dict[str, str], args, *, prune_ledger: Path, round_num: int, panel_manifest: Path) -> dict[str, str]`
  - Merge tally + emit KVs into `core`, apply diff-mode status selection, rewrite `review-core.env`.
  - Record or clear prune ledger per final classification and `core_status`.
  - Return updated `core`.
- `_run_under_quorum_revote(round_dir, core, args, threshold_env, *, prune_ledger: Path, round_num: int) -> bool`
  - Orchestrate snapshot → restricted ballot → subdir dispatch → selective merge → full-ballot retally → emit-tally → core refresh.
  - Return false before changing final round artifacts on setup/extraction/argv failure, absent `TALLY_STATUS`, or `TALLY_STATUS=main-agent-vote-required`.

In `_run_round`:

- Stop unlinking `degraded-retry.done` at round entry; clear only `degraded-retry.flag`.
- When `degraded-retry.done` exists before first capture, reload settled `core` from disk and skip capture/retry.
- Parse `threshold = _parse_env_file(threshold_env)` after first core capture.
- Replace the degraded branch with the control-flow structure above.
- Ensure `_surface_under_quorum_warning`, `_surface_parse_failed_warning`, `_surface_dropped_reviewer_warning`, `write_rejected_findings_aggregate`, and coder apply all run against the post-retry refreshed `core` / `_core_round_state` locals.
- Leave the existing full fresh-panel retry behavior intact for:
  - reviewer slot failures (`FAILED_SLOTS > 0`)
  - dynamic slot failures/drops (`DYNAMIC_FAILED_SLOTS > 0`, `DYNAMIC_DROPPED_SLOTS > 0`, straggler/dropped-slot evidence)
  - voter slot removal (`PARSE_FAILED_COUNT > 0`)
  - NOT_SUBSTANTIVE degradation
  - partial-judge / judge-availability banners
  - zero surviving judges
  - malformed threshold/voter/ballot data
  - targeted retally collapsing to `main-agent-vote-required`

### UPDATED: python/tests/review/test_review_and_fix.py

Add and adapt tests around existing degraded retry coverage.

**Targeted success test**

- Fake first `review_core_impl` writes: multi-item `findings.md`, degraded under-quorum `voting-tally.md`, `review-core-threshold.env` with `FAILED_SLOTS=0`, `NOT_SUBSTANTIVE_SLOTS=0`, `DYNAMIC_FAILED_SLOTS=0`, `DYNAMIC_DROPPED_SLOTS=0`, `review-core-tally.env` with matching `VOTER_COUNT`/`ELIGIBLE_VOTER_COUNT`, `review-core-gather.env` with `FILE_LIST_FILE`, `review-core-voters.env`, `proposer-map.tsv`, `panel-manifest.ndjson`, `collector-results.env`, and core KVs `UNDER_QUORUM_COUNT=1`, `UNDER_QUORUM_ITEMS=FINDING_1`, `PARSE_FAILED_COUNT=0`, `VOTER_COUNT=3`.
- Stub command runner for targeted dispatch, retally, and emit-tally.
- Use table-formatted revote output for `FINDING_1` in at least one voter slot.
- Assert:
  - `review_core_impl` runs once
  - restricted dispatch ballot contains only `FINDING_1`
  - dispatch argv includes required `--codex-available`, `--cursor-available`, `--round-num`, and `--site`
  - retally argv uses full `findings.md`, `--review-tmpdir=round_dir`, merged voter files (not originals), `proposer-map.tsv`, manifest, collector, `--scope-files` from gather env, and session/plan args when present
  - merged voter files retain original votes plus appended targeted lines for `FINDING_1` only, including normalized table-form revote rows
  - emit-tally runs after retally with `--session-env-path` and `--implement-tmpdir` when set
  - post-retry `core` / `review-core.env` reflect retally counts and cleared or updated `UNDER_QUORUM_*`
  - prune ledger is cleared or re-recorded from the final classification when degradation clears
  - `_core_round_state` inputs drive downstream accepted/rejected file paths
  - `voting-tally-degraded-attempt-1.md` exists; no second `review_core_impl`

**Fallback tests**

- `PARSE_FAILED_COUNT=1` with `UNDER_QUORUM_COUNT>0` → full `review_core_capture` still runs.
- `FAILED_SLOTS=1` with `UNDER_QUORUM_COUNT>0` → full retry still runs.
- `DYNAMIC_FAILED_SLOTS=1` or `DYNAMIC_DROPPED_SLOTS=1` with `UNDER_QUORUM_COUNT>0` → full retry still runs.
- `NOT_SUBSTANTIVE_SLOTS=1` → full retry still runs.
- `STRAGGLER_DROPPED_COUNT>0` in `dropped-reviewer-attempts.env` → full retry.
- Missing/unreadable `review-core-threshold.env` → full retry, not targeted.
- Missing requested under-quorum id in `findings.md` → targeted returns false, full retry runs.
- Missing `review-core-voters.env` or voter paths → targeted returns false, full retry runs.
- Judge-availability banner in attempt-1 tally → full retry.
- Targeted retally returns `TALLY_STATUS=main-agent-vote-required` → targeted returns false, full retry runs, final artifacts not replaced by targeted emit.
- Targeted revote returns false after `degraded-retry.flag` touched → full `review_core_capture` still runs, pre-fallback `_append_round_oos_artifact` runs, and `degraded-retry.done` is written.

**Sentinel/idempotency test**

- Pre-create `degraded-retry.done` before `_run_round` re-entry → neither first-pass `review_core_capture` nor targeted/full retry re-runs; settled artifacts reload from disk.

**Regression updates**

- Update `test_no_spurious_under_quorum_warning_after_successful_retry` (and similar) to expect targeted re-vote instead of second `review_core_impl` when the fixture qualifies as pure under-quorum.
- Keep existing parse-failed and dropped-reviewer full-retry assertions.

## Edge cases

- Any `UNDER_QUORUM_ITEMS` id absent from `findings.md`, or an OOS id requested but only a FINDING block exists: abort targeted path, fall back to full retry before replacing final artifacts.
- Restricted ballot must include every requested id type (`FINDING_*` and `OOS_*`) that appears in `UNDER_QUORUM_ITEMS`.
- Re-vote output in markdown-table form must be normalized before merge; otherwise healthy revotes are dropped and retally keeps stale under-quorum results.
- Re-vote output missing for one voter slot: merge original snapshot for that slot; full retally decides remaining degradation.
- Final retally still under-quorum: preserve `voting-tally-degraded-attempt-2.md` when it differs from attempt 1; proceed best-effort under the single retry cap.
- Final retally `main-agent-vote-required`: abort targeted path before emit replaces artifacts; full-panel fallback owns MAV handling.
- `degraded-retry.flag` means retry started; `degraded-retry.done` means retry settled (targeted or full). Never let flag block fallback.
- Resumed round with `degraded-retry.done` present must not rerun first-pass capture.
- Existing `dropped-reviewer-attempts.env` warnings still surface on full-retry paths.
- Zero-findings degraded banners: no retry (unchanged).

## Failure modes

- Retallying only the restricted ballot would drop unaffected findings. Mitigation: always retally the full original `findings.md` with merged round-level voter files.
- Overwriting `voting-tally.md` before attempt-1 preservation loses audit evidence. Copy attempt 1 first.
- Defaulting missing threshold fields to zero can misroute malformed or dynamic-degraded rounds into the targeted path. Fail closed on absent required keys and dynamic counters.
- Appending full revote files can overwrite healthy first-pass votes on untouched items. Mitigation: normalize table votes, then selective line merge keyed to `UNDER_QUORUM_ITEMS`.
- Skipping `emit-tally` leaves accepted/rejected aggregates and `review-core.env` on the first-pass snapshot. Run emit-tally and refresh `core` before `_surface_*` and coder apply.
- Omitting session/implement emit context can leave OOS parent-copy behavior on the stale snapshot. Mirror `_emit_tally_with_context`.
- Omitting proposer/manifest/collector/scope/session/not-substantive tally args can change classification or scoreboard rows. Replay `_tally_voted_ballot` argv parity from round artifacts, including `review-core-gather.env`.
- Successful targeted retry without prune-ledger refresh can prune later rounds from stale classification. Record or clear via `_record_prune_round` / `_clear_reviewer_prune_round`.
- Targeted failure without full-panel fallback leaves the round stuck on attempt 1. Wire explicit `review_core_capture` fallback.
- Skipping pre-fallback OOS append loses attempt-1 accumulation semantics on full retry. Preserve `_append_round_oos_artifact` before fallback capture.
- Clearing `degraded-retry.done` on re-entry can repeat costly retries or rerun capture over settled artifacts. Preserve done sentinel and short-circuit reload.
- Rerunning first-pass capture on resume after retry completion can overwrite settled artifacts. Short-circuit when done sentinel exists.

## Testing strategy

Run changed-file tests:

```bash
python3 -m pytest python/tests/review/test_review_and_fix.py -k "degraded or under_quorum or parse_failed or dropped_reviewer or targeted"

Run relevant Python lint/checks:

python3 python/cli.py checks run-relevant

If `checks run-relevant` is too broad or blocked by local state, run the pytest command above plus the repo's normal Python lint target for changed Python work.

## Risk and difficulty

Workflow-affecting review orchestration: changes retry behavior, persisted round artifacts, emit/tally parity, prune-ledger state, resume idempotency, in-memory routing state, and cost-sensitive agent fan-out. Does not change security handling, merge, CI, or session-env writers.

confidence: high

## Acceptance

Run changed-file tests:

```bash
python3 -m pytest python/tests/review/test_review_and_fix.py -k "degraded or under_quorum or parse_failed or dropped_reviewer or targeted"

Run relevant Python lint/checks:

python3 python/cli.py checks run-relevant

If `checks run-relevant` is too broad or blocked by local state, run the pytest command above plus the repo's normal Python lint target for changed Python work.

review_status: complete
rounds_completed: 2
difficulty: MODERATE
mechanical_churn: false
diff_lines: 480

## Test plan
(no test plan section in plan-file)
