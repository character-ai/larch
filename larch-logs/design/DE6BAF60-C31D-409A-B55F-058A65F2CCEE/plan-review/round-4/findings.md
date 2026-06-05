### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:56-60 / scripts/lib-external-launcher-common.sh:694-699 / skills/review-and-fix/scripts/review-and-fix.sh:326-329
- **Concern**: Proposed env-key auth-prep failure case cannot trigger codex_auth_setup_failed With OPENAI_API_KEY set external_prepare_codex_auth always returns 0 because env-key strip failures are swallowed via || true; codex_auth_setup_failed is set only when that helper returns non-zero; cp/mktemp failures skip prepare without setting the flag; so the env-key auth-setup breadcrumb branch is unreachable and the plan already exempts the same breadcrumb for implementer (line 77). Scenario: A delegating mv stub or read-only temp config leaves codex_rc at 0 with codex_auth_setup_failed=false, so assertions for codex-env-key-failure: Codex auth setup failed on the OPENAI_API_KEY auth path never fire and the new case is either a false-green or an implement-time harness failure
- **Proposed resolution**: Drop review-and-fix dispatch item 4 (env-key auth-prep failure fallback); keep item 5 (env-key dispatch failure) and login auth-prep failure item 2; add an explicit note mirroring test-codex-implementer.sh item 3 that this breadcrumb is unreachable under current production semantics unless lib-external-launcher-common.sh changes

### FINDING_2:
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh (planned env-key auth-prep case); scripts/lib-external-launcher-common.sh:691-699
- **Concern**: Planned env-key auth-prep failure reuses the login mv-stub mechanism, but env-key prep ignores strip/mv failures and returns 0 after mkdir succeeds. Scenario: The new case can dispatch Codex instead of hitting the intended auth-setup-failed branch, so the asserted codex-env-key auth-prep breadcrumb is not exercised
- **Proposed resolution**: For the env-key auth-prep case, specify a failure that makes external_prepare_codex_auth return nonzero in env-key mode, such as a narrowly delegated mkdir stub for the larch-codex-review-fix-home path, or drop this case and keep only the env-key dispatch-failure breadcrumb test

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:49-51
- **Concern**: Login auth-prep cleanup snapshots a case-private TMPDIR but the plan never exports TMPDIR on run_review_and_fix. Scenario: review-and-fix.sh creates larch-codex-review-fix-home.* under inherited TMPDIR or /tmp (review-and-fix.sh:277); a before/after find on an unexported case tmpdir stays empty and passes even if a temp home survives elsewhere
- **Proposed resolution**: Add TMPDIR="$case_tmp" (or export TMPDIR="$case_tmp") to the login auth-prep failure subshell alongside unset OPENAI_API_KEY and HOME="$fixture_home" before run_review_and_fix

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-external-launcher-common.sh:691-699; skills/review-and-fix/scripts/review-and-fix.sh:277-285
- **Concern**: Plan adds an env-key auth-prep failure test that the current tests-only change cannot trigger. Scenario: In env-key mode external_prepare_codex_auth ignores config strip failures and returns 0 once the temp CODEX_HOME exists, so the planned mv-stub prep failure will still dispatch Codex instead of producing the expected auth-setup breadcrumb and absent argv capture
- **Proposed resolution**: Drop the env-key auth-prep failure case, or re-scope it to the planned env-key dispatch-failure breadcrumb test unless the PR intentionally changes production behavior to make env-key strip failures fatal

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/test-check-reviewers.sh:227-247;scripts/test-check-reviewers.sh:377-401
- **Concern**: Trusted-project -c adjacency is pinned to t10-env-key-false even though t6m already runs a live login-path probe with argv capture. Scenario: check-reviewers.sh:236-245 always injects trust_level before auth -c overrides on every live probe; t6m already logs argv via LARCH_TEST_CODEX_PROBE_ARGV_LOG, so extending t10-env-key-false adds OPENAI_API_KEY plus false-stamp setup without new production surface
- **Proposed resolution**: Add adjacency plus trust string assertions to the existing t6m argv log; keep t10-env-key-false limited to stamp miss, env-key argv, and sentinel leak checks

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:36-38
- **Concern**: Stamp-isolation case 38 omits login-stamp cache preconditions. Scenario: With `OPENAI_API_KEY` unset, `larch_codex_probe_stamp_key` already selects `codex-login` (`scripts/check-reviewers.sh:82-88,324-326`), so a fresh `larch-codex-env-key-present-*.stamp` cannot short-circuit login mode; if a fresh `codex-login` `true` stamp is also present, the probe cache-hits, Codex is never invoked, and the case still passes without proving login-path argv/symlink wiring
- **Proposed resolution**: Add an explicit fixture contract: no fresh `codex-login` stamp (absent, `false`, or expired) whenever the case must "exercise the login path"; keep the env-key stamp as decoy and assert live-probe argv lacks env-key overrides (and/or shows login auth material)

