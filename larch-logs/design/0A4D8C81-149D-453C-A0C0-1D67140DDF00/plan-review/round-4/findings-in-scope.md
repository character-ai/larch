### FINDING_1: Design MAV round-start timestamp can be pruned before deferred timing
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-dyn-ledger-contract, Cursor-Pragmatic, Codex-dyn-handoff-lifecycle
- **Severity**: important
- **Concern**: The design `main-agent-vote-required` path persists the round start timestamp in `plan-review/round-N`, but the snapshot/allowlist flow can drop `round-start-s` before `skills/design/SKILL.md` emits the deferred timing row. The deferred helper may then fall back to the current time and undercount the round duration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add round-start-s to design_round_artifact_included and its docs/tests, or persist the timestamp in an already-preserved artifact before snapshot exit
  - From Codex-Edge, Codex-dyn-ledger-contract: Add round-start-s to design_round_artifact_included or persist the timestamp after snapshot to a stable path that the inline adjudication path reads; cover this in the design MAV timing test
  - From Cursor-Pragmatic: Mirror implement: persist `$DESIGN_TMPDIR/plan-review/round-${round_num}/round-start-s` before MAV return; read that path in `record-plan-review-round-timing.sh` from `skills/design/SKILL.md` after re-tally (document in plan + helper md)
  - From Codex-dyn-handoff-lifecycle: Add round-start-s to scripts/lib-design-round-artifacts.sh and its focused test/docs, or persist/read the start from a path that _snapshot_round_dir does not prune. Write it no-clobber so the original start is kept.

### FINDING_2: Implement rejected-count fallback greps the wrong marker
- **Reviewer(s)**: Cursor-Edge, Cursor-Pragmatic, Cursor-Innovation, Codex-Requirements, Cursor-dyn-ledger-contract
- **Severity**: important
- **Concern**: The deferred implement review timing helper falls back to grepping `rejected-findings.md` for `^_OUTCOME=rejected`, but compact tally artifacts use lines such as `FINDING_N_OUTCOME=rejected`. If `review-tally.env` is absent, rejected counts can be silently emitted as 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge, Cursor-Pragmatic: When review-tally.env is absent fall back to review-tally.env-style patterns on that file if present else grep -cE '(^|[0-9]+:)(FINDING_[0-9]+_OUTCOME=rejected|_OUTCOME=rejected)$' on rejected-findings.md (mirror emit-tally.sh:68-75)
  - From Cursor-Innovation: Mirror emit-tally: grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$' on round-dir rejected-findings.md, or read REJECTED_COUNT from review-tally.env only
  - From Codex-Requirements: Use the established marker grep -cE '(^|_)FINDING_[0-9]+_OUTCOME=rejected$|^FINDING_[0-9]+_OUTCOME=rejected$' or simply grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$' for the compact file, and add a fallback test without review-tally.env
  - From Cursor-dyn-ledger-contract: Mirror emit-tally.sh: read `ACCEPTED_COUNT`/`REJECTED_COUNT` from `review-tally.env` first; fallback `grep -cE '^FINDING_[0-9]+_OUTCOME=rejected$'` on the tally env (or count only in-scope `FINDING_*_OUTCOME=rejected` lines, not OOS, if matching `REJECTED_COUNT` semantics)

### FINDING_3: Deferred round helpers do not bind tmpdir to ledger resolution
- **Reviewer(s)**: Codex-Innovation, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed helper contracts accept `--implement-tmpdir` / `--design-tmpdir`, but `timing-ledger.sh` resolves its ledger only from `--ledger` or exported environment. A fresh prompt-side shell passing only the documented tmpdir argument can silently emit no deferred round row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: In each helper, derive the ledger from the validated tmpdir and pass timing-ledger.sh --ledger "$tmpdir/timing-ledger.tsv", or export the matching TMPDIR plus LARCH_TIMING_LEDGER before calling record-round.
  - From Codex-Pragmatic: In both new helper scripts, canonicalize the tmpdir arg and invoke timing-ledger with the matching env root, e.g. IMPLEMENT_TMPDIR="$implement_tmpdir" LARCH_TIMING_SKILL=implement ... and DESIGN_TMPDIR="$design_tmpdir" LARCH_TIMING_SKILL=design ...; do not rely on caller-exported vars or --ledger for these paths

### FINDING_4: JSON round array plan may append after a closed object
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Concern**: The timing report JSON plan extends `emit_json_step` with `emit_round_array` but does not explicitly require delaying the final `}`. An implementation could append `,"rounds":[...]` after an already closed object and produce invalid JSON.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: In `emit_json_step`, print base fields without the final `}`, call `emit_round_array`, then print `}`; add a fixture asserting `jq` parses Step 3/5 entries with and without `rounds`

### FINDING_5: Accepted-only OOS counting lacks focused helper-level coverage
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Timing-report fixture tests only prove JSON can emit an `oos` value already present in ledger rows; they would not catch `record-plan-review-round-timing.sh` counting rejected or exonerated `OOS_N` rows from `voting-tally.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a focused helper test that writes voting-tally.md with accepted rejected and exonerated OOS_N rows, invokes record-plan-review-round-timing.sh, and asserts the emitted round row oos column counts accepted rows only

### FINDING_6: Design MAV is listed in both immediate-emission and deferred-emission paths
- **Reviewer(s)**: Cursor-dyn-handoff-lifecycle
- **Severity**: important
- **Concern**: The plan lists `main-agent-vote-required` among skip-revise branches that emit a round row immediately, while a later exception says MAV must defer emission to `skills/design/SKILL.md`. Following the early-emission bullet could append a stale preliminary row before inline re-tally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-handoff-lifecycle: Remove main-agent-vote-required from the early-emit branch list; keep only the deferral bullet (persist round-start-s, no record-round until post-adjudication in SKILL.md)

### FINDING_7: Pre-publish timing stderr can leak onto published design surface
- **Reviewer(s)**: Codex-dyn-publish-freshness
- **Severity**: important
- **Concern**: The pre-publish timing render writes `timing-report-final.stderr.log` to the top-level design publish surface. Because `design-log-publish.sh` stages most top-level files, successful or failed renders can leave unintended timing artifacts eligible for publication.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-freshness: Use an unpublished temp stderr path; after validating rc and nonempty JSON, atomically move only timing-report-final.json into the top-level publish surface and remove stderr/failure temp files before design-log-publish.sh. On failure, leave no timing-report-final.* top-level artifact and append the warning to execution-issues.md

### FINDING_8: Timing-report test plan retains conflicting stale attachment expectation
- **Reviewer(s)**: Codex-dyn-publish-freshness
- **Severity**: latent
- **Concern**: The timing-report test plan includes an old expectation that a later Step 5 round after a Step 7 mark should still attach to Step 5 without a re-mark, conflicting with the newer interval-semantics expectation that it should be omitted unless Step 5 is re-marked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-publish-freshness: Drop the old line-110 expectation and keep the two interval-semantics cases: no Step 5 re-mark omits the later round; a timing-only Step 5 re-mark attaches it to the second Step 5 entry
