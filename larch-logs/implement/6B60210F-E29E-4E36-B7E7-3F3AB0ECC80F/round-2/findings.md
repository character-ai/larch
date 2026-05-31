Aggregating reviewer inputs into a merged finding list: grouping by behavioral risk, preserving severity merge rules, and separating out-of-scope items.
Structured finding list from the supplied reviewer inputs (merged by behavioral risk; first-seen order for IDs).

---

### FINDING_1: `make lint` hard-requires Python toolchain
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-ci-pipeline-output.txt, dyn-strangler-boundary-output.txt
- **Severity**: important
- **Concern**: The `lint` target now depends on `py-lint` and `py-test` before harnesses and pre-commit. Contributors without ruff/pylint/pyright/pytest (and Node for pyright) cannot run `make lint` on bash-only changes; this conflicts with Phase 1 scope (standalone `make py-lint` / `make py-test` and CI jobs only) and widens local-vs-CI drift because CI runs separate `python-lint` / `python-tests` jobs with installs, not the umbrella `lint` target.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-pipeline-output.txt: Either remove `py-lint`/`py-test` from the `lint` prerequisite chain (keep them as explicit/CI-only targets), or add install/bootstrap steps or documented prerequisites in `docs/linting.md` and the `lint` comment block.
  - From dyn-strangler-boundary-output.txt: Drop `py-lint` and `py-test` from the `lint` prerequisite list; keep them as explicit/CI/relevant-checks-only targets so the strangler tree stays opt-in until Phase 7.

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

### FINDING_3: Foundation context/outcome/logging modules unwired
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `python/outcomes.py`, `python/run_context.py`, and `python/logging_util.py` are test-only with no runtime wiring. There is no proof that `StepResult` / `RunContext` / journal APIs work on a real orchestration path before later phases.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot provided a fix beyond generic “address concern”; add minimal composition smoke or document API-only status in `python/README.md`.)

---

### FINDING_4: Live `ship-pr.sh` adds Python CI job argv mapping
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `_per_job_argv` gains `python-lint` / `python-tests` cases mapping to `make py-lint` / `make py-test`. This contradicts strict “ship-pr untouched” Phase 1 acceptance but is needed for local CI-fix parity; should be an explicit strangler exception or deferred until cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot.)

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

### FINDING_7: Operator-path redaction regex looser than bash
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `python/redact.py` operator-path punctuation regexes may be looser than bash `sed` classes in `redact-tmpdir-paths.sh`. Some `/Users/.../...` punctuation-boundary paths may not match bash redaction parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; align `NOT_PATH`/suffix exclusions with bash and extend parity tests.)

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

### FINDING_9: Duplicate `_ensure_success` in `git.py` and `gh.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `_ensure_success` is duplicated in `python/git.py` and `python/gh.py`, increasing maintenance when error messaging changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; share one helper when a third module needs it.)

---

### FINDING_10: Duplicated agent output/refusal scan paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `python/agents.py` duplicates parse/refusal scans for sidecar vs `output_file`, raising classification drift risk vs bash on a single path.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; factor shared scan helper.)

---

### FINDING_11: Weak `test_config.py` constant coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Constant coverage in `python/test_config.py` is weaker than plan wording; regressions in new config constants may go unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; assert full documented constant set.)

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

### FINDING_15: `binary_present` bool API diverges from bash truthiness
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `binary_present` bool API in `python/agents.py` diverges from bash `1`/`true`/`yes` rules; passing string `"0"` skips binary-missing classification in Python.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; normalize like bash or require bool at API boundary.)

---

### FINDING_16: `launch_tier` invokes `.sh` without explicit `bash`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `launch_tier` runs `scripts/launch-*-ci.sh` without explicit `bash`; non-executable script bits cause `EACCES` from `proc.run`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; prepend `bash` to argv or document executable requirement.)

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

### FINDING_23: Plan says `ship-pr.sh` untouched but branch edits it
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Plan acceptance says `scripts/ship-pr.sh` is untouched, but the branch edits `_per_job_argv` for python jobs — documentation/acceptance mismatch with additive CI job mapping.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; update plan/acceptance text to include ship-pr job argv mapping as intentional.)

---

## Out of scope (Piece 2)

### OOS_1: [OUT_OF_SCOPE] Unreachable `RuntimeError` in `python/retry.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unreachable `RuntimeError` after exhaustive loop; linters may warn with no runtime effect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; remove dead raise or satisfy linter.)

---

### OOS_2: [OUT_OF_SCOPE] Large copied `python/.pylintrc`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: 660-line copied pylint config is repo noise only for Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; accept for Phase 1 or trim in follow-up.)

---

### OOS_3: [OUT_OF_SCOPE] Journal/breadcrumb writers do not redact payloads
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `python/logging_util.py` journal writers do not redact payloads; secrets in journal fields could hit disk when ship-pr Python path is wired.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; redact at write time when wiring ship-pr Python path.)

