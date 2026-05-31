### FINDING_1: ship-pr.sh modified despite plan “untouched” acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch edits `scripts/ship-pr.sh` (e.g. per-job argv around 2137–2142 / 2166–2171) even though plan acceptance treats `ship-pr.sh` as untouched and only enumerates four non-python UPDATED files. That is scope/plan drift: strangler audits and future phases may assume zero Phase 1 ship-pr edits; local `/implement` replay for `python-lint` / `python-tests` may fail or acceptance may be marked failed while relying only on the ci-failed-jobs allowlist is insufficient. The change should be documented as intentional fifth wiring (with test coverage for argv mapping) or reverted in favor of allowlist-only replay until a later phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_10: PEM redaction parity (line splitting and anchor whitespace)
- **Reviewer(s)**: dyn-redact-parity-output.txt
- **Severity**: important
- **Concern**: PEM handling diverges from bash newline-only stream model: `text.splitlines(keepends=True)` breaks on VT/FF/U+2028, not only `\n` (e.g. VT prefix yields `'\x0b<REDACTED-PRIVATE-KEY>\n'` vs bash `'<REDACTED-PRIVATE-KEY>\n'`; U+2028 before `-----BEGIN` leaves full key in bash while Python partially redacts). PEM anchor regexes use `^[ \t>]*` but bash uses `^[[:space:]>]*`, so VT/FF on the same line as `-----BEGIN` can prevent Python match and leave key material. Align splitting on `\n` only and anchors with POSIX-whitespace equivalence to bash.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-redact-parity-output.txt: Split PEM processing on `\n` only (preserving line endings manually), matching the bash stream model, and keep BEGIN/END detection on those logical lines.
  - From dyn-redact-parity-output.txt: Align the anchor with bash by using an explicit POSIX-whitespace class equivalent (e.g. `^[\t \v\f\r>]*` or a documented `\s`-based pattern scoped to the same characters bash accepts).


