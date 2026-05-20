### FINDING_1: **Important** `correctness` `scripts/collect-agent-results.sh:135-154`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/collect-agent-results.sh:135-154`      `preserve_and_publish_ns_retry` publishes the validated retry with `cp "$retry_output" "$orig_output"` directly over the canonical reviewer file. If that copy fails after opening/truncating the destination, for example due to ENOSPC or an interrupted write, the collector leaves `RESULTS[IDX]` as `STATUS=NOT_SUBSTANTIVE` but the original first-pass file may now contain partial retry content instead of the validated first-pass body. Publish through a temp file in the same directory and `mv` it over `orig_output` only after the copy succeeds; keep the `*-ns-retry.txt` artifact separately if retaining it is required.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: scripts/collect-agent-results.sh:149-151
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Success breadcrumb names only the retry filename Operators may think canonical OK prose lives on -ns-retry.txt while REVIEWER_FILE points at orig. Breadcrumb should name orig publish path or both artifacts.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/collect-agent-results.sh:150
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Breadcrumb wording for successful publish Operators may think the merged canonical prose is only under the ns-retry basename when it was also copied onto ORIG_OUTPUT. Mention ORIG_OUTPUT (or say published to canonical path) alongside the retry artifact name.
- **Suggested revision**: Address the concern above.


### FINDING_12: code-quality: scripts/test-collect-agent-results.sh:310-312
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] C_NS_STRUCTURED comment still describes emitting retry sidecar path. Misleading for maintainers updating structured NS assertions. Rewrite comment to match orig-path publish and first-pass sidecar behavior.
- **Suggested revision**: Address the concern above.


### FINDING_14: correctness: scripts/collect-agent-results.sh:1272-1278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] structured NS-retry publishes prose before verifying structured sidecar exists If the post-validate file check fails after preserve_and_publish_ns_retry, ORIG_OUTPUT already holds retry prose and -first-pass.txt may exist while RESULTS stays NOT_SUBSTANTIVE Validate sidecar before publishing or restore ORIG_OUTPUT from the first-pass sidecar when aborting
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: scripts/collect-agent-results.sh:141-155
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] publish cp can fail after first-pass sidecar exists On I/O/disk-full during retry-to-orig cp, STATUS stays NOT_SUBSTANTIVE but -first-pass.txt remains; tooling assuming sidecar implies successful publish pairs wrong with STATUS. Remove first-pass sidecar on publish failure or document and test partial-failure invariant.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/collect-agent-results.sh:141-155
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] If preserving the first pass succeeds but publishing the retry body onto ORIG_OUTPUT fails, the helper returns without deleting the new -first-pass sidecar while leaving STATUS=NOT_SUBSTANTIVE. A tmpdir can accumulate a misleading *-first-pass.txt that does not correspond to a successful NS-retry publish, confusing debugging or hygiene scans. On publish failure remove the first-pass sidecar or add a paired cleanup note in the contract.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/collect-agent-results.sh:141-155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] second cp in preserve_and_publish_ns_retry can fail after first-pass sidecar exists Disk full or I/O error after copying first pass leaves orphan -first-pass.txt and may corrupt orig while STATUS stays NOT_SUBSTANTIVE Use temp file plus atomic mv into orig_output or explicit rollback on publish failure
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/collect-agent-results.sh:149-155
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] In-place cp publishes retry body onto canonical ORIG_OUTPUT ENOSPC or interrupted cp can truncate ORIG_OUTPUT while the collector leaves RESULTS at NOT_SUBSTANTIVE, yielding plausible but wrong primary transcripts for consumers that read only ORIG_OUTPUT. Write to a temp in the same directory and atomically mv into ORIG_OUTPUT, or equivalent atomic replace.
- **Suggested revision**: Address the concern above.


### FINDING_21: risk-integration: scripts/collect-agent-results.sh:1272-1279
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] preserve_and_publish_ns_retry runs before structured sidecar presence check If STRUCTURED_SIDECAR disappears or the post-validate file check fails after prose publish, stdout still reports NOT_SUBSTANTIVE while disk may already show merged retry prose at ORIG_OUTPUT plus a first-pass sidecar. Validate or assert STRUCTURED_SIDECAR before mutating ORIG_OUTPUT, or restore ORIG_OUTPUT when abandoning the branch.
- **Suggested revision**: Address the concern above.


### FINDING_24: risk-integration: scripts/collect-agent-results.sh:75-96
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] preserve_and_publish_ns_retry failure paths (first-pass copy or retry publish) are untested. Ordering or return-code bugs could leave inconsistent files or wrong STATUS without detection. Add a controlled failure test (read-only orig, tempfs full, or stubbed cp).
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: scripts/test-collect-agent-results.sh:463-477
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] C_NS_FP_RETRY_FAIL only asserts absence of first-pass sidecar without proving NS retry ran. If NS retry stops being launched or waited on but first-pass output stays NOT_SUBSTANTIVE, the test still passes and misses the regression. Assert NS retry sentinel/output exists with non-zero exit or capture stdout and assert NOT_SUBSTANTIVE plus a retry-specific artifact.
- **Suggested revision**: Address the concern above.


### FINDING_3: **[correctness]** [`scripts/collect-agent-results.sh:149-151`](scripts/collect-agent-results.sh): On success, the breadcrumb text says retry content is “retained” at `$(basename "$retry_output")` (the `*-ns-retry.txt` basename), while the published transcript the result row points at is `$orig_output` after `cp`. That wording can misread logs when triaging paths. **Suggested fix:** Mention `$(basename "$orig_output")` (published path) and optionally note the retry artifact path separately, or drop the second breadcrumb if it adds noise.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/collect-agent-results.sh:149-151`](scripts/collect-agent-results.sh): On success, the breadcrumb text says retry content is “retained” at `$(basename "$retry_output")` (the `*-ns-retry.txt` basename), while the published transcript the result row points at is `$orig_output` after `cp`. That wording can misread logs when triaging paths. **Suggested fix:** Mention `$(basename "$orig_output")` (published path) and optionally note the retry artifact path separately, or drop the second breadcrumb if it adds noise.
- **Suggested revision**: Address the concern above.


### FINDING_9: code-quality: scripts/collect-agent-results.sh:149-150
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] breadcrumb implies canonical retry body path is still the -ns-retry file Operators tail the wrong file when triaging from breadcrumbs alone Reword to state publish into basename(orig_output) and optional note that -ns-retry.txt is retained
- **Suggested revision**: Address the concern above.


