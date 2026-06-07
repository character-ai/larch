### OOS_6: [OUT_OF_SCOPE] Revert helper failure silently continues with the WORSE plan
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-workflow-contract-output.txt
- **Severity**: important
- **Concern**: If `snapshot-plan-round.sh revert-round` fails after the operator chooses Revert, the flow can continue with the WORSE applied plan, contradicting the Revert contract and operator intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-workflow-contract-output.txt: Address the concern above.


### OOS_7: [OUT_OF_SCOPE] Structure tests do not pin Step 0-pre KV count
- **Reviewer(s)**: dyn-state-io-output.txt
- **Severity**: latent
- **Concern**: Structure tests pin several `approve_requested` strings but not the Step 0-pre eight-KV success-count check; reviewer marked this as a pre-existing harness gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-state-io-output.txt: Address the concern above.


### OOS_8: [OUT_OF_SCOPE] `PYTHON` override and bare `python3` probes remain split
- **Reviewer(s)**: dyn-ci-pycompat-output.txt
- **Severity**: latent
- **Concern**: Make targets honor overridable `PYTHON`, while implement/bootstrap and ship paths probe bare `python3`; reviewer marked this split as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pycompat-output.txt: Address the concern above.


### OOS_9: [OUT_OF_SCOPE] README omits Python floor
- **Reviewer(s)**: dyn-ci-pycompat-output.txt
- **Severity**: nit
- **Concern**: `README.md` still does not state the Python 3.11 floor or bash rollback knob, while installation docs do; reviewer marked this as a pre-existing doc-surface gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pycompat-output.txt: Address the concern above.


### OOS_10: [OUT_OF_SCOPE] test-design-structure comment is stale
- **Reviewer(s)**: dyn-workflow-contract-output.txt
- **Severity**: nit
- **Concern**: A structure-test comment still says “always-explicit Gate B” even though the harness now pins auto-apply defaults.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contract-output.txt: Address the concern above.


### OOS_11: [OUT_OF_SCOPE] plan-review has a stale Gate B apply-point line
- **Reviewer(s)**: dyn-workflow-contract-output.txt
- **Severity**: nit
- **Concern**: `plan-review.md` still says Gate B is the sole apply point without the auto-apply / `--approve` split, though later sections were updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-workflow-contract-output.txt: Address the concern above.

### OOS_12: [OUT_OF_SCOPE] validate-plan defaults repo root to plugin tree
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-bash-flow-output.txt, dyn-vendor-fix-output.txt
- **Severity**: latent
- **Concern**: `validate-plan.sh` defaults `--repo-root` to the plugin tree rather than the consumer repo, which can weaken Tier 3 command resolution; reviewers marked this as broader or pre-existing, though auto-fix makes it more visible.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-bash-flow-output.txt, dyn-vendor-fix-output.txt: Address the concern above.


### OOS_13: [OUT_OF_SCOPE] Python 3.11 baseline changes are unrelated to this PR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-workflow-contract-output.txt
- **Severity**: latent
- **Concern**: Python/CI baseline lowering from 3.12 to 3.11 appears unrelated to the `/design` Gate B auto-apply work and may increase review or merge risk if kept in the same PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-workflow-contract-output.txt: Address the concern above.


