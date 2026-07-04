### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:403-431
- **Concern**: Cross-session `skip-sentinel` can run before aggregate pool promotion. Scenario: Bug B only checks `_extract_unfiled_blocks` on recovered `oos-accepted-design.md`. On a same-issue re-run, cross-session recovery can mark prior blocks filed while new qualifying items live only in `oos-aggregate-pool.md`. Prepare returns `skip-sentinel` before the trigger promotes them, so aggregate-only filing still fails on re-runs.
- **Proposed resolution**: Run pool read/evaluate/promote (or at least consult the pool trigger) before any cross-session `skip-sentinel` return; only skip when recovered accepted text has no unfiled blocks and the pool cannot fire filing.

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_tally.py:833-834 and python/larch/review/review_tally.py:878-907
- **Concern**: Pool accumulation omits a dedup contract the edge cases require. Scenario: The plan lists "duplicate plan-review rounds should not duplicate pool items" but does not require `_append_unique_artifact_blocks` (or equivalent stable-id dedup) when appending to `oos-aggregate-pool.md` / the session pool. Re-tallied or repeated blocks can inflate latent counts and fire filing on duplicates.
- **Proposed resolution**: Specify and implement pool writes with the same unique-block append helper used for `oos-accepted-design.md`, and make trigger counting operate on deduped pool entries.

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5b.py:227-257 and skills/design/references/finalize-step5.md:49-55
- **Concern**: Bug A retry path still lacks a once-only guard (accepted FINDING_3 incomplete). Scenario: The plan adds `NEXT_ACTION=retry-file-and-annotate` but does not define a retry sentinel, env flag, or orchestrator branch bound. `/larch:issue` is orchestrator-owned, and finalize-step5 still continues to Step 5b.5 on generic annotate failure. A second empty stdout can loop or strand accepted OOS again.
- **Proposed resolution**: Add a durable once-only marker (for example `$DESIGN_TMPDIR/.oos-issue-retry-used`), document the `file-issues` annotate-failure branch in finalize-step5.md to re-run issue+annotate only when the marker is absent, and have design_step5b refuse a second retry with a non-retryable status.

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/review/review_tally.py:1130-1235
- **Concern**: `/implement` pool location and `emit_tally` promotion inputs are underspecified. Scenario: Design pins `$DESIGN_TMPDIR/oos-aggregate-pool.md`, but implement only says "equivalent session-level file." `review_core_body.py` calls `emit_tally` without `--session-env-path` or `--implement-tmpdir`, so promotion logic must guess where the per-run pool lives.
- **Proposed resolution**: Pin the implement pool to `$IMPLEMENT_TMPDIR/oos-aggregate-pool.md` (written from `tally_code_votes` via `session_env_path.parent`), and have `emit_tally` resolve it from `Path(args.review_tmpdir).parent` or an explicit `--session-env-path` before trigger evaluation and sink promotion.

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:894-903
- **Concern**: /implement aggregate pool omits vote-accepted OOS as trigger inputs. Scenario: The plan narrows `tally_code_votes` pool candidates to non-accepted OOS plus rerouted findings, so a run with one accepted `important` OOS and one rejected OOS will keep filing only the accepted item even though the approved aggregate rule should promote all public collected OOS once any collected item is important or blocking.
- **Proposed resolution**: Collect every non-security OOS-tagged block, including result=accepted blocks, into the session aggregate pool; when promotion runs, de-dupe against the accepted sink so `OOS_ACCEPTED_COUNT` stays vote-based.

### FINDING_6:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_loop.py:510-520
- **Concern**: Design pool survives Gate C manual review re-entry. Scenario: The plan adds `oos-aggregate-pool.md` but does not add it to the direct-review-entry cleanup list that already clears `oos-accepted-design.md`; after Gate C sends the plan back for review, stale OOS from the rejected plan can still trigger filing and be promoted into the final batch.
- **Proposed resolution**: Add the new aggregate pool sidecar and any previous snapshot for it to the same direct-review-entry cleanup path, or otherwise reset the pool whenever existing plan-review OOS artifacts are reset.

