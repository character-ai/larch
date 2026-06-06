### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:30,136-137
- **Concern**: Auth-prep failure contract cites launch-review.sh:442-455 but omits .meta/.done synthesis and says exit non-zero. Scenario: Background /research, validation, voter, and judge lanes wait on ${OUTPUT}.done via collect-agent-results.sh; launcher that only truncates output and writes .diag (or exits non-zero) without stub .meta/CMD_JSON=[] and .done leaves SENTINEL_TIMEOUT for up to 1860s — contradicting the edge-case fail-fast claim
- **Proposed resolution**: Mirror launch-review.sh:444-463 exactly: truncate output, write STATUS=FAILED .diag, write stub .meta, write .done with AUTH_PREP_RC, process exit 0; extend test-launch-codex-exec.sh and launch-codex-exec.md to pin that bundle

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:76-78,scripts/lint-fix-loop.sh:537
- **Concern**: launch-codex-exec.sh is modeled on launch-codex-ci.sh (always exit 0, LAUNCHER_EXIT kv) but run_codex() rewrite does not define how foreground callers read failure. Scenario: run_codex return value drives `if run_codex ...; then` at lint-fix-loop.sh:537; a launcher that exits 0 while emitting LAUNCHER_EXIT=N makes codex auth/exec failures look successful, skipping the codex→cursor waterfall and proceeding with a failed codex.log
- **Proposed resolution**: Specify run_codex captures launcher stdout and maps LAUNCHER_EXIT to its return code (ship-pr.sh pattern), or document an alternate contract; extend test-lint-fix-loop.sh to assert non-zero run_codex on stubbed auth/exec failure

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:537-540, scripts/collect-agent-results.sh:293-315
- **Concern**: Proposed generic launcher lacks an explicit process-exit and pre-run sentinel contract. Scenario: If launch-codex-exec.sh follows launch-codex-ci.sh and only emits LAUNCHER_EXIT while exiting 0, lint-fix-loop treats failed Codex as success and skips Cursor fallback; if auth setup fails before run-external-agent without writing OUTPUT.done, collect-agent-results waits until sentinel timeout instead of failing fast.
- **Proposed resolution**: Define launch-codex-exec.sh to write minimal OUTPUT.meta and OUTPUT.done on all pre-run failures, then either exit with the inner LAUNCHER_EXIT or update run_codex to parse LAUNCHER_EXIT before returning.

### FINDING_4:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/run-negotiation-round.sh:84-93
- **Concern**: Negotiation Codex auth wiring omits trusted-project config from the explicit launch shape. Scenario: The plan moves negotiation to an ephemeral CODEX_HOME; without -c projects."<workspace>".trust_level="trusted", a workspace that was trusted only in the user's normal Codex config can fail before the stdin-piped prompt runs.
- **Proposed resolution**: When adding CODEX_AUTH_ARGS, also compute PROJECT_KEY from WORKSPACE and pass -c "$TRUST_CONFIG_ARG" before the auth args, matching check-reviewers.sh and the new launcher; generate the generic launcher trust arg from --workdir.

### FINDING_5:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh:30 / plan.txt:136-137
- **Concern**: Auth-prep preflight omits `${OUTPUT}.meta` and `${OUTPUT}.done` stubs the plan claims enable fail-fast collection. Scenario: Background `/research`, validation, voter, and judge fences wait on `${OUTPUT}.done` via `wait-for-reviewers.sh`. Auth-prep failure before `run-external-agent.sh` leaves no sentinel; collector hits `SENTINEL_TIMEOUT` (~21–31 min) despite `.diag` only. `launch-review.sh:444-463` writes `.meta`+`.done`+`.diag` for this path.
- **Proposed resolution**: Mirror `launch-review.sh:444-463` on auth-prep (and other pre-`run-external-agent` prefights): truncate output, write `.diag`/`STATUS=FAILED`, stub `.meta` (`CMD_JSON=[]`) and `.done` (non-zero rc). Extend harness to assert all three artifacts.

