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


