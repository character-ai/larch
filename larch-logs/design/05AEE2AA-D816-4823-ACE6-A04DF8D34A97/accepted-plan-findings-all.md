### FINDING_1: Pre-aggregation nit drop is missing
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-Review Pipeline Gate, Codex-dyn-Review Pipeline Gate
- **Severity**: blocking
- **Concern**: design plan-review still lets nit or missing-severity rows reach aggregation and ballot dispatch instead of the planned oos-dropped-before-vote.md backstop, so the emit-cut does not apply on the design path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/review/plan_review_round.py: run the shared nit-drop helper on findings-in-scope.md (or ballot.txt) before aggregate and again before voter dispatch; write dropped blocks to round-*/oos-dropped-before-vote.md; take the existing zero-findings branch when all blocks drop; extend python/tests/review/test_plan_review.py for design-path coverage.
  - From Codex-Arch: Add python/larch/review/plan_review_round.py as UPDATED. After collection and before aggregate/ballot, drop nit FINDING and OOS blocks to oos-dropped-before-vote.md, refresh zero-ballot handling when all blocks drop, and add the plan-review test case.
  - From Cursor-Innovation: Wire the same drop-to-oos-dropped-before-vote.md helper into plan_review_round.py on findings-in-scope.md (pre-aggregate) and ballot.txt (pre-vote backstop); add plan-review coverage in python/tests/review/test_plan_review.py
  - From Codex-Innovation: Add a firm update to plan_review_round.py to drop nit rows from both in-scope and OOS materialization before aggregation and ballot creation, append them to oos-dropped-before-vote.md, and take the zero-findings branch when only dropped rows remain
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/review/plan_review_round.py` (or shared helper): run the same drop-to-`oos-dropped-before-vote.md` filter on findings/ballot inputs before voter dispatch, mirroring the code-review backstop
  - From Codex-Pragmatic: Add the new drop-before-vote filter to the design round after composing in-scope and OOS files and before aggregation/ballot creation; write `oos-dropped-before-vote.md` and take the zero-findings branch when all rows drop
  - From Cursor-Requirements: Add ### UPDATED: python/larch/review/plan_review_round.py: default missing reviewer severity to minor, invoke prune-nit-findings on composed in-scope/OOS inputs before aggregate-findings (write oos-dropped-before-vote.md), and extend plan-review tests for the design path
  - From Codex-Requirements: Update review_collect or the prune-nit parser to recognize the pre-aggregate [nit] shape, and update plan_review_round.py to drop/audit severity nit rows before writing active findings; route all-dropped to zero findings
  - From Cursor-dyn-Review Pipeline Gate: Add a firm plan step on plan_review_round.py or shared helper to run the new drop-to-oos-dropped-before-vote.md filter before aggregate-findings mirroring review_core_body.py
  - From Codex-dyn-Review Pipeline Gate: Add a firm update for python/larch/review/plan_review_round.py to run the updated prune-nit-findings drop/audit step before aggregate-findings, write oos-dropped-before-vote.md, and take the zero-findings branch when all blocks are dropped.


### FINDING_2: Emit-tally rebuild can refile non-fileable OOS
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Review Pipeline Gate
- **Severity**: blocking
- **Concern**: emit-tally's OOS serialize/rebuild path still keys on Result=accepted instead of the strict-majority-YES fileable predicate, so accepted-but-minor OOS can re-enter the accepted sink and be filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/issue/oos.py (and python/tests/issue/test_oos.py): teach serialize to apply the same strict-majority-major file predicate (classification TSV plus voter files, or an explicit fileable marker written at tally time); skip non-fileable accepted blocks; align emit-tally rebuild checks with fileable counts only.
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/issue/oos.py` (and `emit-tally` tests): apply the same strict-majority-`major` fileable helper during serialize/rebuild, or stop rebuilding from full `oos.md` once tally writes the gated sink
  - From Cursor-Requirements: In review_tally.py emit-tally (and any shared helper), rebuild only fileable OOS blocks using the same strict-majority YES rule as tally; add a test in python/tests/review/test_review_tally.py where accepted-minor OOS in oos.md does not serialize into the accepted sink
  - From Cursor-dyn-Review Pipeline Gate: Add ### UPDATED: python/larch/issue/oos.py applying the shared strict-majority-major fileable predicate before writing serialize output and align emit-tally rebuild checks in review_tally.py with fileable counts only


