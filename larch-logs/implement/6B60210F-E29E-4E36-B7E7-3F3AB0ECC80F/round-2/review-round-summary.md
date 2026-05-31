# Review Round 2

- Mode: `diff`
- 14 accepted, 9 rejected (9 exonerated)

## Accepted Findings

### FINDING_1: `make lint` hard-requires Python toolchain
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-pipeline-output.txt, dyn-strangler-boundary-output.txt
- **Severity**: important
- **Concern**: The `lint` target now depends on `py-lint` and `py-test` before harnesses and pre-commit. Contributors without ruff/pylint/pyright/pytest (and Node for pyright) cannot run `make lint` on bash-only changes; this conflicts with Phase 1 scope (standalone `make py-lint` / `make py-test` and CI jobs only) and widens local-vs-CI drift because CI runs separate `python-lint` / `python-tests` jobs with installs, not the umbrella `lint` target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pipeline-output.txt: Either remove `py-lint`/`py-test` from the `lint` prerequisite chain (keep them as explicit/CI-only targets), or add install/bootstrap steps or documented prerequisites in `docs/linting.md` and the `lint` comment block.
  - From dyn-strangler-boundary-output.txt: Drop `py-lint` and `py-test` from the `lint` prerequisite list; keep them as explicit/CI/relevant-checks-only targets so the strangler tree stays opt-in until Phase 7.

---


### FINDING_12: `_retry_read` raises after transient exhaustion instead of returning last result
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-process-retry-output.txt
- **Severity**: important
- **Concern**: `_retry_read` always funnels through `_ensure_success`, so after `with_transient_retry` exhausts on a transient signature the helper raises `ShipError` instead of returning the last `CommandResult`. Phase 1 plan and bash `ship_pr_with_transient_retry` treat exhausted transient retries as a distinct terminal outcome (`exit_transient_net`), not a generic command failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Return last CommandResult from read helpers or add non-raising variants; test 3-attempt exhaustion.
  - From dyn-process-retry-output.txt: Have `_retry_read` return `retried.value` (or a small wrapper carrying `RetryResult` metadata) and let typed callers decide whether to parse JSON, raise, or map transient exhaustion to `Outcome.TRANSIENT`/`TransientNetworkError`; reserve `_ensure_success` for call sites that truly require fail-fast semantics.

---


### FINDING_13: `pr_create` missing bash create-conflict recovery
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-process-retry-output.txt
- **Severity**: latent
- **Concern**: `pr_create` only deduplicates via pre-flight `pr_for_branch` and a single non-retried `gh pr create`. It does not implement bash `recover_existing_pr_after_create_conflict` for the race where list is empty but create fails with “already exists,” risking duplicate PRs or hard failure at Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Re-run pr_for_branch after transient create errors before retrying create.
  - From dyn-process-retry-output.txt: After a non-zero create, inspect combined stdout/stderr for the conflict shape and re-query `pr_for_branch` (with the same retry policy as other reads) before surfacing failure; mirror the bash fallback URL/title extraction only if list recovery is inconclusive.

---


### FINDING_14: Python `LAUNCHER_FAILURE_CLASS` default diverges from bash waterfall
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Waterfall uses `classify_launch_failure` semantics, but ship-pr reads `LAUNCHER_FAILURE_CLASS` from capture with health default. Missing KV in capture: bash continues tiers; Python `classify` → other/unknown → false first-fixer-non-health short-circuit at cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add parse_launcher_failure_class(capture) defaulting to health; use in launch_fn; test missing KV line.

---


### FINDING_17: `test-ship-pr.sh` omits `python-lint` / `python-tests` argv cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ci-pipeline-output.txt
- **Severity**: important
- **Concern**: `ci_per_job_argv_table` / per-job argv regression stub does not assert `python-lint` → `make py-lint` and `python-tests` → `make py-test`. A broken `_per_job_argv` branch would not be caught despite workflow job classifier updates.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pipeline-output.txt: Add `check_case python-lint "" "make py-lint"` and `check_case python-tests "" "make py-test"` to the stub (or generate cases from the workflow job list like `test-ci-failed-jobs.sh` does).

---


### FINDING_18: `relevant-checks.sh` always appends `py-test` without `pytest` probe
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-ci-pipeline-output.txt, dyn-strangler-boundary-output.txt
- **Severity**: important
- **Concern**: For Python-touched paths, `maybe_append_py_lint_target` skips when lint tools are missing, but `py-test` is always appended with no `pytest` probe. Implement sessions touching `python/*.py` without `pytest` on PATH fail relevant-checks even when lint is warn-skipped.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pipeline-output.txt: Mirror the lint helper with a `maybe_append_py_test_target` that warns and skips when `pytest` is absent, or document that `pip install -r python/requirements-test.txt` is mandatory before any Python edit (and fail fast with an explicit install hint).
  - From dyn-strangler-boundary-output.txt: Mirror the py-lint guard for `pytest` (warn-and-skip when missing, document required `pip install -r python/requirements-test.txt` in `docs/linting.md` / install docs), or treat missing pytest as exit 2 with an explicit install hint rather than an opaque `make py-test` failure.

---


