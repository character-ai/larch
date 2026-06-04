### FINDING_1: code-quality: skills/design/scripts/design-publish.sh:301-338
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Three publish-failure branches duplicate append-tool-failure and recovery warn logic. Future exit-code or warn changes may update only one branch and leave inconsistent operator surfaces. Add record_publish_failure() helper and route all three branches through it.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/design/scripts/render-final-summary.sh:313-328,404-417
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] failed-publish recovery notes duplicated in invoke_render and compose_self_fallback. Fallback summaries can omit PR/recovery lines that the full renderer shows after a wording change. Extract write_failed_publish_notes() used by both code paths.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/test-design-log-publish.sh:53-74,182-216 and scripts/test-design-multi-round-integration.sh:38-56
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Duplicate gh stub registration/headRefOid logic across harnesses. Already required a separate integration-test fix when stub arms split; next gate change risks drift again. Share one stub fragment or template for pr checks/view behavior.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: scripts/design-log-publish.sh:834-840
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Up to three jq invocations per registration probe. 31-probe timeouts multiply subprocess overhead unnecessarily. Single jq -e 'type == "array" and length > 0' for registration detection.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/design-log-publish.sh:838-839
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Non-array checks JSON logs larch_err every probe. Persistent API error shape spams stderr for up to 300s. Log non-array diagnostic once per publish attempt then stay quiet.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: scripts/test-design-log-publish.sh:811-818
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unused head_probe/checks_probe counters in gh stub. Misleads maintainers about which knobs control stub behavior. Remove dead counters or use them in assertions.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/design-log-publish.sh:841-884
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Registration only requires non-empty required-check JSON and matching headRefOid before --watch; stale passing checks on the new head could satisfy registration before new workflows start. After force-push pause reuse, first probe returns green checks and updated headRefOid while new required jobs have not started; script merges via --admin before fresh CI runs. Consider requiring pending/in_progress checks or a post-push freshness signal before calling --watch, if observed in production.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/scripts/render-final-summary.sh:295-297
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] failed-publish outcome still sets RUN_LOGS_PATH to larch-logs/design/<run-id>/ as if logs merged to main. Operator reads terminal Run logs line and searches main; logs exist only on recovery branch or open flush PR. For failed-publish, use N/A or qualify the path with not-merged / see recovery branch in the note block.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: scripts/design-log-publish.sh:838-839
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Non-array JSON from gh pr checks --json logs larch_err on every registration probe (up to 31). Rate-limited or malformed API responses spam stderr during the 300s window. Log once per run or only on the final failed probe.
- **Suggested revision**: Address the concern above.

### FINDING_10: **risk-integration** `skills/design/scripts/test-design-publish.sh:329-333` — Failure-envelope cases assert `--outcome failed-publish` and `execution-issues.md`, but none assert that `DESIGN_LOG_PR_NUMBER`, `DESIGN_LOG_PR_URL`, or `DESIGN_LOG_RECOVERY_BRANCH` (exported in `design-publish.sh` before post-publish render) appear in `final-summary.md` or `RENDER_LOG` when the publish stub emits them. The new `publish-env` case only checks `.design-publish-result.env`. **Suggested fix:** Extend `test-design-publish.sh` (e.g. the `publish-env` or `PUBLISH_OK=false` case) to grep `final-summary.md` for `Log flush PR` / `Log recovery branch` after stubbing `PUBLISH_PR_NUMBER`, `PUBLISH_PR_URL`, and `PUBLISH_RECOVERY_BRANCH`, matching the plan’s recovery-metadata operator contract.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/test-design-publish.sh:329-333` — Failure-envelope cases assert `--outcome failed-publish` and `execution-issues.md`, but none assert that `DESIGN_LOG_PR_NUMBER`, `DESIGN_LOG_PR_URL`, or `DESIGN_LOG_RECOVERY_BRANCH` (exported in `design-publish.sh` before post-publish render) appear in `final-summary.md` or `RENDER_LOG` when the publish stub emits them. The new `publish-env` case only checks `.design-publish-result.env`. **Suggested fix:** Extend `test-design-publish.sh` (e.g. the `publish-env` or `PUBLISH_OK=false` case) to grep `final-summary.md` for `Log flush PR` / `Log recovery branch` after stubbing `PUBLISH_PR_NUMBER`, `PUBLISH_PR_URL`, and `PUBLISH_RECOVERY_BRANCH`, matching the plan’s recovery-metadata operator contract.
- **Suggested revision**: Address the concern above.

