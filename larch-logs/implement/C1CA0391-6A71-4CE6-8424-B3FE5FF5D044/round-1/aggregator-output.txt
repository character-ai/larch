### FINDING_1: [OUT_OF_SCOPE] Redundant terminal-status guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The inner `OK || cap_hit` check duplicates the enclosing terminal-status branch around the ledger append, adding maintenance drift risk without changing behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Unused first-run ledger variable
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The Bug A test stores `first_run_group_ledger` only for a non-empty check, creating reader noise and implying later assertions that do not exist.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_3: cap_hit grouped test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The grouped `cap_hit` regression test checks counters, sidecars, and ledger rows but does not assert `DISPATCH_OK=true`, so some dispatch failure shapes could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] dispatch-with-waterfall docs stale after ledger changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The documentation still describes OK-only ledger appends and omits invocation-time ledger truncation, which can mislead retry/debug readers about `cap_hit` dedup and stale-ledger behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] Concurrent dispatches can race on shared ledger truncation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Parallel grouped dispatchers using the same slots-file directory can truncate or append to each other's shared ledger files, matching the existing shared-file race class.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Codex background launch can close stdin early
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Codex launched `run_in_background` without a TTY may close stdin, causing `/implement` to commit before review fixups when monitoring exits early.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] cap_hit bypasses substantive result-pattern validation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `cap_hit` remains outside `--require-result-pattern` validation, and ledger dedup can propagate a minimal `STATUS=cap_hit` placeholder to grouped peers without substantive review content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Bug A rerun test omits DISPATCH_OK assertion
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The second invocation in the Bug A rerun block does not assert `DISPATCH_OK=true`, making settlement failures harder to diagnose.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Phase-2 grouped cap_hit path lacks direct regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The tests cover grouped `cap_hit` dedup for the current path but do not directly exercise a phase-2 grouped `cap_hit` ledger write, leaving that branch vulnerable to regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_10: Bug A test lacks direct ledger-truncation assertion
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The two-run Bug A regression relies on counters and output content but does not directly assert stale ledger rows were removed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] reuse_slot_result cp failure aborts dispatcher
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A stale ledger row pointing at a deleted source file can cause `cp` in `reuse_slot_result` to abort under `set -e` instead of falling back to relaunch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
