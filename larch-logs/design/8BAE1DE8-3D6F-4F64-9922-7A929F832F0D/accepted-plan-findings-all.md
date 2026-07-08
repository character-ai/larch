### FINDING_1: Refresh targeted retally outputs and state
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Targeted Revote Correctness
- **Severity**: major
- **Concern**: After a targeted retally succeeds, the round can still leave summaries, rejected-finding aggregates, and in-memory status/count fields on the first-pass snapshot, so downstream warnings and composed outputs can disagree with the settled ballot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_run_under_quorum_revote`, after full-ballot `tally-code-votes` succeeds, invoke the same `emit-tally` argv shape as `review_core_body._tally_voted_ballot` (read `scout_status`, `dynamic_slots`, `static_slot_count` from first-pass `core` or `review-core.env`), then merge emit/tally KVs into `core` and refresh `review-core.env`
  - From Cursor-Pragmatic: Run logs, round summaries, and compose paths can disagree with the settled ballot. After successful full-ballot retally, call the same `emit-tally` argv bundle `review_core_body` uses (read `review-core-emit.env` fields or rebuild from round context), merge tally KVs into `review-core.env`, then replace round-level outputs.
  - From Cursor-Pragmatic: A successful targeted revote that flips accept/reject counts or clears under-quorum can still route as the first-pass outcome. After retally succeeds, merge tally stdout into `core`, re-run `_core_round_state(core=core, round_dir=round_dir)`, and reassign `core_status` / count locals before `_surface_*` warnings and coder apply.
  - From Cursor-Requirements: After a successful targeted full-ballot retally, run the same `emit-tally` step `review_core_body` uses (mode/scout/dynamic args from first-pass round artifacts), then refresh in-memory `core` from the retally stdout before `_core_round_state`.
  - From Cursor-Requirements: Mirror `review_core_body` diff-mode status selection after retally: when mode is diff and post-retally `ACCEPTED_COUNT>0`, set `REVIEW_CORE_STATUS` to `fix-required` or `cap-reached` using the round cap already available to `_run_round`, then re-run `_core_round_state`.
  - From Cursor-dyn-Targeted Revote Correctness: After successful targeted retally, merge tally KVs into `core` (at minimum `UNDER_QUORUM_*`, `PARSE_FAILED_COUNT`, `VOTER_COUNT`, count fields, classification path) and call `_core_round_state` again before warning surfacing; full-panel fallback should keep today's `_merge_dropped_reviewer_attempt` path


### FINDING_2: Preserve original voter outputs in the merge
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-dyn-Targeted Revote Correctness
- **Severity**: major
- **Concern**: The re-vote path can overwrite the original voter outputs or let appended targeted votes replace healthy first-pass votes on untouched items.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_run_under_quorum_revote`, snapshot `VOTER_N_PATH` from `review-core-voters.env` first; run restricted dispatch with `--review-tmpdir` set to `under-quorum-revote/` (or copy originals into merge inputs before any dispatch); merge original plus revote into new round-level voter files passed to retally
  - From Cursor-Innovation: When merging, keep all original text but append only re-vote lines whose ballot id is in UNDER_QUORUM_ITEMS (reuse BALLOT_HEADING_RE / anchored FINDING_N: and OOS_N: patterns). Optionally assert restricted dispatch output contains no other ids before merge.
  - From Codex-dyn-Targeted Revote Correctness: Capture the tally invocation args and assert the retally reads the merged per-slot files, not the originals, while keeping the existing full-ballot and single-core-call assertions.


