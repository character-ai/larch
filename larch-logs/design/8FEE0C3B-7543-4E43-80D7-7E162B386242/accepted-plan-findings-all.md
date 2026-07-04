### FINDING_1: Design promotion needs OOS header rewrite
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Oos Filing Integrator, Codex-dyn-Oos Filing Integrator
- **Severity**: blocking
- **Concern**: Promoted `/design` rerouted findings keep `FINDING_N` headers, so `design_oos._extract_unfiled_blocks` cannot see them and `file_oos_prepare_main` can still return `skip-no-items` even after the aggregate trigger fires.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror the /implement _normalize_oos_header_text path in plan_review_tally aggregate promotion (assign sequential OOS_N headers) and add a plan-review test that promotes a latent-rerouted FINDING_N block through prepare
  - From Cursor-Innovation: Mirror the `/implement` path: normalize promoted public chunks to `### OOS_<n>:` (reuse `_normalize_oos_header_text` or a small design helper) before `_accumulate_round_oos`, and add a plan-review tally test that promoted latent FINDING blocks survive `file_oos_prepare_main`.
  - From Codex-Innovation: Normalize promoted design reroute candidates to OOS_N headings before _accumulate_round_oos, or teach prepare to convert them before issue_cap; add a prepare-level assertion for latent or neutral-rescued promoted findings.
  - From Cursor-Pragmatic: Mirror the implement contract in plan_review_tally: assign monotonic OOS_N via the same normalization helper used in review_tally (_normalize_oos_header_text), rewrite promoted rerouted finding chunks before _accumulate_round_oos, and extend plan-review tests to assert prepare reaches ready with oos-combined headers parseable by design_oos.
  - From Cursor-Requirements: In plan_review_tally._render assign monotonic ### OOS_<n>: headers to promoted rerouted chunks before _accumulate_round_oos mirroring review_tally._normalize_oos_header_text seed next seq from existing oos-accepted-design.md via file_oos._next_oos_number or equivalent
  - From Cursor-Requirements: Extend mandated tests with a file_oos_prepare_main fixture asserting FILE_DESIGN_OOS_STATUS=ready and non-empty oos-combined.md for promotion-only latent or important pools
  - From Cursor-dyn-Oos Filing Integrator: Mirror review_tally._normalize_oos_header_text in plan_review_tally post-trigger promotion; allocate monotonic OOS_N across cumulative oos-accepted-design.md; add a plan-review test that promoted FINDING blocks reach oos-combined.md
  - From Codex-dyn-Oos Filing Integrator: Normalize every promoted design filing chunk that originated from a FINDING_N block to a unique ### OOS_N: header before _accumulate_round_oos, or extend the design OOS parser with an explicit accepted-file format change. Add the plan-review test to run file_oos_prepare_main or assert oos-combined.md contains the promoted finding.


### FINDING_2: Promoted review sinks still trip emit-tally equality
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-Oos Filing Integrator, Codex-dyn-Oos Filing Integrator
- **Severity**: blocking
- **Concern**: Promoted `/implement` OOS blocks can make the accepted sink larger than `OOS_ACCEPTED_COUNT`, but `emit-tally` still enforces exact equality and refuses to write summaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Update review_tally.py emit_tally to allow sink_count >= oos_accepted_count without rebuild when promotion is present (e.g. new OOS_FILING_COUNT KV or relax the mismatch guard) and add a test where OOS_ACCEPTED_COUNT=0 with three promoted latent blocks passes emit-tally
  - From Codex-Arch: Keep scoreboards and vote-result rows based on votes, but make emitted `OOS_ACCEPTED_COUNT` match the non-security accepted sink, including aggregate-promoted OOS, or update `emit-tally` to validate against a separate sink count.
  - From Codex-Innovation: Make the tally/emit contract explicit: either include promoted public blocks in the count used by emit-tally, or add a separate promoted-count or accepted-sink-count field and update emit-tally to accept that exact sink total without changing scoreboard vote results.
  - From Cursor-Pragmatic: Add an explicit ### UPDATED: emit_tally section in review_tally.py: treat sink_count >= oos_accepted_count with a non-empty promotion-tolerant sink as preserve-not-rebuild (or emit a separate OOS_POOL_COUNT). Update emit-tally tests accordingly; keep scoreboard counts vote-only.
  - From Codex-Pragmatic: For promoted non-security review OOS, either increment the emitted OOS_ACCEPTED_COUNT to the non-security accepted-sink count or update emit-tally's invariant to distinguish vote count from filing count; add the planned test against emit-tally/session output
  - From Cursor-dyn-Oos Filing Integrator: Add a MAY_UPDATE emit_tally guard: treat tally-written sink as authoritative when sink_count>=OOS_ACCEPTED_COUNT and blocks are non-security; or add an explicit promoted-count KV and relax the equality check; add a test mirroring test_emit_tally_refuses_destructive_oos_rebuild_mismatch for promotion-only runs
  - From Codex-dyn-Oos Filing Integrator: Keep scoreboard and OOS_ACCEPTED_COUNT vote-based, but add an explicit filing-count contract or promotion-aware emit-tally validation before writing promoted sink blocks. Update the mismatch test so intentional aggregate-promotion extras are accepted while unrelated destructive rebuild mismatches still fail.