### FINDING_6:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:363-388 / scripts/launch-codex-exec.sh
- **Concern**: `run_codex()` exit-code propagation not reconciled with `launch-codex-ci.sh` always-`exit 0` pattern. Scenario: Plan copies `launch-codex-ci.sh` which always `exit 0` and emits `LAUNCHER_EXIT` on stdout for `ship-pr.sh`. `run_codex` uses `launch-codex-exec.sh … || codex_rc=$?` and gates Cursor fallback at line 537. Launcher exit 0 on Codex failure makes `run_codex` return 0 and lint-fix may treat a failed Codex run as success.
- **Proposed resolution**: Specify terminal `exit "$LAUNCHER_EXIT"` in `launch-codex-exec.sh` (preflight and exec paths), or have `run_codex` parse `LAUNCHER_EXIT` from launcher stdout. Pin the chosen contract in `test-lint-fix-loop.sh`.

### FINDING_7:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:68-93 / plan.txt:86
- **Concern**: Inline negotiation wiring omits `~/.codex/config.toml` copy present in `check-reviewers.sh:211-213`. Scenario: Negotiation today uses the real `~/.codex` tree. Ephemeral `CODEX_HOME` with only `auth.json` drops user `config.toml` settings (model/provider defaults) on the login path.
- **Proposed resolution**: When copying `check-reviewers.sh:214-242`, include the `config.toml` copy/strip step from lines 211-213, or document login-path config loss as accepted.

### FINDING_8:
- **Reviewer(s)**: Codex-Edge, Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh (planned auth-prep failure path); scripts/collect-agent-results.sh:293-310; scripts/launch-review.sh:451-463
- **Concern**: Planned auth-prep failure path omits the .done sentinel contract. Scenario: The plan says to truncate output and write .diag before exiting non-zero, but collect-agent-results waits on OUTPUT.done; a pre-launch auth setup failure would sit until SENTINEL_TIMEOUT and hide the env-key auth reason instead of failing fast
- **Proposed resolution**: Mirror the full launch-review preflight failure contract: write OUTPUT.diag, a minimal OUTPUT.meta, and OUTPUT.done with the auth-prep exit code before returning; add the auth-failure harness assertion for .done and collector FAILED behavior

### FINDING_9:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:363-388; scripts/lint-fix-loop.sh:537-540; scripts/launch-codex-ci.sh:258-264
- **Concern**: Launcher exit status is ambiguous for the lint-fix-loop caller. Scenario: run_codex currently returns the external-agent exit code and the caller waterfalls to Cursor/main-agent on failure; a launcher modeled on launch-codex-ci may emit LAUNCHER_EXIT but exit 0, causing lint-fix-loop to treat failed Codex dispatch as selected and skip fallback
- **Proposed resolution**: Make launch-codex-exec.sh exit with LAUNCHER_EXIT for this generic caller, or have lint-fix-loop parse the emitted LAUNCHER_EXIT and return non-zero when it is non-zero; pin this in test-lint-fix-loop.sh

### FINDING_10:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh:30 <TMPDIR>/plan.txt:134-137
- **Concern**: Auth-prep failure spec stops at .diag and omits collector sentinels. Scenario: When external_prepare_codex_auth fails before run-external-agent.sh runs, the plan only requires truncating OUTPUT and writing ${OUTPUT}.diag then exiting non-zero. collect-agent-results.sh waits on ${OUTPUT}.done (scripts/collect-agent-results.sh:758-771); without a launcher-written .done (and the companion .meta launch-review.sh writes at 455-462), background /research, validation, voter, and judge lanes hit SENTINEL_TIMEOUT instead of fast FAILED with the .diag reason — contradicting the edge-case claim that .diag alone enables fail-fast
- **Proposed resolution**: Mirror the full launch-review.sh:444-463 auth-prep block: write ${OUTPUT}.diag, ${OUTPUT}.meta (TOOL/TIMEOUT/OUTPUT_FILE/CMD_JSON=[]), and ${OUTPUT}.done with AUTH_PREP_RC; exit 0 like launch-review (not non-zero). Pin .done/.meta in test-launch-codex-exec.sh and launch-codex-exec.md, not only .diag

