### FINDING_10: [OUT_OF_SCOPE] Python version floor probes and tests can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-py311-compat-output.txt
- **Severity**: latent
- **Concern**: Python 3.11 floor enforcement is duplicated across skill/wrapper/test surfaces, and the current test helper does not exercise the documented shell guard or verify all enforcement surfaces.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-py311-compat-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_14: [OUT_OF_SCOPE] INTERNAL_ERROR diagnostics hide exception detail
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Broad exception handling reports generic `INTERNAL_ERROR`, slowing triage by omitting redacted exception class/message from operator-visible diagnostics or journals.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_2: [OUT_OF_SCOPE] `pr_view_current` helpers are unused dead code
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt
- **Severity**: important
- **Concern**: `pr_view_current` / `pr_view_current_read` are never called, adding misleading PR-resolution API surface and future maintenance risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-gh-cli-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_22: [OUT_OF_SCOPE] Bash merge loop also lacks iteration cap
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The bash driver shares the unbounded merge-loop family, but hardening it is marked as a separate scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_25: [OUT_OF_SCOPE] Python `ensure_pr` omits explicit base branch
- **Reviewer(s)**: dyn-gh-cli-output.txt
- **Severity**: latent
- **Concern**: `ensure_pr` calls `gh.pr_create` without `--base`, unlike bash, leaving a parity gap for repositories whose default branch is not `main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-cli-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_27: [OUT_OF_SCOPE] Volatile cleanup test does not assert staged reset behavior
- **Reviewer(s)**: dyn-git-porcelain-output.txt
- **Severity**: nit
- **Concern**: The AM porcelain test does not assert that `git reset HEAD -- <rel>` runs when the index column is non-space.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-git-porcelain-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_29: [OUT_OF_SCOPE] Early argparse exits may violate JSON stdout contract
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: latent
- **Concern**: `ship.py main()` catches broad exceptions, but argparse failures and other early exits can still produce non-JSON stdout/non-contract exit codes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_30: [OUT_OF_SCOPE] `version_bump.py` warning uses raw stderr
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: nit
- **Concern**: `python/version_bump.py` has the same direct-stderr quiet-routing gap as scrub warnings, but is pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_31: [OUT_OF_SCOPE] Positive stdout/stderr contract observation
- **Reviewer(s)**: dyn-stream-protocol-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed no issue: stdout JSON remains isolated through `emit_result`, subprocess output is captured, and tests/SKILL guard preserve the machine contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stream-protocol-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_32: [OUT_OF_SCOPE] Positive Python floor-lowering coverage observation
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed the Python 3.11 floor-lowering appears complete across planned surfaces, with remaining 3.12 pins matching the contributor/runtime split.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_33: [OUT_OF_SCOPE] Positive Python 3.11 syntax observation
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed changed Python code uses 3.11-safe syntax and no 3.12-only constructs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_34: [OUT_OF_SCOPE] `datetime.UTC` import matches declared 3.11 floor
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed `from datetime import UTC` hard-requires 3.11+, matching the declared floor and guarded paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_35: [OUT_OF_SCOPE] `docs/linting.md` does not mention new Python CI matrix
- **Reviewer(s)**: dyn-py311-compat-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` still describes `python-lint`/`python-tests` as single jobs rather than the new `["3.11", "3.12"]` matrix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-py311-compat-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_9: [OUT_OF_SCOPE] Bash larch-log path lacks volatile-only skip
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: Bash ship/log commit flow can still commit refresh-only churn because the Python volatile-only classifier has not been ported to bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, dyn-git-porcelain-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

