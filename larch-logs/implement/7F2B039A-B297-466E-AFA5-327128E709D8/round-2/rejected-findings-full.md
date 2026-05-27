### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Malformed-plan emergency fallback can materialize an empty plan
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: When `plan-block-read.sh` truncates the output on `MALFORMED`, emergency fallback can leave or copy an empty plan unless the orchestrator or bootstrap explicitly checks for non-empty fallback content.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_11: Empty preflight tmpdir probes root path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: If `PREFLIGHT_TMPDIR_OPT` is empty, the bypass log path becomes `/emergency-bypass.log`, causing an unnecessary root filesystem probe.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: Invalid bootstrap emergency flag value is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bootstrap lacks a harness case for an invalid `--emergency-requested` value, so bad argv may fail late or with the wrong exit behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_14: Renderer false emergency path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The render harness does not assert that the default or omitted emergency flag produces no Emergency line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Emergency raw-body fallback exposes untrusted issue text as plan
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Emergency raw-issue-body fallback can materialize collaborator-controlled GitHub text into `plan.txt` without implementer-layer untrusted-data wrapping, allowing malicious issue text to be treated as authoritative instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: Emergency can bypass inadequate-plan audit refusal
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `--emergency` bypasses clarify on `AUDIT=refuse`, so an inadequate or hostile extracted `larch:plan` can still proceed to implementation without a visible design-audit warning or narrower bypass semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_17: Emergency bypass provenance is not mechanically enforced
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Shell helpers accept `--emergency-requested true` without validating that a bypass manifest/log or raw-body fallback actually happened, so metadata can over-claim emergency handling despite orchestrator drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Bootstrap persists run flags redundantly
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `persist_run_flags` may run up to three times per bootstrap invocation, causing redundant atomic rewrites and noisy harness invoke logs without functional benefit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: `--emergency` flag binding is under-specified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The flags table documents `--emergency` but does not explicitly bind it to the `emergency_requested` mental flag/default, leaving orchestrator behavior to inference.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

