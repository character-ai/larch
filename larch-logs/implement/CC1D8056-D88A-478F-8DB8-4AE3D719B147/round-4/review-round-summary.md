# Review Round 4

- Mode: `diff`
- 9 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: eval_research_main missing require_value semantics for value-taking flags
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `eval research --baseline --smoke-test` binds `--baseline` to `--smoke-test`, passes ref regex validation, and fails at `git show` instead of exiting 2 with a clear missing-value error. Value-taking flags should reject missing values and values starting with `--`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reject missing values and values starting with `--` for all value-taking flags; exit 2 with harness-matching stderr; add pytest for trailing-flag and flag-followed-by-flag cases


### FINDING_10: Missing hostile proxy-environment bypass test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Citation validator SSRF contract requires ignoring `HTTP_PROXY` and related vars, but no test guards against proxy-aware fetch regressions for `fetch_url()` or the subprocess fetch worker.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test with proxy env vars set and injected fetch seam asserting no proxy routing
  - From dyn-test-replacement-output.txt: Add a test that sets all proxy env vars and uses an injected connector or local stub to prove requests still target the pinned public IP/host rather than the proxy.


### FINDING_11: Missing --baseline unresolved git ref test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: `eval_research` handles invalid ref syntax and success paths, but no test stubs `git show` failure for a syntactically valid unresolved ref and asserts the diagnostic exit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Stub git show failure and assert exit 2 plus diagnostic text
  - From dyn-test-replacement-output.txt: Stub `subprocess.run` to return exit `1` for a syntactically valid ref and assert `eval_research()` exits `1` with the unresolved-ref diagnostic.


### FINDING_12: Missing private IPv6 literal SSRF rejection test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Only IPv4 private literals are tested though `_private_hostname()` handles bracketed IPv6. Plan-required private IPv6 literal rejection (e.g. `https://[::1]/`, `https://[fd00::1]/`) is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add tests for ::1 or fc00:: private IPv6 URL literals
  - From dyn-test-replacement-output.txt: Add parametrized `fetch_url()` cases for `https://[::1]/`, `https://[fd00::1]/`, and similar private IPv6 hosts expecting `FAIL(ssrf-private-host)`.


### FINDING_13: Missing slow DNS timeout bounded-completion test
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: DNS coverage only exercises immediate `gaierror`. Blocking resolution via `_resolve_public_ips()` `future.result(timeout=timeout)` could stall citation validation; slow-DNS timeout behavior is untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Inject slow resolver and assert bounded completion with timeout or network-error token
  - From dyn-test-replacement-output.txt: Inject a resolver or monkeypatched `getaddrinfo` that sleeps past the timeout and assert `UNKNOWN(timeout)` or budget backfill without hanging the test run.


### FINDING_17: fetch_url() Host header includes URL userinfo
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: `fetch_url()` sends `Host: {parsed.netloc}`, which includes URL userinfo. A citation like `https://user:pass@example.com/a` connects to `example.com` but sends `Host: user:pass@example.com`, causing false validation failures and leaking embedded credentials into an HTTP header.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Build `Host` from `parsed.hostname` plus explicit port, or reject URLs with `parsed.username` / `parsed.password`.


### FINDING_18: Quiet routing tests use broken pre-dup2 fd-3 harness
- **Reviewer(s)**: dyn-test-replacement-output.txt
- **Severity**: important
- **Concern**: Research and eval quiet tests pre-`dup2` a scratch file onto fd 3, but `logging_util.quiet_init()` immediately rebinds fd 3 to the captured stdout pipe. That clobbers the test file handle, so `fd3.txt` is usually empty and assertions mostly check pipe stdout instead of post-`quiet_init` fd-3 contract routing and log separation. Plan-required quiet-enabled coverage for all KV-emitting verbs is not actually validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-test-replacement-output.txt: Drop the pre-`dup2` harness. Run each verb with quiet enabled, assert KV lines appear on the captured contract stream, and assert they are absent from the quiet log file and from stderr.
  - From dyn-test-replacement-output.txt: Remove this test or fold it into the parametrized quiet test with the corrected harness above, covering `validate-citations`, `render-findings-batch`, `run-planner`, and `banner`.
  - From dyn-test-replacement-output.txt: Use the same corrected quiet harness as research tests: capture the contract stream, read the quiet log path from env, and assert KV output is on fd 3 only.


### FINDING_5: validate_citations uncaught errors skip fail-soft sidecar and SUMMARY
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: `validate_citations` lacks a bash EXIT-trap equivalent. Disk/permission errors, mid-run exceptions, or uncaught `OSError` in `check_fileline()` can exit non-zero without writing a degraded sidecar or final `SUMMARY=`, breaking fail-soft Step 3 splice behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Wrap validation in try/except/finally; always write degraded sidecar + SUMMARY on validation paths; return 0 except usage/flag errors
  - From codex-generic-output.txt: Catch `OSError` around the line-count read and return a ledger result such as `UNKNOWN(file-unreadable)`.


### FINDING_8: Accidental tmp-case5b.sh debug script committed at repo root
- **Reviewer(s)**: cursor-specialist-testing-output.txt, codex-generic-output.txt
- **Severity**: important
- **Concern**: A local scratch script with a hardcoded machine path and `jq` dependency ships in the plugin tree. It is not wired into `make lint`, can confuse operators, and cannot work outside the author's checkout.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Delete tmp-case5b.sh before merge; keep coverage in test-collect-agent-bash32.sh if needed
  - From codex-generic-output.txt: Remove `tmp-case5b.sh` from the branch.


