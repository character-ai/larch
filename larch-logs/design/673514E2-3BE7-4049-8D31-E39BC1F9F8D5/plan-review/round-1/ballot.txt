### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:30-31
- **Concern**: Driver render-final-summary invocation omits required --outcome and --mode CLI flags. Scenario: render-final-summary.sh parses --outcome/--mode from argv only (skills/design/scripts/render-final-summary.sh:13-21); exporting SUMMARY_OUTCOME/MODE_STR env without those flags exits 2 or uses wrong mode
- **Proposed resolution**: In design-route.sh cancel branches call render-final-summary.sh with --outcome cancelled-title-filter|cancelled-reentry-guard and --mode N/A or jq-derived classification plus env DESIGN_TMPDIR/ISSUE_NUMBER/SESSION_ID

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: code-quality
- **Location**: skills/design/scripts/design-route.sh:6-12; skills/design/scripts/design-init-runparams.sh:6-13; scripts/lib-quiet.md:31-37
- **Concern**: Plan moves user-visible banners into quiet phase drivers but only says to print them to stderr, which conflicts with the repo's post-larch_quiet_init contract. Scenario: The moved cancel/resume/INIT_STATUS banners can be implemented with raw printf >&2; S041 rejects that and, if missed, the operator messages go to the quiet log instead of the caller
- **Proposed resolution**: Update the plan to require larch_err/larch_errf for every moved driver banner and resume-refresh failure message; keep raw final-summary.md emission only in SKILL.md

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:422-445
- **Concern**: Resume refresh failure allows ROUTE=resume@* with exit 0. Scenario: Failed write-design-current-env.sh still yields resume@*; orchestrator continues into resumed step with stale env
- **Proposed resolution**: Require driver exit 1 or non-resume ROUTE before emit; do not use ERROR= with exit 0 unless SKILL checks ERROR

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan:skills/design/SKILL.md thin-route cancel-pause-load
- **Concern**: cancel-pause-load claims driver stderr banner already exists. Scenario: Driver emits only KVs; operator may lose abort text if orchestrator banner removed per plan
- **Proposed resolution**: Keep orchestrator cancel-pause-load banner; fix plan wording

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1165-1173
- **Concern**: FINDING_18 pins omitted from plan harness updates. Scenario: CI fails after SKILL removes _wdce_resume_* resume refresh block
- **Proposed resolution**: Reframe FINDING_18 to design-route.sh ownership in plan and tests

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:359-361
- **Concern**: contract-drift SKILL contains pins not migrated. Scenario: Removing detailed contract-drift prose from SKILL breaks global structure greps
- **Proposed resolution**: Add driver banner pins and update contains checks in plan testing section

### FINDING_7:
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:8-13, skills/design/scripts/design-init-runparams.sh:8-13
- **Concern**: Moved operator banners are specified as stderr prints inside quiet drivers. Scenario: After larch_quiet_init, raw printf >&2 goes to the quiet log, not the caller-visible stderr; cancel/init failure recovery text can disappear and leave only the generic SKILL abort
- **Proposed resolution**: Require moved user-facing banners to use larch_err or larch_errf, and pin that no raw stderr prints are added after larch_quiet_init