### FINDING_3: Bug A retry path is still not wired
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Cursor-dyn-Oos Filing Integrator
- **Severity**: important
- **Concern**: Empty `/issue` stdout after Bug A still leaves Step 5b without a reliable retry or repair path, so accepted OOS can remain unannotated or stranded behind the sentinel.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/design/design_step5b.py to surface retry NEXT_ACTION on annotate failure and either loop prepare/file/annotate once or emit a contract the Step 5b skill finalize path already handles; extend test_design_oos.py to assert step5b behavior not only annotate KVs
  - From Codex-Arch: Handle this branch in the plan. Either recover and annotate from the issue sentinel, or clear/quarantine the sentinel and emit a recognized retry or repair action. Include `design_step5b.py` if a new `NEXT_ACTION` is introduced.
  - From Cursor-Innovation: Update `design_step5b.py` annotate handling and `finalize-step5.md` so `annotate-failed-empty-stdout` blocks Step 5b.5/5c until `/larch:issue` stdout is captured and annotate succeeds; wire an explicit retry or reuse the documented manual recovery sequence.
  - From Cursor-Pragmatic: Promote orchestration to firm scope: emit NEXT_ACTION=retry-file-and-annotate from annotate, teach design_step5b.py and skills/design/references/finalize-step5.md to re-run file-issues plus annotate once without writing step-5b complete, and add step5b lifecycle tests for the retry path.
  - From Codex-Pragmatic: In the empty-stdout retry path, remove or quarantine the count-only oos-issue-sentinel, or make prepare ignore that sentinel when accepted blocks still lack Filed URL and no usable stdout/sentinel URL map exists; route the retry action through step5b and test this exact retry
  - From Cursor-Requirements: Add ### UPDATED: python/larch/design/design_step5b.py and ### UPDATED: skills/design/references/finalize-step5.md to branch on annotate-failed-empty-stdout and the retry NEXT_ACTION to re-run /larch:issue then annotate in the same Step 5b pass without writing .completed/step-5b
  - From Cursor-dyn-Oos Filing Integrator: Emit NEXT_ACTION=retry-file-and-annotate from annotate; update design_step5b annotate wrapper and finalize-step5.md to re-run /larch:issue plus annotate instead of marking 5b complete; add an orchestration test not only annotate_main KVs


