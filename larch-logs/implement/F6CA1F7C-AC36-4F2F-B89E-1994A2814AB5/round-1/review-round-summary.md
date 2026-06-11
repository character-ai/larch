# Review Round 1

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_10: Pause save/load origin-fallback repo guard lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The publish harness covers origin-fallback omission, but pause save/load do not. They could pass origin-fallback `--repo` while publish tests stay green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add log assertion that issue-wire CLI omits --repo on origin-fallback-only resolution.


### FINDING_13: design-route lacks a leading-hyphen title callsite test
- **Reviewer(s)**: dyn-cutover-fidelity-output.txt
- **Severity**: latent
- **Concern**: CLI-layer tests cover leading-hyphen titles, but `design-route.sh` lacks a callsite fixture proving argv forwarding still treats `-leading-hyphen` as a title instead of a flag.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-cutover-fidelity-output.txt: Add a design-route harness case (or extend an existing design integration test) that sets `ISSUE_TITLE='-leading-hyphen'` and asserts title-eligibility routing still parses KVs instead of treating the title as a flag.


### FINDING_2: ISSUE_WIRE_REPO can use origin-fallback repos for issue writes
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `design-publish.sh` and pause save/load paths may pass a repo resolved from git origin into issue-wire writes. That can edit the wrong repo instead of using only explicit operator input or `gh repo view` resolution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Track an issue-wire-safe repo separately and set it only from an explicit operator repo or gh repo view success.
  - From codex-specialist-edge-cases-output.txt: Pass issue-wire --repo only for operator-supplied or gh-only-resolved repos, otherwise omit it


### FINDING_20: Quiet-mode usage diagnostics go to the quiet log instead of operator stderr
- **Reviewer(s)**: dyn-kv-routing-contracts-output.txt
- **Severity**: important
- **Concern**: Several KV entrypoints call `quiet_init()` before usage validation, then print diagnostics to `sys.stderr`. Under quiet mode, those messages are redirected to the quiet log instead of the operator-visible diagnostic stream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-kv-routing-contracts-output.txt: Add a small `logging_util` diagnostic helper (mirror `voting._plain_diagnostic` / bash `larch_err`: write to fd 4 when quiet is active, else `sys.stderr`) and route all post-`quiet_init` usage failures in `plan_block_read_main`, `_run_named_block_cli`, and siblings through it instead of bare `print(..., file=sys.stderr)`.


### FINDING_5: Quiet-mode issue-wire KV routing lacks real contract coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-kv-routing-contracts-output.txt
- **Severity**: important
- **Concern**: `python/test_issue_wire.py` does not adequately test KV output under active quiet mode. Direct tests can also redirect stdout/stderr through `quiet_init`, making assertions order-dependent and leaving plan-review-loop capture regressions undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add subprocess test with quiet parent env asserting KV lines on child stdout.
  - From codex-specialist-testing-output.txt: Monkeypatch issue_wire.logging_util.quiet_init to no-op in direct unit tests, and use subprocess tests for real quiet-mode routing.
  - From dyn-kv-routing-contracts-output.txt: Add fd-3 capture tests modeled on `test_clarify_state_emits_kv_on_fd3_under_quiet_mode`: `monkeypatch.delenv(LARCH_QUIET_DISABLE)`, set a session tmpdir, redirect fd 1 to a pipe, invoke `plan_block_read_main` / malformed `plan_block_strip_body_main`, and assert KVs appear on the contract stream while incidental stdout stays off it.


### FINDING_6: Invalid-repo gh failure path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `plan-block read` lacks coverage for the legacy invalid-repo `gh` failure path. A regression could emit `ERROR=invalid-repo` and violate forked `/implement` preflight expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add mocked gh issue view failure test: exit 2, FAILED=true, no invalid-repo token.


### FINDING_7: Redaction failure write path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `named-block` and `plan-block` write do not test the redaction failure exit-3 path. A regression could change exit code or KV shape.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Monkeypatch redactor to raise ShipError(redaction:...); assert exit 3 and FAILED=true KVs.


### FINDING_8: tracking-issue-write mark-false-positive subprocess path lacks coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-tracking-issue-write.sh` does not cover `mark-false-positive` insert-signal-marker subprocess behavior. CLI failure handling or leading-hyphen title parsing can regress undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add mark-false-positive cases for CLI failure envelope and hyphen-prefixed title.


