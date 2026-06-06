### FINDING_1: Auth-prep/pre-run failures omit collector sidecars
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Requirements, Cursor-Innovation, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements, Codex-dyn-auth-surface, Cursor-dyn-launcher-contracts, Codex-dyn-launcher-contracts, Cursor-dyn-harness-coverage, Codex-dyn-harness-coverage
- **Severity**: important
- **Concern**: The planned `launch-codex-exec.sh` auth-prep/pre-run failure path only truncates output and writes `.diag`, but background collectors wait on `${OUTPUT}.done` and expect sidecar metadata. Without writing `.meta` and `.done`, research/validation/voter/judge lanes can stall until sentinel timeout instead of failing fast with the auth-prep reason; several reviewers also note the plan conflicts with `launch-review.sh` by saying to exit non-zero instead of synthesizing sidecars and returning in the existing launcher style.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror launch-review.sh:444-463 exactly: truncate output, write STATUS=FAILED .diag, write stub .meta, write .done with AUTH_PREP_RC, process exit 0; extend test-launch-codex-exec.sh and launch-codex-exec.md to pin that bundle
  - From Codex-Arch: Define launch-codex-exec.sh to write minimal OUTPUT.meta and OUTPUT.done on all pre-run failures, then either exit with the inner LAUNCHER_EXIT or update run_codex to parse LAUNCHER_EXIT before returning.
  - From Cursor-Edge: Mirror `launch-review.sh:444-463` on auth-prep (and other pre-`run-external-agent` prefights): truncate output, write `.diag`/`STATUS=FAILED`, stub `.meta` (`CMD_JSON=[]`) and `.done` (non-zero rc). Extend harness to assert all three artifacts.
  - From Codex-Edge: Mirror the full launch-review preflight failure contract: write OUTPUT.diag, a minimal OUTPUT.meta, and OUTPUT.done with the auth-prep exit code before returning; add the auth-failure harness assertion for .done and collector FAILED behavior
  - From Cursor-Innovation: Mirror the full launch-review.sh:444-463 auth-prep block: write ${OUTPUT}.diag, ${OUTPUT}.meta (TOOL/TIMEOUT/OUTPUT_FILE/CMD_JSON=[]), and ${OUTPUT}.done with AUTH_PREP_RC; exit 0 like launch-review (not non-zero). Pin .done/.meta in test-launch-codex-exec.sh and launch-codex-exec.md, not only .diag
  - From Codex-Innovation: Make scripts/launch-codex-exec.sh mirror launch-review.sh’s full early-failure contract: truncate output, write .diag, write .meta, and write <output>.done with the failure exit code before exiting; add this to test-launch-codex-exec.sh
  - From Cursor-Pragmatic: Mirror launch-review.sh:442-463 fully on auth-prep failure: truncate OUTPUT; write .diag with STATUS=FAILED and env-key-aware FAILURE_REASON; write minimal .meta (TOOL/TIMEOUT/CMD_JSON=[]); write .done with the prep RC; exit 0. Extend test-launch-codex-exec.sh to assert .meta and .done exist
  - From Codex-Pragmatic: Mirror the full launch-review auth-prep block: also write ${OUTPUT}.meta and ${OUTPUT}.done with AUTH_PREP_RC before returning
  - From Cursor-Requirements: Copy the full launch-review prelaunch-failure block: truncate OUTPUT write .diag STATUS=FAILED write stub .meta (CMD_JSON=[]) write .done with AUTH_PREP_RC exit 0; extend test-launch-codex-exec.sh to assert .meta/.done on auth-prep failure
  - From Codex-dyn-auth-surface: Add explicit planned behavior and harness assertions that auth-prep and other pre-run failures write OUTPUT, OUTPUT.diag, OUTPUT.meta, and OUTPUT.done with the failure exit code before exiting
  - From Cursor-dyn-launcher-contracts: Specify auth-prep failure must also write ${OUTPUT}.meta (TOOL/TIMEOUT/OUTPUT_FILE/CMD_JSON=[]) and ${OUTPUT}.done with AUTH_PREP_RC, matching launch-review.sh:455-462; update edge-case prose and harness to assert both files
  - From Codex-dyn-launcher-contracts: Mirror the full launch-review early-failure sidecar contract: truncate output, write .diag, write .meta, and write OUTPUT.done with the failure code before exiting
  - From Cursor-dyn-harness-coverage: Mirror the full launch-review preflight synthesis (.diag STATUS=FAILED, .meta with TOOL/TIMEOUT/OUTPUT_FILE, .done with prep rc, exit 0) in launch-codex-exec.md and test-launch-codex-exec.sh; drop the exit non-zero requirement for this path
  - From Codex-dyn-harness-coverage: Mirror launch-review on auth-prep failure by writing OUTPUT.meta and OUTPUT.done, and add harness assertions for both sidecars