### FINDING_11: CI runs inline python lint/test, not `make py-lint` / `make py-test`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: CI python jobs run inline linter/pytest commands while docs and ship-pr replay use `make py-lint` / `make py-test`. Future Makefile-only flags could ship in Make targets but not CI; local ship-pr replay diverges from CI. Run `make py-lint` and `make py-test` in CI, or update docs and add a drift guard test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_12: `gh` read retries raise `ShipError` vs failed `CommandResult`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Exhausted transient read retries in `python/gh.py` (447–458) raise `ShipError` via `_ensure_success` instead of returning a failed `CommandResult` as plan wording suggests for last-result paths. Document fail-fast policy or add non-raising read helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_13: No unit test for `wrapper_rc=2` waterfall fall-through
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: No test that `wrapper_rc=2` continues the waterfall without short-circuit; regression could reintroduce short-circuit on validation failures. Add `test_waterfall_continues_on_wrapper_rc_2`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_14: `pr_for_branch` lacks direct unit tests
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `pr_for_branch` has no direct unit tests despite retry-wrapped use on the `pr_create` dedup path; retry/parsing regressions break dedup with only indirect coverage. Add stub-runner tests for success, empty list, and transient retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: `build_launch_argv` tests cover only cursor tier
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Only cursor launch argv is tested; codex and claude argv shapes are untested. Parametrize `build_launch_argv` tests across `config.FIXER_TIER_ORDER`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_19: Unguarded `json.loads` / `int` on `gh` output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `gh` JSON parsing (119–229) is unguarded; bad output raises `JSONDecodeError`/`ValueError` instead of `ShipError`, breaking uniform recovery in later phases. Wrap parsing in a helper that raises `ShipError` with redacted context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_2: Unused `parse_json_stdout` in `python/git.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unused `parse_json_stdout` helper (around 151–152) is dead API on an untested surface; remove until needed or wire into a JSON-parsing git helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_20: Transient retry classifier ordering stricter than bash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Transient classifier ordering in `python/retry.py` (45–55) is stricter than bash `lib-net.sh`; stderr like `"during request: unexpected EOF"` matches bash globs but not Python index ordering, so Python may not retry when bash would. Match bash any-order globs; add reversed-substring parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_24: Unknown `merge_method` silently defaults to squash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Unknown `merge_method` (240–244) defaults to squash; typo silently changes behavior. Validate `merge_method` and raise `ShipError`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_25: `first_tier` not in `tiers` breaks first-tier short-circuit
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: important
- **Concern**: When `first_tier` is set but not in `tiers`, rotation is skipped yet `first` stays `first_tier`, so at `idx == 0` the attempted tier fails `tier == first` and a first-tier `other` failure never short-circuits. Bash sets `first_tier` from the fixed triple offset. If `first_tier not in tier_list`, treat `first` as `tier_list[0]` after rotation (or raise), and add a unit test.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-waterfall-semantics-output.txt: If `first_tier not in tier_list`, treat `first` as `tier_list[0]` after any rotation (or raise), and add a unit test for `first_tier` absent from `tiers`.


### FINDING_4: `run_waterfall` short-circuit uses injected failure class, not launcher capture KV
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-semantics-output.txt
- **Severity**: important
- **Concern**: `run_waterfall` short-circuits on `TierAttempt.failure.failure_class == "other"` using an embedded/injected failure class, while live bash (`run_ci_fix_vendor` / `ship_pr_read_launcher_failure_class`) derives class from the launcher capture’s last `LAUNCHER_FAILURE_CLASS=` line via `parse_launcher_failure_class`, mapping missing/unknown to `health`. When KV lines are absent, `classify_launch_failure` can label the same capture `other` while parse yields `health`—e.g. `wrapper_rc=0`, `launcher_exit=1`, empty capture: classify→other, parse→health—so Python may skip remaining tiers while bash continues. Phase 7 wiring that sets `failure` via classify instead of parse would diverge from bash. Derive short-circuit input from `parse_launcher_failure_class` on the capture (extend `TierAttempt` with `failure_log` if needed), or document and test that `launch_fn` must set `failure_class` only from parse, not classify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-waterfall-semantics-output.txt: Have the short-circuit branch call `parse_launcher_failure_class` on the launcher capture path (extend `TierAttempt` with `failure_log` if needed), or document and test an invariant that `launch_fn` must set `failure.failure_class` only from `parse_launcher_failure_class`, not `classify_launch_failure`.


### FINDING_8: Unreachable `RuntimeError` after retry loop in `python/retry.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unreachable `RuntimeError` after an exhaustive retry loop (89–90); noise for readers/linters. Remove trailing raise or use `assert False` after proving loop totality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


### FINDING_9: Operator-path / tmpdir redaction parity vs bash
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-redact-parity-output.txt
- **Severity**: important
- **Concern**: Python operator-path redaction in `python/redact.py` does not reproduce bash delimiter-specific second-segment character classes in `scripts/redact-tmpdir-paths.sh` (e.g. distinct exclusions before `,`, `;`, `:`, `"}`; `\n`-prefixed variants). Python reuses `({_NOT_PATH}+)` uniformly; verified mismatches include `cwd=<OPERATOR_REPO_PATH>,bar,`, `;`/`:` analogues, `foo\n<OPERATOR_REPO_PATH>,repo,`, and JSON `"}` where `}` is allowed in the repo capture (`{"cwd":"/Users/example/my}repo"}` unchanged in bash, redacted in Python). Phase 1 requires byte-identical parity. Parity tests in `python/test_redact.py` do not cover the full `scripts/test-redact-tmpdir-paths.sh` vector set, so pytest can stay green while session paths leak in gh bodies/logs. Parametrize from every `assert_eq` in that harness (or run it and compare outputs).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-redact-parity-output.txt: Port each bash operator pattern verbatim, giving the repo capture group the same punctuation exclusions as the matching sed rule (including the `\n`-prefixed variants), rather than reusing `_NOT_PATH` uniformly.
  - From dyn-redact-parity-output.txt: For the `"}` (and other delimiter-terminated) operator patterns, give the repo capture the same excluded-character set as the corresponding bash rule, not the generic `_NOT_PATH`.
  - From dyn-redact-parity-output.txt: Port the bash tmpdir harness vectors (or the failing cases above) into parametrized pipeline parity tests so CI catches regex drift against `scripts/redact-tmpdir-paths.sh`.


