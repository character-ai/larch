### FINDING_1: classify_launch_failure scans refusal text from output_file
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: Python classifies refusal text found only in the primary output file as `other/refusal`, while the bash launcher only checks refusal patterns in the sidecar and treats primary-output refusal text as `other/unknown`, breaking planned parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-waterfall-launch-output.txt: Address the concern above.

### FINDING_2: git.py lacks planned per-operation stub tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Only a small subset of `git.py` helpers have stub-runner argv/parsing tests, so regressions in untested helpers such as rebase, push, reset, merge-base, branch, and ls-files can pass CI until live integration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_3: gh.py lacks planned operation and retry-policy tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Most `gh.py` helpers are not covered by stub-runner tests, and retry behavior for idempotent reads versus mutating operations is not locked down, allowing argv, JSON, and retry-policy regressions before Phase 7 wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: launcher classification parity tests cover only timeout
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: Bash parity for `classify_launch_failure` only exercises timeout, leaving auth, binary-missing, health-probe, parse, refusal, and unknown cases free to drift from `lib-external-launcher-common.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-launch-output.txt: Address the concern above.

### FINDING_5: redaction parity tests do not cover full bash vectors or chained pipeline
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-redaction-parity-output.txt
- **Severity**: important
- **Concern**: Python redaction parity is limited to a few samples and does not cover the full bash harness vectors or the production `tmpdir | secrets` pipeline, leaving security-sensitive regex and ordering drift unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, dyn-redaction-parity-output.txt: Address the concern above.

### FINDING_6: gh helpers parse JSON before checking command failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-retry-idempotency-output.txt
- **Severity**: important
- **Concern**: `gh.py` read helpers and PR helpers call `json.loads` or coerce empty stdout before checking `CommandResult.returncode`, so failed `gh` calls can become `JSONDecodeError`, false “empty” results, or unintended mutating PR creation instead of controlled fail-closed errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-retry-idempotency-output.txt: Address the concern above.

### FINDING_7: git value helpers ignore non-zero return codes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Value-returning `git.py` helpers parse stdout even when git exits non-zero, which can mask failures as plausible empty values or unrelated parse errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: parse_json_stdout is unused
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `parse_json_stdout` in `python/git.py` is dead, untested API surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_9: logging_util hardcodes LARCH_QUIET_DISABLE
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `logging_util.py` uses a hardcoded environment variable name instead of `config.ENV_LARCH_QUIET_DISABLE`, so config renames would not propagate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_10: logging_util dataclasses are mutable
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Mutable dataclasses in `logging_util.py` are inconsistent with the frozen-record convention used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_11: python/.pylintrc is mostly stock template
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The 661-line `.pylintrc` appears mostly stock, making active overrides hard to review and future diffs noisy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_12: stdlib guard does not import runtime modules or catch dynamic imports
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdlib-boundary-output.txt
- **Severity**: latent
- **Concern**: `test_stdlib_only.py` only AST-parses imports and does not import runtime modules or audit dynamic import paths, so import-time failures and dynamic non-stdlib dependencies can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] py-lint and py-test are missing from canonical linting docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-tooling-output.txt
- **Severity**: latent
- **Concern**: `docs/linting.md` does not document the Python CI jobs or `make py-lint` / `make py-test`, so contributors relying on the canonical linting doc may miss the Python toolchain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-tooling-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] duplicate stub-runner test helpers may drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `test_git.py` and `test_gh.py` duplicate stub-runner patterns, which could drift as tests grow.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_15: run_waterfall does not rotate tiers like ship-pr
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: `run_waterfall` walks tiers in list order and gates first-fixer short-circuit on the unrotated index, diverging from bash `run_ci_fix_vendor` when the first tier is offset.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, dyn-waterfall-launch-output.txt: Address the concern above.

### FINDING_16: pr_for_branch omits --state open
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `pr_for_branch` does not pass `--state open`, so closed or non-open PRs may affect deduplication differently from bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] EXIT_STALL name obscures bash transient-net meaning
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `EXIT_STALL` names bash exit code 6 in a way that could be confused with a stalled outcome rather than transient network semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_18: CI failed-jobs harness allowlist omits Python jobs
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ci-tooling-output.txt
- **Severity**: important
- **Concern**: The workflow job audit in `scripts/test-ci-failed-jobs.sh` does not allow the new `python-lint` and `python-tests` jobs, so harness/CI checks fail despite `ci-failed-jobs.sh` mapping them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, dyn-ci-tooling-output.txt: Address the concern above.

### FINDING_19: retry transient-signature parity is undercovered
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `test_retry.py` covers only a small subset of bash `lib-net.sh` transient and non-transient vectors, so classifier drift can break retry semantics at cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_20: py-lint and py-test are not included in make lint or relevant-checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Contributors running only `make lint` or `relevant-checks.sh` can miss Python failures until CI runs the new jobs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_21: pr_create dedup test asserts oversimplified argv
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The `pr_create` dedup test does not assert the full `gh pr list` argv, so regressions in flags like `--head` or `--repo` could pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] subprocess timeout test may be slow
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: A real sleep-based timeout test may be slow or flaky on loaded runners.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_23: gitleaks allowlist changed without SECURITY.md update
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `.gitleaks.toml` now allowlists Python redaction fixtures and dev cache paths, but `SECURITY.md` does not document the resulting blind spots, especially `python/test_redact.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_24: gh mutating payloads are not centrally redacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Mutating GitHub helpers may publish unredacted body/title text, allowing secrets or tmpdir paths from plans/logs to reach public GitHub surfaces in future Python wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_25: logging/journal APIs accept arbitrary unredacted strings
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Breadcrumb and JSONL logging utilities can persist arbitrary unredacted text, which future callers may use with stderr or plan content containing secrets.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_26: python redact lacks streaming mode
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `python/redact.py` lacks the bash streaming redaction mode, so large future sidecar blobs may require full buffering or skip parity with streaming call sites.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_27: CI installs Python dev tools without hash pinning
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Python CI installs dev tools from package indexes without hash-locked requirements or a documented trusted install policy.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] SECURITY.md does not document python/redact.py
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `SECURITY.md` does not yet describe `python/redact.py` as a second redaction implementation or outbound scrubber before Python cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_29: retry signature matching is order-insensitive where bash is ordered
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `is_transient_net_signature` can classify reversed-token messages as transient because it uses order-independent substring checks, diverging from bash case patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_30: pr_create lacks post-create conflict recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-retry-idempotency-output.txt
- **Severity**: latent
- **Concern**: PR creation is check-then-create only and lacks bash-style already-exists conflict recovery, so concurrent PR creation can surface as an unhandled error instead of returning the existing PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, dyn-retry-idempotency-output.txt: Address the concern above.