### FINDING_11: **risk-integration** `skills/design/scripts/plan-review-loop.sh:934-978` — Collector stderr capture was refactored (temp file instead of `tee` into FD 3/4 under `LARCH_QUIET_PID`), but this branch does not touch `test-plan-review-loop.sh`. That path is outside the plan’s file list and is only indirectly exercised via `scripts/test-design-multi-round-integration.sh` (`env -u LARCH_QUIET_PID`). **Suggested fix:** Run `make test-plan-review-loop` / `test-harnesses-16` on the branch; if quiet collector stderr is the target, add or extend a case in `test-plan-review-loop.sh` that runs under `LARCH_QUIET_PID` and asserts `plan-review-collector.stderr` still receives collector output.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `skills/design/scripts/plan-review-loop.sh:934-978` — Collector stderr capture was refactored (temp file instead of `tee` into FD 3/4 under `LARCH_QUIET_PID`), but this branch does not touch `test-plan-review-loop.sh`. That path is outside the plan’s file list and is only indirectly exercised via `scripts/test-design-multi-round-integration.sh` (`env -u LARCH_QUIET_PID`). **Suggested fix:** Run `make test-plan-review-loop` / `test-harnesses-16` on the branch; if quiet collector stderr is the target, add or extend a case in `test-plan-review-loop.sh` that runs under `LARCH_QUIET_PID` and asserts `plan-review-collector.stderr` still receives collector output.
- **Suggested revision**: Address the concern above.

### FINDING_12: **risk-integration** `scripts/design-log-publish.sh:825-876` — The registration loop stops when `SECONDS` exceeds `REG_DEADLINE` (`break` at lines 862–863) as well as when `reg_probe` exceeds `REG_MAX_PROBES`, but timeout stderr always cites the full budget (`${REG_MAX_PROBES} probes`) rather than probes actually run. Under slow GitHub or clock pressure, operators may think all 31 probes ran when fewer did. **Suggested fix:** Include the final `reg_probe` value in the `larch_err` text (e.g. `probe ${reg_probe}/${REG_MAX_PROBES}`), and add a harness case that forces deadline exit (mock `SECONDS` / inject a sleep stub that advances time) if you want CI to pin both termination modes.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:825-876` — The registration loop stops when `SECONDS` exceeds `REG_DEADLINE` (`break` at lines 862–863) as well as when `reg_probe` exceeds `REG_MAX_PROBES`, but timeout stderr always cites the full budget (`${REG_MAX_PROBES} probes`) rather than probes actually run. Under slow GitHub or clock pressure, operators may think all 31 probes ran when fewer did. **Suggested fix:** Include the final `reg_probe` value in the `larch_err` text (e.g. `probe ${reg_probe}/${REG_MAX_PROBES}`), and add a harness case that forces deadline exit (mock `SECONDS` / inject a sleep stub that advances time) if you want CI to pin both termination modes.
- **Suggested revision**: Address the concern above.

### FINDING_13: **latent** `scripts/test-design-log-publish.sh` (harness-wide) — Merge-gate behavior is covered well with stubbed `gh` (`--json` vs `--watch`, head OID alignment, stderr substrings, probe budgets). There is still no test against real `gh pr checks` registration latency or pending rc=8 JSON from GitHub. **Suggested fix:** Treat manual acceptance (one live `/design` flush PR) as required before merge; optional follow-up: a gated integration job with a throwaway repo.
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **latent** `scripts/test-design-log-publish.sh` (harness-wide) — Merge-gate behavior is covered well with stubbed `gh` (`--json` vs `--watch`, head OID alignment, stderr substrings, probe budgets). There is still no test against real `gh pr checks` registration latency or pending rc=8 JSON from GitHub. **Suggested fix:** Treat manual acceptance (one live `/design` flush PR) as required before merge; optional follow-up: a gated integration job with a throwaway repo.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: - **risk-integration** `scripts/test-design-structure.sh:413-1131` — Still pins `design-publish.sh` call ordering and subshell capture, but does not grep for registration-gate tokens (`REG_TIMEOUT`, `did not register within`, `headRefOid`, `PUSH_HEAD_SHA`). `design-publish.md` lists `test-design-structure.sh` as a sync target. Pre-existing structural gap, amplified by this change. ### Summary The core #3413 work is in good shape: flush re-enabled in `design-publish.sh`, two-phase head-bound registration in `design-log-publish.sh`, SECURITY/docs updated, and `test-design-log-publish.sh` adds the planned race / never-register / CI-fail / pending-rc / stale-head cases with strong stderr and `GH_STUB_LOG` assertions. Existing happy-path and pause-reuse cases were updated for `TEST_CLONE_ROOT` / `headRefOid`, and `test-design-multi-round-integration.sh` was fixed for the `--json`/`--watch` stub split. Main gaps before merge: assert failed-publish recovery metadata in the rendered summary (not only result env), and confirm the `plan-review-loop.sh` stderr change via `test-plan-review-loop` (not just multi-round integration). I did not execute harnesses in this read-only review; run `make test-design-publish test-design-log-publish test-design-multi-round-integration test-plan-review-loop` (or `bash scripts/relevant-checks.sh`) to confirm green.
- **Suggested revision**: Address the concern above.