### FINDING_11:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/collect-agent-results.sh:293-316
- **Concern**: Planned launch-codex-exec auth-prep failure path does not state it writes the required .done sentinel. Scenario: When external_prepare_codex_auth fails before run-external-agent.sh runs, collect-agent-results.sh waits for <output>.done until timeout even though the launcher already failed, so the “fail fast” contract regresses
- **Proposed resolution**: Make scripts/launch-codex-exec.sh mirror launch-review.sh’s full early-failure contract: truncate output, write .diag, write .meta, and write <output>.done with the failure exit code before exiting; add this to test-launch-codex-exec.sh

### FINDING_12:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:537-540
- **Concern**: Plan does not pin launch-codex-exec failure status for lint-fix-loop’s Codex waterfall branch. Scenario: run_codex() is used in an if condition; if the new launcher follows launch-codex-ci.sh’s emit-KV-but-exit-0 pattern on child failure, lint-fix-loop treats failed Codex as success and skips Cursor/main-agent fallback
- **Proposed resolution**: Define launch-codex-exec.sh to exit with the underlying Codex/run-external-agent status, or have run_codex() capture launcher stdout, parse LAUNCHER_EXIT, keep launcher KVs out of lint-fix-loop stdout, and return that parsed status

### FINDING_13:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh:30
- **Concern**: Auth-prep failure spec is incomplete vs launch-review.sh:442-463. Scenario: Plan copies launch-codex-ci mechanics but cites launch-review for auth-prep failure yet only mandates truncating OUTPUT and writing .diag then exiting non-zero; it omits stub .meta and .done sidecars and conflicts with launch-review exit 0. Background fences wait on ${OUTPUT}.done via collect-agent-results.sh; without a sentinel the lane hits SENTINEL_TIMEOUT (~1860s) despite the edge-case claim of fail-fast collection
- **Proposed resolution**: Mirror launch-review.sh:442-463 fully on auth-prep failure: truncate OUTPUT; write .diag with STATUS=FAILED and env-key-aware FAILURE_REASON; write minimal .meta (TOOL/TIMEOUT/CMD_JSON=[]); write .done with the prep RC; exit 0. Extend test-launch-codex-exec.sh to assert .meta and .done exist

### FINDING_14:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:363-388
- **Concern**: Plan omits exit-code propagation after routing run_codex() through launch-codex-exec.sh. Scenario: launch-codex-exec.sh is modeled on launch-codex-ci.sh which always exits 0 and reports status via emit_kv LAUNCHER_EXIT. run_codex() currently returns the run-external-agent.sh RC and gates the codex→cursor waterfall at line 537; a bare launcher invocation would make run_codex appear successful on auth or exec failure
- **Proposed resolution**: After invoking launch-codex-exec.sh capture LAUNCHER_EXIT from stdout (ship-pr pattern) or read ${run_dir}/codex.log.done and return that RC; document the contract in lint-fix-loop.md and pin it in test-lint-fix-loop.sh

### FINDING_15:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/wait-for-reviewers.sh:92-147
- **Concern**: Auth-prep failure path for the new launch-codex-exec writes output and .diag but no .done sentinel. Scenario: The research/voter/judge collectors wait only for <output>.done; if external_prepare_codex_auth fails before run-external-agent starts, collect-agent-results waits the full timeout instead of failing fast
- **Proposed resolution**: Mirror the full launch-review auth-prep block: also write ${OUTPUT}.meta and ${OUTPUT}.done with AUTH_PREP_RC before returning

### FINDING_16:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/lint-fix-loop.sh:537-540
- **Concern**: run_codex rewrite risks losing the Codex child exit status. Scenario: If launch-codex-exec follows launch-codex-ci and reports Codex failure via LAUNCHER_EXIT while exiting 0, lint-fix-loop treats a failed Codex run as success and skips Cursor/main-agent fallback
- **Proposed resolution**: Capture launcher stdout in run_codex, parse LAUNCHER_EXIT, and return non-zero when it is non-zero; or explicitly make the launcher exit with the child status while preserving the sentinel contract

