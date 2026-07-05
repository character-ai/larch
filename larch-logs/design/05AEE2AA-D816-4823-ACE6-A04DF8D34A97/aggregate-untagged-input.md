### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_round.py
- **Concern**: Pin dropped-nit audit to plan-review/round-N/ not design tmpdir root. Scenario: /design keeps stable top-level ballot and findings paths that each round overwrites; writing oos-dropped-before-vote.md at design root clobbers prior rounds and may omit the file from plan-review/round-N/ committed forensics
- **Proposed resolution**: Write the audit beside the round dir already passed as --round-dir (plan-review/round-N/oos-dropped-before-vote.md) and add a test_plan_review.py assertion that round flush/publish retains per-round copies

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/plan_review_round.py
- **Concern**: Nit-drop must cover the separate oos_md stream before ballot compose. Scenario: Plan-review aggregates only findings-in-scope.md then merges oos_md in _compose_attributed_ballot; filtering only the post-aggregate ballot or in-scope file leaves nit-tagged OOS rows on the ballot and wastes judge tokens
- **Proposed resolution**: Run the shared drop helper on in_scope before aggregate-findings and on oos_md (or the composed ballot) before voter dispatch, with audit append for both passes

### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_core_body.py
- **Concern**: Pre-aggregate nit-drop must run before findings-pre-aggregate.md snapshot. Scenario: Empty-merge restores findings-pre-aggregate.md then copies it back to findings.md; a snapshot taken before the drop resurrects nit rows even when the pre-ballot backstop is supposed to be the hard guard
- **Proposed resolution**: Mutate findings.md with the pre-aggregate drop first, then copy to findings-pre-aggregate.md, then aggregate; keep the existing pre-ballot backstop as a second pass only

### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py
- **Concern**: Emit-tally aggregate-pool promotion still keys on Result=accepted only. Scenario: _finalize_emit_oos_filing calls _promote_aggregate_oos_pool, which promotes pool blocks with Result=accepted into oos-accepted-review.md without judge severities; accepted-but-minor OOS can re-enter the filing sink after tally gating
- **Proposed resolution**: Apply the shared strict-majority-major fileable predicate inside _promote_aggregate_oos_pool (and pool ingestion) or stop promoting from pool when the gated sink is authoritative

### FINDING_5:
- **Reviewer(s)**: Codex-Arch
- **Severity**: blocking
- **Focus area**: security
- **Location**: python/larch/review/review_aggregate.py:1021-1075; python/larch/report/run_log_batch.py:448-470
- **Concern**: Dropped-nit audit can publish security-tagged blocks. Scenario: The plan writes dropped nit blocks to oos-dropped-before-vote.md and then commits that file as a round-log artifact. A reviewer-emitted nit OOS with focus-area=security bypasses the existing post-vote security sidecar path and can become public despite the SECURITY.md local-only contract.
- **Proposed resolution**: Before writing the dropped audit, partition drops with the shared security classifier. Write only non-security drops to oos-dropped-before-vote.md, route security drops to security-oos-observations.md or another non-allowlisted local sidecar, and keep the run-log allowlist limited to the public audit file.

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:162-171
- **Concern**: `_compose_finding_block` still defaults blank structured severity to `nit`. Scenario: Plan edge cases require missing/blank severity to become `minor` and only explicit `nit` to drop. Collection composes `Severity: nit` for empty `severity` on both FINDING and OOS blocks before the new pre-aggregate filter, so omitted severities are dropped as nits instead of kept as `minor` on the ballot.
- **Proposed resolution**: In `plan_review_round.py`, change the default from `severity or 'nit'` to `severity or 'minor'` (or omit the line and let the shared nit-drop helper default blanks). Add/adjust plan-review coverage for structured rows with empty severity.

