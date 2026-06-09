### OOS_1: [OUT_OF_SCOPE] B1 cutover, deletion, and manifest work are incomplete
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt
- **Severity**: important
- **Concern**: The branch still has retained bash callers/scripts and lacks the planned cutover/deletion/manifest updates, so Python replacements are not fully exercised and acceptance criteria remain unmet.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.
  - From dyn-contract-parity-output.txt: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] Phantom tests do not assert retained-script argv contracts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Current phantom tests stub subprocess output without checking the actual helper targets or append-execution-issue arguments, so wiring regressions can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### OOS_3: [OUT_OF_SCOPE] `check-main-sync` exit paths lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The Python `check-main-sync` behavior for exit 0/1/2 is not covered by pytest before bash retirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### OOS_4: [OUT_OF_SCOPE] Additional PR/push CLI parity coverage gaps remain
- **Reviewer(s)**: dyn-contract-parity-output.txt
- **Severity**: latent
- **Concern**: `python/test_pr_cli.py` lacks coverage for create-branch/create-PR flows, and `python/test_push_cli.py` does not fully exercise the checkpoint-probe envelope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-parity-output.txt: Address the concern above.


### OOS_5: [OUT_OF_SCOPE] Migration lint tests do not cover ship-pr label carve-out sufficiently
- **Reviewer(s)**: dyn-migration-gate-output.txt
- **Severity**: nit
- **Concern**: Existing tests cover full-line comments but not `record_failure` label strings or live `$SCRIPT_DIR/...` invocations, so the ship-pr carve-out can regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-gate-output.txt: Address the concern above.


