### FINDING_1: plan-size-trigger path must re-run the hard-gate handler before prompting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Mid-review `LOOP_STATUS=plan-size-trigger` can invoke the hard prompt with stale or missing `check-plan-size` KVs, so Override logging may lack current trigger data and the flow can continue without the full Step 2b.5 contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: mid-review Override can bypass required downstream gate checks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Allowing Override on the `plan-size-trigger` path may short-circuit Gate B / Step 3.5 / Step 3.6 and publish an oversized plan through Step 3b -> 4 -> Gate C without the intended review controls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_3: oversized-plan Override lacks durable downstream traceability
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Override weakens an intentional hard size safety control, but the published plan or `/implement` preflight has no enforceable marker that an oversized plan was accepted as risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_4: Step 2b.5 lacks normative Other handling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If the operator uses AskUserQuestion `Other`, historical behavior could let the agent proceed ad hoc without the required Override audit contract or structured three-option re-prompt.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_5: prior Override or Other response must not be sticky across repeated hard gates
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The plan-size-trigger matrix does not explicitly forbid reusing an earlier Override/Other decision, so a later oversized re-emit may skip the required independent re-prompt and audit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_6: Override audit should record the full check-plan-size capture
- **Reviewer(s)**: dyn-audit-log-output.txt
- **Severity**: important
- **Concern**: The Override audit prose only names selected fields and omits parsed values such as `HARD_TRIGGER_FIRED`, `SOFT_ADVISORY`, and `MECHANICAL_CHURN`, leaving room for inconsistent audit files instead of preserving the full `check-plan-size.sh` KV stdout contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-log-output.txt: Address the concern above.

### FINDING_7: Override audit append can fail silently
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-audit-log-output.txt
- **Severity**: important
- **Concern**: The Override path treats `append-tool-failure.sh` as best-effort, and missing or failed capture writes can leave no durable `Warnings` entry even though the option text promises the override is recorded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-audit-log-output.txt: Address the concern above.

### FINDING_8: plan-review-loop.md sibling docs are missing the soft-advisory three-option breadcrumb
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-sync-output.txt
- **Severity**: important
- **Concern**: `plan-review-loop.sh` was updated for the plan-size soft advisory, but the sibling `.md` does not document the `plan-size-trigger` breadcrumb or the `Split / Override / Cancel` contract required by the plan and script-md sync expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-doc-sync-output.txt: Address the concern above.

### FINDING_9: structure pins do not enforce hard-branch option order or anti-recommendation text
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flow-control-output.txt
- **Severity**: important
- **Concern**: `test-design-structure.sh` only checks for the Override label/invariant, so CI would still pass if the Step 2b.5 hard prompt reordered `Split / Override / Cancel`, dropped an option, or weakened the advised-against language.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-flow-control-output.txt: Address the concern above.

### FINDING_10: structure pins do not protect the Override audit contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-audit-log-output.txt
- **Severity**: latent
- **Concern**: Prompt-only Override logging could be edited away or garbled while tests still pass because the structure test does not pin `operator-override-hard-trigger`, `append-tool-failure.sh`, `Warnings`, redaction, or capture-before-append requirements.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-audit-log-output.txt: Address the concern above.

### FINDING_11: Override routing lacks automated behavior coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no automated test that selecting Override returns to the caller and continues review rather than setting `SUMMARY_OUTCOME`, exiting, or taking the Split path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: flags.md still implies all hard-trigger choices enter Split-path
- **Reviewer(s)**: dyn-flow-control-output.txt
- **Severity**: important
- **Concern**: The `--partition` bullet in `skills/design/references/flags.md` says hard plans show the prompt before entering Split-path automatically, which can mis-route Override as a precursor to decomposition instead of continuing review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flow-control-output.txt: Address the concern above.

### FINDING_13: README hard-gate wording still implies Override enters Split-path
- **Reviewer(s)**: dyn-flow-control-output.txt
- **Severity**: important
- **Concern**: The `/design` README row mentions `Split`/`Override`/`Cancel` but still ends with wording that implies Override leads to the same Split-path rather than continuing plan review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flow-control-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] approval-gates.md omits Override by name
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-doc-sync-output.txt
- **Severity**: nit
- **Concern**: Gate B says no Split or Cancel returns to the caller, which is functionally compatible with Override but may be unclear for agents reading only `approval-gates.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-doc-sync-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] plan-review-loop.md soft-advisory drift was classified by some reviewers as doc-only
- **Reviewer(s)**: dyn-flow-control-output.txt, dyn-audit-log-output.txt
- **Severity**: nit
- **Concern**: Some reviewers noted `plan-review-loop.md` never documented the soft-advisory printf, so the omitted sibling update may be doc drift rather than a functional routing defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flow-control-output.txt, dyn-audit-log-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] rc=2 check-plan-size bypasses the hard gate
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: A degraded `check-plan-size` helper result can let an oversized plan proceed without offering Override, but this was identified as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] discussion-rounds.md remains Split/Cancel-only by design
- **Reviewer(s)**: dyn-doc-sync-output.txt
- **Severity**: nit
- **Concern**: `skills/design/references/discussion-rounds.md` still documents Step 1c/1d semantic-sprawl as Split/Cancel-only, explicitly outside this PR’s scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-doc-sync-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] approval-gates.md Split-path exit status appears pre-existing
- **Reviewer(s)**: dyn-flow-control-output.txt
- **Severity**: nit
- **Concern**: `approval-gates.md:164` says Split-path exits with `exit 1`, which may conflict with `decompose-panel.md` approved-partition exit 0, but was reported as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-flow-control-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] validation Override has a similar pre-existing audit pattern
- **Reviewer(s)**: dyn-audit-log-output.txt
- **Severity**: nit
- **Concern**: `validate-plan-commands` Override uses a similar `append-tool-failure.sh` pattern without mandating capture format, but that pattern predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-audit-log-output.txt: Address the concern above.
