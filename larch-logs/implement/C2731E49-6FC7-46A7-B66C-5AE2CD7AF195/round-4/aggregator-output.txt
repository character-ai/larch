### FINDING_1: Extract emergency bypass log helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `append_emergency_bypass_log_if_present` is a large inline helper inside `scripts/implement-bootstrap.sh`, mixing validation, redaction, and fallback append behavior in a way that makes bootstrap plan materialization harder to maintain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Add executable emergency Preflight regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Emergency Preflight bypass behavior is prompt-only and currently pinned mostly by static grep tests, so regressions in bypass, warning, empty-body, audit-refuse, exit, or log behavior could ship without executable coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Hoist duplicate bypass-log append call
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `append_emergency_bypass_log_if_present` is called in both branches of `phase_plan_materialize`, creating a risk that resume and initial behavior diverge in future edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Avoid redundant run flag persistence
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `persist_run_flags HARD` runs in both `phase_tracking` and happy-path `phase_plan_materialize`, adding unnecessary rewrites and ordering coupling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Separate token report corruption changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `TOKEN_REPORT_CORRUPT_ZERO` behavior was bundled with emergency flag wiring, forcing reviewers to audit unrelated token-cost behavior while reviewing emergency support.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Default tracking metadata emergency flag from run flags
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `post-tracking-issue.sh` only accepts emergency state through argv, so a future caller that omits `--emergency-requested` can post metadata without `Emergency: true` even when `run-flags.sh` records emergency mode.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Structurally pin emergency bootstrap argument forwarding
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests do not sufficiently pin `_ib_emergency` expansion in both initial bootstrap and resume-plan-tail call paths, so one path could stop forwarding emergency state until runtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Surface tracking metadata post failures
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `post_tracking_metadata` uses `|| true` on resume paths, allowing `gh` upsert failures to continue silently without `Emergency: true` in `larch:metadata`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_9: Cover clean emergency run without bypass log
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: There is no bootstrap harness case for an emergency run with a valid plan and no bypass log, so regressions that add spurious warnings or drop emergency metadata on clean emergency runs may be missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: Document emergency flag binding
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: The flags table does not explicitly bind `--emergency` to `emergency_requested`, making it easier for orchestrator code to set the wrong variable and skip bypass behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Add argv and non-emergency Preflight coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The `--emergency`/`--draft` mutex and non-emergency no-plan exit behavior are grep-only assertions rather than executable control-flow tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Define resume override behavior for emergency false
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: There is no test for explicit `--emergency-requested false` overriding persisted true on resume, so emergency state could be downgraded and metadata or summary emergency lines dropped unintentionally.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Rename misleading bypass-log test header
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A test section header says the bypass log is replayed even though the assertion is about no replay, which can mislead maintainers during future emergency/resume edits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Wrap raw emergency issue body as untrusted data
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Emergency mode can use raw GitHub issue body as `plan.txt` without `larch:plan` extraction, allowing collaborator-authored instruction-like text to be treated as authoritative implementation guidance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: Only consume bypass log after successful append
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If both `append-tool-failure.sh` and fallback `append-execution-issue.sh` fail, bootstrap still writes the consumed sentinel, losing the bypass log permanently without an execution-issues entry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_16: Preserve bypass log before plan materialization failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bypass log consumption only happens in `phase_plan_materialize`, so if bootstrap exits after Preflight and tmpdir cleanup runs, the durable execution-issues trail may be lost.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_17: Enforce non-empty emergency raw body during copy-plan
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The empty raw-body guard is not enforced at bootstrap copy-plan, so a non-compliant run could write an empty `plan.txt` and proceed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Isolate unrelated Bash prelude documentation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: An unrelated Bash block prelude was added in the same `SKILL.md` diff as emergency work, increasing review noise for the emergency feature.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Admission blocker checks fail open
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `scripts/implement-admission.sh` blocker checks fail open on API errors, allowing `ADMISSION_RESULT=pass` with unknown blockers; the reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Raw issue body prompt influence surface
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Full issue bodies are copied to `feature-description.txt`, allowing collaborator issue text to influence implementer prompts; the reviewer marked this as pre-existing, with emergency only adding a raw-body plan path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Resume-plan-tail can proceed without plan artifacts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Resume after an early dirty-tree bail may run without required `plan.txt` artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] Branch includes work outside emergency plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The branch diff versus `main` includes substantial work outside the #3041 emergency plan, so reviewers validating PR scope should restrict review to the emergency-touched paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Prompt-only Preflight reliance as plan-fidelity note
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Emergency bypass behavior relies on orchestrator prompt prose rather than a shell harness simulating Preflight items 3-5 end to end; the source classified this as a known operational reliance rather than a plan gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
