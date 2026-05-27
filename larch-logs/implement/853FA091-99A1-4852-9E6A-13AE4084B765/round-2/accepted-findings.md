### FINDING_1: Design mindset still conflicts with SIMPLE no-sketch path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` still contains blanket Design Mindset language that says never skip Step 2a, while Anti-pattern #1 now allows SIMPLE-tier runs to skip sketches. The conflict could cause SIMPLE runs to still launch four personality sketches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_13: Security OOS and voter-bias structural pins were dropped
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: The structural harness no longer pins SECURITY.md-mandated security OOS exclusion or voter-bias anchors. A future edit could remove security exclusion prose from `plan-review.md`, allowing security-tagged OOS to reach public OOS files while lint still passes.
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


### FINDING_3: timing-report fallback drops workflow_path and hides classification warnings
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/timing-report.sh` resolves fallback workflow classification only through `read-design-classification.sh`, suppressing its stderr and failing to prefer `workflow_path` from v1/v2 run params. Legacy or hand-edited run params with `workflow_path=SIMPLE` but no `design_classification` can be reported as HARD/unknown, and operators may miss HARD-default warnings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