### FINDING_15: **CI still gates merge**: Registration timeout, head mismatch, and watch failure all set `merge_rc≠0`, emit `PUBLISH_OK=false`, and skip `--watch` or merge (see ```790:903:scripts/design-log-publish.sh```).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **CI still gates merge**: Registration timeout, head mismatch, and watch failure all set `merge_rc≠0`, emit `PUBLISH_OK=false`, and skip `--watch` or merge (see ```790:903:scripts/design-log-publish.sh```).
- **Suggested revision**: Address the concern above.

### FINDING_16: **Stale-check bypass closed**: Binding registration to `PUSH_HEAD_SHA` addresses pause/force-push reuse where green checks on an old head could otherwise satisfy a naive “checks exist” probe.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Stale-check bypass closed**: Binding registration to `PUSH_HEAD_SHA` addresses pause/force-push reuse where green checks on an old head could otherwise satisfy a naive “checks exist” probe.
- **Suggested revision**: Address the concern above.

### FINDING_17: **Stdout contract hygiene**: `jq -e` is redirected to `/dev/null`; registration probes use `set +e` so pending-check non-zero `gh` exits do not abort the script or leak booleans onto the KV stream.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Stdout contract hygiene**: `jq -e` is redirected to `/dev/null`; registration probes use `set +e` so pending-check non-zero `gh` exits do not abort the script or leak booleans onto the KV stream.
- **Suggested revision**: Address the concern above.

### FINDING_18: **Pre-merge redaction unchanged**: Tmpdir allowlist, symlink guards, plan-review allowlist, and `scrub-log-secrets` fail-closed behavior remain; re-enable restores `SECRET_SCRUB_VIOLATIONS` surfacing in `design-publish.sh`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Pre-merge redaction unchanged**: Tmpdir allowlist, symlink guards, plan-review allowlist, and `scrub-log-secrets` fail-closed behavior remain; re-enable restores `SECRET_SCRUB_VIOLATIONS` surfacing in `design-publish.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_19: **Inputs bounded**: `--issue` (digits), `--run-id` (`larch_log_slug_is_valid`), `--repo` (`validate_repo` in `design-publish.sh`), `PR_NUM` from `gh` parsing.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Inputs bounded**: `--issue` (digits), `--run-id` (`larch_log_slug_is_valid`), `--repo` (`validate_repo` in `design-publish.sh`), `PR_NUM` from `gh` parsing.
- **Suggested revision**: Address the concern above.

### FINDING_20: **Documentation aligned**: `SECURITY.md` and `design-log-publish.md` now describe registration-before-watch and distinguish `did not register within` vs `did not pass`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Documentation aligned**: `SECURITY.md` and `design-log-publish.md` now describe registration-before-watch and distinguish `did not register within` vs `did not pass`.
- **Suggested revision**: Address the concern above.

