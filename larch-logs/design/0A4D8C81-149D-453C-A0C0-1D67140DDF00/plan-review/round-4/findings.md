### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-design-round-artifacts.sh:17-24; skills/design/scripts/plan-review-loop.sh:341-353
- **Concern**: Design MAV deferred timing persists round-start-s in plan-review/round-N but the snapshot allowlist drops unknown files. Scenario: The main-agent-vote-required path snapshots and rewrites plan-review/round-N before returning to SKILL.md, so round-start-s is lost and the deferred timing helper cannot compute the real round duration
- **Proposed resolution**: Add round-start-s to design_round_artifact_included and its docs/tests, or persist the timestamp in an already-preserved artifact before snapshot exit

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:64-66
- **Concern**: Rejected-count fallback greps rejected-findings.md for ^_OUTCOME=rejected. Scenario: emit-tally.sh writes compact rejected-findings.md as grep -n lines like 42:FINDING_2_OUTCOME=rejected (see skills/review/scripts/emit-tally.sh:105-112); when review-tally.env is missing the fallback returns 0 and per-round rejected is silently under-reported
- **Proposed resolution**: When review-tally.env is absent fall back to review-tally.env-style patterns on that file if present else grep -cE '(^|[0-9]+:)(FINDING_[0-9]+_OUTCOME=rejected|_OUTCOME=rejected)$' on rejected-findings.md (mirror emit-tally.sh:68-75)

### FINDING_3:
- **Reviewer(s)**: Codex-Edge, Codex-dyn-ledger-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-design-round-artifacts.sh:17-24; skills/design/scripts/plan-review-loop.sh:1414-1420
- **Concern**: Design MAV start timestamp is persisted in the round directory, but the plan does not add round-start-s to the design round artifact allowlist. Scenario: _snapshot_round_dir copies only allowlisted files and then replaces the round directory, so a pre-snapshot round-start-s file can be dropped before skills/design/SKILL.md tries to emit the deferred timing row; the helper then falls back to current time and undercounts the main-agent-vote-required round
- **Proposed resolution**: Add round-start-s to design_round_artifact_included or persist the timestamp after snapshot to a stable path that the inline adjudication path reads; cover this in the design MAV timing test

### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/record-implement-review-round-timing.sh (NEW; plan ~65-66)
- **Concern**: Deferred implement rejected-count fallback uses grep '^_OUTCOME=rejected'. Scenario: Round rejected-findings.md uses FINDING_N_OUTCOME=rejected (see skills/review/scripts/emit-tally.sh); fallback always returns 0 when review-tally.env is missing
- **Proposed resolution**: Mirror emit-tally: grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$' on round-dir rejected-findings.md, or read REJECTED_COUNT from review-tally.env only

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-ledger.sh:55-82; skills/review-and-fix/scripts/record-implement-review-round-timing.sh:1; skills/design/scripts/record-plan-review-round-timing.sh:1
- **Concern**: New helper args do not guarantee ledger resolution. Scenario: The proposed helpers take --implement-tmpdir/--design-tmpdir, but timing-ledger.sh only finds the ledger from --ledger or exported env. A fresh prompt-side shell that calls the helper with only its documented args can silently drop the required round row.
- **Proposed resolution**: In each helper, derive the ledger from the validated tmpdir and pass timing-ledger.sh --ledger "$tmpdir/timing-ledger.tsv", or export the matching TMPDIR plus LARCH_TIMING_LEDGER before calling record-round.

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:1414-1420
- **Concern**: Design `main-agent-vote-required` deferral does not name a persist/read path for `_round_start` (implement specifies `round-$N/round-start-s`). Scenario: Inline `skills/design/SKILL.md` re-tally cannot reliably recover wall-clock start; duration may fall back to `date +%s` at adjudication time and under-count the round
- **Proposed resolution**: Mirror implement: persist `$DESIGN_TMPDIR/plan-review/round-${round_num}/round-start-s` before MAV return; read that path in `record-plan-review-round-timing.sh` from `skills/design/SKILL.md` after re-tally (document in plan + helper md)

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/timing-report.sh:368-371
- **Concern**: Plan extends `emit_json_step` with `emit_round_array` but does not require deferring the object closing `}`. Scenario: Implementer may append `,"rounds":[...]` after `"outlier":false}`, producing invalid JSON in `timing-report-final.json`
- **Proposed resolution**: In `emit_json_step`, print base fields without the final `}`, call `emit_round_array`, then print `}`; add a fixture asserting `jq` parses Step 3/5 entries with and without `rounds`

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/timing-ledger.sh:53-79
- **Concern**: New deferred round helper contracts do not explicitly bind the provided tmpdir as the timing-ledger root before calling record-round. Scenario: timing-ledger.sh only resolves the default ledger from exported IMPLEMENT_TMPDIR/DESIGN_TMPDIR or LARCH_TIMING_LEDGER, and it exits 0 on failure; prompt-side helper calls that pass only --implement-tmpdir/--design-tmpdir can silently emit no deferred MAV/handoff round row
- **Proposed resolution**: In both new helper scripts, canonicalize the tmpdir arg and invoke timing-ledger with the matching env root, e.g. IMPLEMENT_TMPDIR="$implement_tmpdir" LARCH_TIMING_SKILL=implement ... and DESIGN_TMPDIR="$design_tmpdir" LARCH_TIMING_SKILL=design ...; do not rely on caller-exported vars or --ledger for these paths

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/tally-plan-review.sh:464-492
- **Concern**: FINDING_1: Plan does not place accepted-only OOS parsing under a helper-level test. Scenario: timing-report fixture tests can only prove JSON emits an oos value already present in ledger rows; it will not catch record-plan-review-round-timing.sh counting rejected or exonerated OOS rows from voting-tally.md
- **Proposed resolution**: Add a focused helper test that writes voting-tally.md with accepted rejected and exonerated OOS_N rows, invokes record-plan-review-round-timing.sh, and asserts the emitted round row oos column counts accepted rows only

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review/scripts/emit-tally.sh:70-72
- **Concern**: FINDING_2: Implement deferred helper fallback grep uses the wrong rejected marker. Scenario: The proposed fallback grep '^_OUTCOME=rejected' will miss compact rejected-findings.md lines such as FINDING_1_OUTCOME=rejected when review-tally.env is absent, emitting rejected=0 despite mandatory per-round rejected counts
- **Proposed resolution**: Use the established marker grep -cE '(^|_)FINDING_[0-9]+_OUTCOME=rejected$|^FINDING_[0-9]+_OUTCOME=rejected$' or simply grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$' for the compact file, and add a fallback test without review-tally.env

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-ledger-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/record-implement-review-round-timing.sh:66
- **Concern**: Deferred implement round helper fallback greps rejected-findings.md with `^_OUTCOME=rejected`. Scenario: Committed implement rounds use compact lines `FINDING_N_OUTCOME=rejected` / `OOS_N_OUTCOME=rejected` (see larch-logs/implement/.../round-5/rejected-findings.md; skills/review/scripts/emit-tally.md). If `review-tally.env` is missing on a deferred `main-agent-vote-required` / `coder-main-agent-required` row, fallback returns 0 rejected while artifacts show rejections
- **Proposed resolution**: Mirror emit-tally.sh: read `ACCEPTED_COUNT`/`REJECTED_COUNT` from `review-tally.env` first; fallback `grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$'` on the tally env (or count only in-scope `FINDING_*_OUTCOME=rejected` lines, not OOS, if matching `REJECTED_COUNT` semantics)

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-handoff-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:92-97
- **Concern**: Plan lists main-agent-vote-required among skip-revise branches that emit a round row immediately after counts settle, while the MAV exception two lines later forbids loop emission and defers to skills/design/SKILL.md. Scenario: An implementer following the early-emit bullet can append a preliminary round row with 0-judge fallback counts before inline re-tally, exactly the stale-count failure mode the plan warns about in Failure modes §4
- **Proposed resolution**: Remove main-agent-vote-required from the early-emit branch list; keep only the deferral bullet (persist round-start-s, no record-round until post-adjudication in SKILL.md)

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-handoff-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:319-400, scripts/lib-design-round-artifacts.sh:17-24
- **Concern**: Design MAV start persistence targets a snapshot-pruned round directory, but the plan does not update the design round artifact allowlist for round-start-s. Scenario: The proposed main-agent-vote-required path persists _round_start in plan-review/round-N and then returns through the existing snapshot path; _snapshot_round_dir rebuilds the round directory and deletes files whose basenames are not accepted by design_round_artifact_included, whose current allowlist lacks round-start-s. skills/design/SKILL.md may then miss the persisted start and under-count inline adjudication time.
- **Proposed resolution**: Add round-start-s to scripts/lib-design-round-artifacts.sh and its focused test/docs, or persist/read the start from a path that _snapshot_round_dir does not prune. Write it no-clobber so the original start is kept.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-publish-freshness
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-publish.sh:257-264; scripts/design-log-publish.sh:259-273,348-365; <TMPDIR>/plan.txt:102-103
- **Concern**: Pre-publish timing render writes timing-report-final.stderr.log onto the top-level design publish surface. Scenario: design-log-publish.sh stages all top-level files except a small exclusion set, so a successful render can add a new committed timing-report-final.stderr.log path, and a failed or empty render can still leave top-level timing artifacts eligible for publication
- **Proposed resolution**: Use an unpublished temp stderr path; after validating rc and nonempty JSON, atomically move only timing-report-final.json into the top-level publish surface and remove stderr/failure temp files before design-log-publish.sh. On failure, leave no timing-report-final.* top-level artifact and append the warning to execution-issues.md

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-publish-freshness
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:108-114
- **Concern**: The timing-report test plan keeps a stale mis-attachment assertion that conflicts with the replacement interval cases. Scenario: Line 110 says a later Step 5 round after a Step 7 mark should still attach to Step 5 without a re-mark, while line 111 correctly says the no-re-mark case should omit that later round
- **Proposed resolution**: Drop the old line-110 expectation and keep the two interval-semantics cases: no Step 5 re-mark omits the later round; a timing-only Step 5 re-mark attaches it to the second Step 5 entry
