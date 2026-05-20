# Review Round 2

- Mode: `diff`
- Accepted findings: 16
- Rejected findings: 4
- Exonerated findings: 2
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `docs/run-logs-required-files.tsv:2` / `scripts/verify-run-log-completeness.sh:31`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `docs/run-logs-required-files.tsv:2` / `scripts/verify-run-log-completeness.sh:31`      The new completeness manifest says it applies to committed `/implement` runs that reach Step 7a, but it marks later artifacts like `version-bump-reasoning.md` and `run-statistics.md` as `always` required. A run that reaches Step 7a, commits `session-transcript.jsonl`, then stalls before Step 8 or Step 9a.1 will be reported as incomplete even though those later batches were never supposed to exist. Fix by either scoping the manifest/verifier to successful merged runs only, or adding real conditions for Step 7a / Step 8 / Step 9a.1 artifacts and teaching `verify-run-log-completeness.sh` to apply them.
- **Suggested revision**: Address the concern above.


### FINDING_19: code-quality: scripts/test-verify-run-log-completeness.sh:48-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Inverted/misleading failure messages when batch slug lookup or extension check fails. Harder to diagnose manifest/TSV drift from CI logs. Use explicit negated wording for failure branches.
- **Suggested revision**: Address the concern above.


### FINDING_20: code-quality: scripts/test-verify-run-log-completeness.sh:48-55
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness failure strings invert success/failure wording for unknown batch slug and extension mismatch. A manifest regression produces misleading pass/fail wording in logs. Fix messages to state unknown slug vs extension mismatch explicitly.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: docs/run-logs-required-files.tsv:1-15 and scripts/verify-run-log-completeness.md:24-27
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Manifest header and verifier doc claim Step-7a-scoped completeness but rows mark Step-8+ files (version-bump-reasoning.md run-statistics.md) as condition=always alongside Step-7a batches. Running verify-run-log-completeness.sh on a log tree captured immediately after the Step-7a flush (before bump/OOS statistics writes) yields false MISSING for version-bump-reasoning.md and run-statistics.md despite a valid in-progress run. Reword scope to final merged terminal tree or extend condition semantics and verify script to match SKILL batch timing.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: docs/run-logs-required-files.tsv:1-16
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Manifest comments say partial runs may omit session-transcript but row 15 marks session-transcript.jsonl as condition=always. Verify script reports MISSING=session-transcript.jsonl for committed partial run dirs that docs describe as valid, causing false alarms or contradictory contracts. Use a distinct condition for Step-7a-only files or otherwise align manifest rows with documented bailout paths.
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: docs/run-logs-required-files.tsv:2-15; scripts/verify-run-log-completeness.md:24-27
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Manifest prose says Step 7a scope and only session-transcript as Step-7a-only gap yet lists Step 8/9a.1 files as always required. Running verify on a post-7a-pre-bump tree or misreading docs yields false MISSING or wrong mental model of which batches belong to which phase. Rewrite manifest/verifier scope to match actual write order or add conditional rows that mirror the step graph.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/capture-session-transcript.sh:67; scripts/refresh-run-logs.sh:89-95
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Execution-issues warnings always label Step 7a even when capture runs from refresh-run-logs on CI retries. Triage assumes transcript warnings occurred at Step 7a though they were emitted during pre-push refresh. Add caller-provided label or neutral wording in append_warning.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: scripts/test-capture-session-transcript.sh:179-204
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Default-branch test no longer asserts repo stays free of staged larch-log paths after commit-failed. larch-log could leave a dirty partial tree without harness detection. Reintroduce a focused filesystem or git-status assertion aligned with larch-log behavior.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: scripts/test-verify-run-log-completeness.sh (file) and agent-lint.toml:143-152
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] New scripts/test-verify-run-log-completeness.sh lacks required sibling scripts/test-verify-run-log-completeness.md per script-md-siblings; agent-lint exclude lists the missing path. Editing the harness triggers script-md-siblings expectations for a stub that does not exist; exclude references a non-existent file. Add scripts/test-verify-run-log-completeness.md stub per script-md-siblings (keep agent-lint exclude aligned).
- **Suggested revision**: Address the concern above.