### FINDING_21: **No command-injection surface added**: `gh`/`git` arguments use quoted variables; branch names derive from validated `RUN_ID`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No command-injection surface added**: `gh`/`git` arguments use quoted variables; branch names derive from validated `RUN_ID`. **Residual operational risk (pre-existing, amplified by re-enable)** Re-enabling flush means more automated `--admin` merges and more committed `larch-logs/design/` content on the default branch. That increases impact if a `gh` token with admin-merge scope is compromised or if redaction/scrub fails — but the branch does not remove scrub gates or allowlist controls.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/design-log-publish.sh:825-884
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Registration retries pr view with transient backoff on every probe while checks JSON is non-empty but head OID mismatches, consuming REG_DEADLINE faster than the nominal 31×10s budget. Pause/force-push reuse can show green required checks for an old head while headRefOid lags; the run times out with did not register within even though checks existed, blocking [DESIGNED] rename and leaving a recovery PR. Skip transient retry for head-only probes during registration, or emit an explicit stale-head diagnostic when checks are non-empty but headRefOid != PUSH_HEAD_SHA.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/design-log-publish.sh:878-879
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Registration-timeout larch_err cites REG_MAX_PROBES budget, not probes actually run. Early REG_DEADLINE break makes logs claim 31 probes when fewer ran, slowing incident triage. Log actual reg_probe count alongside REG_MAX_PROBES in the timeout message.
- **Suggested revision**: Address the concern above.

### FINDING_24: architecture: scripts/design-log-publish.sh:882-884
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Post-registration gh pr checks --watch has no local timeout. A required check or gh watch can stall indefinitely after up to 300s registration; operator must kill /design manually. Document operational handling; consider a bounded watch in a follow-up change.
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] code-quality: skills/design/scripts/design-publish.sh:1699-1701
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] LOG_RECOVERY_BRANCH duplicated in result env KVs. None functional. Deduplicate the second append when touching that helper next.
- **Suggested revision**: Address the concern above.

### FINDING_26: architecture: skills/design/scripts/plan-review-loop.sh:835-883
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan scoped changes to design-log publish/merge files only; branch also modifies plan-review collector stderr and multi-round integration quiet-mode handling. A #3413-focused reviewer or rollback of publish changes could miss unrelated plan-review behavior changes; violates plan Approach to keep the fix local to the flush path. Remove these hunks from this PR or update the plan/acceptance to explicitly include them with rationale.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: skills/design/scripts/design-publish.md:24-28
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract doc omits failed-publish outcome and DESIGN_LOG_* recovery exports that implementation and tests now rely on. Operators troubleshooting a stuck flush PR read design-publish.md and do not see how failed publish is rendered or which recovery fields exist. Document failed-publish, DESIGN_LOG_* exports, and post-publish render behavior on publish failure.
- **Suggested revision**: Address the concern above.

### FINDING_28: architecture: skills/design/SKILL.md:538
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] SKILL.md lists failed-publish on the orchestrator Final summary block enum but Gate C uses design-publish.sh internal render. Orchestrator authors may export SUMMARY_OUTCOME=failed-publish on a path that never sets DESIGN_LOG_* recovery metadata. Clarify failed-publish is design-publish.sh-only or wire orchestrator paths if truly needed.
- **Suggested revision**: Address the concern above.

### FINDING_29: **risk-integration** `scripts/design-log-publish.sh:811-879` — Registration-timeout stderr always reports `${REG_MAX_PROBES}` probes (e.g. `31`) even when the loop stops earlier because `SECONDS` passed `REG_DEADLINE` (round 3 added the deadline guard at 825–867). Operators comparing logs to the 300s budget can conclude GitHub never registered checks across the full probe budget when the run actually hit wall-clock first with fewer probes, which revives the kind of mis-triage this issue separated (`did not register within` vs `did not pass`). **Suggested fix:** Include the actual probe count in the timeout `larch_err` (e.g. `${reg_probe}` or `reg_probe-1` after the loop) alongside `REG_MAX_PROBES` and `REG_TIMEOUT`, and/or add a distinct suffix when exit was deadline-driven vs probe-budget-driven.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:811-879` — Registration-timeout stderr always reports `${REG_MAX_PROBES}` probes (e.g. `31`) even when the loop stops earlier because `SECONDS` passed `REG_DEADLINE` (round 3 added the deadline guard at 825–867). Operators comparing logs to the 300s budget can conclude GitHub never registered checks across the full probe budget when the run actually hit wall-clock first with fewer probes, which revives the kind of mis-triage this issue separated (`did not register within` vs `did not pass`). **Suggested fix:** Include the actual probe count in the timeout `larch_err` (e.g. `${reg_probe}` or `reg_probe-1` after the loop) alongside `REG_MAX_PROBES` and `REG_TIMEOUT`, and/or add a distinct suffix when exit was deadline-driven vs probe-budget-driven.
- **Suggested revision**: Address the concern above.