### FINDING_3: Design OOS pool promotion ignores the new file gate
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-Review Pipeline Gate
- **Severity**: blocking
- **Concern**: design_oos Step 5b still promotes aggregate-pool rows using retired body severities and does not consistently apply the shared fileable predicate, so accepted major items can stall and accepted-minor items can still be promoted/filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Add ### UPDATED: python/larch/design/design_oos.py (and python/tests/design/test_design_oos.py): repoint aggregate severities to major|minor|nit, apply the shared fileable predicate before promotion, and only promote pool rows already marked fileable; add python/tests/design/test_design_oos.py coverage for accepted-minor pool blocks staying out of oos-accepted-design.md.
  - From Codex-Arch: Add python/larch/design/design_oos.py and python/tests/design/test_design_oos.py as firm updates. Either always promote already-fileable pool blocks, or update the trigger to the new scale, for example major triggers promotion and nit is impossible/dropped. Remove or restate the latent threshold.
  - From Cursor-Innovation: Add ### UPDATED: python/larch/design/design_oos.py: repoint aggregate severities to major|minor|nit, apply the shared fileable predicate before promotion, and only promote pool rows already marked fileable; add python/tests/design/test_design_oos.py coverage for accepted-minor pool blocks staying out of oos-accepted-design.md.
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/design/design_oos.py`: repoint aggregate trigger/promotion to unified severities and the shared fileable predicate (or drop latent-count promotion); only promote pool blocks already fileable under the tally gate
  - From Cursor-Requirements: Add ### UPDATED: python/larch/design/design_oos.py to drop latent-threshold promotion, stop using retired reviewer severities, trust tally fileable sinks only, and add python/tests/design/test_design_oos.py coverage for accepted-minor pool rows not filing
  - From Cursor-dyn-Review Pipeline Gate: Add ### UPDATED: python/larch/design/design_oos.py to repoint aggregate triggers to major/minor apply the shared fileable predicate before promotion and file only from gated oos-accepted-design.md


### FINDING_4: Plan-review continuation miscounts high findings
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: structured continuation logic in plan_review_loop still keys high/high_new off blocking/important, so accepted major findings may fail to extend or escalate correctly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: python/larch/review/plan_review_loop.py to the plan: import the shared high-severity set (major only) from the updated Gate B module and replace the hardcoded blocking|important sets in continuation logic
  - From Codex-Innovation: Add plan_review_loop.py and replace the high-severity checks with major or a shared Gate B high mapping; update the corresponding plan-review tests
  - From Cursor-Pragmatic: Add `### UPDATED: python/larch/review/plan_review_loop.py` to the plan: import the shared high-severity set (major only) from the updated Gate B module and replace the hardcoded blocking|important sets in continuation logic
  - From Codex-Pragmatic: Update the structured high-severity checks to use major and adjust the related continuation expectations
  - From Cursor-Requirements: Add plan_review_loop.py to firm updates and change structured high/high_new checks to major, with test_plan_review coverage for accepted-major continuation/escalation
  - From Codex-Requirements: Add plan_review_loop.py to firm updates and change structured high/high_new checks to major, with test_plan_review coverage for accepted-major continuation/escalation


