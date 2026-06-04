### FINDING_10: `CONE_RECONCILED` can be set from a pre-install banner before upgrade success
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 treats the reconcile intent fragment as success even though `upgrade-larch.sh` prints it before uninstall/reinstall/verification, so a failed repair can still trigger Step 8 restart guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt: Address the concern above.


### FINDING_11: Missing retention coverage for empty configured sparse-checkout lists
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no case for an empty sparse-checkout configuration, so hook silence and upgrade reconcile behavior can diverge without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_18: `LARCH_CONE_RECONCILED=true` is gated too tightly on stable-version verification
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt
- **Severity**: latent
- **Concern**: Successful same-version cone repair may not emit the machine restart signal when later version verification fails or `LATEST_STABLE` is unavailable, leaving release parsing to fragile substring inference or causing missed restarts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt, dyn-harness-isolation-output.txt, dyn-sparse-contract-output.txt: Address the concern above.


### FINDING_2: Cone-reconcile coverage does not exercise real `upgrade-larch.sh` on a drifted marketplace
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-isolation-output.txt
- **Severity**: important
- **Concern**: Tests rely on helper/stub/string-fragment checks instead of a hermetic run of production `upgrade-larch.sh` against a drifted sparse checkout, so regressions in early-exit bypass, reconcile wiring, or `LARCH_CONE_RECONCILED=true` emission can pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-harness-isolation-output.txt: Address the concern above.


### FINDING_23: Skill-tool fallback can reconcile without updating `release-step7.env`
- **Reviewer(s)**: dyn-release-state-output.txt
- **Severity**: important
- **Concern**: When `RESOLVED_ROOT` is empty, Step 7 writes false state before the prose fallback; if the fallback repairs the cone, Step 8 may skip the required restart because no captured output rewrites the env file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-state-output.txt: Address the concern above.


### FINDING_30: Recovery command display breaks when `$HOME` contains a single quote
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `$marketplace_clone` is shown inside single quotes in an advisory `rm -rf` command; a literal quote in `HOME` produces a broken copy-paste command.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_5: Root-resolution tests miss metadata-vs-`CURRENT_VERSION` mismatch cases
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-harness-isolation-output.txt
- **Severity**: important
- **Concern**: The harness does not pin cases where installed metadata and prepare `CURRENT_VERSION` disagree while multiple cache directories exist, so release root selection can silently fall back to the wrong cache path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-state-output.txt, dyn-harness-isolation-output.txt: Address the concern above.


### FINDING_6: Repeatedly sourcing `upgrade-larch.sh` can leak ERR traps into the harness
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Sourcing `upgrade-larch.sh` repeatedly in the parent harness can re-register recovery traps, so unrelated harness errors may invoke production recovery behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: `NEW_VERSION_INSTALLED` detection is tied to brittle pre-success output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt
- **Severity**: important
- **Concern**: Release Step 7 infers `NEW_VERSION_INSTALLED` from upgrade banner text instead of successful verification or a machine signal, causing both missed restarts and false-positive restarts depending on output shape and failure timing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-upgrade-flow-output.txt, dyn-release-state-output.txt: Address the concern above.