### FINDING_2: lint-fix-loop could lose Codex failure status
- **Reviewer(s)**: Cursor-Arch, Codex-Arch, Cursor-Edge, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Codex-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: `run_codex()` is planned to call a launcher modeled on `launch-codex-ci.sh`, which may emit `LAUNCHER_EXIT` while exiting 0. Because `lint-fix-loop.sh` branches on `run_codex`’s return value to decide whether to fall back to Cursor/main-agent, Codex auth or exec failures could be treated as success and skip the waterfall.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Specify run_codex captures launcher stdout and maps LAUNCHER_EXIT to its return code (ship-pr.sh pattern), or document an alternate contract; extend test-lint-fix-loop.sh to assert non-zero run_codex on stubbed auth/exec failure
  - From Codex-Arch: Define launch-codex-exec.sh to write minimal OUTPUT.meta and OUTPUT.done on all pre-run failures, then either exit with the inner LAUNCHER_EXIT or update run_codex to parse LAUNCHER_EXIT before returning.
  - From Cursor-Edge: Specify terminal `exit "$LAUNCHER_EXIT"` in `launch-codex-exec.sh` (preflight and exec paths), or have `run_codex` parse `LAUNCHER_EXIT` from launcher stdout. Pin the chosen contract in `test-lint-fix-loop.sh`.
  - From Codex-Edge: Make launch-codex-exec.sh exit with LAUNCHER_EXIT for this generic caller, or have lint-fix-loop parse the emitted LAUNCHER_EXIT and return non-zero when it is non-zero; pin this in test-lint-fix-loop.sh
  - From Codex-Innovation: Define launch-codex-exec.sh to exit with the underlying Codex/run-external-agent status, or have run_codex() capture launcher stdout, parse LAUNCHER_EXIT, keep launcher KVs out of lint-fix-loop stdout, and return that parsed status
  - From Cursor-Pragmatic: After invoking launch-codex-exec.sh capture LAUNCHER_EXIT from stdout (ship-pr pattern) or read ${run_dir}/codex.log.done and return that RC; document the contract in lint-fix-loop.md and pin it in test-lint-fix-loop.sh
  - From Codex-Pragmatic: Capture launcher stdout in run_codex, parse LAUNCHER_EXIT, and return non-zero when it is non-zero; or explicitly make the launcher exit with the child status while preserving the sentinel contract
  - From Cursor-Requirements: Parse LAUNCHER_EXIT from launcher stdout (or equivalent contract documented in launch-codex-exec.md) and return that RC from run_codex(); pin in test-lint-fix-loop.sh

### FINDING_3: Negotiation Codex path omits trusted-project config
- **Reviewer(s)**: Codex-Arch, Codex-Pragmatic
- **Severity**: important
- **Concern**: The proposed ephemeral `CODEX_HOME` negotiation wiring does not explicitly pass the workspace trust config. Workspaces trusted only in the user’s normal Codex config may fail or prompt/refuse before the stdin prompt runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: When adding CODEX_AUTH_ARGS, also compute PROJECT_KEY from WORKSPACE and pass -c "$TRUST_CONFIG_ARG" before the auth args, matching check-reviewers.sh and the new launcher; generate the generic launcher trust arg from --workdir.
  - From Codex-Pragmatic: Compute the trust config from WORKSPACE and pass -c projects."<workspace>".trust_level="trusted" with the auth args; add this to the negotiation harness assertions

### FINDING_4: Negotiation ephemeral CODEX_HOME drops config.toml
- **Reviewer(s)**: Cursor-Edge
- **Severity**: latent
- **Concern**: The inline negotiation auth path copies only `auth.json` into an ephemeral `CODEX_HOME`, unlike the existing reviewer check path that also preserves/strips `config.toml`. This can drop model/provider defaults or other user config used by the login path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: When copying `check-reviewers.sh:214-242`, include the `config.toml` copy/strip step from lines 211-213, or document login-path config loss as accepted.

### FINDING_5: Codex exec auth lint checks file-scope helper presence instead of invocation wiring
- **Reviewer(s)**: Cursor-dyn-auth-surface
- **Severity**: important
- **Concern**: `scripts/lint-codex-exec-auth.sh` can pass a file merely because it references `external_prepare_codex_auth` somewhere, even if individual `codex exec` invocations do not expand `${CODEX_AUTH_ARGS[@]}`. This leaves OPENAI_API_KEY preference regressions undetected in branches such as negotiation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-auth-surface: Tighten rule (a): flag each non-comment codex exec line unless it is inside launch-codex-exec.sh, carries a pragma, or the same function/block also expands CODEX_AUTH_ARGS immediately before exec; drop file-scope helper-presence bypass

### FINDING_6: Collected launcher calls omit --add-dir required by retry validator
- **Reviewer(s)**: Codex-dyn-launcher-contracts, Codex-dyn-harness-coverage
- **Severity**: important
- **Concern**: Planned research/validation/voter/judge `launch-codex-exec` calls omit `--add-dir`, but collector retry validation requires that shape. Empty-output retry could reject reconstructed metadata as invalid instead of performing the intended one-shot retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-launcher-contracts: Ensure collect-managed launch-codex-exec invocations include at least one --add-dir, preferably by defaulting to --add-dir "$workdir" when the caller supplies none
  - From Codex-dyn-harness-coverage: Either pass a safe --add-dir for collected launch-codex-exec callers or adjust the collector allowlist, then add one harness path that drives collect-agent-results retry from launcher-written .meta
