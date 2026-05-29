### FINDING_1: [OUT_OF_SCOPE] Plugin description still advertises --trivial
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `.claude-plugin/plugin.json:4` still lists `--trivial` as a live `/design` tier flag, so marketplace/install metadata contradicts the updated SKILL/docs and fails the planned completeness sweep for removed `--trivial` references.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Stale Pre-Step-0 brainstorm guidance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md:267` still refers to a removed Pre-Step-0 / tier-gate upgrade path for `brainstorm_requested` on already-planned ad-hoc Q&A runs. Operators may look for a deleted flow instead of the remaining argv `--brainstorm` and Step 0b title-prefix auto-enable sources.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Redundant PLAN_LINE assignment in final summary script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `skills/design/scripts/render-final-summary.sh:245-247` has a redundant `PLAN_LINE=0 findings` assignment in the missing/empty voting-tally branch after trivial-mode handling was removed. This is not a functional bug, but it obscures intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] Duplicate tier flags lack mechanical rejection coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Duplicate-tier rejection for `/design --simple --hard` is prompt/prose enforced without a structural or harness assertion. If SKILL prose is ignored or edited, duplicate tier flags may reach `session-setup.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Completeness rg gates are manual-only
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The completeness sweeps for removed `--trivial` and `TRIVIAL_DOC_ONLY` references are not registered in `make lint`, so future doc drift can pass CI while violating plan acceptance checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] Legacy TRIVIAL_DOC_ONLY pause tier lacks explicit fixture
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `TRIVIAL_DOC_ONLY` was removed from accepted pause `TIER` values, so pre-consolidation paused runs fail `invalid-tier` and cannot resume in place. Existing tests cover generic invalid tiers but not the literal legacy token or an explicit deprecation warning.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Stale quick review-budget value remains
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/write-run-params.sh:157-158` still accepts `--review-budget quick` even though `--trivial` has been removed from argv/docs. A tmpdir `run-params.json` with `review_budget=quick` can still skip plan-command validation, but this is pre-existing orchestrator/tmpdir trust scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_8: Legacy --trivial rejection now happens later
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Removing Pre-Step-0 also removed early `--trivial` rejection before `session-setup.sh`; `/design --trivial N` may allocate `DESIGN_TMPDIR` before failing through the tier question path instead of an explicit removal error.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] brainstorm.md still mentions upgrade paths
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/brainstorm.md:3` still references upgrade paths that are no longer documented after the `flags.md` edit, which can mislead readers using the brainstorm contract alone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