### FINDING_8:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:422-447
- **Concern**: The plan allows resume env-refresh failure to be reported via ERROR= while the thinned resume branch always continues. Scenario: A driver that emits ROUTE=resume@step plus ERROR=env-refresh-failed with exit 0 would make SKILL.md print resumed and enter the resumed step with stale source-env.sh
- **Proposed resolution**: For SIMPLE scope, require design-route.sh to abort resume refresh failures with exit 1 after a visible larch_err banner; do not add a new ERROR= success-path protocol unless SKILL.md explicitly aborts on it before resume@* continues

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:359-361,1094-1095,1494-1500
- **Concern**: The test-update plan misses existing SKILL.md pins for moved operator text. Scenario: After thinning SKILL.md, test-design-structure.sh can still fail on old SKILL.md banner pins, or those pins may be deleted without replacing driver-side coverage
- **Proposed resolution**: Audit all moved banner string pins; move contract-drift, env-refresh-failed, lifecycle/archival, and session-cache banner assertions to the owning driver while keeping only thin-fence assertions in SKILL.md

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1494-1498
- **Concern**: Plan reframes Check 20/21/FINDING_20 pins but omits Check 26 session-cache banner greps still targeting SKILL.md. Scenario: After moving the reentry banner into design-route.sh, Check 26 still requires the literal banner in SKILL.md; make test-design-structure fails or the pin is dropped and banner text drifts
- **Proposed resolution**: Add Check 26 reframe to the plan: relocate the refusing spurious re-entry banner pin to design-route.sh (keep DESIGN_REENTRY_MARKER_PATH override wording); drop the SKILL.md literal requirement

### FINDING_11:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:359-361
- **Concern**: Plan migrates FINDING_20_ENV_REFRESH_BANNER but not the earlier global contract-drift contains that still require detailed SKILL.md prose. Scenario: Thin init fence replaces the contract-drift case banner with a generic INIT_STATUS abort; contains at 359-361 still require contract drift, aborting before silent tier downgrade, and bash scripts/test-write-run-params.sh in SKILL.md — CI fails unless pins move to design-init-runparams.sh or SKILL keeps duplicate text
- **Proposed resolution**: Extend test-design-structure.sh plan steps: reframe lines 359-361 to driver-side contract-drift stderr (mirror FINDING_20_ENV_REFRESH_BANNER); keep a minimal generic abort pin in SKILL.md only if still desired

### FINDING_12:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:1165-1173
- **Concern**: Plan reframes Check 21 write-design-current-env ownership but leaves FINDING_18 resume-env pins requiring _wdce_resume_args and resume failure prose in SKILL.md. Scenario: Thinned resume@* branch removes inline write-design-current-env.sh; FINDING_18 greps at 1165-1173 still fail unless explicitly updated alongside Check 21
- **Proposed resolution**: Add explicit FINDING_18 reframe to the plan: move _wdce_resume_args / resume env refresh failed pins to design-route.sh; retain Step 0a write-design-current-env mention for Check 21 line 1367

### FINDING_13:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/design/scripts/design-route.sh:241-243
- **Concern**: Resume env-refresh failure signaling is left as either driver exit 1 or ERROR= result-env without a pinned choice. Scenario: Driver exit 1 before ROUTE=resume@* emit hits orchestrator generic design-route.sh failed (exit N) unless stderr is exact; ERROR= with exit 0 needs a new orchestrator branch — implementer may pick inconsistently and lose the pinned resume env refresh failed message
- **Proposed resolution**: Pick one contract in the plan (recommend: driver stderr carries the existing resume failure text; driver exit 1 before emit_route_result; orchestrator keeps generic _route_rc abort) and add a matching pin in test-design-structure.sh

### FINDING_14:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:8-9; skills/design/scripts/design-init-runparams.sh:8-9; scripts/lib-quiet.sh:73-78,143-149
- **Concern**: Driver-owned operator banners are specified as stderr prints, but these drivers run under larch_quiet_init. Scenario: Raw printf >&2 inside either driver goes to the quiet log, while SKILL.md is being thinned to rely on the driver for the detailed cancel/env-failure reason. Operators would only see the generic abort.
- **Proposed resolution**: Specify that all moved driver banners use larch_err/larch_errf, not raw stderr, and keep the smoke/pin under normal quiet mode.

