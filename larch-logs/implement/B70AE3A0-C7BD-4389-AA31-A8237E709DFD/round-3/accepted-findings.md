### FINDING_10: Python 3.11 shell guard fails outside the JSON protocol
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Step 8 Python version guard exits 1 with text only, while Python-path orchestration expects structured JSON outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_15: Mixed volatile and canonical run-log deltas are untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt
- **Severity**: latent
- **Concern**: No regression test proves that a flush containing both refresh sidecars and substantive canonical artifacts still commits rather than being skipped as volatile-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-git-porcelain-output.txt: Address the concern above.


### FINDING_17: CI breadcrumb elapsed text is not meaningfully tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The CI poll breadcrumb test uses a fixed zero elapsed clock, so elapsed reporting regressions would not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_20: Unexpected-exception diagnostics bypass quiet routing and may leak details
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-stdio-quiet-output.txt
- **Severity**: latent
- **Concern**: Unexpected exception handling prints raw tracebacks or direct stderr diagnostics, bypassing `BreadcrumbWriter` and potentially leaking stack details or splitting observability channels.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, dyn-stdio-quiet-output.txt: Address the concern above.


### FINDING_26: Phase breadcrumb coverage is incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The happy-path stage-order test asserts only some breadcrumbs and does not cover every major phase required by the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_30: PR creation ignores stderr URLs after invalid stdout URLs
- **Reviewer(s)**: dyn-gh-create-output.txt
- **Severity**: important
- **Concern**: On successful `gh pr create`, stdout URLs are treated as terminal even when validation fails, so a real PR URL present only on stderr is never tried.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-gh-create-output.txt: Address the concern above.


### FINDING_4: Unexpected Python exceptions are reported as operational stalls
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `ship.py main()` maps arbitrary uncaught exceptions to STALLED exit 4, causing programming bugs to look like recoverable operational stalls.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: Quiet routing can hide operator-visible breadcrumbs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdio-quiet-output.txt
- **Severity**: important
- **Concern**: `BreadcrumbWriter` treats `LARCH_QUIET_ACTIVE` as sufficient for quiet routing while `LARCH_QUIET_PID` is unused, so breadcrumbs can skip stderr or vanish when FD 4/log-file routing is not actually initialized.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdio-quiet-output.txt: Address the concern above.


### FINDING_8: `pr_view_current` is duplicated and unsafe as a PR recovery fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `pr_view_current` duplicates `pr_view` parsing and may resolve the checked-out branch’s PR rather than the intended newly created PR head branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: Post-create transient network errors become stalls
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `pr_create` can swallow `TransientNetworkError` during post-create PR resolution and return STALLED exit 4 instead of TRANSIENT exit 6, preventing retry behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


