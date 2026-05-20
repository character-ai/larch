### FINDING_10: [OUT_OF_SCOPE] **[correctness]** [`docs/run-logs-required-files.tsv:179-193`](docs/run-logs-required-files.tsv) (new) — Header comments state that pre–Step 7a bailouts may omit Step-7a-only batches, while the `session-transcript.jsonl` row still uses `condition=always`, so [`scripts/verify-run-log-completeness.sh:53-60`](scripts/verify-run-log-completeness.sh) will flag `MISSING=session-transcript.jsonl` for those partial trees whenever the verifier is pointed at them. That may be intended, but the TSV comment vs `always` row reads contradictory without an explicit `partial` condition column in use.
- **Reviewer**: dyn-refresh-transcript-output.txt
- **Concern**: - **[correctness]** [`docs/run-logs-required-files.tsv:179-193`](docs/run-logs-required-files.tsv) (new) — Header comments state that pre–Step 7a bailouts may omit Step-7a-only batches, while the `session-transcript.jsonl` row still uses `condition=always`, so [`scripts/verify-run-log-completeness.sh:53-60`](scripts/verify-run-log-completeness.sh) will flag `MISSING=session-transcript.jsonl` for those partial trees whenever the verifier is pointed at them. That may be intended, but the TSV comment vs `always` row reads contradictory without an explicit `partial` condition column in use.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] **[risk-integration]** (Scout items verified as non-issues in this diff) — [`scripts/refresh-run-logs.sh:44-45`](scripts/refresh-run-logs.sh) exits before the transcript block when `NO_LOGS_COMMIT=true`, so [`scripts/refresh-run-logs.sh:94`](scripts/refresh-run-logs.sh) hardcoding `--no-logs-commit "false"` is unreachable in that state. [`scripts/larch-log-batches.sh:31`](scripts/larch-log-batches.sh) defines `session-transcript` as **replace**, so repeated `larch-log.sh write` across retries overwrites the batch rather than appending. The second [`flush-execution-issues.sh`](skills/implement/scripts/flush-execution-issues.sh) block ([`scripts/refresh-run-logs.sh:96-104`](scripts/refresh-run-logs.sh)) runs after capture when `execution-issues.md` is non-empty and the Step 7a gate files exist, matching the contract documented in [`scripts/refresh-run-logs.md`](scripts/refresh-run-logs.md).
- **Reviewer**: dyn-refresh-transcript-output.txt
- **Concern**: - **[risk-integration]** (Scout items verified as non-issues in this diff) — [`scripts/refresh-run-logs.sh:44-45`](scripts/refresh-run-logs.sh) exits before the transcript block when `NO_LOGS_COMMIT=true`, so [`scripts/refresh-run-logs.sh:94`](scripts/refresh-run-logs.sh) hardcoding `--no-logs-commit "false"` is unreachable in that state. [`scripts/larch-log-batches.sh:31`](scripts/larch-log-batches.sh) defines `session-transcript` as **replace**, so repeated `larch-log.sh write` across retries overwrites the batch rather than appending. The second [`flush-execution-issues.sh`](skills/implement/scripts/flush-execution-issues.sh) block ([`scripts/refresh-run-logs.sh:96-104`](scripts/refresh-run-logs.sh)) runs after capture when `execution-issues.md` is non-empty and the Step 7a gate files exist, matching the contract documented in [`scripts/refresh-run-logs.md`](scripts/refresh-run-logs.md).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] **[risk-integration]** [`CHANGELOG.md`](CHANGELOG.md) (existing historical entry referencing a Step 18 `capture-session-transcript` wrapper) — Still describes the old lifecycle; not introduced by this diff’s hunks. Optional follow-up if you want changelog narrative to match the new Step 7a contract.
- **Reviewer**: dyn-sentinel-removal-output.txt
- **Concern**: - **[risk-integration]** [`CHANGELOG.md`](CHANGELOG.md) (existing historical entry referencing a Step 18 `capture-session-transcript` wrapper) — Still describes the old lifecycle; not introduced by this diff’s hunks. Optional follow-up if you want changelog narrative to match the new Step 7a contract. **Evidence for scout checklist (no extra preamble):** [`scripts/larch-log.sh:442-449`](scripts/larch-log.sh) applies post-merge sentinel refusal when `IMPLEMENT_TMPDIR` is set and the sentinel path exists, then unconditional default-branch refusal via `current_branch_is_default` with `exit 1` and stderr — no bypass flags in that `commit` option block. [`scripts/refresh-run-logs.sh:30-33`](scripts/refresh-run-logs.sh) exits before the new `capture-session-transcript.sh` call on merged outcomes. Callers of `capture-session-transcript.sh` in-repo are [`skills/implement/SKILL.md`](skills/implement/SKILL.md) and [`scripts/refresh-run-logs.sh`](scripts/refresh-run-logs.sh) per grep; the post-merge `MERGE_RESULT` gate addresses the “unexpected post-merge on main” path for the refresh caller.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] **correctness** — [`scripts/refresh-run-logs.sh:44-45`](scripts/refresh-run-logs.sh): `NO_LOGS_COMMIT=true` exits before any flush or capture, so there is no stray `larch-log.sh commit` from those paths when logs are suppressed; `flush-execution-issues.sh` only invokes `larch-log.sh append`, not `commit` ([`skills/implement/scripts/flush-execution-issues.sh:171-177`](skills/implement/scripts/flush-execution-issues.sh)).
- **Reviewer**: dyn-flush-ordering-output.txt
- **Concern**: - **correctness** — [`scripts/refresh-run-logs.sh:44-45`](scripts/refresh-run-logs.sh): `NO_LOGS_COMMIT=true` exits before any flush or capture, so there is no stray `larch-log.sh commit` from those paths when logs are suppressed; `flush-execution-issues.sh` only invokes `larch-log.sh append`, not `commit` ([`skills/implement/scripts/flush-execution-issues.sh:171-177`](skills/implement/scripts/flush-execution-issues.sh)).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] **correctness** — [`skills/implement/scripts/flush-execution-issues.sh:96-125`](skills/implement/scripts/flush-execution-issues.sh) / [`scripts/lib-execution-issues.sh:95-154`](scripts/lib-execution-issues.sh): Per-file SHA sentinel plus per-section `source_sha256` dedup already prevents replaying markdown that was cleared in the first flush when the post-transcript flush runs; this logic predates the branch and is not weakened by the new ordering.
- **Reviewer**: dyn-flush-ordering-output.txt
- **Concern**: - **correctness** — [`skills/implement/scripts/flush-execution-issues.sh:96-125`](skills/implement/scripts/flush-execution-issues.sh) / [`scripts/lib-execution-issues.sh:95-154`](scripts/lib-execution-issues.sh): Per-file SHA sentinel plus per-section `source_sha256` dedup already prevents replaying markdown that was cleared in the first flush when the post-transcript flush runs; this logic predates the branch and is not weakened by the new ordering.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_15: [OUT_OF_SCOPE] code-quality: CHANGELOG.md
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Changelog still narrates Step 18-era transcript capture; not updated alongside behavior move. Reader confusion when bisecting features; not introduced in this diff’s touched files. Update in a separate docs pass if desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_16: [OUT_OF_SCOPE] security: scripts/capture-session-transcript.sh:141-147
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] render-failed already includes trimmed renderer stderr in warnings; same class of leakage as new write/commit stderr mirroring. Pre-existing pattern in the same file; not introduced by this diff. Consider shared redaction for all stderr-in-warning paths if tightening.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_17: [OUT_OF_SCOPE] security: scripts/capture-session-transcript.sh:95-118
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Fallback discovery walks HOME/.claude/projects and logs recovered paths. Pre-existing behavior; not part of this diff’s functional goal. N/A for this branch review.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### FINDING_2: **Nit** `code-quality` `scripts/larch-log.md:90`, `scripts/larch-log-batches.md:16`, `scripts/test-capture-session-transcript.md:3`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `scripts/larch-log.md:90`, `scripts/larch-log-batches.md:16`, `scripts/test-capture-session-transcript.md:3`      Several sibling contracts still say `session-transcript` is captured at Step 18 or mention default-branch suppression, which now conflicts with the Step 7a behavior. Update those doc lines to match `scripts/capture-session-transcript.md`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_30: security: SECURITY.md:110-111
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Stale security narrative: still ties capture-session-transcript subprocess contract to Step 18 and claims wrapper-level default-branch commit suppression alongside larch-log.sh. Operators or auditors rely on SECURITY.md for post-merge/default-branch transcript safety; text no longer matches capture-session-transcript.sh after removal of current_branch_is_default and Step 7a move. Update SECURITY.md to describe Step 7a + refresh callers, actual commit refusal behavior, and post-merge guards without claiming removed wrapper suppression.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