### FINDING_30: **risk-integration** `scripts/design-log-publish.sh:882-888` — After registration succeeds, any non-zero `gh pr checks --watch --fail-fast` is reported only as `required CI checks did not pass`, with no branch for the pre-fix `no checks reported` failure mode. If `gh` ever returns that message on `--watch` after a successful `--json` probe (API inconsistency or check-suite reset between phases), operators are steered toward “CI failed” rather than “registration/watch gap,” weakening the diagnostic split this branch introduces. Harnesses assert substring separation for the never-registered path but not for this watch-after-register edge. **Suggested fix:** When `ci_rc -ne 0`, if `ci_wait_out` matches the known `no checks reported` pattern, emit a third diagnostic (e.g. `checks not available for watch after registration`) or re-enter a short registration backoff before failing closed; keep `did not pass` only when watch output reflects an actual failing/pending required check.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **risk-integration** `scripts/design-log-publish.sh:882-888` — After registration succeeds, any non-zero `gh pr checks --watch --fail-fast` is reported only as `required CI checks did not pass`, with no branch for the pre-fix `no checks reported` failure mode. If `gh` ever returns that message on `--watch` after a successful `--json` probe (API inconsistency or check-suite reset between phases), operators are steered toward “CI failed” rather than “registration/watch gap,” weakening the diagnostic split this branch introduces. Harnesses assert substring separation for the never-registered path but not for this watch-after-register edge. **Suggested fix:** When `ci_rc -ne 0`, if `ci_wait_out` matches the known `no checks reported` pattern, emit a third diagnostic (e.g. `checks not available for watch after registration`) or re-enter a short registration backoff before failing closed; keep `did not pass` only when watch output reflects an actual failing/pending required check.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] **Pre-existing:** `--reason pause` still runs the same post-push PR create + merge gate as final flush (`scripts/design-pause-save.sh`); a successful pause publish can still `--admin` merge log snapshots mid-design. Re-enabling Step 5c does not change that, but it is worth remembering when judging production risk.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **Pre-existing:** `--reason pause` still runs the same post-push PR create + merge gate as final flush (`scripts/design-pause-save.sh`); a successful pause publish can still `--admin` merge log snapshots mid-design. Re-enabling Step 5c does not change that, but it is worth remembering when judging production risk.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] **Positive (no issue):** Splitting `gh` stub `--json` vs `--watch` arms, deriving default `headRefOid` from `TEST_MERGE_BRANCH` / `ls-remote`, stale-head knobs, and the updated CI-fail stderr assertions materially reduce the original registration-race + false “CI failed” conflation; the core #3413 fix aligns with the stated acceptance criteria.
- **Reviewer**: dyn-gh-ci-output.txt
- **Concern**: - **Positive (no issue):** Splitting `gh` stub `--json` vs `--watch` arms, deriving default `headRefOid` from `TEST_MERGE_BRANCH` / `ls-remote`, stale-head knobs, and the updated CI-fail stderr assertions materially reduce the original registration-race + false “CI failed” conflation; the core #3413 fix aligns with the stated acceptance criteria.
- **Suggested revision**: Address the concern above.

### FINDING_33: **architecture** `skills/design/SKILL.md:1515-1525` — Step 5c’s `.design-publish-result.env` parser still allowlists only `PLAN_WRITE_OK|PUBLISH_OK|RENAMED|…`, but this branch expands `design-publish.sh` to persist `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, and `LOG_RECOVERY_BRANCH` in the same file (`skills/design/scripts/design-publish.md:1576-1577`, `design-publish.sh:159-181`). Recovery metadata therefore lives in the result artifact and in `WARN=` replay, yet the orchestrator never binds those keys for Step 5d/6 or downstream automation that reads the env file instead of re-parsing publish stdout. **Suggested fix:** Extend the Step 5c `case` allowlist (and stdout fallback merge) to include `PR_NUMBER|PR_URL|RECOVERY_BRANCH|LOG_RECOVERY_BRANCH`, or document that only `design-publish.sh` / `final-summary.md` consumers may read them.
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - **architecture** `skills/design/SKILL.md:1515-1525` — Step 5c’s `.design-publish-result.env` parser still allowlists only `PLAN_WRITE_OK|PUBLISH_OK|RENAMED|…`, but this branch expands `design-publish.sh` to persist `PR_NUMBER`, `PR_URL`, `RECOVERY_BRANCH`, and `LOG_RECOVERY_BRANCH` in the same file (`skills/design/scripts/design-publish.md:1576-1577`, `design-publish.sh:159-181`). Recovery metadata therefore lives in the result artifact and in `WARN=` replay, yet the orchestrator never binds those keys for Step 5d/6 or downstream automation that reads the env file instead of re-parsing publish stdout. **Suggested fix:** Extend the Step 5c `case` allowlist (and stdout fallback merge) to include `PR_NUMBER|PR_URL|RECOVERY_BRANCH|LOG_RECOVERY_BRANCH`, or document that only `design-publish.sh` / `final-summary.md` consumers may read them.
- **Suggested revision**: Address the concern above.