### FINDING_3: **[risk-integration]** [`SECURITY.md:108-111`](SECURITY.md) — The durable-run-store paragraph still claims (1) `capture-session-transcript.sh` is in the same defense-in-depth posture as `larch-log.sh commit` for default-branch refusal, and (2) that the Step 18 bash block exports `IMPLEMENT_TMPDIR` specifically so `capture-session-transcript.sh` can see `post-merge-sentinel`. This branch removes branch/sentinel handling from [`scripts/capture-session-transcript.sh`](scripts/capture-session-transcript.sh) and moves capture to Step 7a in [`skills/implement/SKILL.md`](skills/implement/SKILL.md), so that text is now wrong and can mislead operators about where the guard lives. **Suggested fix:** Rewrite that sentence to name `larch-log.sh commit` (post-merge sentinel + default-branch checks at [`scripts/larch-log.sh:442-449`](scripts/larch-log.sh)) and `scripts/refresh-run-logs.sh`’s early `MERGE_RESULT` skip ([`scripts/refresh-run-logs.sh:30-33`](scripts/refresh-run-logs.sh)) as the enforcement surfaces; align the `IMPLEMENT_TMPDIR` export note with Step 7a / `refresh-run-logs.sh` (which does `export IMPLEMENT_TMPDIR="$IMPL_TMPDIR"` at [`scripts/refresh-run-logs.sh:54`](scripts/refresh-run-logs.sh)), not Step 18 transcript capture.
- **Reviewer**: dyn-sentinel-removal-output.txt
- **Concern**: - **[risk-integration]** [`SECURITY.md:108-111`](SECURITY.md) — The durable-run-store paragraph still claims (1) `capture-session-transcript.sh` is in the same defense-in-depth posture as `larch-log.sh commit` for default-branch refusal, and (2) that the Step 18 bash block exports `IMPLEMENT_TMPDIR` specifically so `capture-session-transcript.sh` can see `post-merge-sentinel`. This branch removes branch/sentinel handling from [`scripts/capture-session-transcript.sh`](scripts/capture-session-transcript.sh) and moves capture to Step 7a in [`skills/implement/SKILL.md`](skills/implement/SKILL.md), so that text is now wrong and can mislead operators about where the guard lives. **Suggested fix:** Rewrite that sentence to name `larch-log.sh commit` (post-merge sentinel + default-branch checks at [`scripts/larch-log.sh:442-449`](scripts/larch-log.sh)) and `scripts/refresh-run-logs.sh`’s early `MERGE_RESULT` skip ([`scripts/refresh-run-logs.sh:30-33`](scripts/refresh-run-logs.sh)) as the enforcement surfaces; align the `IMPLEMENT_TMPDIR` export note with Step 7a / `refresh-run-logs.sh` (which does `export IMPLEMENT_TMPDIR="$IMPL_TMPDIR"` at [`scripts/refresh-run-logs.sh:54`](scripts/refresh-run-logs.sh)), not Step 18 transcript capture.
- **Suggested revision**: Address the concern above.


### FINDING_4: **[risk-integration]** [`scripts/capture-session-transcript.sh:59-68`](scripts/capture-session-transcript.sh) — `append_warning` hardcodes the prose prefix `Step 7a — session-transcript status=...` for every outcome. [`scripts/refresh-run-logs.sh:84-95`](scripts/refresh-run-logs.sh) invokes the same script during Step 8+ pre-push retries, so committed [`skills/implement/scripts/flush-execution-issues.sh`](skills/implement/scripts/flush-execution-issues.sh) / `execution-issues.ndjson` entries can falsely attribute transcript status to **Step 7a** when the event was a **pre-push refresh**, which weakens traceability for CI-retry forensics. **Suggested fix:** add an optional flag (for example `--warning-step-label` / `--caller-label`) defaulting to `7a`, and pass a distinct label from `refresh-run-logs.sh` (for example `pre-push-refresh`).
- **Reviewer**: dyn-refresh-transcript-output.txt
- **Concern**: - **[risk-integration]** [`scripts/capture-session-transcript.sh:59-68`](scripts/capture-session-transcript.sh) — `append_warning` hardcodes the prose prefix `Step 7a — session-transcript status=...` for every outcome. [`scripts/refresh-run-logs.sh:84-95`](scripts/refresh-run-logs.sh) invokes the same script during Step 8+ pre-push retries, so committed [`skills/implement/scripts/flush-execution-issues.sh`](skills/implement/scripts/flush-execution-issues.sh) / `execution-issues.ndjson` entries can falsely attribute transcript status to **Step 7a** when the event was a **pre-push refresh**, which weakens traceability for CI-retry forensics. **Suggested fix:** add an optional flag (for example `--warning-step-label` / `--caller-label`) defaulting to `7a`, and pass a distinct label from `refresh-run-logs.sh` (for example `pre-push-refresh`).
- **Suggested revision**: Address the concern above.


