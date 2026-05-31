# Review Round 1

- Mode: `diff`
- 21 accepted, 14 rejected (13 exonerated)

## Accepted Findings

### FINDING_1: classify_launch_failure scans refusal text from output_file
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: Python classifies refusal text found only in the primary output file as `other/refusal`, while the bash launcher only checks refusal patterns in the sidecar and treats primary-output refusal text as `other/unknown`, breaking planned parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-waterfall-launch-output.txt: Address the concern above.


### FINDING_12: stdlib guard does not import runtime modules or catch dynamic imports
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdlib-boundary-output.txt
- **Severity**: latent
- **Concern**: `test_stdlib_only.py` only AST-parses imports and does not import runtime modules or audit dynamic import paths, so import-time failures and dynamic non-stdlib dependencies can pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-stdlib-boundary-output.txt: Address the concern above.


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


### FINDING_2: git.py lacks planned per-operation stub tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Only a small subset of `git.py` helpers have stub-runner argv/parsing tests, so regressions in untested helpers such as rebase, push, reset, merge-base, branch, and ls-files can pass CI until live integration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_20: py-lint and py-test are not included in make lint or relevant-checks
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Contributors running only `make lint` or `relevant-checks.sh` can miss Python failures until CI runs the new jobs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: gitleaks allowlist changed without SECURITY.md update
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `.gitleaks.toml` now allowlists Python redaction fixtures and dev cache paths, but `SECURITY.md` does not document the resulting blind spots, especially `python/test_redact.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### FINDING_29: retry signature matching is order-insensitive where bash is ordered
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `is_transient_net_signature` can classify reversed-token messages as transient because it uses order-independent substring checks, diverging from bash case patterns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_3: gh.py lacks planned operation and retry-policy tests
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Most `gh.py` helpers are not covered by stub-runner tests, and retry behavior for idempotent reads versus mutating operations is not locked down, allowing argv, JSON, and retry-policy regressions before Phase 7 wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_31: retry backoff assumes tuple length matches max attempts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Increasing `TRANSIENT_RETRY_MAX_ATTEMPTS` without extending `BACKOFF` can cause an `IndexError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_35: ship-pr per-job argv lacks Python job mappings
- **Reviewer(s)**: dyn-ci-tooling-output.txt
- **Severity**: important
- **Concern**: `ci-failed-jobs.sh` classifies `python-lint` and `python-tests` as fixable, but `scripts/ship-pr.sh` `_per_job_argv` has no matching `make py-lint` / `make py-test` cases, causing live CI recovery to bail as unfixable.
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


### FINDING_4: launcher classification parity tests cover only timeout
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-launch-output.txt
- **Severity**: important
- **Concern**: Bash parity for `classify_launch_failure` only exercises timeout, leaving auth, binary-missing, health-probe, parse, refusal, and unknown cases free to drift from `lib-external-launcher-common.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-waterfall-launch-output.txt: Address the concern above.


### FINDING_47: redaction pass order differs from production pipeline
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: important
- **Concern**: `redact()` applies secrets before tmpdir paths, while key production outbound pipelines apply tmpdir before secrets; because the passes are not commutative, secret-shaped session suffixes can leak path structure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Address the concern above.


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


### FINDING_9: logging_util hardcodes LARCH_QUIET_DISABLE
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `logging_util.py` uses a hardcoded environment variable name instead of `config.ENV_LARCH_QUIET_DISABLE`, so config renames would not propagate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


