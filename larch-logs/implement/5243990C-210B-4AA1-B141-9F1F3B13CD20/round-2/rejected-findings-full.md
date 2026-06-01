### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: Structural pin omits `STEP17_EMITTED_PRESENT` parse requirement
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-implement-structure.sh` does not require the Step 18 prose to keep parsing `STEP17_EMITTED_PRESENT`, so that wrapper-emitted KV could be dropped without structural lint failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_16: `.step17-emitted` non-write sentinel is only checked in one harness case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Later Step 18b harness cases could regress and write `.step17-emitted` without failing CI because the absence/unchanged sentinel is only asserted in the first case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: `clear-stall` and `seed-terminal-state` lack tmpdir boundary validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: These subcommands do not use sibling `validate_tmpdir_path` / canonical directory checks, so a symlink or outside writable `--implement-tmpdir` could redirect atomic state writes outside the intended session boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Failed mv can leave temp-file orphans
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `clear-stall` / `seed-terminal-state` mv failures can leave `ship-pr-state.sh.tmp.*` files behind in `IMPLEMENT_TMPDIR`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: Structural test omits non-empty `summary-final.md` emit guard pin
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-implement-structure.sh` does not pin the planned `EMIT_BODY && WFR_RC=0 && -s summary-final.md` guard, so orchestration prose could drop the non-empty summary check while tests still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: Step 18b can abort before emitting tail KVs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `step-18b-final-report.sh` uses `set -euo pipefail` without an ERR trap or guaranteed tail emission, so unexpected helper/session rehydration failures can leave the orchestrator without `EMIT_BODY` / `WFR_RC`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: State validation parsing is duplicated
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `check_ship_pr_state_format` duplicates parsing logic from `validate_ship_pr_state`, creating drift risk for future format-rule changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_7: `clear-stall` treats absent disk state as failed clear
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt
- **Severity**: important
- **Concern**: `clear-stall` emits `CLEARED=false` when `ship-pr-state.sh` is absent, so a successful recovery from a session-only/in-memory stall can be routed to terminal failure instead of creating a minimal cleared state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: `rewrite_ship_pr_state_keys` interpolates unescaped values into dynamic awk
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-bash32-output.txt
- **Severity**: latent
- **Concern**: `rewrite_ship_pr_state_keys` builds awk source by embedding file/CLI values directly; values containing quotes, backslashes, newlines, or awk metacharacters can corrupt rewrites and may enable command execution under some awk implementations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-bash-state-output.txt, dyn-bash32-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