### FINDING_5: Dropped-nit audit lineage is not retained
- **Reviewer(s)**: Cursor-Innovation, Codex-Innovation, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: oos-dropped-before-vote.md is not being committed into the round-log surface, so the dropped-nit audit trail disappears after temp cleanup and the docs remain inconsistent about what should be rendered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add ### UPDATED: python/larch/report/run_log_batch.py (allowlist oos-dropped-before-vote.md), update docs/run-logs.md accordingly, and extend python/tests/report/test_run_logs.py so the audit file is committed while final-summary rendering stays suppressed per step 5
  - From Codex-Innovation: Add run_log_batch.py and test_run_logs.py to the plan; allowlist oos-dropped-before-vote.md as a round artifact and flip the retired-artifact test to require it
  - From Cursor-Requirements: Add an Approach/doc note: dropped nits stay out of human summaries (audit only in oos-dropped-before-vote.md), #6028 applies only to non-nit dropped-OOS candidates if any, and update docs/run-logs.md accordingly
  - From Codex-Requirements: Add the new audit basename to the implement round artifact allowlist and the design plan-review round inclusion path, then cover it in run-log or plan-review artifact tests


### FINDING_6: Aggregator prompt still encodes retired severity labels
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements
- **Severity**: important
- **Concern**: agents/orchestrator-aggregator.md still tells the aggregator to merge the old blocking/important/latent/nit vocabulary and order, so prompt validation or output generation can conflict with the new severity schema.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add agents/orchestrator-aggregator.md to firm files and update the schema plus merge rule to major > minor > nit, matching the validator
  - From Codex-Pragmatic: Add `agents/orchestrator-aggregator.md` to the firm updates and change its severity requirement and merge order to `major|minor|nit` with `major` highest and no `latent`
  - From Cursor-Requirements: Add ### UPDATED: agents/orchestrator-aggregator.md with major>minor merge rules (no nit emission), align with review_aggregate.py validator changes, and extend python/tests/review/test_review_aggregate.py aggregator expectations
  - From Codex-Requirements: Add agents/orchestrator-aggregator.md to firm updates; change the schema and merge order to major > minor > nit and update aggregate prompt tests


### FINDING_7: Legacy high markers still gate code-review convergence
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: round_runner's convergence helper still looks for Important/Blocking markers, so code-review rounds with accepted major findings can be marked converged too early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Add round_runner.py to the firm plan; rename or generalize the helper and match - **Severity**: major, with retained legacy high labels only for historical compatibility
  - From Codex-Requirements: Add round_runner.py and python/tests/review/test_review_and_fix.py to the plan; recognize major as high in the convergence helper and update the regression test


### FINDING_1: Per-round dropped-nit audit must live under the round directory
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation
- **Severity**: important
- **Concern**: The dropped-nit audit is written at the design/plan-review root instead of the per-round committed subtree, so later rounds can overwrite earlier forensic copies and the round artifact set may miss the audit file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Write the audit beside the round dir already passed as --round-dir (plan-review/round-N/oos-dropped-before-vote.md) and add a test_plan_review.py assertion that round flush/publish retains per-round copies
  - From Cursor-Innovation: Write or mirror `oos-dropped-before-vote.md` under `design/plan-review/round-{N}/` every round (extend the shared drop helper with an explicit audit path or `--round-dir`). Document that design retention is via publish subtree copy, not `run_log_batch` alone.


### FINDING_2: Nit-drop must cover the separate OOS stream before ballot composition
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: Filtering only the in-scope side leaves nit-tagged rows in the OOS sidecar path, so the composed ballot can still carry nits and waste judge tokens.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Run the shared drop helper on in_scope before aggregate-findings and on oos_md (or the composed ballot) before voter dispatch, with audit append for both passes


### FINDING_3: Pre-aggregate nit-drop must happen before the pre-aggregate snapshot
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: If the snapshot is taken before the nit-drop mutation, the pre-aggregate restore path can resurrect nits that were supposed to be removed by the hard backstop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mutate findings.md with the pre-aggregate drop first, then copy to findings-pre-aggregate.md, then aggregate; keep the existing pre-ballot backstop as a second pass only


### FINDING_4: Emit-tally pool promotion still bypasses the shared fileable gate
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: blocking
- **Concern**: Pool-to-sink promotion still keys only on accepted status, so accepted-but-minor OOS can be re-promoted into the filing sink even when the gate is supposed to require the stricter fileable predicate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Apply the shared strict-majority-major fileable predicate inside _promote_aggregate_oos_pool (and pool ingestion) or stop promoting from pool when the gated sink is authoritative
  - From Cursor-Pragmatic: Extend the `review_tally.py` update to gate `_append_oos_pool_candidate`, `_promote_aggregate_oos_pool`, and any emit-tally pool-to-sink promotion on the shared fileable predicate (or only promote rows already present in the gated accepted sink); cover with an accepted-minor-in-pool emit-tally test