### FINDING_31: retry backoff assumes tuple length matches max attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Increasing `TRANSIENT_RETRY_MAX_ATTEMPTS` without extending `BACKOFF` can cause an `IndexError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_32: run_waterfall API omits planned classify_fn
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The `run_waterfall` API omits the `classify_fn` described in the plan, risking duplicate or mismatched classification in later phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_33: extra gitleaks edit is outside enumerated plan files
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `.gitleaks.toml` is an extra root edit beyond the four files enumerated in the plan and should be documented as a required CI adjunct if retained.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_34: config constant tests cover only a sample
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test_config.py` samples a handful of constants, so renamed or removed public config constants may go untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_35: ship-pr per-job argv lacks Python job mappings
- **Reviewer(s)**: dyn-ci-tooling-output.txt
- **Severity**: important
- **Concern**: `ci-failed-jobs.sh` classifies `python-lint` and `python-tests` as fixable, but `scripts/ship-pr.sh` `_per_job_argv` has no matching `make py-lint` / `make py-test` cases, causing live CI recovery to bail as unfixable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-tooling-output.txt: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] ci-failed-jobs docs omit Python jobs
- **Reviewer(s)**: dyn-ci-tooling-output.txt
- **Severity**: nit
- **Concern**: `scripts/ci-failed-jobs.md` omits `python-lint` and `python-tests` from the documented fixable jobs list.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-tooling-output.txt: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] GitHub Actions and Makefile Python command parity is correct
- **Reviewer(s)**: dyn-ci-tooling-output.txt
- **Severity**: nit
- **Concern**: The reviewer observed no issue: GitHub Actions and Makefile commands for the new Python jobs match, cache paths align, and Node setup is scoped to `python-lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-tooling-output.txt: Address the concern above.