### FINDING_3: Replay the full tally context on targeted retally
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Targeted Revote Correctness
- **Severity**: major
- **Concern**: Targeted retally is missing the original first-pass tally context, so proposer mapping, manifest/collector, scope/session, and not-substantive settings can diverge from the healthy-panel path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Full-ballot retally argv contract is underspecified versus `review_core_body._tally_voted_ballot`. Scenario: Plan lists ballot and merged voters only; omitting `--proposer-map-file`, `--manifest-file`, `--collector-results-file`, `--not-substantive-count`, `--scope-files`, `--plan-file`, and `--session-env-path` can change scoreboard dead rows, scope-drift handling, and classification relative to the first pass even when votes are fixed
  - From Codex-Arch: if the full retally only gets merged voter files and voter tools Carry the original proposer-map, manifest, scope, and collector inputs into the re-tally, or call the existing tally entrypoint with the original context and only swap the merged voter files
  - From Cursor-Innovation: Full retally argv parity with review_core is unspecified. Scenario: _run_under_quorum_revote says to retally the full ballot but does not pin the same tally-code-votes flags review_core uses (--manifest-file, --collector-results-file, --proposer-map-file, --scope-files, --plan-file, --session-env-path, --not-substantive-count when nonzero). Omission can change scoreboard dead rows, drift handling, or classification relative to a normal core pass even when votes merge correctly.
  - From Cursor-Pragmatic: Missing `--not-substantive-count`, `--manifest-file`, or `--collector-results-file` can change scoreboard rows, yield TSV, or classification versus the first pass even with identical votes. Document and implement argv replay from round_dir artifacts (`review-core-threshold.env`, `panel-manifest.ndjson`, `collector-results.env`, session paths) matching the first `review_core_capture` tally call.
  - From Codex-Pragmatic: Replay the original dispatch/tally argv, including the generated proposer map, or copy `proposer-map.tsv` into the re-vote dir before dispatching.
  - From Cursor-Requirements: Document and implement `_run_under_quorum_revote` tally/dispatch argv assembly by reusing the same optional args from `round_dir` artifacts produced by the initial `review_core_capture`, matching `_tally_voted_ballot` in `review_core_body.py`.
  - From Cursor-dyn-Targeted Revote Correctness: Have `_run_under_quorum_revote` dispatch on the restricted ballot in the subdir but run final full-ballot `tally-code-votes` with `--review-tmpdir` set to `round_dir`, `--ballot-file` `round_dir/findings.md`, merged `--voter-files`/`--voter-tools`, and the same optional args `_tally_voted_ballot` forwards (session-env, proposer-map, manifest, collector, scope/plan, not_substantive_count)


### FINDING_5: Require complete restricted ballots
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Restricted ballot extraction can silently drop requested items or item types, especially missing ids and OOS blocks, so the targeted retry may not cover the full degraded set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Require every UNDER_QUORUM_ITEMS id to be present before building the restricted ballot; otherwise fall back to the full retry before replacing artifacts
  - From Codex-Innovation: Require every requested id to be present. If any id is missing, abort the targeted path and fall back to the full fresh-panel retry before preserving final artifacts.
  - From Codex-Pragmatic: Copy both FINDING and OOS blocks, or fall back to the full-panel retry whenever any requested id is OOS and cannot be copied.
  - From Codex-Requirements: Require the restricted ballot to cover every ballot item type that the tally can emit, including OOS_* headings, or fall back to the full-panel retry when any requested id cannot be extracted.


### FINDING_6: Tighten the pure under-quorum gate
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-Targeted Revote Correctness
- **Severity**: major
- **Concern**: The pure under-quorum gate is too permissive and can fail open on missing or incomplete threshold metadata or when other degradation signals imply the panel is not actually healthy enough for the targeted path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Threshold parsing fails open on missing or truncated data. Scenario: A missing review-core-threshold.env or absent FAILED_SLOTS field is treated as zero, so an incomplete threshold snapshot can take the targeted path
  - From Codex-Innovation: _pure_under_quorum_degradation treats missing threshold metadata as zero failed slots.. Scenario: If review-core-threshold.env is absent or unreadable, the helper can still classify the round as pure under-quorum and bypass the safer full retry even though the panel-failure data is unknown.
  - From Cursor-Pragmatic: Pure under-quorum gate ignores reviewer NOT_SUBSTANTIVE and partial-judge degradation. Scenario: `_pure_under_quorum_degradation` checks only `UNDER_QUORUM_COUNT`, `PARSE_FAILED_COUNT`, and `FAILED_SLOTS`. `review_tally.py` also stamps degraded banners for `NOT_SUBSTANTIVE_SLOTS` and `effective < expected` judges. Those paths still get a banner today and trigger full `review_core_capture`.
  - From Codex-Requirements: Default missing threshold fields to zero without a presence check.. Scenario: If review-core-threshold.env is absent or malformed, the plan can misclassify the round as pure under-quorum and take the targeted path without the reviewer-slot data needed to prove that retry is safe.
  - From Codex-dyn-Targeted Revote Correctness: Threshold helper defaults missing data to zero instead of failing closed. Scenario: A missing or truncated review-core-threshold.env can still satisfy the pure-under-quorum gate, so a malformed degraded round can skip the safe full-panel retry and run the targeted path on incomplete data.