### FINDING_19: `relevant-checks.sh` glob omits `python/.pylintrc`
- **Reviewer(s)**: dyn-ci-pipeline-output.txt
- **Severity**: important
- **Concern**: Python routing glob lists `python/*.py` and config files but not `python/.pylintrc`. Config-only PRs may skip `py-lint`/`py-test` locally while CI `python-lint` still runs pylint over the full tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pipeline-output.txt: Add `python/.pylintrc` to the same `case` pattern (and extend `scripts/test-relevant-checks.sh` with a `.pylintrc`-only fixture).

---


### FINDING_2: Inline `gh --body` in argv (lint, security, parity)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-process-retry-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` passes PR/issue bodies via inline `--body` in argv lists. That fails `lint-gh-body-inline` on `make lint` / full lint, exposes body/title content in process listings, and can leak sensitive text in `ShipError` messages that join full argv. The live bash path uses `--body-file` after redaction; large bodies may also hit argument-size limits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Use temp files and `gh --body-file`; redact before write; never include body in exception strings
  - From cursor-specialist-edge-cases-output.txt: Use --body-file under tmpdir after redact.redact.
  - From dyn-process-retry-output.txt: Accept a filesystem path (or write body to a tmp file internally), invoke `gh pr create … --body-file <path>`, and align other create flags with `create-pr.sh` (`--base`, `--assignee @me`) so argv construction matches production behavior.

---


### FINDING_20: `ship-pr` Python job replay lacks CI install prereqs
- **Reviewer(s)**: dyn-ci-pipeline-output.txt, dyn-strangler-boundary-output.txt
- **Severity**: important
- **Concern**: Failed `python-lint` / `python-tests` replay via `make py-lint` / `make py-test` does not run `pip install` or `setup-node` as in `.github/workflows/ci.yaml`. Local fix loops can fail on missing pyright/Node or tool drift while CI is green, or burn iterations ending in `ci-local-unfixable`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pipeline-output.txt: Either wrap replay in a small helper that installs `python/requirements-dev.txt` and documents/verifies Node (matching CI), or document in `python/README.md` and ship-pr breadcrumbs that per-job replay requires the same prereqs as `make py-lint` plus Node for pyright.
  - From dyn-strangler-boundary-output.txt: Add a small replay wrapper (or extend `_per_job_argv`) that installs the pinned requirements (and documents Node for pyright) before invoking the Make targets, or gate replay with the same PATH checks used in `scripts/relevant-checks.sh:47-63` and fall back when tools are absent.

---


### FINDING_21: Transient signature parity covers only 5 of 18 bash cases
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `python/test_retry.py` transient signature parity covers 5 of 18 bash harness cases from `test-lib-net.sh`; classifier divergence on unpaired signatures goes undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; extend parity parametrize to full table.)

---


### FINDING_22: Docs omit Python CI jobs and `make lint` behavior
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `docs/linting.md` CI usage bullet omits `python-lint` and `python-tests` jobs and does not state that `make lint` always runs Python targets, so operators expect optional `py-lint` but `make lint` hard-fails without deps.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; update CI bullet and lint docs or soften Makefile deps.)

---


### FINDING_5: Unchecked `gh --json` key access
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `python/gh.py` JSON parsing uses unchecked dict key access. Malformed or schema-shifted `gh --json` output raises `KeyError` instead of `ShipError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; validate required keys after `json.loads` and raise `ShipError` with command context.)

---


### FINDING_6: Missing transient-retry tests for idempotent `gh` reads
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-process-retry-output.txt
- **Severity**: important
- **Concern**: `python/test_gh.py` does not prove that idempotent read helpers (`pr_view`, `run_list`, etc.) re-invoke on transient signatures or that mutating ops do not retry. `_retry_read` regression could ship undetected until Phase 7.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-process-retry-output.txt: Add `RecordingRunner` scenarios: (1) two transient stderr blobs then success → assert three calls and parsed record; (2) three transient failures → assert call count == `config.TRANSIENT_RETRY_MAX_ATTEMPTS` and document expected exhaustion semantics once `_retry_read` is fixed.

---


### FINDING_8: Insufficient bash redaction parity test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-redaction-parity-output.txt
- **Severity**: important
- **Concern**: `python/test_redact.py` only has one secrets and one tmpdir sample parity check. Regex drift in `python/redact.py` can ship without CI catching leakage or over-redaction relative to `scripts/test-redact-secrets.sh` and `scripts/test-redact-tmpdir-paths.sh` (30+ vectors, unterminated-PEM fail-closed, blockquote/indented PEM, full harness sets).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redaction-parity-output.txt: Add a `_bash_redact_pipeline(text)` helper that pipes through `redact-tmpdir-paths.sh | redact-secrets.sh` (matching `scripts/design-log-publish.sh:74-75` and `scripts/tracking-issue-write.sh:71-72`), then parametrized parity tests over the bash harness vectors (or extracted shared fixtures) asserting `_parity_normalize(redact.redact(v)) == _parity_normalize(pipeline(v))` for every case.
  - From dyn-redaction-parity-output.txt: Add a parity test that feeds the same `UNTERMINATED_BODY` fixture through `printf … | redact-tmpdir-paths.sh | redact-secrets.sh` and asserts identical stdout to `redact.redact()`, including absence of `tail-that-should-not-silently-survive` and presence of the truncation marker.
  - From dyn-redaction-parity-output.txt: Port the bash Section 4a `INDENTED_BODY` fixture into a parametrized parity test (Python vs `redact-secrets.sh` pipeline) asserting `<REDACTED-PRIVATE-KEY>`, no key material, and preserved prefix/suffix prose.

---


