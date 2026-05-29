### FINDING_13: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:2760-2762
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Post-rebump gh pr edit uses with_transient_retry with outer || true and never reads _WTR_RC Persistent title sync failure is silent (best-effort by design) Optional: read _WTR_RC and log at debug level without failing ship-pr
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_14: [OUT_OF_SCOPE] correctness: scripts/design-log-publish.sh:685-686
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Remote branch cleanup skipped when gh pr list probe fails (recovery_probe_ok=false) All create retries fail and list probe fails; orphan remote branch remains and operator retry can NFF on push Document operator recovery or retry list with separate cleanup policy
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_19: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **correctness** — `scripts/tracking-issue-write.sh:321` — `create-issue` failure path reads `$net_fail_file` but create is not wrapped; under `set -u` this can abort before `emit_gh_failure`. Pre-existing redaction contract expects `ERR_TMP`; not a new leakage path, but breaks controlled failure handling.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_20: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **correctness** — `scripts/tracking-issue-write.sh:503-506`, `557-567` — `rename` / `mark-false-positive` `rm -f` the `*_fail_file` before `cat` on failure, so `emit_gh_failure` often gets empty input (generic message only). Does not increase secret exposure; weakens diagnostics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_21: [OUT_OF_SCOPE] **security (positive)** — Plan carve-outs are correctly implemented: bare `gh issue create` (`tracking-issue-write.sh:310`, `create-one.sh`, `apply-combination.sh`) and bare `git clone` (`setup-forked-open-source-repo.sh`) avoid non-idempotent retries.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **security (positive)** — Plan carve-outs are correctly implemented: bare `gh issue create` (`tracking-issue-write.sh:310`, `create-one.sh`, `apply-combination.sh`) and bare `git clone` (`setup-forked-open-source-repo.sh`) avoid non-idempotent retries.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] **security (positive)** — `with_transient_retry` invokes `"$@"` with proper quoting; predicates are fixed function names, not user-controlled eval.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 4. **security (positive)** — `with_transient_retry` invokes `"$@"` with proper quoting; predicates are fixed function names, not user-controlled eval.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_23: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 5. **architecture** — `scripts/lib-net.sh:27-64` lift is sound for injection; `ship_pr_with_transient_retry` (`scripts/ship-pr.sh:2420-2435`) preserves terminal transient-exit semantics without widening command surface. No hard-coded secrets, new auth scopes, or command-injection regressions were found in the diff. Main security-adjacent gap introduced by the branch is **retry without deduplication on GitHub comment writes**; secondary gap is **unredacted transport diagnostics** in a few kv-emitting scripts that bypass the repo’s fail-closed redaction choke points. ```tsv schema_version	scope	severity	focus_area	location	what	scenario_or_breakage	suggested_fix 1	in_scope	latent	risk-integration	scripts/tracking-issue-write.sh:397-405 Retrying gh issue comment can duplicate public comments after server-side success with a lost client response exposing duplicated operational content on the issue. Add a list-and-match recovery probe before retry or exclude gh issue comment from with_transient_retry like gh issue create. 1	in_scope	latent	security	scripts/gh-pr-body-update.sh:86-97 Failure ERROR= is built from raw fail_file without redact-secrets so GitHub CLI auth or transport stderr can surface token-shaped substrings in stdout KEY=value output and ship-pr failure artifacts. Pipe fail_file through redact_text or emit_gh_failure before setting ERROR=. 1	in_scope	latent	security	scripts/check-remote-branch.sh:56-74 STATE=error ERROR= emits unredacted FAIL_CAPTURE from git ls-remote retries which can include credential-helper or auth diagnostics visible to implement preflight consumers. Redact FAIL_CAPTURE with redact-secrets.sh before emit_kv ERROR. ```
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] architecture: scripts/design-log-publish.sh:720-732
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Worktree removed before merge_rc check on merge failure Harder local recovery after merge fail; remote PR remains Pre-existing; optional defer worktree remove until merge outcome known
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_33: [OUT_OF_SCOPE] correctness: .claude/skills/audit-runs/scripts/audit-close-priors.sh:112-113
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] CLOSE_FAILED omits captured gh stderr Operator sees generic close failed without API detail Read close_fail_file before rm into REASON
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/create-pr.sh:178-184
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Bare gh pr list in create conflict recovery. Transient list failure after wrapped create can block existing-PR recovery. Wrap list or document single-shot recovery.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_8: [OUT_OF_SCOPE] code-quality: scripts/git-push.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Parallel push-retry abstractions coexist with lib-net. Inconsistent retry behavior across implement scripts. Consolidate or document when to use each wrapper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