### FINDING_15:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-design-structure.sh:359-361,1287-1290,1165-1173,1494-1498
- **Concern**: Plan lists only partial test-design-structure.sh pin moves (FINDING_20 / Check 20–21). Scenario: Implementing the listed edits alone leaves greps that still require lifecycle/archival/reentry banner literals, resume `_wdce_resume_*` anchors, and contract-drift prose in `SKILL.md`; `bash scripts/test-design-structure.sh` fails after banners move to drivers
- **Proposed resolution**: Extend the harness section to reframe Check 20 (1287–1290), Check 26 (1494–1498), FINDING_9 resume pins (1165–1173), and global contract-drift pins (359–361) to `design-route.sh` / `design-init-runparams.sh`, with thin-SKILL replacements only where ordering still matters

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/design-route.sh:8-12, skills/design/scripts/design-init-runparams.sh:8-12, scripts/lib-quiet.md:31-37
- **Concern**: Plan moves user-visible banners and child failure handling into quiet phase drivers but only says to print to stderr. Scenario: After larch_quiet_init, raw stderr and nested quiet child stderr go to quiet logs, so cancel/reentry/resume/env-refresh diagnostics can disappear or trip S041 lint
- **Proposed resolution**: Specify larch_err/larch_errf for all new driver-owned operator banners and relay child failures through larch_err or FD4; pin this in the moved-banner tests

### FINDING_17:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh (proposed reentry stderr banner)
- **Concern**: Re-entry guard stderr banner must use argv CLAUDE_PID not shell $PPID. Scenario: When moved into design-route.sh, $PPID is the driver subshell parent (the Step 0b fence bash), not the Claude session id passed as --claude-pid; banner and marker_path guidance show the wrong ppid
- **Proposed resolution**: Compose the cancel-reentry-guard stderr line with issue=#$ISSUE ppid=$CLAUDE_PID (and DESIGN_REENTRY_MARKER_PATH from design_reentry_marker_path "$ISSUE" "$CLAUDE_PID"); pin the literal in test-design-structure.sh Check 20/24

### FINDING_18:
- **Reviewer(s)**: Cursor-dyn-stdout-kv-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-route.sh:4-30
- **Concern**: Plan does not require failure-tolerance around the new in-driver render-final-summary.sh calls on cancel routes. Scenario: design-route.sh runs with set -euo pipefail; render-final-summary.sh can exit non-zero (validator/upsert/tmpdir failures). An unguarded call aborts before emit_route_result, so _route_out never gets ROUTE=cancel-title-filter/cancel-reentry-guard and the orchestrator hits the generic design-route.sh failed abort instead of the cancel path with final-summary.md emit
- **Proposed resolution**: Mirror design-publish.sh:292-296: wrap each cancel-route render in set +e or append || true, still redirect stdout off the KV stream, then always emit the cancel ROUTE and print reject banners to stderr

### FINDING_19:
- **Reviewer(s)**: Cursor-dyn-stdout-kv-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:51-569
- **Concern**: Thinned cancel-title-filter/cancel-reentry-guard branches say emit final-summary.md verbatim but omit the shared [ -s ... ] non-empty gate used elsewhere. Scenario: After stdout is redirected in the driver, chat summary depends entirely on orchestrator file emit. If render fails without writing final-summary.md, a gateless emit is a no-op and the operator gets only the stderr reject banner with no structured ## /design run block (regression vs today un-captured render stdout)
- **Proposed resolution**: Add to the SKILL.md Step 0b cancel branch spec the same gate as ### Final summary block (lines 569+): when [ -s ${FINAL_SUMMARY_PATH:-$DESIGN_TMPDIR/final-summary.md} ] emit verbatim; pin it in test-design-structure.sh alongside the thinned-branch verbatim emit pin

