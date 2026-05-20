### FINDING_1: **Important** `correctness` `scripts/collect-agent-results.sh:135-154`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/collect-agent-results.sh:135-154`      `preserve_and_publish_ns_retry` publishes the validated retry with `cp "$retry_output" "$orig_output"` directly over the canonical reviewer file. If that copy fails after opening/truncating the destination, for example due to ENOSPC or an interrupted write, the collector leaves `RESULTS[IDX]` as `STATUS=NOT_SUBSTANTIVE` but the original first-pass file may now contain partial retry content instead of the validated first-pass body. Publish through a temp file in the same directory and `mv` it over `orig_output` only after the copy succeeds; keep the `*-ns-retry.txt` artifact separately if retaining it is required.
- **Suggested revision**: Address the concern above.

### FINDING_2: **[correctness]** [`scripts/collect-agent-results.sh:142-143`](scripts/collect-agent-results.sh) and [`scripts/collect-agent-results.sh:149-151`](scripts/collect-agent-results.sh): Appending `>&2` to `emit_breadcrumb` does **not** route breadcrumbs to the quiet library’s user-visible stderr (FD 4 via `larch_err`). After `larch_quiet_init`, both stdout and stderr are redirected to the same quiet log (`exec >>"$log_file" 2>&1` in [`scripts/lib-quiet.sh:70-75`](scripts/lib-quiet.sh)), so `>&2` is effectively redundant for the default branch. When `LARCH_QUIET_BREADCRUMBS` is set, `emit_breadcrumb` calls `emit`, which writes with `printf ... >&3` ([`scripts/lib-quiet.sh:97-102`](scripts/lib-quiet.sh), [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh)), so the outer `>&2` does **not** redirect that output at all (no-op for FD 3). This neither achieves “real stderr for orchestrator visibility” nor matches the voter pattern’s stated reason in [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh) (there, `>&2` avoids polluting a **captured** stdout from the surrounding function). **Suggested fix:** Remove the misleading `>&2` unless this function is ever called in a context where its stdout is captured; if operator-visible diagnostics are required, use `larch_err` / `larch_errf` (FD 4) instead of relying on `emit_breadcrumb >&2`.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/collect-agent-results.sh:142-143`](scripts/collect-agent-results.sh) and [`scripts/collect-agent-results.sh:149-151`](scripts/collect-agent-results.sh): Appending `>&2` to `emit_breadcrumb` does **not** route breadcrumbs to the quiet library’s user-visible stderr (FD 4 via `larch_err`). After `larch_quiet_init`, both stdout and stderr are redirected to the same quiet log (`exec >>"$log_file" 2>&1` in [`scripts/lib-quiet.sh:70-75`](scripts/lib-quiet.sh)), so `>&2` is effectively redundant for the default branch. When `LARCH_QUIET_BREADCRUMBS` is set, `emit_breadcrumb` calls `emit`, which writes with `printf ... >&3` ([`scripts/lib-quiet.sh:97-102`](scripts/lib-quiet.sh), [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh)), so the outer `>&2` does **not** redirect that output at all (no-op for FD 3). This neither achieves “real stderr for orchestrator visibility” nor matches the voter pattern’s stated reason in [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh) (there, `>&2` avoids polluting a **captured** stdout from the surrounding function). **Suggested fix:** Remove the misleading `>&2` unless this function is ever called in a context where its stdout is captured; if operator-visible diagnostics are required, use `larch_err` / `larch_errf` (FD 4) instead of relying on `emit_breadcrumb >&2`.
- **Suggested revision**: Address the concern above.