### FINDING_4: Aggregate filing trigger is still per-round, not per-run
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The aggregate filing trigger is evaluated per review round instead of over the whole run's collected OOS pool, so split latent items never trip filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Persist public aggregate-promotion candidates across rounds, then evaluate the trigger against the per-run pool before filing. When it fires, promote all unfiled non-security candidates from prior and current rounds.
  - From Cursor-Innovation: Accumulate public pool candidates and severities across rounds (session sidecar or rollup over round classification artifacts) and evaluate the trigger once before filing, or move trigger evaluation to Step 5b prepare / the filer over the full run.
  - From Codex-Innovation: Apply the same per-run pool rollup used for design (session-level candidate store or filing-time evaluation over accumulated round artifacts) before writing session `oos-accepted-review.md`.
  - From Cursor-Pragmatic: Persist a cumulative non-security OOS candidate pool for design and implement, or evaluate the trigger from accumulated candidates before final filing; when it fires, promote all unfiled public candidates from prior and current rounds without duplicating vote-accepted blocks
  - From Codex-Pragmatic: Persist or derive cumulative non-security OOS candidates across review rounds before evaluating the aggregate trigger and promotion. Add cross-round tests for three latent items and for a later trigger promoting earlier collected public OOS.
  - From Codex-Requirements: Persist non-security OOS promotion candidates or severity counts across rounds and evaluate the trigger against the accumulated run pool before final filing; when it trips, promote all unfiled public candidates from prior rounds as well as the current round.


### FINDING_1: Design prepare can skip before aggregate promotion
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Innovation, Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: blocking
- **Concern**: `design_oos.py` can return `skip-sentinel` or `skip-no-items` before the aggregate pool is read and promoted, so qualifying pool-only OOS never reach filing on same-issue reruns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Run pool read/evaluate/promote (or at least consult the pool trigger) before any cross-session `skip-sentinel` return; only skip when recovered accepted text has no unfiled blocks and the pool cannot fire filing.
  - From Codex-Innovation: After sentinel recovery, merge/evaluate aggregate-pool promotions before deciding skip-sentinel. Compute unfiled blocks over the recovered plus promoted accepted text, and test cache recovery with an aggregate-only important item.
  - From Cursor-Innovation: Move aggregate pool evaluation and promotion to run before the `skip-no-items` checks on empty/missing `oos-accepted-design.md` (and re-check unfiled blocks after promotion). Add a prepare test with empty accepted sink plus a triggering pool.
  - From Cursor-Pragmatic: Move aggregate pool read, trigger evaluation, and promotion into `oos-accepted-design.md` immediately after cross-session/sentinel guards and before the `if not accepted.is_file() or accepted.stat().st_size == 0` branch; only then run `_extract_unfiled_blocks` and the existing ready path.
  - From Codex-Pragmatic: Apply aggregate-pool promotion before any skip-sentinel return, or run the Bug B unfiled check against recovered accepted text after adding triggered pool items. Add a sentinel-plus-aggregate-only regression test.


### FINDING_3: Bug A retry needs an orchestrator-owned once-only contract
- **Reviewer(s)**: Cursor-Arch, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The retry path for empty `/issue` stdout is still not safely owned by the orchestrator, so accepted OOS can be stranded or retried twice.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add a durable once-only marker (for example `$DESIGN_TMPDIR/.oos-issue-retry-used`), document the `file-issues` annotate-failure branch in finalize-step5.md to re-run issue+annotate only when the marker is absent, and have design_step5b refuse a second retry with a non-retryable status.
  - From Codex-Innovation: `finalize-step5.md` keeps `/larch:issue` prompt-side. The plan assigns retry to `design_step5b.py`, but that wrapper only calls `file_oos_annotate_main`; it cannot invoke the Skill tool. Annotate can emit `NEXT_ACTION=retry-file-and-annotate`, yet finalize prose still treats empty stdout as warn-and-continue to Step 5b.5 (lines 49-55), so Bug A can remain. Add an orchestrator `NEXT_ACTION=retry-file-and-annotate` branch in `finalize-step5.md` (and dispatch docs): re-run the file-issues `/larch:issue` capture once, then annotate; do not write `.completed/step-5b` until success. Limit the wrapper to surfacing the action and a retry sentinel; test the orchestrator contract, not an internal issue relaunch.
  - From Cursor-Pragmatic: Extend finalize-step5 (and tests) with an explicit branch on annotate `NEXT_ACTION=retry-file-and-annotate`: if no retry sentinel exists, re-run the file-issues Skill call, rewrite `oos-issue.stdout.txt`, rerun annotate, and write a once-only sentinel; on second failure surface non-retryable error and do not write `.completed/step-5b`.
  - From Cursor-Requirements: Have `file_oos_annotate_main` emit `NEXT_ACTION=retry-file-and-annotate` only. Document a new `finalize-step5.md` branch (under `NEXT_ACTION=file-issues`) that re-runs `/larch:issue`, rewrites `oos-issue.stdout.txt`, and re-invokes annotate once without writing `.completed/step-5b`. Limit `design_step5b.py` to surfacing that action, not calling `/larch:issue`.