### FINDING_5: **[risk-integration]** [`scripts/capture-session-transcript.sh:71-77`](scripts/capture-session-transcript.sh) — `emit_status` always calls `append_warning` before exiting, including for `SESSION_TRANSCRIPT_STATUS=captured` ([`scripts/capture-session-transcript.sh:179`](scripts/capture-session-transcript.sh)). Moving capture into [`scripts/refresh-run-logs.sh:84-95`](scripts/refresh-run-logs.sh) means **each** Trigger A/B/C success adds another “session-transcript status=captured” line to the append-only [`execution-issues`](docs/run-logs.md) batch ([`scripts/larch-log-batches.sh:31`](scripts/larch-log-batches.sh) batch mode append), diluting the audit trail compared to the old single Step 18 capture. **Suggested fix:** omit or dedupe `append_warning` for `captured` when invoked from the refresh path, or only append on non-`captured` statuses for refresh callers.
- **Reviewer**: dyn-refresh-transcript-output.txt
- **Concern**: - **[risk-integration]** [`scripts/capture-session-transcript.sh:71-77`](scripts/capture-session-transcript.sh) — `emit_status` always calls `append_warning` before exiting, including for `SESSION_TRANSCRIPT_STATUS=captured` ([`scripts/capture-session-transcript.sh:179`](scripts/capture-session-transcript.sh)). Moving capture into [`scripts/refresh-run-logs.sh:84-95`](scripts/refresh-run-logs.sh) means **each** Trigger A/B/C success adds another “session-transcript status=captured” line to the append-only [`execution-issues`](docs/run-logs.md) batch ([`scripts/larch-log-batches.sh:31`](scripts/larch-log-batches.sh) batch mode append), diluting the audit trail compared to the old single Step 18 capture. **Suggested fix:** omit or dedupe `append_warning` for `captured` when invoked from the refresh path, or only append on non-`captured` statuses for refresh callers.
- **Suggested revision**: Address the concern above.


### FINDING_6: **[risk-integration]** [`scripts/capture-session-transcript.sh:80-130`](scripts/capture-session-transcript.sh) — On retries, if `--source-file` is empty/invalid and discovery does not recover a transcript path, `emit_status` still appends `source-file-missing` / `transcript-path-missing` / `transcript-file-missing` warnings to `execution-issues.md` ([`scripts/refresh-run-logs.sh:89-95`](scripts/refresh-run-logs.sh)). A prior successful Step 7a flush may already have committed a good [`session-transcript.jsonl`](docs/run-logs.md); the new warning reads like the run never captured a transcript. **Suggested fix:** on refresh, detect an existing `session-transcript` batch in the staging log root (or pass `--refresh-mode`) and soften the message (for example “refresh skipped; prior transcript retained”) instead of the same skip text as first capture.
- **Reviewer**: dyn-refresh-transcript-output.txt
- **Concern**: - **[risk-integration]** [`scripts/capture-session-transcript.sh:80-130`](scripts/capture-session-transcript.sh) — On retries, if `--source-file` is empty/invalid and discovery does not recover a transcript path, `emit_status` still appends `source-file-missing` / `transcript-path-missing` / `transcript-file-missing` warnings to `execution-issues.md` ([`scripts/refresh-run-logs.sh:89-95`](scripts/refresh-run-logs.sh)). A prior successful Step 7a flush may already have committed a good [`session-transcript.jsonl`](docs/run-logs.md); the new warning reads like the run never captured a transcript. **Suggested fix:** on refresh, detect an existing `session-transcript` batch in the staging log root (or pass `--refresh-mode`) and soften the message (for example “refresh skipped; prior transcript retained”) instead of the same skip text as first capture.
- **Suggested revision**: Address the concern above.


### FINDING_7: **[risk-integration]** [`scripts/test-capture-session-transcript.sh:179-204`](scripts/test-capture-session-transcript.sh) — `default-branch-loud-fail` only asserts `SESSION_TRANSCRIPT_STATUS=commit-failed` and the generic `session-transcript status=commit-failed` marker in `execution-issues.md`. It does not pin the failure to [`scripts/larch-log.sh`](scripts/larch-log.sh)’s explicit refusal text emitted at [`scripts/larch-log.sh:447-448`](scripts/larch-log.sh), so an accidental regression that maps some other non-zero `larch-log.sh commit` outcome into `commit-failed` with a different stderr shape could still satisfy the test. **Suggested fix:** Add an `assert_contains` on the execution-issues log (or the appended warning body) for a distinctive substring from that refusal path, e.g. `refusing commit on default branch` (present in stderr before trimming in [`scripts/capture-session-transcript.sh`](scripts/capture-session-transcript.sh)’s `commit-failed` message).
- **Reviewer**: dyn-sentinel-removal-output.txt
- **Concern**: - **[risk-integration]** [`scripts/test-capture-session-transcript.sh:179-204`](scripts/test-capture-session-transcript.sh) — `default-branch-loud-fail` only asserts `SESSION_TRANSCRIPT_STATUS=commit-failed` and the generic `session-transcript status=commit-failed` marker in `execution-issues.md`. It does not pin the failure to [`scripts/larch-log.sh`](scripts/larch-log.sh)’s explicit refusal text emitted at [`scripts/larch-log.sh:447-448`](scripts/larch-log.sh), so an accidental regression that maps some other non-zero `larch-log.sh commit` outcome into `commit-failed` with a different stderr shape could still satisfy the test. **Suggested fix:** Add an `assert_contains` on the execution-issues log (or the appended warning body) for a distinctive substring from that refusal path, e.g. `refusing commit on default branch` (present in stderr before trimming in [`scripts/capture-session-transcript.sh`](scripts/capture-session-transcript.sh)’s `commit-failed` message).
- **Suggested revision**: Address the concern above.