### FINDING_8:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:429-431
- **Concern**: Aggregate promotion must run before the empty accepted-sink early exit. Scenario: When every OOS item is pool-only (zero vote-accepted blocks), `oos-accepted-design.md` is empty at prepare time. The existing guard returns `skip-no-items` before the planned pool read/promotion, so the primary case (qualifying pool with no vote-accepted OOS) never reaches filing.
- **Proposed resolution**: Move aggregate pool evaluation and promotion to run before the `skip-no-items` checks on empty/missing `oos-accepted-design.md` (and re-check unfiled blocks after promotion). Add a prepare test with empty accepted sink plus a triggering pool.

### FINDING_9:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py
- **Concern**: Trigger severity counts only the cumulative pool file, not the full per-run collected pool. Scenario: The issue binds the trigger to all non-security collected OOS (any vote outcome) plus rerouted/neutral-rescued findings. The plan accumulates only non-accepted OOS and reroutes into `oos-aggregate-pool.md`, then counts severities there only. Two vote-accepted `latent` blocks already in `oos-accepted-design.md` plus one pool `latent` reroute totals three but the trigger sees one, so the reroute stays unfiled.
- **Proposed resolution**: When evaluating the trigger at prepare/emit time, count body severities from the pool plus non-security blocks already in the accepted sink (deduped), or also record vote-accepted OOS into the pool for counting-only.

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/design/design_step5b.py
- **Concern**: skills/design/references/finalize-step5.md. Scenario: Bug A retry still cannot re-run `/larch:issue` from the Step 5b Python wrapper alone
- **Proposed resolution**: `finalize-step5.md` keeps `/larch:issue` prompt-side. The plan assigns retry to `design_step5b.py`, but that wrapper only calls `file_oos_annotate_main`; it cannot invoke the Skill tool. Annotate can emit `NEXT_ACTION=retry-file-and-annotate`, yet finalize prose still treats empty stdout as warn-and-continue to Step 5b.5 (lines 49-55), so Bug A can remain. Add an orchestrator `NEXT_ACTION=retry-file-and-annotate` branch in `finalize-step5.md` (and dispatch docs): re-run the file-issues `/larch:issue` capture once, then annotate; do not write `.completed/step-5b` until success. Limit the wrapper to surfacing the action and a retry sentinel; test the orchestrator contract, not an internal issue relaunch.

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/review_core_body.py:1136-1137
- **Concern**: `/implement` emit-tally callers omit session/implement paths needed for session pool promotion. Scenario: The plan evaluates the aggregate trigger in `emit_tally` over a session-level pool and requires dual local/session accepted-OOS writes. Production `review_core_body` builds `emit_args` without `--session-env-path` or `--implement-tmpdir` on the main, panel-failed, MAV, and aggregator-exhaust paths (only zero-findings adds them). `emit_tally` then cannot read `$IMPLEMENT_TMPDIR/oos-aggregate-pool.md` or persist promotion to the session sink in live Step 5 runs.
- **Proposed resolution**: Add `### UPDATED: python/larch/review/review_core_body.py` and forward `--session-env-path` plus `--implement-tmpdir` on every `emit_tally` invocation, mirroring the zero-findings branch.

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:403-414
- **Concern**: Bug B skip-sentinel can still bypass aggregate promotion. Scenario: On a same-issue rerun, cache recovery can mark all old accepted OOS as filed, then emit skip-sentinel before oos-aggregate-pool.md promotes a new important unaccepted OOS item. The run still files nothing.
- **Proposed resolution**: After sentinel recovery, merge/evaluate aggregate-pool promotions before deciding skip-sentinel. Compute unfiled blocks over the recovered plus promoted accepted text, and test cache recovery with an aggregate-only important item.

