### FINDING_1: Missing contract and env documentation
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Concern**: The plan changes probe stamp semantics, negative TTL behavior, and Cursor preflight retry behavior without updating the related script and configuration contract docs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add minimal doc updates for the changed contracts in the same PR: check-reviewers stamp/env semantics, lib-cursor-auth preflight retry/test knob, and configuration docs for LARCH_PROBE_NEGATIVE_TTL_SECONDS


### FINDING_2: Option B can run the full live-probe retry loop
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: After `cursor_auth_preflight` returns 2, Option B may still run the full live-probe retry loop, causing long delays on Darwin hosts without Cursor auth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: On _pf_rc==2 run at most one live probe or skip the loop when Option A retries still return 2


### FINDING_3: Preflight stderr can mislead before live-probe recovery
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-preflight-gate-regression
- **Severity**: important
- **Concern**: Preflight failure text is emitted before the Option B live probe runs, so a transient preflight miss can show a scary false failure even when the live probe succeeds and Cursor is marked present.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Defer actionable stderr until live probe fails or use a preflight-miss retry breadcrumb when callers will continue probing
  - From Cursor-dyn-preflight-gate-regression: Suppress or defer preflight stderr when _pf_rc=2 and live probe will run; emit actionable message only if live probe also fails


### FINDING_4: Missing negative regression coverage for persistent preflight and live-probe failure
- **Reviewer(s)**: Codex-dyn-preflight-gate-regression
- **Severity**: important
- **Concern**: The planned tests cover preflight failure followed by live success, but do not pin the Darwin path where preflight keeps failing and the live probe also fails. That leaves the new negative behavior and stderr suppression unverified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-preflight-gate-regression: Add one t-optb-negative test: Darwin test mode with LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=1,1,1, a cursor stub that prints a unique Security-code marker to stderr and exits nonzero, and assertions that CURSOR_PRESENT=false is emitted and the raw live-probe marker does not appear on script stderr.


### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/check-reviewers.sh:281-314
- **Concern**: [SCOPE-REDUCTION] Option B unconditional live-probe fallback after preflight exit 2. Scenario: After Option A exhausts 3 keychain reads on a Darwin host with no Cursor credentials, check-reviewers still runs up to MAX_AUTH_RETRIES full cursor agent probes (each up to LARCH_PROBE_TIMEOUT_SECONDS) instead of bailing immediately; bootstrap and repeated reviewer probes become much slower with no change to the final CURSOR_PRESENT=false outcome
- **Proposed resolution**: Drop Option B from the plan and ship Option A + Option C only; if defense-in-depth is still wanted, gate a single live-probe attempt behind an explicit opt-in env knob rather than always running the full retry loop after a confirmed preflight failure


### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/check-reviewers.sh:281-312
- **Concern**: [SCOPE-REDUCTION] Preflight auth miss falls through to the full Cursor auth retry loop. Scenario: A real missing keychain entry can now launch Cursor up to MAX_AUTH_RETRIES times, with up to LARCH_PROBE_TIMEOUT_SECONDS per attempt, regressing the fast-fail path that preflight exists to protect
- **Proposed resolution**: Keep the live-probe fallback, but cap the _pf_rc==2 path to one live probe attempt; keep the existing retry loop only when preflight succeeds




### FINDING_1: Option B fallback must mirror Cursor auth setup chain
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The preflight-exit-2 live fallback can diverge from the normal Cursor probe path because the plan does not explicitly require `cursor_preread_service_token`, `cursor_auth_export_env`, and `cursor_launcher_setup_private_config_dir` before the single `larch_run_one_cursor_probe`. A literal implementation may false-negative or skip launcher parity.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Spell out that the preflight=2 branch runs the same setup chain as the preflight=0 path (preread export_env private config dir) then exactly one larch_run_one_cursor_probe then cleanup and stamp write
  - From Cursor-Innovation: Mirror the preflight-0 branch: run the same `&&` prep chain before the single live probe; only skip the probe when prep fails; always run `cursor_launcher_cleanup_private_config_dir` afterward.
  - From Cursor-Pragmatic: Spell out the same `&&` setup chain (and the same setup-failure short-circuit) before the single live probe on preflight exit 2; keep `cursor_launcher_cleanup_private_config_dir` after both success and failure.
  - From Cursor-Requirements: Add an explicit step: on preflight exit 2 run the same setup trio as the success path (only skip the full MAX_AUTH_RETRIES loop on private-config hard failure); then run one larch_run_one_cursor_probe; then cleanup


