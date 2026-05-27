### FINDING_1: Shared tier fallback parsing can diverge or misclassify reports
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Tier resolution is duplicated and partly grep-based across timing/reporting scripts, which can diverge from the canonical workflow_path-first classification behavior or misread crafted/conflicting JSON when stricter parsers are unavailable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Duplicate Focus area enum anchors add noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Ten repeated Focus area enum anchor comments in `skills/design/SKILL.md` look accidental and may mislead readers or grep-based references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Topology vocabulary still uses legacy round-cap wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/shared/topology.tsv` still describes Step 5 round-cap terminology instead of the updated design classification or tier-label vocabulary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Timing-ledger acceptance text conflicts with write-only docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Acceptance criteria or plan text still imply `timing-ledger.sh` should read workflow_path/design_classification fallback, while docs describe timing-ledger as write-only and readers as owning fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Step 3 cap counter is not persisted at review entry
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The Step 3 review-round counter is persisted only after panel settlement, so empty or unrecognized statuses, crashes after launch, or plan-contract expectations can leave the count stale and allow extra panels beyond the tier cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_6: Failed panels consume review cap without usable findings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `panel-failed` persists the review-round count, so repeated dispatch failures can exhaust the SIMPLE/HARD cap without producing review findings or voting output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Legacy Quick-mode token-report heuristic remains
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/report-tokens/scripts/run-analysis.sh` still maps legacy Quick-mode tally text to SIMPLE, which can misclassify historical or malformed logs after tier removal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: Step 3 cap harness lacks HARD-tier coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The cap test only covers SIMPLE cap=3, so regressions around HARD cap=5 blocking or allowing the fifth round could pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: SIMPLE tier external-review trust boundary is underdocumented
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Replacing TRIVIAL quick mode with SIMPLE can send plans and context to external Codex/Cursor reviewers, while operators migrating from `--trivial` may still expect Claude-only review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_10: SIMPLE reviewer guidance can suppress security hardening
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: SIMPLE tier prose emphasizes exonerating non-correctness findings, so security hardening that is not framed as correctness may be voted down.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_11: Review cap can approve against stale external artifacts after plan edits
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: After the review cap is reached, Discuss-further can change the plan while stale panel artifacts still gate approval, allowing approval without fresh external review of the edited plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_12: Sourcing cap env file creates same-UID shell injection risk
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/SKILL.md` sources `.step3-review-cap.env` from `DESIGN_TMPDIR`, allowing a same-UID writer to inject shell code before orchestration reads the values.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: Collaborative sketches docs still reference deleted Quick mode
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `docs/collaborative-sketches.md` still documents Quick mode sketch attribution, implying a deleted 2-slot Cursor/Codex sketch path still exists beside SIMPLE/HARD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