### FINDING_13:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:1120-1134
- **Concern**: Implement emit-tally is not wired to the session-level pool. Scenario: The plan stores the /implement aggregate pool under the session path, but the normal review_core emit-tally calls do not pass --session-env-path. Production runs can miss latent items split across rounds even if direct emit-tally tests pass.
- **Proposed resolution**: Thread --session-env-path into the review_core_body emit_tally calls that follow tally-code-votes, especially the normal and main-agent-vote-required branches.

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:429-431
- **Concern**: Aggregate pool promotion must run before the empty accepted-sink early exit. Scenario: The plan adds trigger evaluation in `file_oos_prepare_main`, but the current control flow returns `skip-no-items` when `oos-accepted-design.md` is missing or empty before any pool read. A run with zero vote-accepted OOS but a qualifying aggregate pool (e.g. three latent items) still exits at line 429 and never promotes.
- **Proposed resolution**: Move aggregate pool read, trigger evaluation, and promotion into `oos-accepted-design.md` immediately after cross-session/sentinel guards and before the `if not accepted.is_file() or accepted.stat().st_size == 0` branch; only then run `_extract_unfiled_blocks` and the existing ready path.

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:1207-1227
- **Concern**: `emit_tally` `oos serialize` rebuild can erase aggregate promotions. Scenario: The plan relaxes the OOS sink count guard but still routes `OOS_ACCEPTED_COUNT > 0` through `python/cli.py oos serialize`, which truncates `--output-file` and rebuilds only vote-eligible blocks from `oos.md`. Any aggregate promotion written to `oos-accepted-review.md` before that branch is wiped whenever vote-accepted OOS exist in the same round.
- **Proposed resolution**: Run aggregate pool evaluation and promotion after the serialize branch completes (or skip serialize when the session pool triggered promotion), then recompute sink count and apply the relaxed `sink_count >= OOS_ACCEPTED_COUNT` check; mirror promoted blocks to the session sink when it differs from the round file.

### FINDING_16:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/finalize-step5.md:41-55
- **Concern**: Bug A retry needs an orchestrator-owned once-only contract, not only annotate status text. Scenario: `/larch:issue` is prompt-side; `design_step5b.py` cannot re-invoke it. The plan adds `NEXT_ACTION=retry-file-and-annotate` from annotate and updates `design_step5b.py`, but finalize-step5 still treats non-zero annotate as continue/failure without a bounded re-entry that re-runs file-issues then annotate, and no durable marker prevents a second retry on resume.
- **Proposed resolution**: Extend finalize-step5 (and tests) with an explicit branch on annotate `NEXT_ACTION=retry-file-and-annotate`: if no retry sentinel exists, re-run the file-issues Skill call, rewrite `oos-issue.stdout.txt`, rerun annotate, and write a once-only sentinel; on second failure surface non-retryable error and do not write `.completed/step-5b`.

### FINDING_17:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_tally.py:919-942
- **Concern**: Pool sidecar append should dedupe like existing OOS accumulators. Scenario: The edge cases call out duplicate pool entries across review rounds, but the plan does not specify dedupe when appending to `oos-aggregate-pool.md` / the implement session pool. Re-tallies can duplicate blocks, inflate latent counts, and append duplicate promoted headers into the accepted sink.
- **Proposed resolution**: Reuse `_append_unique_artifact_blocks` (or equivalent block-key dedupe) when accumulating pool sidecars; keep promotion idempotent by skipping chunks already present in the accepted sink.

### FINDING_18:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py (plan.txt:51,86-88)
- **Concern**: FINDING_1: /implement pool is narrowed to non-accepted OOS, so accepted latent OOS may not count toward the aggregate trigger. Scenario: The spec counts OOS-tagged items with any vote outcome. With one vote-accepted latent OOS plus two neutral latent OOS, the planned /implement pool counts only two latent items, so the three-latent trigger does not fire and the neutral items stay unfiled.
- **Proposed resolution**: Keep OOS_ACCEPTED_COUNT vote-based, but include all non-security OOS-tagged items in the aggregate trigger pool, or count existing accepted-sink latent blocks together with the pool before deciding promotion. Add the mixed accepted-plus-nonaccepted latent case to test_review_tally.py.

### FINDING_19:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/design/design_oos.py:403-414
- **Concern**: FINDING_2: Cross-session sentinel recovery can still skip before aggregate-pool promotion. Scenario: On a same-issue /design rerun, the cache can annotate all old accepted OOS blocks, while oos-aggregate-pool.md contains a new important unaccepted OOS. If prepare checks _extract_unfiled_blocks on recovered accepted text before promoting the pool, it emits skip-sentinel and never files the new pool item.
- **Proposed resolution**: Apply aggregate-pool promotion before any skip-sentinel return, or run the Bug B unfiled check against recovered accepted text after adding triggered pool items. Add a sentinel-plus-aggregate-only regression test.