### FINDING_3: New Cursor stub tests must pin hermetic auth-test environment
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Concern**: The new Option B tests use Darwin preflight failure stubs but the plan does not require the hermetic environment variables used by existing Cursor stub tests. On Darwin CI, this can hit the real keychain or produce unrelated flakes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Require LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 LIB_CURSOR_AUTH_TEST_UNAME=Darwin LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ=... and CURSOR_API_KEY= on every new t-optb and t-optc Cursor case mirroring t0/t1/t2


### FINDING_4: One-shot fallback must satisfy AUTH_ATTEMPT contract and disable retries
- **Reviewer(s)**: Codex-Arch, Cursor-Pragmatic, Codex-Pragmatic, Cursor-dyn-stamp-caller-coverage, Codex-dyn-stamp-caller-coverage, Codex-dyn-test-mock-priority
- **Severity**: important
- **Concern**: The one-shot preflight-exit-2 branch calls `larch_run_one_cursor_probe` outside the existing retry loop, but that helper reads `AUTH_ATTEMPT` under `set -u` and returns retry sentinel `2` for auth-classified failures when retries remain. Without an explicit setup and terminal-failure rule, the path can abort, retry, or fail to write `CURSOR_PRESENT=false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before the one live fallback call, set `AUTH_ATTEMPT` to a value that disables retries, for example `AUTH_ATTEMPT=$MAX_AUTH_RETRIES`, or add an explicit no-retry wrapper; keep the new no-full-loop test auth-classified so it proves one invocation and no unbound-variable abort
  - From Cursor-Pragmatic: On the preflight-exit-2 branch set `AUTH_ATTEMPT=1`, call the probe once, treat any non-zero `_one_rc` (including `2`) as failure with no loop, then write the stamp.
  - From Codex-Pragmatic: In the plan, require the preflight-exit-2 branch to set AUTH_ATTEMPT=$MAX_AUTH_RETRIES before the single larch_run_one_cursor_probe call, capture its rc, and treat any nonzero rc as CURSOR_PRESENT=false.
  - From Cursor-dyn-stamp-caller-coverage: In the preflight-exit-2 branch, set AUTH_ATTEMPT=1 (same as the existing loop entry at 294) immediately before the single larch_run_one_cursor_probe call
  - From Codex-dyn-stamp-caller-coverage: State that the preflight-exit-2 one-shot path must initialize AUTH_ATTEMPT before calling larch_run_one_cursor_probe, preferably AUTH_ATTEMPT=$MAX_AUTH_RETRIES to force a single non-retry result, then map any nonzero return to CURSOR_PRESENT=false.
  - From Codex-dyn-test-mock-priority: Set AUTH_ATTEMPT before the one-shot fallback, preferably AUTH_ATTEMPT="$MAX_AUTH_RETRIES", and treat any nonzero probe result as the single fallback failure


### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:31-35,61-69,123-133
- **Concern**: [SCOPE-REDUCTION] Public quiet-mode env knob over-serves a one-call deferral need. Scenario: Adding LARCH_CURSOR_AUTH_PREFLIGHT_QUIET creates a new shared lib and docs contract just so check-reviewers can suppress one preflight message before its fallback. If set globally, it can also hide direct launcher guidance.
- **Proposed resolution**: Do not add the public env knob or lib-doc surface. In check-reviewers.sh, redirect cursor_auth_preflight stderr to a temp file and replay it only if the one live fallback fails, or keep the existing immediate message if you want the smaller patch.




### FINDING_5: Plan is missing required Acceptance section
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The plan lacks a `## Acceptance` section. Standard `/implement` preflight can refuse plans without that heading and at least one verifiable criterion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add ## Acceptance after ## Plan with checkboxes distilled from Testing strategy (e.g. test-lib-cursor-auth retry cases pass; test-check-reviewers Option B/C cases pass; relevant-checks.sh green; transient preflight miss can still yield CURSOR_PRESENT=true via one-shot live fallback; default LARCH_PROBE_NEGATIVE_TTL_SECONDS=0 ignores cached false stamps)