### FINDING_8: **correctness** — [`docs/run-logs-required-files.tsv:2-15`](docs/run-logs-required-files.tsv): Comment lines state that partial / pre–Step 7a trees may omit `session-transcript.jsonl`, but the manifest row still uses `condition=always` for `session-transcript.jsonl`. [`scripts/verify-run-log-completeness.sh:19-27`](scripts/verify-run-log-completeness.sh) only honors `always`, so the machine check cannot encode the prose caveat; any partial tree will get `MISSING=session-transcript.jsonl` indistinguishable from a broken Step 7a tree. **Suggested fix:** introduce a non-`always` condition (or a separate manifest) aligned with “Step 7a reached”, and teach the verifier to skip or branch on that signal; or drop the contradictory comment and document that the verifier must only be pointed at Step-7a-complete directories.
- **Reviewer**: dyn-flush-ordering-output.txt
- **Concern**: - **correctness** — [`docs/run-logs-required-files.tsv:2-15`](docs/run-logs-required-files.tsv): Comment lines state that partial / pre–Step 7a trees may omit `session-transcript.jsonl`, but the manifest row still uses `condition=always` for `session-transcript.jsonl`. [`scripts/verify-run-log-completeness.sh:19-27`](scripts/verify-run-log-completeness.sh) only honors `always`, so the machine check cannot encode the prose caveat; any partial tree will get `MISSING=session-transcript.jsonl` indistinguishable from a broken Step 7a tree. **Suggested fix:** introduce a non-`always` condition (or a separate manifest) aligned with “Step 7a reached”, and teach the verifier to skip or branch on that signal; or drop the contradictory comment and document that the verifier must only be pointed at Step-7a-complete directories.
- **Suggested revision**: Address the concern above.


### FINDING_9: **correctness** — [`scripts/capture-session-transcript.sh:169-177`](scripts/capture-session-transcript.sh) plus [`skills/implement/SKILL.md:1697-1698`](skills/implement/SKILL.md) / [`scripts/refresh-run-logs.sh:89-109`](scripts/refresh-run-logs.sh): `capture-session-transcript.sh` still runs `larch-log.sh commit` when `--no-logs-commit false`, while Step 7a and `refresh-run-logs.sh` each end with another `larch-log.sh commit`. After a successful capture, `emit_status "captured"` appends the status line to `execution-issues.md` **after** that internal commit ([`scripts/capture-session-transcript.sh:67-74`](scripts/capture-session-transcript.sh), [`179:179`](scripts/capture-session-transcript.sh)), so the post-transcript `flush-execution-issues.sh` pass materializes new NDJSON tail that the **following** commit must pick up. That is two separate git commits for one logical “pre-bump” or “pre-push refresh” flush, which contradicts the “single flush commit” mental model the scout checklist called out. **Suggested fix:** add a `--defer-commit` (or similar) path used by Step 7a / `refresh-run-logs.sh` so capture only writes, and retain a single `larch-log.sh commit` at the orchestrator tail; or explicitly document and test the two-commit contract if it is intentional.
- **Reviewer**: dyn-flush-ordering-output.txt
- **Concern**: - **correctness** — [`scripts/capture-session-transcript.sh:169-177`](scripts/capture-session-transcript.sh) plus [`skills/implement/SKILL.md:1697-1698`](skills/implement/SKILL.md) / [`scripts/refresh-run-logs.sh:89-109`](scripts/refresh-run-logs.sh): `capture-session-transcript.sh` still runs `larch-log.sh commit` when `--no-logs-commit false`, while Step 7a and `refresh-run-logs.sh` each end with another `larch-log.sh commit`. After a successful capture, `emit_status "captured"` appends the status line to `execution-issues.md` **after** that internal commit ([`scripts/capture-session-transcript.sh:67-74`](scripts/capture-session-transcript.sh), [`179:179`](scripts/capture-session-transcript.sh)), so the post-transcript `flush-execution-issues.sh` pass materializes new NDJSON tail that the **following** commit must pick up. That is two separate git commits for one logical “pre-bump” or “pre-push refresh” flush, which contradicts the “single flush commit” mental model the scout checklist called out. **Suggested fix:** add a `--defer-commit` (or similar) path used by Step 7a / `refresh-run-logs.sh` so capture only writes, and retain a single `larch-log.sh commit` at the orchestrator tail; or explicitly document and test the two-commit contract if it is intentional.
- **Suggested revision**: Address the concern above.


