### FINDING_1: code-quality: scripts/ship-pr.sh:1587-1594,scripts/create-pr.sh:130-254
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Nested transient retry: ship-pr wraps all of create-pr.sh while create-pr now wraps push and gh pr create internally. Sustained GitHub flake during /implement Step 9b can run up to 3 outer script retries each re-running 3 inner push and 3 inner create attempts with stacked 2s/4s backoff (~tens of seconds, duplicate push/create work). Keep retry at one layer for the ship-pr→create-pr chain (caller env gate or drop outer wrap; inner-only for standalone create-pr).
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/ship-pr.sh:3087-3088,scripts/merge-pr.sh:283-393
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Nested transient retry: ship-pr envelope wrapper around merge-pr.sh plus new inner fetch/merge wraps. CI-merge phase can multiply fetch and gh pr merge attempts beyond the plan’s 3-attempt intent and amplify latency during outages. Same single-layer rule: inner wraps for standalone merge-pr; outer ship_pr only when envelope predicate is needed, or vice versa.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-lib-net.sh:38-51
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Test harness duplicates ship_pr_with_transient_retry instead of testing ship-pr.sh’s copy. Future ship-pr wrapper changes can pass test-lib-net while breaking production envelope exhaustion. Share one definition or add an edit-in-sync contract test against ship-pr.sh.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/design-log-publish.sh:683-684
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Misleading log when create_rc=0 but PR recovery is empty. Operator sees gh pr create failed even though create returned 0 and cleanup correctly kept the remote branch. Branch error text on create_rc and recovery outcome.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Best-effort gh pr edit wrap ignores _WTR_RC per plan. Harder to extend logging/metrics on silent title-sync failures. Capture _WTR_RC then ignore, per lib-net.md Shape B.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/lint-awk-multibyte-regex.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Orthogonal 381-line linter bundled in retry PR. Harder bisect and review of retry-only changes. Split follow-up if not CI-blocking.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/create-pr.sh:178-184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Bare gh pr list in create conflict recovery. Transient list failure after wrapped create can block existing-PR recovery. Wrap list or document single-shot recovery.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] code-quality: scripts/git-push.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Parallel push-retry abstractions coexist with lib-net. Inconsistent retry behavior across implement scripts. Consolidate or document when to use each wrapper.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/tracking-issue-write.sh:320-322
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] create-issue failure reads net_fail_file but create still redirects stderr to ERR_TMP only gh issue create fails; emit_gh_failure gets empty ERR_CONTENT and operators lose the real API error Use ERR_CONTENT=$(cat "$ERR_TMP") in the create-issue else branch
- **Suggested revision**: Address the concern above.

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

### FINDING_13: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Post-rebump gh pr edit uses with_transient_retry with outer || true and never reads _WTR_RC Persistent title sync failure is silent (best-effort by design) Optional: read _WTR_RC and log at debug level without failing ship-pr
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] correctness: scripts/design-log-publish.sh:685-686
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Remote branch cleanup skipped when gh pr list probe fails (recovery_probe_ok=false) All create retries fail and list probe fails; orphan remote branch remains and operator retry can NFF on push Document operator recovery or retry list with separate cleanup policy
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: scripts/test-design-log-publish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Plan-required end-to-end transient gh pr create retry test is missing. After push succeeds, a one-shot transient API failure still leaves a remote branch; without a succeed-on-retry fixture, regressions in with_transient_retry around pr create would reintroduce the original non-fast-forward failure on operator retry. Add gh stub attempt counter: fail attempts 1-2 with transient stderr, succeed on 3; assert PUBLISH_OK=true and remote branch retained until merge.
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