### FINDING_6: Deferred preflight stderr replay must use quiet API
- **Reviewer(s)**: Cursor-dyn-stderr-fd-contract, Codex-dyn-stderr-fd-contract
- **Severity**: important
- **Concern**: The plan defers preflight stderr replay, but does not require replay through `larch_err` or `larch_errf`. Raw `>&2` replay after `larch_quiet_init` can write only to the quiet log, fail lint, or bypass diagnostic redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stderr-fd-contract: Pin replay to `larch_err`/`larch_errf` (line-at-a-time for the multi-line preflight template) or an equivalent helper that mirrors to FD 4; forbid raw `cat "$tmp" >&2`.
  - From Codex-dyn-stderr-fd-contract: Route deferred preflight lines through `larch_err` or `larch_errf`, with `sanitize_diagnostic_line` for captured content; preserve the preflight rc with `_pf_rc=0; cursor_auth_preflight 2>"$tmp" || _pf_rc=$?`




### FINDING_1: Test mock precedence and per-attempt retry semantics are unspecified
- **Reviewer(s)**: Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements, Cursor-dyn-test-mock-precedence, Codex-dyn-test-mock-precedence
- **Severity**: important
- **Concern**: The plan does not define how `LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ` and `LIB_CURSOR_AUTH_TEST_SECURITY_RC` interact under `LARCH_LIB_CURSOR_AUTH_TEST_MODE=1`. Implementations may ignore the sequence knob, apply the single-value mock only once, or fall through to real `security` calls on later attempts, making retry tests flaky or non-deterministic.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Specify normative precedence in the plan (for example: when SEQ is non-empty use it per attempt with last-value repeat; otherwise repeat LIB_CURSOR_AUTH_TEST_SECURITY_RC for every attempt; production ignores both)
  - From Cursor-Pragmatic: State explicitly: when LARCH_LIB_CURSOR_AUTH_TEST_MODE=1 and LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ is non-empty, consume one sequence value per attempt (repeat last on exhaustion); only fall back to LIB_CURSOR_AUTH_TEST_SECURITY_RC when SEQ is unset
  - From Cursor-Requirements: State explicitly: when LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ is unset each retry attempt reuses LIB_CURSOR_AUTH_TEST_SECURITY_RC; when SEQ is set consume it per attempt with last-value repeat per edge cases
  - From Cursor-dyn-test-mock-precedence: In lib-cursor-auth.sh plan text and lib-cursor-auth.md: when SEQ is unset and RC is set under test mode, apply that RC on each retry attempt (same as SEQ=<rc> with repeat-last). Document explicitly.
  - From Codex-dyn-test-mock-precedence: State that LIB_CURSOR_AUTH_TEST_SECURITY_RC_SEQ wins when non-empty. Otherwise LIB_CURSOR_AUTH_TEST_SECURITY_RC supplies every retry attempt. In retry tests, unset or empty the single-value variable.


### FINDING_3: Deferred preflight stderr replay may be skipped on setup failure
- **Reviewer(s)**: Cursor-dyn-quiet-contract-fidelity
- **Severity**: important
- **Concern**: The Option B branch only replays deferred preflight stderr when the one-shot probe fails. If preflight exits 2 and setup fails before the probe runs, operators may get `CURSOR_PRESENT=false` without the quiet-aware diagnostic that explains the preflight failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-quiet-contract-fidelity: Replay deferred sanitized preflight stderr whenever the preflight-exit-2 branch ends with CURSOR_PRESENT=false for any reason (setup failure or probe failure), not only after larch_run_one_cursor_probe returns nonzero