### FINDING_5: Aggregate trigger counts miss accepted and main-agent OOS
- **Reviewer(s)**: Codex-Arch, Cursor-Innovation, Codex-Pragmatic, Codex-Requirements
- **Severity**: important
- **Concern**: The aggregate trigger pool is too narrow, so accepted-sink items and main-agent OOS can be left out of severity counting and promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Collect every non-security OOS-tagged block, including result=accepted blocks, into the session aggregate pool; when promotion runs, de-dupe against the accepted sink so `OOS_ACCEPTED_COUNT` stays vote-based.
  - From Cursor-Innovation: When evaluating the trigger at prepare/emit time, count body severities from the pool plus non-security blocks already in the accepted sink (deduped), or also record vote-accepted OOS into the pool for counting-only.
  - From Codex-Pragmatic: Keep OOS_ACCEPTED_COUNT vote-based, but include all non-security OOS-tagged items in the aggregate trigger pool, or count existing accepted-sink latent blocks together with the pool before deciding promotion. Add the mixed accepted-plus-nonaccepted latent case to test_review_tally.py.
  - From Codex-Requirements: Include non-security accepted review OOS and oos-accepted-main-agent.md items in the /implement aggregate trigger counts, while de-duplicating them from the promoted sink.


### FINDING_6: Direct-review-entry cleanup must reset the new pool sidecar
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: Gate C re-entry can leave stale aggregate-pool state in place, so previously rejected OOS can still be promoted later.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the new aggregate pool sidecar and any previous snapshot for it to the same direct-review-entry cleanup path, or otherwise reset the pool whenever existing plan-review OOS artifacts are reset.


### FINDING_7: emit_tally serialize/rebuild can wipe promoted blocks
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-Requirements
- **Severity**: blocking
- **Concern**: Later `oos serialize` or sink-rewrite branches can overwrite an already-augmented accepted sink, erasing aggregate promotions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: `emit_tally` `oos serialize` rebuild can erase aggregate promotions. Scenario: The plan relaxes the OOS sink count guard but still routes `OOS_ACCEPTED_COUNT > 0` through `python/cli.py oos serialize`, which truncates `--output-file` and rebuilds only vote-eligible blocks from `oos.md`. Any aggregate promotion written to `oos-accepted-review.md` before that branch is wiped whenever vote-accepted OOS exist in the same round.
  - From Cursor-Requirements: emit_tally promotion path still wipes or rebuilds an augmented sink. Scenario: Relaxing the equality guard to `sink_count >= OOS_ACCEPTED_COUNT` is not enough. When `OOS_ACCEPTED_COUNT=0` and a promoted sink is non-empty, the final `else` branch still writes an empty `oos-accepted-review.md`. When `OOS_ACCEPTED_COUNT>0` but the sink is larger, the `oos serialize` rebuild still replaces promoted blocks with vote-only output from `oos.md`.


### FINDING_9:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/design/design_step5b.py:192-285
- **Concern**: [SCOPE-REDUCTION] Prior Bug A retry fix is still wired at the wrong boundary. Scenario: `design_step5b.py` has no Skill-tool boundary, while `finalize-step5.md` states the `/larch:issue` call is prompt-side; making the wrapper re-run `/larch:issue` forces a duplicate lower-level issue pipeline or leaves `NEXT_ACTION=retry-file-and-annotate` unreachable.
- **Proposed resolution**: Keep `design_step5b.py` limited to emitting the retryable status and withholding `.completed/step-5b`; make `skills/design/references/finalize-step5.md` own the one allowed `/larch:issue` retry followed by a second annotate call.


