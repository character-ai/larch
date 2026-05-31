Normalizing the supplied reviewer findings into a merged structured list per the aggregator rules.

### FINDING_1: ship-pr.sh modified despite plan “untouched” acceptance
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: The branch edits `scripts/ship-pr.sh` (e.g. per-job argv around 2137–2142 / 2166–2171) even though plan acceptance treats `ship-pr.sh` as untouched and only enumerates four non-python UPDATED files. That is scope/plan drift: strangler audits and future phases may assume zero Phase 1 ship-pr edits; local `/implement` replay for `python-lint` / `python-tests` may fail or acceptance may be marked failed while relying only on the ci-failed-jobs allowlist is insufficient. The change should be documented as intentional fifth wiring (with test coverage for argv mapping) or reverted in favor of allowlist-only replay until a later phase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_2: Unused `parse_json_stdout` in `python/git.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unused `parse_json_stdout` helper (around 151–152) is dead API on an untested surface; remove until needed or wire into a JSON-parsing git helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: Duplicated parse/refusal classification in `python/agents.py`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicated parse/refusal classification for `sidecar` vs `output_file` (1148–1159); one path can get a parity fix without the other, breaking `classify_launch_failure` parity. Extract a shared text-classification helper used by both branches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: `run_waterfall` short-circuit uses injected failure class, not launcher capture KV
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-waterfall-semantics-output.txt
- **Severity**: important
- **Concern**: `run_waterfall` short-circuits on `TierAttempt.failure.failure_class == "other"` using an embedded/injected failure class, while live bash (`run_ci_fix_vendor` / `ship_pr_read_launcher_failure_class`) derives class from the launcher capture’s last `LAUNCHER_FAILURE_CLASS=` line via `parse_launcher_failure_class`, mapping missing/unknown to `health`. When KV lines are absent, `classify_launch_failure` can label the same capture `other` while parse yields `health`—e.g. `wrapper_rc=0`, `launcher_exit=1`, empty capture: classify→other, parse→health—so Python may skip remaining tiers while bash continues. Phase 7 wiring that sets `failure` via classify instead of parse would diverge from bash. Derive short-circuit input from `parse_launcher_failure_class` on the capture (extend `TierAttempt` with `failure_log` if needed), or document and test that `launch_fn` must set `failure_class` only from parse, not classify.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-waterfall-semantics-output.txt: Have the short-circuit branch call `parse_launcher_failure_class` on the launcher capture path (extend `TierAttempt` with `failure_log` if needed), or document and test an invariant that `launch_fn` must set `failure.failure_class` only from `parse_launcher_failure_class`, not `classify_launch_failure`.

### FINDING_5: `run_waterfall` lacks bash skip-tier / `waterfall_iter` semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `run_waterfall` does not implement bash skip-tier / `waterfall_iter` behavior: bash can skip the rotated first tier when the claude launcher is missing; codex `other` failure does not short-circuit the same way in bash. Python may short-circuit at index 0 incorrectly. Filter tiers before `run_waterfall` or add a skip hook matching `run_ci_fix_vendor`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_6: Launcher invocation: cwd-relative paths, executability, and argv shape
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `build_launch_argv` / launcher `proc.run` use cwd-relative `scripts/launch-*.sh` without a `bash` prefix, assuming repo-root cwd and executable bits. From another cwd, without `+x`, or with a consumer repo’s own `scripts/launch-*.sh`, invocation can fail or execute the wrong script (Phase 7 security: attacker-controlled path as operator). Resolve launchers from `CLAUDE_PLUGIN_ROOT` / `RunContext` with absolute paths, prepend `bash` where ship-pr does, and test cwd independence—parity with `SCRIPT_DIR` / ship-pr launcher wiring.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_7: Duplicate stub `Runner` implementations across test modules
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Duplicate stub `Runner` implementations in `python/test_git.py` and elsewhere; harness fixes must be duplicated. Share one `RecordingRunner`/`StubRunner` in a colocated test helper module.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

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

### FINDING_16: Bash parity tests skip when bash is unavailable
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Bash parity tests skip when bash is missing, so off-CI pytest on macOS/Windows can pass without parity; drift merges until Ubuntu CI fails. Restrict skip to missing helper scripts only, or fail when `CI=true` and bash is missing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: `test-relevant-checks.sh` lacks all-tools-present happy path for Python
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Relevant-checks harness tests Python skip paths but not the happy path when ruff, pylint, pyright, and pytest are on PATH; routing regression when all tools present may go untested. Add a section stubbing tools and asserting both `py-lint` and `py-test` make targets run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: `relevant-checks.sh` skips py-lint/py-test when tools absent
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `py-lint`/`py-test` skipped when tools absent (47–76); Python-only branch can pass relevant-checks locally without pytest/ruff while CI would fail. Fail closed on python changes or require an explicit skip flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: Unguarded `json.loads` / `int` on `gh` output
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `gh` JSON parsing (119–229) is unguarded; bad output raises `JSONDecodeError`/`ValueError` instead of `ShipError`, breaking uniform recovery in later phases. Wrap parsing in a helper that raises `ShipError` with redacted context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Transient retry classifier ordering stricter than bash
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Transient classifier ordering in `python/retry.py` (45–55) is stricter than bash `lib-net.sh`; stderr like `"during request: unexpected EOF"` matches bash globs but not Python index ordering, so Python may not retry when bash would. Match bash any-order globs; add reversed-substring parity tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: `failed_jobs` silently skips malformed job dicts
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `failed_jobs` (362–364) skips malformed job dicts; API shape change could yield an empty failed list with no error. Raise `ShipError` on non-dict job entries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: `proc.run` does not normalize missing binary
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `proc.run` (48–56) does not normalize a missing binary; `FileNotFoundError` escapes instead of structured failure for missing `gh`/`git`. Wrap into `ShipError` or synthetic `CommandResult`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_23: Custom retry predicate can retry successful calls
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Custom predicate in `retry.py` (76–81) can retry when `predicate` is true with `rc == 0`, causing extra attempts and backoff. Ignore transient signature when `rc == 0` or document predicate contract.
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

### OOS_1: [OUT_OF_SCOPE] gitleaks allowlist for python test paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: gitleaks allowlist for `python/test_redact.py` and python caches (`SECURITY.md` 242–246, `.gitleaks.toml` 100–103) is an intentional blind spot; real credentials under allowlisted python paths would not be caught by gitleaks layers 1–2 (TruffleHog may still catch live secrets). Pre-existing policy; keep fixtures synthetic; do not expand allowlist without review.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Bash streaming PEM mode not ported to Python
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Bash redact supports `--streaming` PEM mode (`scripts/test-redact-secrets.sh` 98–115); Python has no streaming API. Not on this branch’s live path; track for a later phase or document intentional non-port in Phase 1.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] Refusal regex on `output_file` only matches bash parity
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: `classify_launch_failure` applies `_REFUSAL_RE` only to `sidecar` and `_PARSE_RE` to both `sidecar` and `output_file`, matching `external_classify_launch_failure` in bash. The parity vector with refusal only in `output_file` encodes `other`/`unknown`, not `refusal`—not a regression.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_4: [OUT_OF_SCOPE] Rotation / `idx == 0` aligns with bash when `first_tier` in list
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: When `first_tier` is in `tier_list`, rotation makes `tier_list[0] == first_tier`, so `idx == 0` aligns with bash `waterfall_iter == 0`; `wrapper_rc == 2` fall-through matches bash because short-circuit requires `wrapper_rc == 0`.
- **Suggested revisions (informational for voters; coder decides)**:

### OOS_5: [OUT_OF_SCOPE] Branch commit inventory (informational)
- **Reviewer(s)**: dyn-waterfall-semantics-output.txt
- **Severity**: nit
- **Concern**: Branch commits since merge-base with main: `a6fb8beac`, `929f244bf`, `a8a657d8e` / `eca4b21ec`, `0ed5744ec` / `202f93e28` (review rounds).
- **Suggested revisions (informational for voters; coder decides)**:

---

**Merge notes (brief):** 41 raw slots consolidated to 25 in-scope findings and 5 out-of-scope blocks. Largest merges: ship-pr plan drift (3→1), waterfall failure-class source (4→1), launcher cwd/argv/security (3→1), operator-path redact + test gaps (4→1), PEM line/anchor issues (2→1). FINDING_3 (extract shared classifier) kept separate from OOS_3 (bash-intentional refusal-on-output_file behavior). OOS_3–OOS_5 are attestations, not action items.
