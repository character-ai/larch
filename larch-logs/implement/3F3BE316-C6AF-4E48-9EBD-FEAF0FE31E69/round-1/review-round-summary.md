# Review Round 1

- Mode: `diff`
- 10 accepted, 7 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: forked runs can auto-file larch issues instead of consumer action output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 18a issue filing is gated only on dev-clone detection and does not honor forked target state, so `/implement --forked` from a larch checkout can file a public larch plugin issue instead of printing the consumer-facing action-required path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_14: same-cause-repeat can dispatch ship-pr for checks stalls
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Repeated checks stalls at steps 3 or 6 can be classified as `same-cause-repeat` and receive a `step8-shippr` hint, violating the expected checks contract-failure `none` hint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: terminal path may not seed disk stall tracking
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `ship-pr-state.sh` is missing, the terminal path can leave `STALL_TRACKING=true` only in memory, causing later branches to miss issue state and skip finalize-state restoration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_16: classify can prefer disk false over in-memory true
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When the gate fires from in-memory stall tracking but disk `STALL_TRACKING=false`, classification can yield unrecoverable/none and leave disk false, leading teardown down the wrong branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_19: secret redaction harness omits ghp token coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harness case 16 does not assert redaction of a `ghp_` token, so a plan-required secret-shaped input could leak to public bug bodies without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_2: symbolic or terminal stall steps can wrongly redispatch ship-pr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `resume_hint_for` only handles exact numeric `STALL_STEP` values, so symbolic or terminal ship-pr steps such as `12d` can be classified as recoverable transient infrastructure and re-invoke `ship-pr.sh` despite failure evidence saying not to.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: invalid failure-detail-log exits instead of continuing without log
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `classify` exits with status 1 on an invalid `failure-detail-log` path, contrary to the plan expectation to continue without that log or clearly document stricter pre-validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: terminal failure comments may target the wrong issue
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The terminal failure path does not load the issue number from `stall-recovery-issue.env`, so a recovery-created issue may not receive the exhaustion comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: deny-list harness does not cover evidence inputs
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Deny-list case 13 does not inject sentinels through `ship-pr-state` or `failure-detail-log`, so leakage from evidence strings into public outputs could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.


### FINDING_9: allowlist TSV is not the runtime source of composition truth
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Public body composition uses hardcoded `safe_*` helpers rather than being driven by the allowlist TSV, so lint can pass while runtime output drifts from allowlisted transforms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


