### FINDING_1: code-quality: scripts/test-ship-pr.sh:6042-6049
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] OOS errexit probes export CLAUDE_PLUGIN_ROOT after source so PLUGIN_ROOT is frozen to REPO_ROOT and the no-op gate stub under tmp/plugin is never used. Probes exercise the real oos-disposition-gate.sh and repo git context; errexit assertions can pass while violating plan hermeticity and may flake if the real gate behavior changes. Export CLAUDE_PLUGIN_ROOT (or set PLUGIN_ROOT) before sourcing ship-pr.sh so gate_script resolves to the stub.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Errexit invariant documents set +uo pipefail but ship-pr.sh uses set -uo pipefail without -e. Maintainers may misread the script baseline and reintroduce wrong set options when adding gate blocks. Say set -uo pipefail and note errexit is intentionally off (no set -e).
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/ship-pr.sh:1554-1572
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] run_pr_prep_phase duplicates save/restore around a helper that already manages errexit. Extra nesting and six lines per call site without added safety once the helper is fixed. Remove outer set +e wrappers and call the helper directly (plan allowed this simplification).
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/test-ship-pr.sh:6015-6033
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] prprep-first and prprep-recovery probes embed copy-pasted wrapper snippets instead of calling production entry points. Production wrapper edits may not update tests; probes could false-pass on stale patterns. Call run_pr_prep_phase with run_recovery_waterfall stubbed or share a small with_saved_errexit helper.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/ship-pr.sh:1004,139
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] _had_errexit in OOS paths vs had_errexit in run_lint_fix_loop_capture for the same idiom. Minor inconsistency when searching or extending errexit patterns. Align variable naming with run_lint_fix_loop_capture.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-ship-pr.sh:470-472
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Section list comment omits errexit section. Developers may not know errexit runs in full test-ship-pr invocations. Add errexit to the listed sections when editing that header.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:362-365
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] die_usage exits 2 separate from orchestrator CI table. Unrelated exit 2 can still confuse incident triage. Pre-existing; address in a separate exit-code hygiene change if desired.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] New errexit section says ship-pr runs with set +uo pipefail; script actually uses set -uo pipefail (u and pipefail on, errexit off). Maintainer misreads baseline shell options or copies wrong set line when editing ship-pr.sh. State set -uo pipefail with errexit off (set +e), matching scripts/ship-pr.sh:4-7.
- **Suggested revision**: Address the concern above.

### FINDING_9: code-quality: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Errexit invariant documents set +uo pipefail instead of set -uo pipefail. Maintainers may believe nounset/pipefail are disabled when debugging errexit leaks. Change +uo to -uo to match scripts/ship-pr.sh:4.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: scripts/test-ship-pr.sh:5967-6107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No end-to-end test that confirmed local harness failure yields documented exit 3/4 not raw harness exit 2. Unit tests pass while a future regression in evaluate-failure routing could still return exit 2 if only translation logic breaks. Add fix-loop-style subject asserting exit 3 with ci-local-unfixable (or stall 4) not exit 2 when harness fails under errexit.
- **Suggested revision**: Address the concern above.

### FINDING_11: risk-integration: scripts/test-ship-pr.sh:6091-6107
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness capture test only covers failing command under set -e. Success path with errexit on is untested; a broken || pattern could wrongly leave _RCC_CMD_RC at 0 after failure or mishandle success. Add sub-case with exit-0 command asserting RCC_CMD_RC=0 and shell survival.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:363-365
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] die_usage still exits 2 outside documented orchestrator table. Unrelated argv errors can still produce undocumented exit 2. Track separately if orchestrator table should cover usage errors.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh:2274-2276
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] _run_per_job_command_once not hardened for errexit. Safe today only while every call stays under if; a future bare call could reintroduce raw exit codes. Harden or add test only if call sites change; pre-existing.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **correctness** `scripts/ship-pr.sh:2274-2277` — `_run_per_job_command_once` still uses the pre-change `cmd > log 2>&1` pattern without `||` hardening; if errexit were ever leaked again, verification could still abort before callers handle failure. **Why out of scope:** unchanged by this branch; plan explicitly left it alone.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **security** `scripts/ship-pr.sh:2180-2221` — Arbitrary command execution would require poisoning `_PJA_ARGV` outside `_per_job_argv()`; callers today only set argv through the whitelist dispatcher. **Why out of scope:** pre-existing design surface, not introduced or widened by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_16: correctness: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] New Errexit invariant section documents baseline as set +uo pipefail instead of set -uo pipefail. A maintainer follows ship-pr.md and believes nounset/pipefail are disabled or errexit is part of the baseline; future edits could re-break CI capture or leak errexit. Replace with set -uo pipefail to match scripts/ship-pr.sh:4.
- **Suggested revision**: Address the concern above.

### FINDING_17: architecture: scripts/test-ship-pr.sh:5967-6110
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Unit probes cover toggles and capture in isolation but not ship-pr.sh exiting with a documented code after a failing local harness in evaluate-failure. A regression in another errexit leak or unhardened helper invocation could restore raw exit 2 while errexit section tests still pass. Add a minimal subprocess test asserting exit 3/4 with BAIL_REASON not raw harness rc 2.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/test-ship-pr.sh:470-472
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Section inventory comment omits errexit though the section runs in default full test-ship-pr. Contributors may not discover errexit tests when debugging section failures. Update the comment to list errexit.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/ship-pr.md:67
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] New Errexit invariant section documents baseline as `set +uo pipefail` but ship-pr.sh uses `set -uo pipefail` at line 4. A maintainer copying the documented set line would disable nounset/pipefail instead of matching production entrypoint behavior. Replace with `set -uo pipefail` and clarify errexit is intentionally off (no `set -e`).
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] correctness: scripts/ship-pr.sh:2872
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] recovery_waterfall invokes OOS gate without outer set +e; non-zero return with leaked errexit could abort before verify_rc=$?. Only matters if errexit leaks again from elsewhere; not introduced by this branch. Optional follow-up: wrap call in same save/restore pattern or rely on helper-only (already sufficient post-fix).
- **Suggested revision**: Address the concern above.