### FINDING_7: Make retry fallback and sentinels robust
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements, Cursor-dyn-Targeted Revote Correctness, Codex-dyn-Targeted Revote Correctness
- **Severity**: major
- **Concern**: The retry branch and single-shot sentinel can let a failed targeted attempt skip the required full-panel fallback, or forget that the retry already completed on later re-entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Targeted-path failure does not wire fallback to full review_core_capture. Scenario: Edge cases say fall back to the existing full retry when ballot extraction or voter metadata is missing, but the _run_round section only swaps in the targeted path and never says to call review_core_capture when _run_under_quorum_revote returns false. After degraded-retry.flag and attempt-1 preservation, a false return would skip both targeted recovery and the current full-panel retry, leaving the round stuck on the first degraded tally.
  - From Cursor-Requirements: Targeted under-quorum fallback cannot rely on the outer `if not degraded_retry_flag` branch. Scenario: Plan edge cases say to fall back to the existing full-panel retry when ballot extraction fails or `_run_under_quorum_revote` returns false, but the retry body only runs when the flag is absent. A targeted attempt that touches `degraded-retry.flag` first would skip `review_core_capture` on fallback and leave attempt-1 artifacts without a real retry.
  - From Cursor-dyn-Targeted Revote Correctness: Degraded-retry flag guard nests the full-panel retry and all post-retry finalization inside `if not degraded_retry_flag.is_file()`. Scenario: Plan edge cases require falling back to `review_core_capture` when targeted setup fails (missing voter env, ballot extract miss, etc.), but the current control flow touches `degraded-retry.flag` and preserves attempt 1 before choosing a path; a failed targeted attempt leaves the flag set and skips the only `review_core_capture` call, so full-panel retry never runs and `degraded-retry.done` / attempt-2 handling never execute
  - From Codex-dyn-Targeted Revote Correctness: Retry cap sentinel is not idempotent across round re-entry. Scenario: The plan relies on degraded-retry.done, but the current round entry still clears both sentinels. A resumed round can forget that the targeted retry already ran and repeat the costly retry path.


### FINDING_1: Normalize table-form revote rows before merging
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: Targeted revote merging filters only anchored `ID:` lines, so parseable markdown-table vote rows can be dropped and the retally can keep stale under-quorum or JUDGE_ERROR results instead of incorporating the successful revote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `_merge_targeted_voter_outputs`, normalize each revote file with `voting._normalize_markdown_table_votes` (or equivalent) before extracting/appending ballot-id vote lines; add a test with table-formatted revote output for an under-quorum id.
  - From Cursor-Pragmatic: In `_merge_targeted_voter_outputs`, run `_normalize_markdown_table_votes` on each revote file (or extract normalized anchored lines per `UNDER_QUORUM_ITEMS`) before appending; keep case-insensitive `FINDING_N`/`OOS_N` matching consistent with `parse_judge_vote`.
  - From Codex-Pragmatic: Normalize revote text with the existing markdown-table vote normalization before filtering, or convert matching table rows for under-quorum ids into anchored ID: vote lines before appending
  - From Codex-Requirements: Normalize revote text with the same table-to-anchored logic used by parse_judge_vote before filtering, or preserve matching markdown table rows, and cover this in the targeted success test.