### FINDING_17:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-negotiation-round.sh:89-94
- **Concern**: Proposed ephemeral CODEX_HOME negotiation path omits the trusted-project config. Scenario: The new temp CODEX_HOME has no saved workspace trust, so codex exec --full-auto can fail or prompt/refuse for the workspace even though the old real-home path worked
- **Proposed resolution**: Compute the trust config from WORKSPACE and pass -c projects."<workspace>".trust_level="trusted" with the auth args; add this to the negotiation harness assertions

### FINDING_18:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh (proposed; plan.txt:30)
- **Concern**: Auth-prep failure path omits collector sidecars and contradicts launch-review exit semantics. Scenario: Plan cites launch-review.sh:442-455 (.diag only) but not 456-462 (.meta/.done) and says exit non-zero; collect-agent-results.sh waits on ${OUTPUT}.done (collect-agent-results.sh:772) so background /research/voter/judge lanes hit SENTINEL_TIMEOUT instead of fast FAILED
- **Proposed resolution**: Copy the full launch-review prelaunch-failure block: truncate OUTPUT write .diag STATUS=FAILED write stub .meta (CMD_JSON=[]) write .done with AUTH_PREP_RC exit 0; extend test-launch-codex-exec.sh to assert .meta/.done on auth-prep failure

### FINDING_19:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:363-388
- **Concern**: Plan rewrites run_codex() to call launch-codex-exec.sh but does not say how to obtain the real exit code. Scenario: launch-codex-exec.sh is modeled on launch-codex-ci.sh which always exits 0 and reports failure via LAUNCHER_EXIT= stdout KV (launch-codex-ci.sh:258-264); lint-fix-loop.sh:537 branches on run_codex return value so a bare invocation would treat Codex failures as success
- **Proposed resolution**: Parse LAUNCHER_EXIT from launcher stdout (or equivalent contract documented in launch-codex-exec.md) and return that RC from run_codex(); pin in test-lint-fix-loop.sh

### FINDING_20:
- **Reviewer(s)**: Cursor-dyn-auth-surface
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/lint-codex-exec-auth.sh:46
- **Concern**: Shell rule uses file-scope external_prepare_codex_auth presence instead of per-invocation wiring. Scenario: A file can call external_prepare_codex_auth once yet launch codex exec without ${CODEX_AUTH_ARGS[@]}; harness only tests helper-referencing files pass, so OPENAI_API_KEY preference can regress undetected (e.g. run-negotiation-round.sh codex branch)
- **Proposed resolution**: Tighten rule (a): flag each non-comment codex exec line unless it is inside launch-codex-exec.sh, carries a pragma, or the same function/block also expands CODEX_AUTH_ARGS immediately before exec; drop file-scope helper-presence bypass

### FINDING_21:
- **Reviewer(s)**: Codex-dyn-auth-surface
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:293-310; scripts/launch-review.sh:451-463
- **Concern**: Finding 1: planned launch-codex-exec auth fast-fail omits the collector sentinel requirement. Scenario: The plan says auth-prep failure truncates output and writes .diag, but collect-agent-results waits on output.done; without a .done like launch-review writes, background research/voter/judge lanes can wait until timeout instead of failing fast
- **Proposed resolution**: Add explicit planned behavior and harness assertions that auth-prep and other pre-run failures write OUTPUT, OUTPUT.diag, OUTPUT.meta, and OUTPUT.done with the failure exit code before exiting

