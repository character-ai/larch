### FINDING_1: Duplicate CI checks retry handling
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/merge-pr.sh:141-201` duplicates `with_transient_retry` failure handling for JSON and text `gh pr checks` paths, increasing the chance future edits fix one path but leave the other wrong.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Redundant create-pr retry branches
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/create-pr.sh:203-213` has identical then/else branches assigning `pr_json=$_WTR_OUT`, obscuring the intended wrapper contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: lib-net docs not updated with signature changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/lib-net.md` was not updated after `is_transient_net_signature` changed, so contributors relying on the documented signature list may miss the new DNS/reset signatures and hosted-name exclusion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Merge-pr S4 does not guard skipped text fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/test-merge-pr.sh` does not explicitly prove that text-format `gh pr checks` is skipped after JSON checks exhaust transient retries. A regression could re-enable the text fallback and still pass parts of the current harness, potentially allowing misleading check output to affect merge readiness.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Remaining bare network calls
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Several pre-existing `gh`/`git` call sites outside the changed rebase-push/create-pr/merge-pr paths still lack `with_transient_retry`, including `create-pr.sh` PR view fallbacks and other scripts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] refresh_pr_info temp-file churn
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/merge-pr.sh:113-125` repeatedly creates and removes temp files inside the UNKNOWN recovery loop, adding unnecessary churn on slow UNKNOWN paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] no such host matcher overmatches
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-net.sh:10-15` uses a bare substring match for `no such host`, so unrelated messages such as `no such hostname` may be classified as transient network failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] Text fallback lacks transient-once test
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/merge-pr.sh:181-194` has no regression case proving the text-only fallback path recovers after a single transient failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] PR URL regex fallback trusts CLI text
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/create-pr.sh:218-221` still falls back to extracting a PR URL from `gh pr create` stderr/stdout with a regex when list recovery yields no number or URL, trusting CLI text as authoritative PR identity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] SLEEP_SCRIPT_DIR can redirect retry sleep executable
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/lib-net.sh:57-58` executes `"${SLEEP_SCRIPT_DIR:-$_lib_net_dir}/sleep-seconds.sh"` when executable, so a poisoned operator environment could redirect backoff execution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