### FINDING_2: Keep prune-ledger clearing/refresh on successful targeted retries
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: major
- **Concern**: A successful targeted revote can leave the reviewer-prune ledger stale or uncleared, so later rounds may prune or retain reviewers using the pre-revote classification instead of the final retally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: After targeted or full retry settles and post-retry `_core_round_state` shows a non-prune status, keep the existing `_clear_reviewer_prune_round(ledger=prune_ledger, round_num=round_num, work_dir=round_dir)` guard before downstream warning/coder work; extend the targeted-success test to assert the prune ledger is cleared when degradation clears.
  - From Cursor-Innovation: In `_run_under_quorum_revote` / the degraded branch, when the final tally is clean and `degraded_this_round` is cleared, call `_clear_reviewer_prune_round` under the same `not _reviewer_prune_status_records(core_status)` guard used after `review_core_capture`.
  - From Codex-Pragmatic: After successful targeted retally, run the same prune-ledger record step as review_core_body with the updated classification TSV and panel manifest, or clear the round row if no valid classification exists
  - From Codex-Requirements: After the final targeted tally classification is written, run the existing prune-ledger recording path with reviewer-prune-ledger.tsv, panel-manifest.ndjson, and the final classification file, and assert the ledger reflects the retally.


### FINDING_3: Load scope-files for targeted retally from first-pass gather artifacts
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: Targeted tally arguments can omit the first-pass `--scope-files` context, which may cause the retally to diverge from the initial scoped run and reclassify drifted findings differently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `_build_targeted_tally_args`, load `round_dir/review-core-gather.env` and pass `FILE_LIST_FILE` as `--scope-files` when the file exists, matching `_tally_voted_ballot` parity.


### FINDING_4: Carry session and implement context into targeted emit-tally
- **Reviewer(s)**: Cursor-Innovation, Cursor-Requirements
- **Severity**: major
- **Concern**: Targeted emit-tally needs the same session and implement context as the first-pass emit path so OOS serialization and parent-copy behavior stay aligned; omitting these flags can leave OOS or classification artifacts on the stale snapshot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Build targeted emit argv through the same extras as `_emit_tally_with_context`: add `--session-env-path` from `args.session_env_path` and `--implement-tmpdir` from `IMPLEMENT_TMPDIR` when set.
  - From Cursor-Requirements: Mirror `_emit_tally_with_context`: forward `--session-env-path` and `--implement-tmpdir` whenever first-pass artifacts provide them, and extend the success test to assert both flags on the emit argv.


### FINDING_5: Fail closed when targeted retally returns main-agent-vote-required
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: If a targeted retally collapses to main-agent-vote-required, continuing through the normal emit path can write the wrong rejected/OOS artifacts instead of handing control back to the existing full-panel fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: If targeted retally yields `TALLY_STATUS=main-agent-vote-required`, either run the MAV emit branch verbatim or return false before replacing round artifacts so the existing full-panel fallback runs.


### FINDING_6: Expand the retry gate to include dynamic degradation signals
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: The targeted-retry gate treats the panel as healthy when `FAILED_SLOTS=0`, but dynamic failed/dropped-slot counters or straggler-drop evidence can still indicate a degraded panel that should take the full fresh-panel retry path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add the dynamic slot counters from `review-core-threshold.env` and the existing dropped-slot evidence to the fail-closed gate before allowing `_run_under_quorum_revote`.


### FINDING_7: Do not rerun first-pass capture when the degraded-retry sentinel already settled
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Concern**: A resumed round can rerun `review_core_capture` even though the retry already completed, which can overwrite settled artifacts and then skip the retry paths because `degraded-retry.done` is already present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Short-circuit before the first `review_core_capture` when the done sentinel exists, or restore the settled artifacts instead of rerunning the round body.


### FINDING_8: Include required dispatch-voters flags in the targeted retry path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Concern**: Targeted voter dispatch can fail validation or run with the wrong round context unless the required `dispatch-voters` flags are included alongside the optional context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add those three required flags to the targeted dispatch argv (sourced from `_run_round` args / first-pass round context) in `_run_under_quorum_revote`, and assert them in the targeted success test stub capture.


### FINDING_9: Preserve the pre-fallback OOS append in the fresh-panel retry path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Concern**: The full-fallback retry path can lose attempt-1 OOS accumulation semantics if it skips the pre-fallback append before rerunning the first-pass capture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: When `targeted_ok` is false and the branch calls `review_core_capture`, keep the existing pre-fallback `_append_round_oos_artifact` call before the full retry, unchanged from current `_run_round`.