### FINDING_7:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: python/larch/review/plan_review_round.py:928-973
- **Concern**: Design dropped-nit audit is not pinned to per-round committed-log paths. Scenario: `/design` plan review writes working artifacts at the design tmpdir root and only mirrors forensics into `plan-review/round-N/` via `ROUND_STAMPED_FORENSICS`. `run_log_batch.py` allowlisting helps `/implement` `write-round`, but design logs are published by copying the design tmpdir; a root-level `oos-dropped-before-vote.md` is overwritten each round, so multi-round runs keep only the last round's dropped-nit audit.
- **Proposed resolution**: Write or mirror `oos-dropped-before-vote.md` under `design/plan-review/round-{N}/` every round (extend the shared drop helper with an explicit audit path or `--round-dir`). Document that design retention is via publish subtree copy, not `run_log_batch` alone.

### FINDING_8:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: docs/voting-process.md:126; docs/point-competition.md:11-84
- **Concern**: Plan leaves canonical voting and scoring docs outside firm updates. Scenario: The PR can land with live prompts and parsers using major|minor|nit plus the fileable-only OOS gate, while public docs still say blocker/uncertain are valid and any threshold-accepted OOS is filed/scored.
- **Proposed resolution**: Add docs/voting-process.md and docs/point-competition.md to firm updates; align severity, high-rate, OOS filing, and OOS scoring prose with major-only high and accepted-plus-major-fileable OOS.

### FINDING_9:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:162-171
- **Concern**: Design ballot composition still defaults blank structured severity to nit. Scenario: When a plan-review structured sidecar omits severity, `_compose_finding_block` writes `- **Severity**: nit`, so the new pre-vote drop treats the row as reviewer-nit and removes it before judges see it, contradicting the plan edge case that missing severity becomes minor
- **Proposed resolution**: Change the compose default to `minor` (or leave severity absent and let the shared pre-aggregate normalizer default blank to `minor` before nit-drop); add a plan-review fixture for missing-severity rows staying on the ballot

### FINDING_10:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: python/larch/review/review_tally.py:505-536
- **Concern**: Emit-tally aggregate-pool promotion is not listed behind the shared fileable gate. Scenario: `_promote_aggregate_oos_pool` still promotes any pool block with `Vote tally: ... Result=accepted` into `oos-accepted-review.md` on every successful `emit-tally`, bypassing strict-majority-`major`; accepted-but-minor pool rows can still reach GitHub filing after tally gating
- **Proposed resolution**: Extend the `review_tally.py` update to gate `_append_oos_pool_candidate`, `_promote_aggregate_oos_pool`, and any emit-tally pool-to-sink promotion on the shared fileable predicate (or only promote rows already present in the gated accepted sink); cover with an accepted-minor-in-pool emit-tally test

### FINDING_11:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/issue/oos.py:64-79
- **Concern**: `oos serialize` still splits only `### FINDING_` blocks while live `oos.md` uses `### OOS_` headers. Scenario: The plan fixes serialize on `Result=accepted`, but `_iter_finding_blocks` ignores canonical `OOS_` blocks written by tally; emit-tally rebuild from `oos.md` can produce zero accepted rows even when fileable accepted OOS exists, breaking recovery when the accepted sink is empty or stale
- **Proposed resolution**: Teach `oos.py` block iteration to split on both `FINDING_` and `OOS_` headers (matching `_non_security_oos_count`), then add serialize/rebuild coverage with `OOS_`-headed `oos.md` input ### 1. [correctness] `python/larch/review/plan_review_round.py:162-171` — blank severity becomes nit at compose time The plan’s design-path nit-drop assumes missing severity defaults to `minor`, but `_compose_finding_block` still emits `severity or 'nit'`. Structured rows with an empty severity field become explicit `nit` and get dropped before voting, which is the opposite of the stated edge case. **Suggested revision:** Default compose to `minor`, or normalize blank severity to `minor` in the shared pre-aggregate filter before nit-drop; add plan-review test coverage for missing-severity rows remaining on the ballot. ### 2. [correctness] `python/larch/review/review_tally.py:505-536` — emit-tally pool promotion bypasses the file gate Step 4 names `review_tally.py` as a filing sink, but `_promote_aggregate_oos_pool` (called from `_finalize_emit_oos_filing` on every successful emit-tally) still promotes pool blocks keyed only on `Result=accepted`. That is a second hop into `oos-accepted-review.md` that can reintroduce accepted-but-minor OOS even if the vote loop gates the accepted sink. **Suggested revision:** Apply the shared fileable predicate to pool append and emit-time pool promotion, or stop promoting pool rows that are not already in the gated accepted sink; add an emit-tally test with accepted-minor pool content. ### 3. [risk-integration] `python/larch/issue/oos.py:64-79` — serialize cannot read canonical `OOS_` blocks The plan updates `oos.py` for the fileable predicate, but `_iter_finding_blocks` only recognizes `### FINDING_` headers. Production `oos.md` from tally uses `### OOS_` blocks, so serialize/rebuild can silently yield an empty accepted sink while fileable OOS remains only in `oos.md`. **Suggested revision:** Split blocks on both `FINDING_` and `OOS_` headers in `oos.py`, and extend `python/tests/issue/test_oos.py` with `OOS_`-headed serialize/rebuild fixtures.

