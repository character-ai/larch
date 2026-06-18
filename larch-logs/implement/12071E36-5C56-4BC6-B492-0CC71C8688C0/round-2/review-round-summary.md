# Review Round 2

- Mode: `diff`
- 6 accepted, 10 rejected (4 neutral)

## Accepted Findings

### FINDING_1: resolve_repo() lacks parity with scripts/resolve-repo.sh
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `resolve_repo()` inlines URL parsing instead of delegating to `scripts/resolve-repo.sh` / `scripts/github-remote-repo.sh`. When `gh repo view` fails, `ssh://git@github.com/org/repo.git` remotes are misparsed (colon-split yields `//git@github.com/org/repo`, regex rejects it, `REPO` stays empty). If `gh` is missing, `subprocess.run(["gh", ...])` can raise `OSError` before the origin fallback runs. Numeric `/design` routes may crash or run `gh issue view` without `--repo` or against the wrong context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Shell out to scripts/resolve-repo.sh (or port github-remote-repo.sh regexes) and keep bash fail-closed semantics on resolution failure.
  - From codex-generic-output.txt: Catch `OSError` around the `gh` probe, then reuse the same remote URL patterns as `scripts/github-remote-repo.sh` for `git@github.com:owner/repo` and `(https|ssh|git)://...github.com/owner/repo`.


### FINDING_11: step0_session_main propagates degraded-tools-gate non-zero exit
- **Reviewer(s)**: dyn-lifecycle-parity-output.txt
- **Severity**: important
- **Concern**: `step0_session_main` ends with `return gate.returncode`. Retired `design-step0-session.sh` ignored degraded-tools-gate exit status and always finished at exit 0 after emitting `STEP0_STATUS` / `DEGRADED_*` KVs. If the gate subprocess fails unexpectedly (crash, `argparse` error, etc.) after session setup succeeded, Step 0a now aborts even though parse KVs, setup output, and degraded status were already relayed. That can block `/design` on a non-actionable infra failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-lifecycle-parity-output.txt: Always `return 0` after relaying gate stdout and printing summary KVs; log gate non-zero to `execution-issues.md` instead of propagating its rc.


### FINDING_15: Makefile -k filter and missing pytest for step0_abort, step0_ap, step1d7
- **Reviewer(s)**: dyn-launcher-cutover-output.txt, dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: `test-design-step0-init` uses a `-k` filter that includes `step0_abort` and `step0_ap`, but `python/test_design_lifecycle.py` has no matching tests for `step0_abort_cleanup_main`, `step0_ap_continue_main`, or `step1d7_main`. The plan and acceptance criteria require a pytest that `step1d7` emits `SKIP_APPROVE_REQUESTED=true|false` from `run-params.json`, but no `test_step1d7_*` exists. Retired shell harnesses are gone, so targeted relevant-checks runs can pass while abort cleanup, AP-continue sentinel ordering, and `SKIP_APPROVE_REQUESTED` emission stay unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-cutover-output.txt: Add pytest coverage for those three verbs (as the plan required) and align the Makefile `-k` expression with actual test names; include `step1e` in a targeted target because Gate A/B re-entry depends on it.
  - From dyn-retirement-coverage-output.txt: Add pytest covering both `skip_approve_requested: true` and `false` (plus missing/malformed `run-params.json` defaulting to `false`), and include `step1d7` in the Makefile `-k` selector if a focused target is added.


### FINDING_19: step1d5 collect-mode pytest coverage incomplete after shell harness retirement
- **Reviewer(s)**: dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: The deleted `test-design-step1d5.sh` covered seven collect-mode contracts (missing paths, per-slot stdout relay, non-zero collector logging, launch-failure idempotency, dirty sidecar override, clean checkpoint, argv forwarding). The new pytest suite only covers pause-before-collect and launch-failure sentinel idempotency; five retired scenarios have no pytest replacement despite the plan saying harness coverage moves to `python/test_design_lifecycle.py`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-retirement-coverage-output.txt: Port the remaining shell-harness cases as pytest tests (stub `subprocess.run` like the existing two tests) so `make test-design-step1d5` retains equivalent coverage.


### FINDING_6: _decode_shell_assignment_value uses bash eval on loaded env files
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `_decode_shell_assignment_value` uses bash `eval` to decode env assignment values loaded from session/parsed env files. A tampered or malformed value in an allowlisted env file could execute shell during decode when `step0-route`/`init` load parsed env or `source-env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Implement a pure-Python bash %q decoder for values written by write_bash_quoted_env; avoid eval on load or gate it behind an explicit debug-only fallback.


### FINDING_8: parse-argv validation branches lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-retirement-coverage-output.txt
- **Severity**: important
- **Concern**: Plan-required `parse-argv` validation branches in `_validate_parse_result` lack pytest coverage beyond the template-literal case. Disallowed flags, `rc=3` + `VALIDATION_ERROR`, `rc=0` with non-empty `VALIDATION_ERROR`, or invalid `POSITIONAL_KIND` could regress without CI failure; `/design` may proceed to session setup with stale or invalid argv bindings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add monkeypatched _run_parse_argv tests for rc=3+VALIDATION_ERROR, rc=0+VALIDATION_ERROR, and invalid POSITIONAL_KIND asserting exit 1 and no session setup.
  - From dyn-retirement-coverage-output.txt: Add monkeypatched `_run_parse_argv` tests for rc `3`, rc `0` with non-empty `VALIDATION_ERROR`, and invalid `POSITIONAL_KIND`, asserting stderr text and exit code `1`.