### FINDING_19: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **correctness** — `scripts/tracking-issue-write.sh:321` — `create-issue` failure path reads `$net_fail_file` but create is not wrapped; under `set -u` this can abort before `emit_gh_failure`. Pre-existing redaction contract expects `ERR_TMP`; not a new leakage path, but breaks controlled failure handling.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **correctness** — `scripts/tracking-issue-write.sh:503-506`, `557-567` — `rename` / `mark-false-positive` `rm -f` the `*_fail_file` before `cat` on failure, so `emit_gh_failure` often gets empty input (generic message only). Does not increase secret exposure; weakens diagnostics.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] **security (positive)** — Plan carve-outs are correctly implemented: bare `gh issue create` (`tracking-issue-write.sh:310`, `create-one.sh`, `apply-combination.sh`) and bare `git clone` (`setup-forked-open-source-repo.sh`) avoid non-idempotent retries.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security (positive)** — Plan carve-outs are correctly implemented: bare `gh issue create` (`tracking-issue-write.sh:310`, `create-one.sh`, `apply-combination.sh`) and bare `git clone` (`setup-forked-open-source-repo.sh`) avoid non-idempotent retries.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] **security (positive)** — `with_transient_retry` invokes `"$@"` with proper quoting; predicates are fixed function names, not user-controlled eval.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **security (positive)** — `with_transient_retry` invokes `"$@"` with proper quoting; predicates are fixed function names, not user-controlled eval.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **architecture** — `scripts/lib-net.sh:27-64` lift is sound for injection; `ship_pr_with_transient_retry` (`scripts/ship-pr.sh:2420-2435`) preserves terminal transient-exit semantics without widening command surface. No hard-coded secrets, new auth scopes, or command-injection regressions were found in the diff. Main security-adjacent gap introduced by the branch is **retry without deduplication on GitHub comment writes**; secondary gap is **unredacted transport diagnostics** in a few kv-emitting scripts that bypass the repo’s fail-closed redaction choke points. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	latent	risk-integration	scripts/tracking-issue-write.sh:397-405 Retrying gh issue comment can duplicate public comments after server-side success with a lost client response exposing duplicated operational content on the issue. Add a list-and-match recovery probe before retry or exclude gh issue comment from with_transient_retry like gh issue create. 1	in_scope	latent	security	scripts/gh-pr-body-update.sh:86-97 Failure ERROR= is built from raw fail_file without redact-secrets so GitHub CLI auth or transport stderr can surface token-shaped substrings in stdout KEY=value output and ship-pr failure artifacts. Pipe fail_file through redact_text or emit_gh_failure before setting ERROR=. 1	in_scope	latent	security	scripts/check-remote-branch.sh:56-74 STATE=error ERROR= emits unredacted FAIL_CAPTURE from git ls-remote retries which can include credential-helper or auth diagnostics visible to implement preflight consumers. Redact FAIL_CAPTURE with redact-secrets.sh before emit_kv ERROR. ```
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

### FINDING_30: risk-integration: scripts/tracking-issue-write.sh:398-418
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Wrapped gh issue comment can duplicate on retry after server success + lost response Lifecycle tracking issue shows duplicate marker comments Document tradeoff or add idempotent comment marker
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: scripts/rebase-push.sh:280-293
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Nested 3x3 transient retries on lease-race push loop Sustained outage extends Step 12c push wall-time materially Document or use single retry layer in lease loop
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] architecture: scripts/design-log-publish.sh:720-732
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Worktree removed before merge_rc check on merge failure Harder local recovery after merge fail; remote PR remains Pre-existing; optional defer worktree remove until merge outcome known
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] correctness: .claude/skills/audit-runs/scripts/audit-close-priors.sh:112-113
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] CLOSE_FAILED omits captured gh stderr Operator sees generic close failed without API detail Read close_fail_file before rm into REASON
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: scripts/design-log-publish.sh:618-623
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan requires capturing push_out from _WTR_OUT after the push wrapper; only push_rc is stored. Push-failure diagnostics cannot use captured stdout even though the wrapper records it in _WTR_OUT. Add push_out=$_WTR_OUT immediately after the push wrapper alongside push_rc.
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: scripts/design-log-publish.sh:164-166,724
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Plan says per-call fail_files are removed by the EXIT trap, but trap - EXIT on the success path skips wt_cleanup. Each successful design-log publish leaves three mktemp capture files in TMPDIR. rm -f push_fail_file create_fail_file merge_fail_file before trap - EXIT, or defer trap - EXIT until after cleanup.
- **Suggested revision**: Address the concern above.

### FINDING_36: architecture: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Post-rebump gh pr edit uses || true on the wrapper without the documented _WTR_RC read pattern. Matches plan wording literally but diverges from the set -e contract documented in lib-net.md. Capture rc via set +e and _WTR_RC, then ignore non-zero for best-effort semantics.
- **Suggested revision**: Address the concern above.