### FINDING_12:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: docs/point-competition.md:11-66; docs/voting-process.md:123-126
- **Concern**: The plan updates docs/run-logs.md but leaves canonical voting and point-competition docs out of the firm file list, even though they still define `blocker|major`, `uncertain`, accepted-OOS filing, and flat OOS scoring semantics.. Scenario: After the PR, users reading the canonical voting/scoring docs get the retired severity scale and are told any threshold-accepted OOS is filed, contradicting the new strict-majority-`major` file gate.
- **Proposed resolution**: Add `docs/point-competition.md` and `docs/voting-process.md` to UPDATED and revise their severity, OOS filing, final-summary audit, and scoring prose to match `major|minor|nit` and fileable-only OOS acceptance.

### FINDING_13:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/larch/review/plan_review_round.py:162-171
- **Concern**: Missing structured severity still composes as nit before the new nit-drop filter. Scenario: `_compose_finding_block` uses `severity or 'nit'`, and `skills/design/references/plan-review.md` still documents missing TSV severity as `nit`. Blank reviewer severity therefore becomes an explicit `nit` row that the pre-ballot drop removes instead of a `minor` ballot row, contradicting the plan edge case and silently discarding findings judges never see
- **Proposed resolution**: Add `### UPDATED: python/larch/review/plan_review_round.py` step to change the compose default to `minor` (or normalize blank severity before compose), update the plan-review severity-default prose to `minor`, and extend `python/tests/review/test_plan_review.py` with a missing-severity fixture that stays on the ballot

### FINDING_14:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: python/larch/review/review_tally.py:1006-1013
- **Concern**: Plan step 4 ties `OOS_ACCEPTED_COUNT` to fileable rows but does not carve out vote-accepted competition scoring. Scenario: `review_tally.py` increments `oos_accepted` for every vote-accepted OOS while scoreboard `oos_accepted` stats come from the same vote `result`. Reusing the fileable gate for the competition counter would drop the required provisional +1 for accepted-but-`minor` OOS documented in `docs/point-competition.md`
- **Proposed resolution**: State explicitly in `review_tally.py` / `plan_review_tally.py` and `skills/shared/voting-protocol.md` that scoreboard +1 uses vote-accepted OOS while `OOS_ACCEPTED_COUNT`, accepted sinks, aggregate pool, and filing use the shared fileable predicate only; add a tally test with accepted-`minor` OOS scoring +1 but `OOS_ACCEPTED_COUNT=0`

### FINDING_15:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/references/self-review.md:14-24, skills/implement/references/self-review.md:27
- **Concern**: The plan's file-gate sink list omits main-agent self-review OOS sinks. Scenario: When all external reviewers fail, or `/implement --self-review` runs, the self-review procedures can still write directly to `oos-accepted-review.md` or `oos-accepted-main-agent.md`; Step 9a.1 can then file those OOS items without an accepted panel result and strict-majority YES `major` severity, violating the new file gate.
- **Proposed resolution**: Add these self-review paths to the plan and keep self-review OOS logged-only unless they pass the same shared fileable predicate through a normal vote/classification artifact.