---

### OOS_4: [OUT_OF_SCOPE] `test_stdlib_only.py` misses dynamic `__import__`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Stdlib test misses non-constant dynamic `__import__`; non-literal import could bypass stdlib enforcement.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; extend AST visitor or ban pattern in review.)

---

### OOS_5: [OUT_OF_SCOPE] `docs/linting.md` CI bullet missing Python jobs
- **Reviewer(s)**: dyn-ci-pipeline-output.txt
- **Severity**: nit
- **Concern**: CI usage bullet still lists legacy jobs but not new `python-lint` / `python-tests` or split requirements files.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot; doc pass for operators.)

---

### OOS_6: [OUT_OF_SCOPE] `python/README.md` omits Node for pyright
- **Reviewer(s)**: dyn-ci-pipeline-output.txt
- **Severity**: nit
- **Concern**: README documents pip installs but not that `make py-lint` / pyright needs Node on the host (CI supplies via `setup-node`; local replay does not).
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct verbatim fix per slot.)

---

### OOS_7: [OUT_OF_SCOPE] `retry.py` EOF/git-fetch ordering parity verified OK
- **Reviewer(s)**: dyn-process-retry-output.txt
- **Severity**: nit
- **Concern**: Reviewer attests ordered substring checks match bash `case` left-to-right semantics; parity vectors for non-transient cases are correct — informational, not a defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix; positive verification.)

---

### OOS_8: [OUT_OF_SCOPE] `launch_tier` without `bash` prefix acceptable
- **Reviewer(s)**: dyn-process-retry-output.txt
- **Severity**: nit
- **Concern**: Reviewer attests `launch_tier` mirrors ship-pr executable-script invocation when `cwd` is repo root and scripts remain `+x`.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix; positive verification.)

---

### OOS_9: [OUT_OF_SCOPE] `make lint` Python deps intentional per reviewer
- **Reviewer(s)**: dyn-process-retry-output.txt
- **Severity**: nit
- **Concern**: Reviewer characterizes `make lint` requiring `py-lint`/`py-test` as intentional dev-ergonomics change, not a subprocess defect — conflicts with in-scope FINDING_1; retained as OOS opinion only.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No fix direction.)

---

### OOS_10: [OUT_OF_SCOPE] No streaming redact API in Python
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: `python/redact.py` only batch `redact(text)`; bash `--streaming` with `in_pem` state matters at Phase 7 for chunked logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Defer to cutover.)

---

### OOS_11: [OUT_OF_SCOPE] Inconsistent bash redact pipeline order
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: Bash callers use both `tmpdir|secrets` and `secrets|tmpdir`; Python hard-codes tmpdir-then-secrets. Resolve at Phase 7 cutover.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Resolve ordering at cutover.)

---

### OOS_12: [OUT_OF_SCOPE] `create-one.sh` secrets-only redaction on live path
- **Reviewer(s)**: dyn-redaction-parity-output.txt
- **Severity**: nit
- **Concern**: `skills/issue/scripts/create-one.sh` still uses `redact-secrets.sh` only; session tmpdir paths can reach public issue bodies pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Pre-existing; outside branch.)

---

### OOS_13: [OUT_OF_SCOPE] Plan vs ship-pr six-line doc drift
- **Reviewer(s)**: dyn-strangler-boundary-output.txt
- **Severity**: nit
- **Concern**: Plan says `ship-pr.sh` untouched; branch adds six lines for CI replay — reconcile in follow-up docs, not a runtime defect.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Doc reconciliation only.)

---

### OOS_14: [OUT_OF_SCOPE] Routing glob also omits `python/README.md`
- **Reviewer(s)**: dyn-strangler-boundary-output.txt
- **Severity**: nit
- **Concern**: Low severity: edits confined to `python/README.md` may skip py targets while affecting the tree.
- **Suggested revisions (informational for voters; coder decides)**:
  - (Low severity; optional glob extension.)

---

### OOS_15: [OUT_OF_SCOPE] No `LARCH_SHIP_PR_IMPL` wiring yet (expected Phase 1)
- **Reviewer(s)**: dyn-strangler-boundary-output.txt
- **Severity**: nit
- **Concern**: No reads of `LARCH_SHIP_PR_IMPL`; Python modules not wired into bash state machine before Phase 7; skills do not reference `python/` — expected strangler boundary.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No action for Phase 1.)

---

**Summary**: 23 in-scope merged findings (`FINDING_1`–`FINDING_23`), 15 out-of-scope blocks (`OOS_1`–`OOS_15`). Highest-density merges: Makefile `lint` (7 slots), inline `gh --body` (4), transient `gh` tests (4), redact parity tests (2+3 dyn), `relevant-checks` pytest guard (3), ship-pr replay prereqs (2).
