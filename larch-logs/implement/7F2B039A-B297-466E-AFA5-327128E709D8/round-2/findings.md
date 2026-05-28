### FINDING_1: Emergency bypass log format is undefined
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Preflight requires structured emergency-bypass.log entries but does not define the required line format, while harnesses expect `BYPASS kind=missing-plan issue=N`; implementers may write incompatible text and bootstrap still appends any non-empty file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: [OUT_OF_SCOPE] Emergency bypass warnings can be duplicated on resume
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `resume-plan-tail` can replay the same `emergency-bypass.log`, producing duplicate Warnings entries in `execution-issues.md` when resuming after a dirty-tree bail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: Bootstrap persists run flags redundantly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `persist_run_flags` may run up to three times per bootstrap invocation, causing redundant atomic rewrites and noisy harness invoke logs without functional benefit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: `--emergency` flag binding is under-specified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The flags table documents `--emergency` but does not explicitly bind it to the `emergency_requested` mental flag/default, leaving orchestrator behavior to inference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_5: Emergency prompt gates lack regression coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `--emergency` behavior is largely prompt-only and insufficiently pinned by automated tests, so edits could remove mutex, bypass, empty-body, or threading rules without CI catching the drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_6: Plugin description omits `--emergency`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `.claude-plugin/plugin.json` does not list `--emergency`, so the marketplace description shows an incomplete `/implement` flag surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Emergency PR includes unrelated changes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The branch bundles unrelated version-bump, design gate, merge/ship, or harness changes with emergency behavior, increasing reviewer burden and merge risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_8: Emergency bypass append failures are swallowed
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `append_emergency_bypass_log_if_present` ignores redaction or append failures with `|| true`, so `execution-issues.md` can under-report emergency bypass activity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt: Address the concern above.

### FINDING_9: Resume can leave stale emergency metadata
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Branch-1 resume persists `EMERGENCY_REQUESTED` from argv but only refreshes tracking metadata when emergency is true, so a retry without `--emergency` can leave GitHub metadata showing `Emergency: true` while local flags and final summary show false.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Malformed-plan emergency fallback can materialize an empty plan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: When `plan-block-read.sh` truncates the output on `MALFORMED`, emergency fallback can leave or copy an empty plan unless the orchestrator or bootstrap explicitly checks for non-empty fallback content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_11: Empty preflight tmpdir probes root path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: If `PREFLIGHT_TMPDIR_OPT` is empty, the bypass log path becomes `/emergency-bypass.log`, causing an unnecessary root filesystem probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_12: Render summary emergency flag callsites are unpinned
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The callsites harness does not require `--emergency-requested` on each `render-run-summary.sh` invocation, so `write-final-report` could drop the flag unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: Invalid bootstrap emergency flag value is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bootstrap lacks a harness case for an invalid `--emergency-requested` value, so bad argv may fail late or with the wrong exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: Renderer false emergency path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The render harness does not assert that the default or omitted emergency flag produces no Emergency line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Emergency raw-body fallback exposes untrusted issue text as plan
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Emergency raw-issue-body fallback can materialize collaborator-controlled GitHub text into `plan.txt` without implementer-layer untrusted-data wrapping, allowing malicious issue text to be treated as authoritative instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: Emergency can bypass inadequate-plan audit refusal
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `--emergency` bypasses clarify on `AUDIT=refuse`, so an inadequate or hostile extracted `larch:plan` can still proceed to implementation without a visible design-audit warning or narrower bypass semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: Emergency bypass provenance is not mechanically enforced
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Shell helpers accept `--emergency-requested true` without validating that a bypass manifest/log or raw-body fallback actually happened, so metadata can over-claim emergency handling despite orchestrator drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Resume admission can skip design checks under emergency
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Resume admission can skip `[DESIGNED]` and related checks when the parent-issue sentinel matches, allowing resume plus `--emergency` on an issue that never completed `/design`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Admission blocker reads fail open
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Admission blocker checks can pass on `gh` or API errors with zero blockers, and emergency runs do not add visibility or fail-closed behavior for that pre-existing posture.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_20: Bypass log append ignores current emergency flag
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `append_emergency_bypass_log_if_present` can replay leftover emergency bypass warnings during a non-emergency resume, making logs report emergency bypasses while run flags and final summary report non-emergency.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
