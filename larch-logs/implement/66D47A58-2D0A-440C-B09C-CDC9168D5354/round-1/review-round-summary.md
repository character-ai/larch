# Review Round 1

- Mode: `diff`
- 10 accepted, 7 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: Auto-apply Gate B duplicates findings presentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Auto-apply Gate B presents both the full Presentation table and a compact findings list, including duplicate rejected/OOS output, creating contradictory/noisy operator output before apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_10: Step 3.5 says auto-apply is silent
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `skills/design/SKILL.md` says Step 3.5 silently revises in auto-apply mode, while `approval-gates.md` requires visible breadcrumb/findings output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: Missing structural pin for defensive manual_gate_b read
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-design-structure.sh` lacks a structural pin for the defensive `manual_gate_b` read idiom, so future edits can weaken the read without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: SECURITY.md lacks Gate B auto-apply trust-boundary documentation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Gate B auto-apply default and fail-open degradation are security-relevant behavior changes but are not documented in `SECURITY.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_2: Gate contract still says every gate prompts
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: `approval-gates.md` still says each gate uses `AskUserQuestion`, contradicting the new default Gate B auto-apply path when `manual_gate_b=false`; an orchestrator may still prompt or hesitate at Gate B.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-prose-stale-output.txt: Address the concern above.


### FINDING_20: Step 4b re-run handler omits auto-applied feedback
- **Reviewer(s)**: dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: `skills/design/SKILL.md` Step 4b says reviewers see all approved-by-user prior feedback applied, but default Gate B may have auto-applied feedback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prose-stale-output.txt: Address the concern above.


### FINDING_3: Quick review output header implies premature plan revision
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `plan-review-quick.md` still references plan revision during quick-mode Step 3, which can make implementers revise `plan.txt` before Gate B instead of only collecting review findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Gate C entry conditions omit default auto-apply path
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: Gate C’s “When” paragraph lists manual settled paths but omits the default auto-apply Gate B path, making the Gate C flow incomplete or misleading after auto-apply.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-prose-stale-output.txt: Address the concern above.


### FINDING_5: Gate C re-review prose omits auto-applied feedback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-prose-stale-output.txt
- **Severity**: important
- **Concern**: Gate C re-review prose says the plan reflects only user-approved prior feedback, which is stale when Gate B findings were auto-applied.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-prose-stale-output.txt: Address the concern above.


### FINDING_9: Gate B manual-mode read failures fail open to auto-apply
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `manual_gate_b` cannot be read or persisted, including missing `jq`, corrupt `run-params.json`, or disk/session failures, Gate B can default to auto-apply even when the operator passed `--manual`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