### FINDING_7:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-128
- **Concern**: Post-table selector retention assertions target strip-edge-config.toml instead of login-home/config.toml. Scenario: Plan item 1 binds exact-count grep -Fxc to strip-edge-config.toml, but the post-table/[[model_providers.openai-larch-env]] fixture is copied-config.toml processed via external_prepare_codex_auth into login-home/config.toml (lines 76-90, 114-128). strip-edge-config.toml is a separate direct-strip fixture (lines 135-156). Counts can pass on the wrong file while post-table array stripping regresses undetected.
- **Proposed resolution**: Move post-table model_provider/env_key count assertions to login-home/config.toml immediately after external_prepare_codex_auth on copied-config.toml; keep strip-edge-config.toml for direct external_strip_codex_larch_env_provider edge cases only.

### FINDING_8:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:284-329; scripts/lib-external-launcher-common.sh:691-699
- **Concern**: Plan adds an env-key auth-prep failure review-and-fix test that the stated mechanism cannot trigger. Scenario: The plan says tests and fixtures only, but external_prepare_codex_auth returns 0 on the OPENAI_API_KEY path after best-effort strip failures, so a conditional mv stub will not produce the requested codex-env-key auth setup breadcrumb. Following the plan either yields a failing harness or forces an unplanned production change.
- **Proposed resolution**: Drop the review-and-fix env-key auth-prep failure case, or replace it with the already planned env-key dispatch-failure breadcrumb and cleanup test. Keep login-mode auth-prep failure coverage for prep-failure behavior.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-stub-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-external-launcher-common.sh:694-699
- **Concern**: skills/review-and-fix/scripts/review-and-fix.sh:284-286. Scenario: plan.txt:56-60
- **Proposed resolution**: Proposed env-key auth-prep failure case uses the same mv-based prep-failure mechanism as login, but external_prepare_codex_auth always returns 0 on the OPENAI_API_KEY branch (strip errors are swallowed with || true) and review-and-fix already mktemps codex_home before calling it, so mkdir cannot fail either. The case cannot emit codex-env-key-failure auth-setup breadcrumbs; it contradicts the same plan’s implementer note that env-key auth-prep breadcrumb is unreachable (plan.txt:77). Drop the env-key auth-prep failure case, or retarget it to the dispatch-failure breadcrumb already covered in plan item 5 (cursor-success stub) unless production is changed to fail closed on env-key strip.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-stub-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:45-48; skills/implement/scripts/test-codex-implementer.sh:441-448
- **Concern**: The plan says to mirror the implementer mv stub, but that existing stub is an unconditional exit 99 and does not delegate unrelated mv calls.. Scenario: Copying that shape into review-and-fix would fail harness or Cursor-fallback mv calls unrelated to the Codex auth-prep rename, creating false failures.
- **Proposed resolution**: Replace “mirroring” with an explicit conditional stub shape: fail only the larch-codex-review-fix-home.* config.toml rewrite/rename and exec /bin/mv "$@" for every other invocation.

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-env-leak
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:26-27 skills/review-and-fix/scripts/review-and-fix.sh:277 plan.txt:51-51 plan.txt:97-97
- **Concern**: Login auth-prep cleanup uses unscoped `$TMPDIR` find but harness never exports a case-private TMPDIR. Scenario: `$TMP` is allocated for harness scratch but not exported; `review-and-fix.sh` creates `larch-codex-review-fix-home.*` under `${TMPDIR:-/tmp}` (default `/tmp`). A before/after `find "$TMPDIR"` scans the shared global tmp namespace, so earlier dispatch cases, CI leftovers, or concurrent runs can add/remove unrelated homes and yield false pass/fail. Edge cases claim a private TMPDIR but Step 2 does not establish one.
- **Proposed resolution**: Inside each new auth subshell export a dedicated dir (`TMPDIR="$work_case/harness-tmp"; mkdir -p "$TMPDIR"`) before `run_review_and_fix`, then run `assert_no_review_fix_homes` on that path; or reuse the implementer `/tmp` before/after survivor diff pattern from `test-codex-implementer.sh`.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-env-leak
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-check-reviewers.sh:28-39 plan.txt:35-38 plan.txt:85-85
- **Concern**: Stamp-isolation login-path subcase does not require `run_cr` / `env -u OPENAI_API_KEY`. Scenario: `run_cr_with_env` (lines 35-39) deliberately keeps `OPENAI_API_KEY` in the child environment. The plan’s “fresh env-key stamp with no `OPENAI_API_KEY` must exercise the login path” case does not mandate `run_cr` or an explicit unset. On hosts/CI that export `OPENAI_API_KEY`, the probe stays in env-key mode, stamp-isolation and login-path assertions become vacuous or order-dependent.
- **Proposed resolution**: Implement that subcase with `run_cr` (or an explicit subshell `unset OPENAI_API_KEY`) on a fresh per-case TMPDIR; keep `run_cr_with_env` only where the sentinel key must be present (legacy strip, live env-key probe).

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-env-leak
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lib-external-launcher-common.sh:691-699; skills/review-and-fix/scripts/review-and-fix.sh:277-285
- **Concern**: The proposed review-and-fix env-key auth-prep failure case says to reuse the same temp-CODEX_HOME prep-failure mechanism as the login case, but the recommended mv-stub strip failure cannot make the env-key auth path fail because env-key mode ignores strip failures with `|| true`.. Scenario: The new env-key auth-prep test may silently proceed to Codex dispatch instead of exercising the `codex-env-key-failure: Codex auth setup failed on the OPENAI_API_KEY auth path` branch, so it either fails assertions or covers the wrong fallback path.
- **Proposed resolution**: For the env-key auth-prep case, specify a prep-failure fixture that makes `external_prepare_codex_auth` return nonzero in env-key mode, such as a narrowly targeted `mkdir` stub for the temp `larch-codex-review-fix-home.*` path, and keep `OPENAI_API_KEY` scoped to that subshell/call.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-assertion-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:76-90
- **Concern**: Post-table grep -Fxc targets strip-edge-config.toml instead of login-home/copied-config path. Scenario: Plan item 1 binds post-table exact-count assertions to strip-edge-config.toml, but the post-table/array multiline fixture is copied-config.toml processed via external_prepare_codex_auth into login-home/config.toml (lines 76-90, 114-128). strip-edge-config.toml is a separate direct-strip fixture (135-156) without [[model_providers.openai-larch-env]] post-table content. grep -Fxc can pass on the wrong file while post-table array stripping regresses undetected.
- **Proposed resolution**: Move post-table model_provider/env_key count assertions to login-home/config.toml immediately after external_prepare_codex_auth on copied-config.toml; keep strip-edge-config.toml for the direct external_strip_codex_larch_env_provider edge cases only.

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-assertion-fidelity
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-lib-external-launcher-common.sh:102-113
- **Concern**: Mutation sanity only flips expected values, not strip/capture prerequisites. Scenario: Plan Failure modes 1 and Testing strategy lines 112-113 say flip one new assertion per harness and confirm failure. That catches inverted expectations but not vacuous wiring: a grep -Fxc count on an unstripped or missing capture file still fails when flipped, without proving the assertion observed production processing.
- **Proposed resolution**: Add one negative control per harness: skip the strip/capture step (or point at a pre-strip snapshot) and require the new assertion to fail before the flip check.

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-assertion-fidelity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/test-lib-external-launcher-common.sh:162-162
- **Concern**: Nested-selector removal assertion still targets wrong file pre-fix. Scenario: Current line 162 asserts absence of model_provider = "openai-larch-env" # strip nested selector in strip-edge-config.toml, but that needle exists only in copied-config.toml line 77 (login-home path). Until moved to login-home/config.toml as the plan states, the assertion is vacuously green on strip-edge-config.
- **Proposed resolution**: When implementing item 1, relocate this assertion to login-home/config.toml post-strip and delete the strip-edge-config.toml copy; add a preflight [[ -f ... ]] before any grep -Fxc count on that path.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-assertion-fidelity
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:56-60; scripts/lib-external-launcher-common.sh:691-699; skills/review-and-fix/scripts/review-and-fix.sh:284-330
- **Concern**: The proposed review-and-fix env-key auth-prep failure case is not reachable with the stated “same mv/config rewrite” mechanism. In env-key mode, external_prepare_codex_auth ignores strip failures with `|| true` and returns 0 after preparing the temp CODEX_HOME.. Scenario: A test following the plan will dispatch Codex instead of taking the auth-prep-failure branch, so assertions that the argv capture is absent and that wrapper/sidecar contain “Codex auth setup failed on the OPENAI_API_KEY auth path” will fail or tempt unnecessary production-only test hooks.
- **Proposed resolution**: Keep the minimum-change contract by dropping this review-and-fix env-key auth-prep-failure case, mirroring the implementer note that this path is fixture-unreachable; retain the env-key dispatch-failure breadcrumb case instead.
