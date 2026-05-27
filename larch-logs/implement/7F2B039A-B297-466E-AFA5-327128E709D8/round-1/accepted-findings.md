### FINDING_1: risk-integration: scripts/implement-bootstrap.sh:704-762
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] persist-implement-run-flags skipped on --resume-plan-tail Operator enables --emergency on dirty-tree recovery but run-flags.sh keeps EMERGENCY_REQUESTED=false from an earlier pass; final summary omits Emergency despite argv. Call persist-implement-run-flags.sh on resume-plan-tail with current EMERGENCY_REQUESTED or merge-update run-flags.sh.
- **Suggested revision**: Address the concern above.


### FINDING_10: code-quality: skills/implement/SKILL.md:295
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Preflight exit code table omits emergency audit-refuse bypass Operators or automation expect exit 3 on all AUDIT=refuse; emergency path continues instead Note emergency exception in exit 3 row
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: skills/implement/SKILL.md:4, README.md:51
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] argument-hint and README argv list omit --emergency CLI discovery surfaces do not show the new flag Add [--emergency] to argument-hint and README code column
- **Suggested revision**: Address the concern above.


### FINDING_12: risk-integration: skills/implement/SKILL.md:178-283
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Preflight --emergency bypass semantics have no offline harness despite plan acceptance and manual test strategy CI passes while SKILL Preflight edits break mutual exclusion empty-body fail-closed or AUDIT=refuse→item-6 behavior without detection Add structural or fixture-based tests for emergency Preflight branches and exit codes
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: scripts/implement-bootstrap.sh:704-763
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] RESUME_PLAN_TAIL skips persist-implement-run-flags and bypass-log consumption Emergency run fails before first persist then resumes: metadata may show Emergency true but write-final-report reads missing run-flags and omits Emergency in larch:final-summary Re-persist EMERGENCY_REQUESTED on resume when run-flags missing; add bootstrap harness for resume-plan-tail + emergency
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: skills/implement/SKILL.md:4;scripts/test-implement-positional-issue.sh:13-14
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] argument-hint and structural test omit --emergency while Flags table documents it Operators and CLI UIs do not surface the flag; updating hint requires coordinated test change Add [--emergency] to argument-hint and update test-implement-positional-issue expectation
- **Suggested revision**: Address the concern above.


### FINDING_18: risk-integration: SECURITY.md:168
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] SECURITY.md was not updated for the new --emergency Preflight bypass despite AGENTS.md requiring security-relevant updates. The canonical security doc still claims plan presence/adequacy are always enforced mechanically; operators may invoke --emergency without understanding the guardrail downgrade. Extend the /implement Preflight section to document --emergency bypass scope, non-bypassed gates, operator opt-in, and raw-issue-body/prompt-injection risk.
- **Suggested revision**: Address the concern above.


### FINDING_19: security: skills/implement/SKILL.md:214-215
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Emergency item 3 materializes the raw GitHub issue body as plan.txt without mechanical untrusted-data wrapping before external implementers read it. A collaborator edits issue #N with instruction-like text; operator runs /implement --emergency N on a missing larch:plan block; Codex/Cursor treat the poisoned body as the binding plan. Document the downgrade in SECURITY.md; warn operators to inspect issue body; consider implementer-launcher trust-boundary wrapping for plan/feature files.
- **Suggested revision**: Address the concern above.


### FINDING_2: risk-integration: scripts/implement-bootstrap.sh:608-614
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] branch-1-resume skips post-tracking-issue metadata refresh Second /implement --emergency on an already-adopted issue never adds Emergency: true to larch:metadata while final-summary may include it. Upsert metadata when EMERGENCY_REQUESTED=true on resume/adopt paths not only branch-2-adopt.
- **Suggested revision**: Address the concern above.


### FINDING_24: architecture: scripts/implement-bootstrap.sh:704-763
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] --resume-plan-tail skips bypass-log consumption and run-flags persist. Dirty-tree or partial Step-0 resume with --emergency leaves stale EMERGENCY_REQUESTED in run-flags.sh and no execution-issues bypass entry. On resume still append non-empty emergency-bypass.log and re-persist run flags with current EMERGENCY_REQUESTED.
- **Suggested revision**: Address the concern above.


### FINDING_25: risk-integration: scripts/implement-bootstrap.sh:665-671
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Metadata is posted before run-flags persist. persist-implement-run-flags.sh fails after larch:metadata shows Emergency: true; final summary reads run-flags and omits Emergency. Persist run flags before post-tracking-issue or upsert metadata after successful persist.
- **Suggested revision**: Address the concern above.


### FINDING_28: code-quality: skills/implement/SKILL.md:313
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] SKILL documents parsing EMERGENCY_REQUESTED from bootstrap stdout but _ib_kv_scan omits it. Future orchestrator logic may assume stdout was parsed. Add EMERGENCY_REQUESTED to _ib_kv_scan or remove from parse list.
- **Suggested revision**: Address the concern above.


### FINDING_3: architecture: SECURITY.md:168
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] SECURITY.md not updated for --emergency bypass Policy doc still claims plan presence/adequacy are always mechanically enforced; operators lack documented trust boundary for bypass. Add a paragraph under /implement Preflight admission covering --emergency scope and residual gates.
- **Suggested revision**: Address the concern above.


### FINDING_5: code-quality: README.md:298
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] README argv signature omits --emergency Users scanning the table may miss the flag despite prose mention. Add [--emergency] to the /implement flags column.
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/implement-bootstrap.sh:665-756, skills/implement/scripts/write-final-report.sh:105-106
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] post-tracking-issue runs in phase_tracking before persist-implement-run-flags in phase_plan_materialize; resume-plan-tail skips persist /implement --emergency N: metadata posts Emergency: true, then gh issue view or persist fails; run-flags.sh never gets EMERGENCY_REQUESTED=true; write-final-report omits - Emergency: true while metadata still shows emergency Persist EMERGENCY_REQUESTED before post-tracking-issue, or add write-final-report fallback when run-flags lacks the key
- **Suggested revision**: Address the concern above.