### FINDING_34: **architecture** `skills/design/scripts/design-publish.sh:343-371` and `skills/design/SKILL.md:1545-1567` — With the flush re-enabled, a publish failure is only reflected in `PUBLISH_OK=false`, `failed-publish` post-render, and driver `WARN=` lines, while Step 5c still writes `step-5c` whenever `PLAN_WRITE_OK=true` and Step 5d still emits the success footer `➡️ 5: finalize — plan written to issue #<N>; NEXT REQUIRED: continue` (`SKILL.md:1565-1567`). Rename and cleanup gating remain correct (`PUBLISH_OK` / Step 6), but the terminal machine footer can read like full design completion when the log flush PR is still open. **Suggested fix:** Gate the footer (or add a distinct footer) on `PUBLISH_OK=true` when `SESSION_ID` is non-empty, or append an explicit “log publish incomplete” token to the footer when `PUBLISH_OK=false`.
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-publish.sh:343-371` and `skills/design/SKILL.md:1545-1567` — With the flush re-enabled, a publish failure is only reflected in `PUBLISH_OK=false`, `failed-publish` post-render, and driver `WARN=` lines, while Step 5c still writes `step-5c` whenever `PLAN_WRITE_OK=true` and Step 5d still emits the success footer `➡️ 5: finalize — plan written to issue #<N>; NEXT REQUIRED: continue` (`SKILL.md:1565-1567`). Rename and cleanup gating remain correct (`PUBLISH_OK` / Step 6), but the terminal machine footer can read like full design completion when the log flush PR is still open. **Suggested fix:** Gate the footer (or add a distinct footer) on `PUBLISH_OK=true` when `SESSION_ID` is non-empty, or append an explicit “log publish incomplete” token to the footer when `PUBLISH_OK=false`.
- **Suggested revision**: Address the concern above.