### FINDING_3: **[correctness]** [`scripts/collect-agent-results.sh:149-151`](scripts/collect-agent-results.sh): On success, the breadcrumb text says retry content is “retained” at `$(basename "$retry_output")` (the `*-ns-retry.txt` basename), while the published transcript the result row points at is `$orig_output` after `cp`. That wording can misread logs when triaging paths. **Suggested fix:** Mention `$(basename "$orig_output")` (published path) and optionally note the retry artifact path separately, or drop the second breadcrumb if it adds noise.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/collect-agent-results.sh:149-151`](scripts/collect-agent-results.sh): On success, the breadcrumb text says retry content is “retained” at `$(basename "$retry_output")` (the `*-ns-retry.txt` basename), while the published transcript the result row points at is `$orig_output` after `cp`. That wording can misread logs when triaging paths. **Suggested fix:** Mention `$(basename "$orig_output")` (published path) and optionally note the retry artifact path separately, or drop the second breadcrumb if it adds noise.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] **[correctness]** [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh): The `{ emit_breadcrumb ...; } >&2` idiom and its interaction with `emit` / FD 3 is pre-existing; the new collector code mirrors the surface syntax without the same “stdout must stay parse-clean” constraint.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/dispatch-code-voters.sh:263-265`](scripts/dispatch-code-voters.sh): The `{ emit_breadcrumb ...; } >&2` idiom and its interaction with `emit` / FD 3 is pre-existing; the new collector code mirrors the surface syntax without the same “stdout must stay parse-clean” constraint.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] **[correctness]** [`scripts/lib-quiet.md:19-21`](scripts/lib-quiet.md) vs [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh): Documentation describes breadcrumbs as going to the “quiet log”; the default implementation writes via ordinary stdout (which is the quiet log only after init), not via FD 3. This predates the branch and is not introduced by the NS-retry change.
- **Reviewer**: dyn-bash-fd-routing-output.txt
- **Concern**: - **[correctness]** [`scripts/lib-quiet.md:19-21`](scripts/lib-quiet.md) vs [`scripts/lib-quiet.sh:114-119`](scripts/lib-quiet.sh): Documentation describes breadcrumbs as going to the “quiet log”; the default implementation writes via ordinary stdout (which is the quiet log only after init), not via FD 3. This predates the branch and is not introduced by the NS-retry change.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/*/collector-results.env
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] historical logs still reference REVIEWER_FILE on -ns-retry.txt paths Manual greps of old log shape do not reflect new REVIEWER_FILE=orig behavior until new runs are committed None in this diff; update playbooks if operators rely on the old suffix
- **Suggested revision**: Address the concern above.

### FINDING_7: code-quality: scripts/collect-agent-results.md:24-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Section 3.7 retry outcome is one overloaded sentence Harder to diff and spot contract drift on future edits Split into short bullets per phase and failure mode
- **Suggested revision**: Address the concern above.

### FINDING_8: code-quality: scripts/collect-agent-results.sh:1280-1283
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Loop temps _ns_sidecar_ext/_ns_new_sidecar are not local Future loop edits could read stale values across iterations. Use local or unique names per iteration.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/collect-agent-results.sh:149-150
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] breadcrumb implies canonical retry body path is still the -ns-retry file Operators tail the wrong file when triaging from breadcrumbs alone Reword to state publish into basename(orig_output) and optional note that -ns-retry.txt is retained
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

### FINDING_13: code-quality: scripts/test-collect-agent-results.sh:341-364
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] C_NSR does not assert -first-pass.txt for the original substantive NS-retry case Regression in substantive-only preserve could be missed if C_NS_FP_SUCCESS were removed or narrowed Add assert_file or grep on OUT_NSR first-pass sidecar like C_NS_FP_SUCCESS
- **Suggested revision**: Address the concern above.

### FINDING_14: correctness: scripts/collect-agent-results.sh:1272-1278
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] structured NS-retry publishes prose before verifying structured sidecar exists If the post-validate file check fails after preserve_and_publish_ns_retry, ORIG_OUTPUT already holds retry prose and -first-pass.txt may exist while RESULTS stays NOT_SUBSTANTIVE Validate sidecar before publishing or restore ORIG_OUTPUT from the first-pass sidecar when aborting
- **Suggested revision**: Address the concern above.

### FINDING_15: correctness: scripts/collect-agent-results.sh:135-155 scripts/collect-agent-results.sh:1280-1286
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Retry publish and structured sidecar relocation use cp, not the plan's mv; -ns-retry.txt remains alongside the published orig path. Callers or operators expecting mv semantics (retry file removed or renamed away after success) or a single post-success transcript file see duplicate retry content and diverge from the written cp+mv contract. Implement mv (and structured mv) as in the plan, or update the authoritative plan/feature text to the cp+retain-retry-artifact behavior.
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

### FINDING_20: correctness: scripts/test-collect-agent-results.sh (C_NSR block)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] C_NSR does not assert -first-pass.txt exists after substantive NS-retry success. A regression that breaks first-pass preservation only for paths exercised by C_NSR might slip until another case fails. Add a first-pass sidecar assertion to C_NSR or document that C_NS_FP_SUCCESS is the canonical assertion for that behavior.
- **Suggested revision**: Address the concern above.

### FINDING_21: risk-integration: scripts/collect-agent-results.sh:1272-1279
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] preserve_and_publish_ns_retry runs before structured sidecar presence check If STRUCTURED_SIDECAR disappears or the post-validate file check fails after prose publish, stdout still reports NOT_SUBSTANTIVE while disk may already show merged retry prose at ORIG_OUTPUT plus a first-pass sidecar. Validate or assert STRUCTURED_SIDECAR before mutating ORIG_OUTPUT, or restore ORIG_OUTPUT when abandoning the branch.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/collect-agent-results.sh:1272-1287
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No test covers structured sidecar publish failure after successful prose publish. A bad chmod/IO edge could break STRUCTURED_SIDECAR path wiring without failing CI. Add a harness that forces sidecar cp failure and asserts RESULTS plus stderr, or a unit-level fixture.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/collect-agent-results.sh:1282-1286;scripts/collect-agent-results.md:19
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Structured sidecar uses cp vs planned mv; doc updated Extra duplicate structured artifact at retry path; behavior matches written doc, not original plan snippet. Accept as-is or switch to mv if duplicate files must be avoided.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/collect-agent-results.sh:75-96
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] preserve_and_publish_ns_retry failure paths (first-pass copy or retry publish) are untested. Ordering or return-code bugs could leave inconsistent files or wrong STATUS without detection. Add a controlled failure test (read-only orig, tempfs full, or stubbed cp).
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/larch-log.sh:92;scripts/collect-agent-results.sh:135-156
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] NS-retry first-pass transcripts are explicitly allow-listed and copied before publishing retry text onto the original output path, enlarging what specialist prose can be committed in published run logs. A reviewer first pass may still contain secrets or local paths before the stricter retry; those bytes can now be retained under *-output-first-pass.txt whereas previously the lean-log design leaned on excluding the canonical specialist output filename. Verify write-round redaction treats *-output-first-pass.txt like other *-output-*.txt artifacts and document operator expectations in SECURITY.md or run-log docs if needed.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/test-collect-agent-results.sh:463-477
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] C_NS_FP_RETRY_FAIL only asserts absence of first-pass sidecar without proving NS retry ran. If NS retry stops being launched or waited on but first-pass output stays NOT_SUBSTANTIVE, the test still passes and misses the regression. Assert NS retry sentinel/output exists with non-zero exit or capture stdout and assert NOT_SUBSTANTIVE plus a retry-specific artifact.
- **Suggested revision**: Address the concern above.

### FINDING_27: security: scripts/collect-agent-results.sh:145-154
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] larch_err messages include full filesystem paths for first-pass and orig outputs. Shared stderr logs may leak absolute workspace or TMPDIR paths to downstream consumers. Prefer basename-only diagnostics or path redaction consistent with other collector errors.
- **Suggested revision**: Address the concern above.