### FINDING_22:
- **Reviewer(s)**: Cursor-dyn-launcher-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-codex-exec.sh:30 / plan.txt:136
- **Concern**: Auth-prep failure path omits collector sentinels the cited reference writes. Scenario: Plan cites launch-review.sh:442-455 but not 455-462; edge case claims .diag alone makes collect-agent-results.sh fail fast, yet collect-agent-results.sh:758-770 only unblocks on ${OUTPUT}.done — auth-prep failure without .meta/.done waits full collector timeout
- **Proposed resolution**: Specify auth-prep failure must also write ${OUTPUT}.meta (TOOL/TIMEOUT/OUTPUT_FILE/CMD_JSON=[]) and ${OUTPUT}.done with AUTH_PREP_RC, matching launch-review.sh:455-462; update edge-case prose and harness to assert both files

### FINDING_23:
- **Reviewer(s)**: Codex-dyn-launcher-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:30,136; scripts/run-external-agent.sh:155-168; scripts/collect-agent-results.sh:293-316; scripts/launch-review.sh:451-463
- **Concern**: Planned auth-prep failure path writes output and .diag but not the .done sentinel that collect-agent-results waits on. Scenario: For background research/voter/judge fences, launch-codex-exec can fail before run-external-agent runs; collect-agent-results then waits for OUTPUT.done until timeout instead of failing fast
- **Proposed resolution**: Mirror the full launch-review early-failure sidecar contract: truncate output, write .diag, write .meta, and write OUTPUT.done with the failure code before exiting

### FINDING_24:
- **Reviewer(s)**: Codex-dyn-launcher-contracts
- **Severity**: latent
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:30,62-74,137; scripts/collect-agent-results.sh:489-496
- **Concern**: Planned research, validation, voter, and judge launcher calls omit --add-dir, but the collector's Codex retry shape validator requires --add-dir. Scenario: An empty-output retry reconstructs CMD_JSON, rejects the argv shape before relaunch, and reports retry metadata invalid instead of performing the documented one-shot retry
- **Proposed resolution**: Ensure collect-managed launch-codex-exec invocations include at least one --add-dir, preferably by defaulting to --add-dir "$workdir" when the caller supplies none

### FINDING_25:
- **Reviewer(s)**: Cursor-dyn-harness-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:444-463
- **Concern**: Auth-prep failure contract for launch-codex-exec is incomplete and contradicts the cited model. Scenario: Plan line 30 cites launch-review.sh:442-455 but specifies only truncate OUTPUT plus .diag and exit non-zero; launch-review also writes ${OUTPUT}.meta and ${OUTPUT}.done and exits 0. collect-agent-results.sh fast-fails on .diag plus sidecar metadata; without .meta/.done a background research or voter fence can sit until timeout on empty output
- **Proposed resolution**: Mirror the full launch-review preflight synthesis (.diag STATUS=FAILED, .meta with TOOL/TIMEOUT/OUTPUT_FILE, .done with prep rc, exit 0) in launch-codex-exec.md and test-launch-codex-exec.sh; drop the exit non-zero requirement for this path

### FINDING_26:
- **Reviewer(s)**: Codex-dyn-harness-coverage
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:451-463; scripts/wait-for-reviewers.sh:99-104
- **Concern**: Planned auth-prep failure harness only asserts output truncation and .diag, but the proposed launcher can fail before run-external-agent creates .done/.meta. Scenario: Backgrounded research/voter/judge callers pass output files to collect-agent-results, which waits on .done sentinels; an auth-prep failure would wait until timeout instead of failing fast
- **Proposed resolution**: Mirror launch-review on auth-prep failure by writing OUTPUT.meta and OUTPUT.done, and add harness assertions for both sidecars

### FINDING_27:
- **Reviewer(s)**: Codex-dyn-harness-coverage
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/collect-agent-results.sh:489-496; skills/research/references/research-phase.md:162-165
- **Concern**: Planned launcher/caller tests do not cover collector retry argv shape; proposed collected calls omit --add-dir while the Codex retry allowlist requires it. Scenario: An empty-output retry for research/validation/voter/judge output is rejected as invalid metadata, so the plan's collector-retry/auth persistence claim would not hold
- **Proposed resolution**: Either pass a safe --add-dir for collected launch-codex-exec callers or adjust the collector allowlist, then add one harness path that drives collect-agent-results retry from launcher-written .meta