### FINDING_35: **correctness** `scripts/design-log-publish.sh:635-654` with `skills/design/scripts/design-publish.sh:356-371` — On `--reason final`, an empty `git status --porcelain` for `larch-logs/design/<RUN_ID>/` returns `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` and exits before push/PR/merge, while `design-publish.sh` then treats that as terminal publish success and runs `[DESIGNED]` rename. That contradicts the updated contract prose that `PUBLISH_OK=true` means admin merge after required CI (`scripts/design-log-publish.md:131`, `SECURITY.md` updates in this branch) and can mark an issue implementable without verifying the run directory reached `main`. Pause mode fail-closes this path (`636-647`); final mode does not. Re-enabling the flush amplifies exposure. **Suggested fix:** For final publishes, either verify `origin/$ORIGIN_DEFAULT` already contains the run tree (similar to the pause `git diff --quiet` check) before `PUBLISH_OK=true`, or keep `PUBLISH_OK=false` with explicit “no delta / already on default” semantics and do not rename unless a merge occurred in this invocation.
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - **correctness** `scripts/design-log-publish.sh:635-654` with `skills/design/scripts/design-publish.sh:356-371` — On `--reason final`, an empty `git status --porcelain` for `larch-logs/design/<RUN_ID>/` returns `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` and exits before push/PR/merge, while `design-publish.sh` then treats that as terminal publish success and runs `[DESIGNED]` rename. That contradicts the updated contract prose that `PUBLISH_OK=true` means admin merge after required CI (`scripts/design-log-publish.md:131`, `SECURITY.md` updates in this branch) and can mark an issue implementable without verifying the run directory reached `main`. Pause mode fail-closes this path (`636-647`); final mode does not. Re-enabling the flush amplifies exposure. **Suggested fix:** For final publishes, either verify `origin/$ORIGIN_DEFAULT` already contains the run tree (similar to the pause `git diff --quiet` check) before `PUBLISH_OK=true`, or keep `PUBLISH_OK=false` with explicit “no delta / already on default” semantics and do not rename unless a merge occurred in this invocation.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] The two-phase registration gate (`PUSH_HEAD_SHA` + non-empty `--json` checks, then `--watch`) is structurally aligned with the #3413 root cause; harness cases in `scripts/test-design-log-publish.sh` exercise race, never-registered, watch-failure, non-zero JSON rc, and stale-head paths coherently with the stderr/`GH_STUB_LOG` split described in the plan.
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - The two-phase registration gate (`PUSH_HEAD_SHA` + non-empty `--json` checks, then `--watch`) is structurally aligned with the #3413 root cause; harness cases in `scripts/test-design-log-publish.sh` exercise race, never-registered, watch-failure, non-zero JSON rc, and stale-head paths coherently with the stderr/`GH_STUB_LOG` split described in the plan.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] `design-publish.sh`’s envelope handling (`_publish_rc` vs `PUBLISH_OK=`, `failed-publish` post-render with `DESIGN_LOG_*` exports, pre/post render split) is internally consistent; post-push `design-log-publish.sh` exit `1` with `PUBLISH_OK=false` on stdout is absorbed by the driver without aborting the orchestrator (`design-publish.md:39-42`).
- **Reviewer**: dyn-publish-flow-output.txt
- **Concern**: - `design-publish.sh`’s envelope handling (`_publish_rc` vs `PUBLISH_OK=`, `failed-publish` post-render with `DESIGN_LOG_*` exports, pre/post render split) is internally consistent; post-push `design-log-publish.sh` exit `1` with `PUBLISH_OK=false` on stdout is absorbed by the driver without aborting the orchestrator (`design-publish.md:39-42`).
- **Suggested revision**: Address the concern above.

