# Review Round 2

- Mode: `diff`
- 16 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_10: correctness: scripts/tracking-issue-write.sh:397-418
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] append-comment removes net_fail_file then reads empty ERR_TMP on failure gh issue comment fails after retries; failure and missing-URL paths report blank stderr Capture net_fail_file into ERR_CONTENT before rm; use that on lines 409 and 417
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/tracking-issue-write.sh:503-506
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] rename removes rename_fail_file before cat on failure gh issue edit rename fails; emit_gh_failure is always empty Cat rename_fail_file into ERR_CONTENT before rm -f
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: scripts/tracking-issue-write.sh:564-567
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] mark-false-positive removes mark_fail_file before cat on failure gh issue edit for false-positive marker fails; emit_gh_failure is always empty Cat mark_fail_file into ERR_CONTENT before rm -f
- **Suggested revision**: Address the concern above.


### FINDING_16: **Latent** — `scripts/tracking-issue-write.sh:397-405`, `scripts/clarify-comment-post.sh:156-162`, `scripts/tracking-issue-summary.sh:110-120`, and similar wrapped `gh issue comment` paths — Retrying `gh issue comment` is not idempotent under “server accepted, client lost response”: a second attempt can post a duplicate public comment with the same (already redacted) body. That duplicates operational content on the issue and can confuse downstream parsers that assume one marker comment per lifecycle event. **Suggested fix:** Either treat comment POST as non-retryable (like `gh issue create`), or add a recovery probe (`gh api` list comments + marker match) before retrying, mirroring `design-log-publish.sh`’s `gh pr list` recovery pattern.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **Latent** — `scripts/tracking-issue-write.sh:397-405`, `scripts/clarify-comment-post.sh:156-162`, `scripts/tracking-issue-summary.sh:110-120`, and similar wrapped `gh issue comment` paths — Retrying `gh issue comment` is not idempotent under “server accepted, client lost response”: a second attempt can post a duplicate public comment with the same (already redacted) body. That duplicates operational content on the issue and can confuse downstream parsers that assume one marker comment per lifecycle event. **Suggested fix:** Either treat comment POST as non-retryable (like `gh issue create`), or add a recovery probe (`gh api` list comments + marker match) before retrying, mirroring `design-log-publish.sh`’s `gh pr list` recovery pattern.
- **Suggested revision**: Address the concern above.


### FINDING_17: **Latent** — `scripts/gh-pr-body-update.sh:86-97` — On failure, `ERROR=` is built from the raw `fail_file` capture (`stdout` + `stderr`) with no `redact-secrets.sh` / `redact_gh_error` pass. GitHub CLI auth/transport failures can include token-shaped substrings in stderr; those flow into the script’s stdout `ERROR=` kv and into `ship-pr.sh` failure captures via `record_failure`. **Suggested fix:** Pipe `fail_file` contents through the same redaction helper used by `tracking-issue-summary.sh` (`redact_text`) or `emit_gh_failure` before setting `ERROR=`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **Latent** — `scripts/gh-pr-body-update.sh:86-97` — On failure, `ERROR=` is built from the raw `fail_file` capture (`stdout` + `stderr`) with no `redact-secrets.sh` / `redact_gh_error` pass. GitHub CLI auth/transport failures can include token-shaped substrings in stderr; those flow into the script’s stdout `ERROR=` kv and into `ship-pr.sh` failure captures via `record_failure`. **Suggested fix:** Pipe `fail_file` contents through the same redaction helper used by `tracking-issue-summary.sh` (`redact_text`) or `emit_gh_failure` before setting `ERROR=`.
- **Suggested revision**: Address the concern above.


### FINDING_18: **Latent** — `scripts/check-remote-branch.sh:56-74` — Transport failures now populate `ERROR=` from the wrapper’s `fail_file` without redaction. Git credential-helper / auth errors can land in structured `STATE=error` output consumed by implement preflight. **Suggested fix:** Run `FAIL_CAPTURE` through `redact-secrets.sh` (or reuse an existing redact helper) before `emit_kv ERROR`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **Latent** — `scripts/check-remote-branch.sh:56-74` — Transport failures now populate `ERROR=` from the wrapper’s `fail_file` without redaction. Git credential-helper / auth errors can land in structured `STATE=error` output consumed by implement preflight. **Suggested fix:** Run `FAIL_CAPTURE` through `redact-secrets.sh` (or reuse an existing redact helper) before `emit_kv ERROR`.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/tracking-issue-write.sh:503-506
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] rename path deletes rename_fail_file before reading it for emit_gh_failure gh issue edit fails with rate-limit or auth stderr; caller gets FAILED=true ERROR= with no diagnostic Copy fail_file to a local before rm -f then pass to emit_gh_failure
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/tracking-issue-write.sh:564-567
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] mark-false-positive path deletes mark_fail_file before reading it for emit_gh_failure Same empty ERROR= on gh issue edit failure after marker insert Copy mark_fail_file content before rm -f
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/tracking-issue-write.sh:405-418
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] append-comment removes net_fail_file then reads empty ERR_TMP on failure Comment post fails; orchestrator sees FAILED=true with blank ERROR= Capture net_fail_file before rm; use for emit_gh_failure on failure and missing-URL paths
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/tracking-issue-write.sh:321
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] create-issue failure branch reads net_fail_file but create is unwapped and uses ERR_TMP Round-1 regression: create failures emit empty ERROR= Use cat ERR_TMP on create-issue failure; keep create unwapped
- **Suggested revision**: Address the concern above.


### FINDING_28: correctness: scripts/merge-pr.sh:351-413
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] MERGE_OUTPUT/ADMIN_OUTPUT use only _WTR_OUT; fail_file with stderr is removed before ERROR= is built Regression from 2>&1 merge: merge exhaustion yields ERROR=Admin merge failed: ; fallback merge failed: Cat fail_file (or merge stdout+stderr) before rm on failure paths
- **Suggested revision**: Address the concern above.


### FINDING_29: correctness: scripts/design-log-publish.sh:684
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Misleading log when create_rc=0 but PR recovery fails Operator believes create failed and may manual-delete branch while PR exists Branch error text on create_rc; preserve RECOVERY_BRANCH when create_rc=0
- **Suggested revision**: Address the concern above.


### FINDING_34: correctness: scripts/design-log-publish.sh:618-623
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan requires capturing push_out from _WTR_OUT after the push wrapper; only push_rc is stored. Push-failure diagnostics cannot use captured stdout even though the wrapper records it in _WTR_OUT. Add push_out=$_WTR_OUT immediately after the push wrapper alongside push_rc.
- **Suggested revision**: Address the concern above.


### FINDING_35: correctness: scripts/design-log-publish.sh:164-166,724
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan says per-call fail_files are removed by the EXIT trap, but trap - EXIT on the success path skips wt_cleanup. Each successful design-log publish leaves three mktemp capture files in TMPDIR. rm -f push_fail_file create_fail_file merge_fail_file before trap - EXIT, or defer trap - EXIT until after cleanup.
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: scripts/design-log-publish.sh:683-684
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Misleading log when create_rc=0 but PR recovery is empty. Operator sees gh pr create failed even though create returned 0 and cleanup correctly kept the remote branch. Branch error text on create_rc and recovery outcome.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/tracking-issue-write.sh:320-322
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] create-issue failure reads net_fail_file but create still redirects stderr to ERR_TMP only gh issue create fails; emit_gh_failure gets empty ERR_CONTENT and operators lose the real API error Use ERR_CONTENT=$(cat "$ERR_TMP") in the create-issue else branch
- **Suggested revision**: Address the concern above.


