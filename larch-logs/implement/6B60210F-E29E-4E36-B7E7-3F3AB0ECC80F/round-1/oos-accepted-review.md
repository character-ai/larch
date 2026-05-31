### FINDING_13: [OUT_OF_SCOPE] py-lint and py-test are missing from canonical linting docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-tooling-output.txt
- **Severity**: latent
- **Concern**: `docs/linting.md` does not document the Python CI jobs or `make py-lint` / `make py-test`, so contributors relying on the canonical linting doc may miss the Python toolchain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-tooling-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_14: [OUT_OF_SCOPE] duplicate stub-runner test helpers may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_git.py` and `test_gh.py` duplicate stub-runner patterns, which could drift as tests grow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_17: [OUT_OF_SCOPE] EXIT_STALL name obscures bash transient-net meaning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `EXIT_STALL` names bash exit code 6 in a way that could be confused with a stalled outcome rather than transient network semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_22: [OUT_OF_SCOPE] subprocess timeout test may be slow
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A real sleep-based timeout test may be slow or flaky on loaded runners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_28: [OUT_OF_SCOPE] SECURITY.md does not document python/redact.py
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` does not yet describe `python/redact.py` as a second redaction implementation or outbound scrubber before Python cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_36: [OUT_OF_SCOPE] ci-failed-jobs docs omit Python jobs
- **Reviewer(s)**: dyn-ci-tooling-output.txt
- **Severity**: nit
- **Concern**: `scripts/ci-failed-jobs.md` omits `python-lint` and `python-tests` from the documented fixable jobs list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-tooling-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_37: [OUT_OF_SCOPE] GitHub Actions and Makefile Python command parity is correct
- **Reviewer(s)**: dyn-ci-tooling-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed no issue: GitHub Actions and Makefile commands for the new Python jobs match, cache paths align, and Node setup is scoped to `python-lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-tooling-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_40: [OUT_OF_SCOPE] branch commit list was reported
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer supplied branch commit metadata rather than a behavioral finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_41: [OUT_OF_SCOPE] current runtime modules have only allowed static imports
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that current runtime modules contain only stdlib and sibling-runtime static imports and no `importlib` / `__import__` usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_42: [OUT_OF_SCOPE] nested imports are covered
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that nested function/class imports are covered by the AST visitor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_43: [OUT_OF_SCOPE] pytest pythonpath may make tests importable at cutover
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: latent
- **Concern**: `python/pyproject.toml` sets `pythonpath = ["."]`, which is appropriate for pytest but should not leak test modules into the production entrypoint layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_44: [OUT_OF_SCOPE] gh retry-policy tests still missing but lower urgency
- **Reviewer(s)**: dyn-retry-idempotency-output.txt
- **Severity**: latent
- **Concern**: The implementation plan calls for read retry and mutating no-retry tests, but the reviewer marked this lower urgency while `python/` is not live.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-idempotency-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_45: [OUT_OF_SCOPE] retry classifier parity found no drift
- **Reviewer(s)**: dyn-retry-idempotency-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that `python/retry.py` matches bash structure for checked signatures and negatives on the inspected vector set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-idempotency-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_46: [OUT_OF_SCOPE] mutating gh wrappers avoid automatic retry
- **Reviewer(s)**: dyn-retry-idempotency-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that mutating wrappers call `_gh` once with no transient retry, aligning with the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-idempotency-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_48: [OUT_OF_SCOPE] Python redaction gap is not live production behavior
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that the live `/implement` path still uses bash helpers, so Python redaction ordering affects future consumers rather than current production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected


### FINDING_49: [OUT_OF_SCOPE] bash redaction call sites are already inconsistent
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: latent
- **Concern**: Some existing bash call sites use secrets-before-tmpdir while others use tmpdir-before-secrets; this predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_50: [OUT_OF_SCOPE] redact.py streaming parity is a future item
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately noted that `redact.py` lacks `redact-secrets.sh --streaming`, but marked it as future parity rather than a regression introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_51: [OUT_OF_SCOPE] Python PEM warning observability differs from bash
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: Python handles unterminated PEM stdout truncation but does not mirror bash stderr `WARN` lines; reviewer classified this as observability only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated


### FINDING_54: [OUT_OF_SCOPE] launch argv uses repo-relative script paths
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: latent
- **Concern**: `build_launch_argv` uses repo-relative launcher paths; this is acceptable with the correct cwd but should be hardened or documented before Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_55: [OUT_OF_SCOPE] run_waterfall is not equivalent to full ship-pr state handling
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: latent
- **Concern**: Reviewer noted that `run_waterfall` omits rollback, verify, and `BAIL_REASON` handling by Phase 1 design, so callers must not treat its short-circuit result as full ship-pr state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