### FINDING_38: **correctness** `scripts/test-design-log-publish.sh:396-907` — Most harness cases before the dedicated merge-gate block (happy path, merge failure, required-check failure, pause seeds, plan-review staging, etc.) only assert `PUBLISH_OK`, merge, or stderr substrings. They never assert that registration polling ran (for example, that `GH_STUB_LOG.checks-json-count` is bounded, or that `--watch` is absent on timeout paths). Because the gh stub’s default `--json` arm already returns a non-empty array and the default `headRefOid` path aligns with `TEST_MERGE_BRANCH` + `ls-remote`, a regression that deleted the registration loop but kept a single `--json` probe followed by `--watch` + merge would still pass those older cases; only the cases from `registration race` through `stale-head never aligns` exercise the new behavior. **Suggested fix:** Add lightweight guards to an existing high-traffic success case (for example, happy path): assert `checks-json-count` is `1`, and that the stub log contains exactly one `pr checks` line with `--watch`, so the default path cannot silently drop registration polling.
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-log-publish.sh:396-907` — Most harness cases before the dedicated merge-gate block (happy path, merge failure, required-check failure, pause seeds, plan-review staging, etc.) only assert `PUBLISH_OK`, merge, or stderr substrings. They never assert that registration polling ran (for example, that `GH_STUB_LOG.checks-json-count` is bounded, or that `--watch` is absent on timeout paths). Because the gh stub’s default `--json` arm already returns a non-empty array and the default `headRefOid` path aligns with `TEST_MERGE_BRANCH` + `ls-remote`, a regression that deleted the registration loop but kept a single `--json` probe followed by `--watch` + merge would still pass those older cases; only the cases from `registration race` through `stale-head never aligns` exercise the new behavior. **Suggested fix:** Add lightweight guards to an existing high-traffic success case (for example, happy path): assert `checks-json-count` is `1`, and that the stub log contains exactly one `pr checks` line with `--watch`, so the default path cannot silently drop registration polling.
- **Suggested revision**: Address the concern above.

### FINDING_39: **correctness** `scripts/test-design-log-publish.sh:53-71,1037-1059` — Stale-head coverage uses `GH_STUB_PR_HEAD_OID_MISMATCH_FIRST` / `GH_STUB_PR_HEAD_OID_MISMATCH` to return the all-zero OID, then `resolve_pr_head_oid` (current `ls-remote`) once the knob expires. That models “headRefOid missing/wrong until GitHub catches up,” but not the #3413 scenario where **required checks are already non-empty for an old head** while `headRefOid` still points at a different real commit. In production, probes 1–2 with `EMPTY_FIRST` never call `pr view` (checks still `[]`); with `MISMATCH_FIRST=2`, registration actually needs **five** `--json` probes and **three** `headRefOid` views, while the test only asserts `head-count == 3`, so a bug that merged after the first mismatched-but-non-empty check row would not be caught by json-probe counting. **Suggested fix:** Add a knob that returns a fixed, valid but non-matching SHA for the first N `headRefOid` responses while `--json` is already non-empty, and assert both `checks-json-count` and `head-count` (or `PUBLISH_OK=false` until alignment) so stale-check gating is tied to real OID inequality, not only the zero-OID sentinel.
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-log-publish.sh:53-71,1037-1059` — Stale-head coverage uses `GH_STUB_PR_HEAD_OID_MISMATCH_FIRST` / `GH_STUB_PR_HEAD_OID_MISMATCH` to return the all-zero OID, then `resolve_pr_head_oid` (current `ls-remote`) once the knob expires. That models “headRefOid missing/wrong until GitHub catches up,” but not the #3413 scenario where **required checks are already non-empty for an old head** while `headRefOid` still points at a different real commit. In production, probes 1–2 with `EMPTY_FIRST` never call `pr view` (checks still `[]`); with `MISMATCH_FIRST=2`, registration actually needs **five** `--json` probes and **three** `headRefOid` views, while the test only asserts `head-count == 3`, so a bug that merged after the first mismatched-but-non-empty check row would not be caught by json-probe counting. **Suggested fix:** Add a knob that returns a fixed, valid but non-matching SHA for the first N `headRefOid` responses while `--json` is already non-empty, and assert both `checks-json-count` and `head-count` (or `PUBLISH_OK=false` until alignment) so stale-check gating is tied to real OID inequality, not only the zero-OID sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_40: **correctness** `scripts/test-design-log-publish.sh:980-1000` — The “registration probe accepts non-zero rc with pending JSON” case sets `GH_STUB_CHECKS_JSON_RC=8` and expects merge success, but it does not assert that registration completed on the **first** `--json` probe (`checks-json-count == 1`). A regression that treated any non-zero `gh pr checks --json` rc as “not registered” and spun until timeout would still fail this test, but a regression that retried registration unnecessarily yet merged on probe 1 would pass without exercising the rc-independent parsing contract. **Suggested fix:** Assert `[[ "$(cat "$GH_STUB_LOG.checks-json-count")" == "1" ]]` (and optionally that stderr does not contain `did not register within`) so non-zero rc is validated together with “register immediately when JSON is non-empty.”
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-log-publish.sh:980-1000` — The “registration probe accepts non-zero rc with pending JSON” case sets `GH_STUB_CHECKS_JSON_RC=8` and expects merge success, but it does not assert that registration completed on the **first** `--json` probe (`checks-json-count == 1`). A regression that treated any non-zero `gh pr checks --json` rc as “not registered” and spun until timeout would still fail this test, but a regression that retried registration unnecessarily yet merged on probe 1 would pass without exercising the rc-independent parsing contract. **Suggested fix:** Assert `[[ "$(cat "$GH_STUB_LOG.checks-json-count")" == "1" ]]` (and optionally that stderr does not contain `did not register within`) so non-zero rc is validated together with “register immediately when JSON is non-empty.”
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-multi-round-integration.sh:25-35` — The slimmer integration gh stub branches on `grep -- '--json'` / `grep -- '--watch'` over `"$*"`, while `test-design-log-publish.sh` uses exact-token `has_arg`. Behavior matches today’s argv shape, but the two stubs could diverge if `gh` flag spelling changes; consider sharing one stub or the same `has_arg` helpers.
- **Suggested revision**: Address the concern above.

### FINDING_42: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-stub-fidelity-output.txt
- **Concern**: - **correctness** `scripts/test-design-log-publish.sh:1016-1032` — Registration `pr view` failures use stub stderr `Could not resolve host: api.github.com`, which production’s `with_transient_retry` treats as transient (up to three attempts per probe). The test still fails closed, but probe-count semantics differ from a single-shot view failure; this is harness realism, not a false pass in the current no-op sleep setup.
- **Suggested revision**: Address the concern above.

