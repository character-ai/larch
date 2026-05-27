### FINDING_1: Design mindset still conflicts with SIMPLE no-sketch path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still contains blanket Design Mindset language that says never skip Step 2a, while Anti-pattern #1 now allows SIMPLE-tier runs to skip sketches. The conflict could cause SIMPLE runs to still launch four personality sketches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicate CI focus-area anchor comments add structural noise
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` has ten duplicate CI focus-area anchor comments that do not add coverage and make Step 3 contract changes harder to review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: timing-report fallback drops workflow_path and hides classification warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` resolves fallback workflow classification only through `read-design-classification.sh`, suppressing its stderr and failing to prefer `workflow_path` from v1/v2 run params. Legacy or hand-edited run params with `workflow_path=SIMPLE` but no `design_classification` can be reported as HARD/unknown, and operators may miss HARD-default warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Gate C cap breadcrumb wording diverges from Step 3 cap wording
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `skills/design/references/approval-gates.md` and `skills/design/SKILL.md` use different wording for the review cap condition, so users may not recognize that Gate C is referring to the same locked cap state reported by Step 3.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Structural harness shrink dropped unrelated invariant pins
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-design-structure.sh` was reduced from roughly 807 lines to 73, dropping structural checks outside the tier-consolidation scope. Flag ordering, dialectic guards, sketch path sync, and other invariants could now regress without `make lint` failing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Anti-pattern #1 SIMPLE carve-out is not pinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The acceptance-critical Anti-pattern #1 rewrite allowing SIMPLE no-sketch behavior is not protected by an executable structural pin, so the skill could revert to blanket never-skip-sketches behavior while lint still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_7: FINDING_2678 voter/source pins were removed instead of relocated
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The FINDING_2678 YES/EXONERATE source pins were removed even though the plan required relocation to `plan-review.md`. Voter prose and rendered prompts could drift without the intended grep coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Pre-Step-0 --trivial hard error lacks behavioral coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no executable test proving `--trivial` errors before `session-setup` and before `DESIGN_TMPDIR` exists. The behavior could stop erroring or run setup while prose pins still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_9: Review cap counter and panel skip lack behavioral coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There is no harness covering review-round cap counter behavior at cap-1, cap, and cap+1. Off-by-one or skip failures could allow extra panel runs or block valid reruns undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_10: invoke-plan-validator wrapper is not directly tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The renamed `skills/design/scripts/invoke-plan-validator.sh` is not invoked directly by any test, so wrapper piping bugs could ship even though the design-driver command path is covered.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: v2 run-params writer test does not enforce exact schema
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-write-run-params.sh` checks fields but does not assert the JSON contains exactly the four expected keys, allowing legacy null fields to slip through.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: read-design-classification fallback chain lacks degraded-toolchain tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The reader harness does not test python3, jq, and grep fallback behavior, so parser regressions may only appear on production hosts missing preferred tools.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Security OOS and voter-bias structural pins were dropped
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The structural harness no longer pins SECURITY.md-mandated security OOS exclusion or voter-bias anchors. A future edit could remove security exclusion prose from `plan-review.md`, allowing security-tagged OOS to reach public OOS files while lint still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: SIMPLE reviewer emphasis may bias against material security findings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `skills/design/scripts/render-plan-review-prompt.sh` tells SIMPLE reviewers to lean toward EXONERATE/addition avoidance without an explicit security carve-out, so full-panel SIMPLE runs may under-report injection, auth, or secret-handling defects.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: grep fallback can mis-read classification from malformed run params
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `scripts/read-design-classification.sh` can parse `design_classification` from non-JSON substrings when python3 and jq are unavailable. Malformed or hostile run params could force SIMPLE tier, wrong caps, or weaker reviewer bias.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Cap short-circuit still falls through to Gate B
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` says cap short-circuit should jump toward Step 3b/4/4b/Gate C, but Step 3 still continues to Gate B with no `STEP3_REVIEW_CAP_REACHED` branch. A capped rerun can skip the panel but re-prompt stale accepted findings instead of going straight to Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Review round counter increments before panel success
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `review-round-count.txt` is incremented before `plan-review-loop.sh` completes and has no rollback on panel failure. A failed panel retry can consume a review round without producing findings, accelerating cap exhaustion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Gate C cap-aware options are prompt-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Gate C omits the rerun option only through prompt prose and does not mechanically read the counter before `AskUserQuestion`. At cap, the orchestrator may still offer “Re-run review panel,” causing a wasted short-circuit turn.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Token analysis still maps legacy Quick tally text to SIMPLE
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `skills/report-tokens/scripts/run-analysis.sh` still has a legacy Quick mode tally heuristic after Quick mode removal. A HARD run missing `timing-report.json` but containing legacy Quick tally text can be mis-bucketed as SIMPLE.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: timing-ledger fallback ownership is undocumented
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Plan/acceptance text cites `timing-ledger.sh` for design classification fallback, but fallback logic exists only in `timing-report.sh`. Contributors may incorrectly duplicate fallback behavior into ledger code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