### FINDING_5: Option C tests may not exercise negative TTL behavior
- **Reviewer(s)**: Cursor-dyn-stamp-caller-audit
- **Severity**: important
- **Concern**: Planned Option C tests may omit a positive `LARCH_PROBE_TTL_SECONDS`. In a zero-TTL harness, fresh-stamp reads can miss before negative-polarity logic runs, so tests could pass without actually exercising `LARCH_PROBE_NEGATIVE_TTL_SECONDS`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stamp-caller-audit: Add explicit LARCH_PROBE_TTL_SECONDS=3600 (or similar) to both test specs so a recent false stamp is readable and Option C is the variable under test




### FINDING_2: Keep keychain retry stderr suppressed
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The retry loop for `security find-generic-password` must preserve stderr suppression on every attempt. Direct callers do not capture `cursor_auth_preflight` stderr, so transient keychain errors can leak before the final actionable message.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Keep `>/dev/null 2>&1` on every production `security find-generic-password` attempt inside the retry loop; only the final actionable block writes to stderr.


### FINDING_3: Codex env-key false stamps can bypass negative TTL policy
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-test-stub-feasibility
- **Severity**: important
- **Concern**: The existing `codex-env-key` false-stamp special case can still reject cached `false` stamps even when `LARCH_PROBE_NEGATIVE_TTL_SECONDS` is positive. That contradicts the shared negative-cache behavior intended for Codex.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Remove the codex-env-key false-stamp bypass once larch_try_read_fresh_stamp owns false-polarity TTL, or gate that bypass only when LARCH_PROBE_NEGATIVE_TTL_SECONDS is 0.
  - From Codex-dyn-test-stub-feasibility: Remove or revise the `codex-env-key` false-stamp special case so `larch_try_read_fresh_stamp` owns false-stamp policy for all Codex stamp keys.


### FINDING_4: Codex negative-TTL test may exercise the wrong stamp path
- **Reviewer(s)**: Codex-dyn-codex-stamp-coverage
- **Severity**: important
- **Concern**: The proposed Codex negative-TTL test is not pinned to Codex login mode. With `OPENAI_API_KEY` present, it can use the env-key stamp path and pass without proving the shared negative-TTL logic covers Codex login stamps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-codex-stamp-coverage: Specify that t-optc-codex must run through run_cr or env -u OPENAI_API_KEY, seed the larch-codex-login stamp, and fail if the env-key stamp path is used


### FINDING_6: Setup-chain tests need child-process test wiring
- **Reviewer(s)**: Codex-dyn-test-stub-feasibility
- **Severity**: important
- **Concern**: Controlled setup-chain tests need wiring that survives `check-reviewers.sh` sourcing the real Cursor auth and setup libraries in the child process. Parent-side function stubs can be overwritten, so the tests may not deterministically force setup failure or prove the setup functions ran.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-test-stub-feasibility: Add minimal test wiring to the plan. Prefer existing observable side effects plus a test-only `mktemp` PATH stub for `larch-cursor-cfg.*`, or add a gated setup-chain call log/failure hook used only by `scripts/test-check-reviewers.sh`.


### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:10-20,69-98,144-162
- **Concern**: [SCOPE-REDUCTION] Plan adds deferred preflight stderr capture sanitize and quiet-aware replay plus acceptance items 5-6 and t-optb stderr tests beyond binding issue goals (Options A/B/C only). Scenario: Binding scope and approved outline require retry negative TTL and one-shot live fallback only; the temp-file defer/replay path and its tests add substantial check-reviewers complexity without being needed to stop transient preflight from skipping the live probe or caching false
- **Proposed resolution**: Remove acceptance 5-6 and t-optb-stderr-routing/t-optb-limited-negative replay assertions; on preflight exit 2 run setup plus one larch_run_one_cursor_probe without redirecting cursor_auth_preflight stderr (keep existing quiet-log routing) and write the stamp from the live outcome only