### FINDING_38: stdlib sibling allowlist includes test modules
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: important
- **Concern**: The stdlib enforcement allowlist treats every `python/*.py` stem as an allowed sibling import, so runtime modules can import `test_*` modules that depend on dev-only packages and still pass the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_39: ImportFrom with module=None is skipped by stdlib guard
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: latent
- **Concern**: `visit_ImportFrom` ignores relative imports such as `from . import x`, leaving a hole in the “walk every import” contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] branch commit list was reported
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer supplied branch commit metadata rather than a behavioral finding.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] current runtime modules have only allowed static imports
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that current runtime modules contain only stdlib and sibling-runtime static imports and no `importlib` / `__import__` usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] nested imports are covered
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that nested function/class imports are covered by the AST visitor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_43: [OUT_OF_SCOPE] pytest pythonpath may make tests importable at cutover
- **Reviewer(s)**: dyn-stdlib-boundary-output.txt
- **Severity**: latent
- **Concern**: `python/pyproject.toml` sets `pythonpath = ["."]`, which is appropriate for pytest but should not leak test modules into the production entrypoint layout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-stdlib-boundary-output.txt: Address the concern above.

### FINDING_44: [OUT_OF_SCOPE] gh retry-policy tests still missing but lower urgency
- **Reviewer(s)**: dyn-retry-idempotency-output.txt
- **Severity**: latent
- **Concern**: The implementation plan calls for read retry and mutating no-retry tests, but the reviewer marked this lower urgency while `python/` is not live.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-idempotency-output.txt: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] retry classifier parity found no drift
- **Reviewer(s)**: dyn-retry-idempotency-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that `python/retry.py` matches bash structure for checked signatures and negatives on the inspected vector set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-idempotency-output.txt: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] mutating gh wrappers avoid automatic retry
- **Reviewer(s)**: dyn-retry-idempotency-output.txt
- **Severity**: nit
- **Concern**: Reviewer observed that mutating wrappers call `_gh` once with no transient retry, aligning with the plan.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retry-idempotency-output.txt: Address the concern above.

### FINDING_47: redaction pass order differs from production pipeline
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: important
- **Concern**: `redact()` applies secrets before tmpdir paths, while key production outbound pipelines apply tmpdir before secrets; because the passes are not commutative, secret-shaped session suffixes can leak path structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.

### FINDING_48: [OUT_OF_SCOPE] Python redaction gap is not live production behavior
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: Reviewer noted that the live `/implement` path still uses bash helpers, so Python redaction ordering affects future consumers rather than current production.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.

### FINDING_49: [OUT_OF_SCOPE] bash redaction call sites are already inconsistent
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: latent
- **Concern**: Some existing bash call sites use secrets-before-tmpdir while others use tmpdir-before-secrets; this predates the branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.

### FINDING_50: [OUT_OF_SCOPE] redact.py streaming parity is a future item
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: latent
- **Concern**: Reviewer separately noted that `redact.py` lacks `redact-secrets.sh --streaming`, but marked it as future parity rather than a regression introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.

### FINDING_51: [OUT_OF_SCOPE] Python PEM warning observability differs from bash
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: Python handles unterminated PEM stdout truncation but does not mirror bash stderr `WARN` lines; reviewer classified this as observability only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.

### FINDING_52: binary_present truthiness diverges from bash
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: `classify_launch_failure` treats truthy strings such as `"0"` as binary-present, while bash only treats `1|true|yes` as present, so shell bridge values can misclassify binary-missing health failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.

### FINDING_53: run_waterfall first-attempt short-circuit may diverge when tiers are skipped
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: latent
- **Concern**: Short-circuit logic uses list index rather than first launched attempt, which can diverge from bash if future tier skipping is modeled in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.

### FINDING_54: [OUT_OF_SCOPE] launch argv uses repo-relative script paths
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: latent
- **Concern**: `build_launch_argv` uses repo-relative launcher paths; this is acceptable with the correct cwd but should be hardened or documented before Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.

### FINDING_55: [OUT_OF_SCOPE] run_waterfall is not equivalent to full ship-pr state handling
- **Reviewer(s)**: dyn-waterfall-launch-output.txt
- **Severity**: latent
- **Concern**: Reviewer noted that `run_waterfall` omits rollback, verify, and `BAIL_REASON` handling by Phase 1 design, so callers must not treat its short-circuit result as full ship-pr state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-launch-output.txt: Address the concern above.
