### FINDING_1: forked runs can auto-file larch issues instead of consumer action output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Step 18a issue filing is gated only on dev-clone detection and does not honor forked target state, so `/implement --forked` from a larch checkout can file a public larch plugin issue instead of printing the consumer-facing action-required path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: symbolic or terminal stall steps can wrongly redispatch ship-pr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `resume_hint_for` only handles exact numeric `STALL_STEP` values, so symbolic or terminal ship-pr steps such as `12d` can be classified as recoverable transient infrastructure and re-invoke `ship-pr.sh` despite failure evidence saying not to.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_3: terminal failure comments may target the wrong issue
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The terminal failure path does not load the issue number from `stall-recovery-issue.env`, so a recovery-created issue may not receive the exhaustion comment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_4: transient-infra classifier matches bare network text too broadly
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The transient infrastructure classifier matches the bare substring `network`, which can misclassify unrelated failure text and waste retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: atomic clear harness does not verify read-back behavior
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Harness case 19 does not exercise the `read-session-env-key` read-back assertions from the documented atomic clear sequence, so ordering regressions could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] missing ship-pr-state forces unrecoverable classification
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: When `ship-pr-state` is missing, classification always yields unrecoverable even if recoverable failure-detail evidence exists, but the source marked this as plan-intentional or product-decision territory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: deny-list harness does not cover evidence inputs
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Deny-list case 13 does not inject sentinels through `ship-pr-state` or `failure-detail-log`, so leakage from evidence strings into public outputs could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: failure-detail-log validation has a TOCTOU race
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `failure-detail-log` is validated and then read via a separate path open, allowing same-UID symlink replacement between validation and `cat`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: allowlist TSV is not the runtime source of composition truth
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Public body composition uses hardcoded `safe_*` helpers rather than being driven by the allowlist TSV, so lint can pass while runtime output drifts from allowlisted transforms.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: dev-clone detection can false-positive into public larch issue filing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Dev-clone detection relies only on `skills/implement/SKILL.md`, so any checkout with that marker can trigger `/larch:issue` even when the run is not the actual larch source repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] redactor does not cover all opaque tokens or PII
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Public stall bodies may still expose secrets outside existing gitleaks/redact coverage, but the source identifies this as pre-existing and already documented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] classification env stores raw session values
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `classification.env` stores raw `BAIL_REASON`, `STALL_STEP`, and `PHASE` under the same-UID session trust model, but the source marks this as pre-existing and not public allowlist exposure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Step 18a no-stall gate ignores session-env stall tracking
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Step 18a can skip recovery when memory and ship-pr disk state are false or absent but session-env `STALL_TRACKING=true`, causing false “no stall detected” handling and wrong teardown.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

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

### FINDING_17: unrecoverable early bails can still file first-detection issues
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: First-detection issue filing can run for terminal or unrecoverable early bails without `ship-pr-state`, producing noisy larch issues without a recovery dispatch path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] early bail may lack finalize-state for teardown
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Early bail before `ship-pr-state` exists may lack `finalize-state` for teardown; the source marks this as pre-existing bootstrap/teardown seeding work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: secret redaction harness omits ghp token coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harness case 16 does not assert redaction of a `ghp_` token, so a plan-required secret-shaped input could leak to public bug bodies without failing CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: invalid failure-detail-log exits instead of continuing without log
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `classify` exits with status 1 on an invalid `failure-detail-log` path, contrary to the plan expectation to continue without that log or clearly document stricter pre-validation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: harness contract documentation is too thin
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The sibling harness contract documentation under-describes the 21 cases, making it easier for contributors to drop deny-list or public-surface coverage without doc review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] title-prefix lifecycle anchor is stale
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The title-prefix lifecycle reference lacks a target section, so operators following it may not find the intended Step 18a context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] manual integration acceptance is not code-provable
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Acceptance criterion 10 depends on manual dry-run or live filing verification that cannot be proven from the code diff alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