### FINDING_20:
- **Reviewer(s)**: Codex-dyn-stdout-kv-isolation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:28-31,65-76; skills/design/scripts/render-final-summary.sh:533-541,543-573
- **Concern**: FINDING_1: The plan requires redirecting render-final-summary.sh stdout on cancel-title-filter and cancel-reentry-guard but never chooses an exact stdout target or states that stderr remains unredirected.. Scenario: render-final-summary.sh post phase prints final-summary.md to stdout before upserting; inside design-route.sh that stdout shares the captured KV stream. An implementer could use no redirect or redirect to stderr, polluting or duplicating the operator summary; using 2>&1 would also hide stderr diagnostics from render-final-summary/upsert failures.
- **Proposed resolution**: Specify the exact redirection on both proposed design-route.sh call sites, e.g. `--post-publish-only >/dev/null` and no `2>&1`, with a small harness pin that both cancel-route calls redirect stdout while leaving stderr live.

### FINDING_21:
- **Reviewer(s)**: Cursor-dyn-harness-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-design-structure.sh:359-361,1094-1095,1165-1173,1287-1290,1494-1498
- **Concern**: Harness reframe list is incomplete for every banner/refresh string removed from SKILL.md Step 0b. Scenario: After thinning, CI fails on untouched pins still grepping SKILL.md for contract-drift prose (359-361), env-refresh banner (1094-1095), resume refresh (_wdce_resume_args / failure text at 1165-1173), title-filter banners (1287-1290), and Check 26 reentry banner (1494-1498) even if the three items named in plan.txt:55-58 are reframed
- **Proposed resolution**: Extend the test-design-structure.sh section to enumerate each pin ID with its new driver target and grep literal (e.g. contract-drift + test-write-run-params.sh → design-init-runparams.sh; session-cache banner → design-route.sh; resume refresh → design-route.sh replacing FINDING_9/FINDING_18 SKILL.md greps)

### FINDING_22:
- **Reviewer(s)**: Codex-dyn-harness-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:31,55-60; skills/design/SKILL.md:403-420; scripts/test-design-structure.sh:1161-1164,1378-1392
- **Concern**: Reentry-guard banner move lacks a named driver-side harness pin. Scenario: The plan moves the reentry refusal banner and MARKER_REMAINING math from SKILL.md into design-route.sh, but the harness instructions only name title-filter, resume, and init-message pins; current Check 24 only preserves branch ordering, so the reentry banner could be dropped while tests still pass
- **Proposed resolution**: Add an explicit scripts/test-design-structure.sh pin against DESIGN_ROUTE_SH for the reentry banner text, e.g. 'refusing spurious re-entry — guard=session-cache' plus the Wait/delete override wording or MARKER_REMAINING calculation

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-harness-pin-migration
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:41-48,55-56; scripts/test-design-structure.sh:359-361
- **Concern**: The contract-drift harness update says add a companion driver pin but does not say to replace existing SKILL.md pins. Scenario: Current test-design-structure.sh still asserts contract-drift, silent-tier-downgrade, and test-write-run-params prose in SKILL.md; following the plan literally either leaves the fat SKILL.md banner in place or makes the harness fail after thinning
- **Proposed resolution**: Change the plan to explicitly reframe scripts/test-design-structure.sh:359-361 from SKILL_MD to DESIGN_INIT_SH, pinning the same contract-drift message fragments in design-init-runparams.sh rather than adding only a companion check

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-harness-pin-migration
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:32,51,58-60; scripts/test-design-structure.sh:1165-1173,1367-1369
- **Concern**: The resume env-refresh move does not account for existing resume-specific FINDING_9 and FINDING_18 SKILL.md pins. Scenario: The plan reframes Check 21 generically, but current harness pins _wdce_resume_args, repo forwarding, rc capture, and the failure banner inside the Step 0b SKILL.md block; after moving that code to design-route.sh, those pins will either fail or pressure the implementer to keep the old SKILL.md refresh code
- **Proposed resolution**: Explicitly direct the implementer to retarget scripts/test-design-structure.sh:1165-1173 to DESIGN_ROUTE_SH for the resume write-design-current-env.sh args, repo forwarding, rc/error handling, and failure message; keep only the generic SKILL.md resumed-from-STEP branch pin as needed