### FINDING_5: Dropped-nit audit must not publish security-tagged blocks
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Concern**: Security-tagged OOS drops can be written into the public dropped-audit file, bypassing the existing local-only security sidecar path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before writing the dropped audit, partition drops with the shared security classifier. Write only non-security drops to oos-dropped-before-vote.md, route security drops to security-oos-observations.md or another non-allowlisted local sidecar, and keep the run-log allowlist limited to the public audit file.


### FINDING_6: Blank structured severity must not compose as nit
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: Missing severity is still emitted as an explicit nit, which makes the new pre-ballot drop treat it as disposable instead of preserving it as a minor ballot row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: In `plan_review_round.py`, change the default from `severity or 'nit'` to `severity or 'minor'` (or omit the line and let the shared nit-drop helper default blanks). Add/adjust plan-review coverage for structured rows with empty severity.
  - From Cursor-Pragmatic: Change the compose default to `minor` (or leave severity absent and let the shared pre-aggregate normalizer default blank to `minor` before nit-drop); add a plan-review fixture for missing-severity rows staying on the ballot
  - From Cursor-Requirements: Add `### UPDATED: python/larch/review/plan_review_round.py` step to change the compose default to `minor` (or normalize blank severity before compose), update the plan-review severity-default prose to `minor`, and extend `python/tests/review/test_plan_review.py` with a missing-severity fixture that stays on the ballot


### FINDING_8: OOS serialization must understand canonical `OOS_` blocks
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: The serializer only splits `FINDING_` headers, but the live OOS file uses `OOS_` headers, so rebuild/serialize can miss valid accepted rows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Teach `oos.py` block iteration to split on both `FINDING_` and `OOS_` headers (matching `_non_security_oos_count`), then add serialize/rebuild coverage with `OOS_`-headed `oos.md` input ### 1. [correctness] `python/larch/review/plan_review_round.py:162-171` — blank severity becomes nit at compose time The plan’s design-path nit-drop assumes missing severity defaults to `minor`, but `_compose_finding_block` still emits `severity or 'nit'`. Structured rows with an empty severity field become explicit `nit` and get dropped before voting, which is the opposite of the stated edge case. **Suggested revision:** Default compose to `minor`, or normalize blank severity to `minor` in the shared pre-aggregate filter before nit-drop; add plan-review test coverage for missing-severity rows remaining on the ballot. ### 2. [correctness] `python/larch/review/review_tally.py:505-536` — emit-tally pool promotion bypasses the file gate Step 4 names `review_tally.py` as a filing sink, but `_promote_aggregate_oos_pool` (called from `_finalize_emit_oos_filing` on every successful emit-tally) still promotes pool blocks keyed only on `Result=accepted`. That is a second hop into `oos-accepted-review.md` that can reintroduce accepted-but-minor OOS even if the vote loop gates the accepted sink. **Suggested revision:** Apply the shared fileable predicate to pool append and emit-time pool promotion, or stop promoting pool rows that are not already in the gated accepted sink; add an emit-tally test with accepted-minor pool content. ### 3. [risk-integration] `python/larch/issue/oos.py:64-79` — serialize cannot read canonical `OOS_` blocks The plan updates `oos.py` for the fileable predicate, but `_iter_finding_blocks` only recognizes `### FINDING_` headers. Production `oos.md` from tally uses `### OOS_` blocks, so serialize/rebuild can silently yield an empty accepted sink while fileable OOS remains only in `oos.md`. **Suggested revision:** Split blocks on both `FINDING_` and `OOS_` headers in `oos.py`, and extend `python/tests/issue/test_oos.py` with `OOS_`-headed serialize/rebuild fixtures.