### FINDING_20:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/round_runner.py:528-528
- **Concern**: /implement aggregate promotion must run at Step 9a.1 filing time, not only in per-round emit_tally. Scenario: After each review round, `_append_round_oos_artifact` copies vote-only `accumulated-oos.md` onto `$IMPLEMENT_TMPDIR/oos-accepted-review.md`, overwriting any blocks promoted earlier in the same round. Multi-round latent pools that never win a vote therefore still reach Step 9a.1 with an empty accepted sink.
- **Proposed resolution**: Pin symmetric promotion to filing time: add an `oos_filer.py` (or shared helper) step before `_working_batch` that reads `$IMPLEMENT_TMPDIR/oos-aggregate-pool.md`, evaluates the trigger, normalizes headers, and appends into `oos-accepted-review.md`. Keep tally rounds append-only to the pool file.

### FINDING_21:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:1207-1227
- **Concern**: emit_tally promotion path still wipes or rebuilds an augmented sink. Scenario: Relaxing the equality guard to `sink_count >= OOS_ACCEPTED_COUNT` is not enough. When `OOS_ACCEPTED_COUNT=0` and a promoted sink is non-empty, the final `else` branch still writes an empty `oos-accepted-review.md`. When `OOS_ACCEPTED_COUNT>0` but the sink is larger, the `oos serialize` rebuild still replaces promoted blocks with vote-only output from `oos.md`.
- **Proposed resolution**: After promotion, refuse only when `sink_count < OOS_ACCEPTED_COUNT`. Skip the `else` wipe when `sink_count > 0`. Skip serialize rebuild when `sink_count > OOS_ACCEPTED_COUNT`. Add the planned `OOS_FILING_COUNT` KV from the post-promotion sink.

### FINDING_22:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/references/finalize-step5.md:41-55
- **Concern**: Bug A retry still assigns `/larch:issue` relaunch to `design_step5b.py`. Scenario: The plan puts the once-only `/larch:issue` plus annotate retry inside the annotate wrapper, but Step 5b filing is orchestrator-owned: `/larch:issue` is invoked from `finalize-step5.md` via the Skill tool, and non-zero annotate exits currently fall through to Step 5b.5 without a retry branch. Empty stdout will still strand accepted OOS.
- **Proposed resolution**: Have `file_oos_annotate_main` emit `NEXT_ACTION=retry-file-and-annotate` only. Document a new `finalize-step5.md` branch (under `NEXT_ACTION=file-issues`) that re-runs `/larch:issue`, rewrites `oos-issue.stdout.txt`, and re-invokes annotate once without writing `.completed/step-5b`. Limit `design_step5b.py` to surfacing that action, not calling `/larch:issue`.

### FINDING_23:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py:1136-1139
- **Concern**: Implement emit-tally does not receive the session aggregate path. Scenario: The plan moves /implement trigger evaluation to emit_tally over a session-level pool, but the normal review-core call still invokes emit-tally with only the round tmpdir. With latent OOS split across /implement rounds, emit_tally can miss the cumulative parent pool and fail the per-run trigger.
- **Proposed resolution**: Add python/larch/review/review_core_body.py to the firm changes and thread --session-env-path, or an explicit aggregate-pool path from the tally env, through every production emit-tally call that evaluates aggregate OOS.

### FINDING_24:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:894-904; python/larch/issue/file_oos.py:614-616
- **Concern**: Implement trigger pool omits accepted and main-agent OOS. Scenario: The plan's /implement pool tests and file-specific change cover non-accepted OOS plus rerouted findings, but the issue scope says any non-security collected OOS can trip the trigger. If an accepted review OOS or oos-accepted-main-agent.md item has important severity and another reviewer OOS was neutral, the high item files but the neutral item remains unpromoted.
- **Proposed resolution**: Include non-security accepted review OOS and oos-accepted-main-agent.md items in the /implement aggregate trigger counts, while de-duplicating them from the promoted sink.
