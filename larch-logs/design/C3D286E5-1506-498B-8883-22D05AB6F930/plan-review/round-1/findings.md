### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:477-905
- **Concern**: Plan stores --risk in retry metadata but still leaves the live launch paths hard-wired to high effort. Scenario: Collector retries pass --risk low back into launch-review.sh, but Codex still calls agent-model-args.sh --with-effort and Cursor still wraps the prompt with /max-mode on, so the retry records OUTER_LAUNCHER_RISK=low while running with high-risk behavior
- **Proposed resolution**: Capture RISK in both lanes and use it at the existing effort gates: omit Codex --with-effort when RISK=low, and skip cursor-wrap-prompt.sh max-mode wrapping when RISK=low. Add the planned meta tests plus a live argv or prompt assertion for low risk.

### FINDING_2:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:25-26,51;scripts/test-launch-review.sh:1371-1390
- **Concern**: Runtime stderr-sink check targets run-external-agent argv but harness only records leaf CLI argv. Scenario: CODEX_STUB_ARGV_LOG/CURSOR_STUB_ARGV_LOG capture codex/cursor argv, not scripts/run-external-agent.sh; following the plan literally can replace the source grep with a stub check that still passes if _RUN_EXTERNAL_SINK_ARGS never reaches run-external-agent
- **Proposed resolution**: Keep run-external-agent real; assert STDERR_SINK= appears before OUTER_LAUNCHER= in the primary .meta (run-external writes base meta before append_outer_meta) or add a test-only run-external-agent wrapper on PATH that logs argv

### FINDING_3:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-review.sh:1372-1389, scripts/test-collect-agent-retry.sh:815-821
- **Concern**: Runtime forwarding tests are specified against argv capture points that cannot observe the forwarded flag. Scenario: launch-review.sh invokes scripts/run-external-agent.sh by absolute path, so the existing leaf CLI argv logs will not contain wrapper flags; collect-agent-results.sh also rejects non-canonical OUTER_LAUNCHER stubs, so a stub launcher path will fail before exercising forwarding
- **Proposed resolution**: Keep real launcher/helper paths and assert observable artifacts instead: for launch-review count exact STDERR_SINK records in OUTPUT.meta; for collector CMD_JSON assert retry-output.meta contains STDERR_SINK; for outer retry use canonical scripts/launch-review.sh with existing CLI stubs and assert the retry meta shows both wrapper and outer records

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Focus area**: code-quality
- **Location**: scripts/launch-cursor-implement.sh:339, scripts/launch-cursor-ci.sh:227, scripts/lib-external-launcher-common.sh:19
- **Concern**: The cursor implement/CI empty-argument edits are behavior-neutral future-proofing in a SIMPLE plan. Scenario: These edits add two extra files without fixing the discarded launch-review --risk bug or a failing test; passing an empty 5th arg also still falls through to ${RISK:-high}, so it does not pin high if RISK is inherited
- **Proposed resolution**: Drop the launch-cursor-implement.sh and launch-cursor-ci.sh call-site edits from this PR unless a current failing contract requires them

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-review.sh:1381-1384
- **Concern**: Runtime stderr-sink plan points at codex stub argv, not run-external-agent. Scenario: Plan says reuse $ARGV / CODEX_STUB_ARGV_LOG; that log is the stubbed codex exec argv. launch-review calls $SCRIPT_DIR/run-external-agent.sh by absolute path, so a passing test could still drop _RUN_EXTERNAL_SINK_ARGS while .meta STDERR_SINK= from append_outer_meta stays green
- **Proposed resolution**: Assert STDERR_SINK= appears before the first OUTER_LAUNCHER= line in ${OUTPUT}.meta (run-external block precedes append_outer_meta); mirror for cursor lane without adding a cursor argv logger unless needed

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation, Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:477
- **Concern**: Plan records --risk in outer meta but still leaves Codex effort hardcoded on the primary launch and replay launch. Scenario: --risk low round-trips to OUTER_LAUNCHER_RISK=low, but launch-review.sh still calls agent-model-args.sh --tool codex --with-effort, so low-risk retries do not actually use low effort
- **Proposed resolution**: Add parsed RISK gating around the model-args call and test that --risk low omits Codex effort args, not only that the .meta value is low

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:592-616
- **Concern**: Proposed collector runtime test cannot point OUTER_LAUNCHER at an argv-recording stub. Scenario: The collector rejects non-canonical OUTER_LAUNCHER values before launch, so the test case described in the plan would fail for the validation guard rather than exercise stderr-sink forwarding
- **Proposed resolution**: Keep OUTER_LAUNCHER as the canonical scripts/launch-review.sh path and assert forwarding through downstream artifacts such as the retry .meta STDERR_SINK line or an inner argv/sink observable produced by the real launcher

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-review.sh:25-26
- **Concern**: Primary-path stderr-sink runtime check can pass without run-external-agent forwarding. Scenario: Replacing the codex source grep with only outer `.meta` `STDERR_SINK=` or sink-file presence still passes if `_RUN_EXTERNAL_SINK_ARGS` regresses, because `cursor_launcher_append_outer_meta` writes the same sink from the launcher variable
- **Proposed resolution**: Record argv at the `run-external-agent.sh` boundary (minimal `$STUB_BIN/run-external-agent.sh` wrapper that logs `"$@"` then `exec`s the real script) and assert `--stderr-sink` plus the sink path appear before `--`; keep the existing outer `.meta` assertion as a second check

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/collect-agent-results.sh:600-622, scripts/collect-agent-results.sh:730-737
- **Concern**: The proposed collector runtime tests use stubs that the collector security checks intentionally reject. Scenario: An OUTER_LAUNCHER tmp stub fails the canonical launch-review.sh check, and a CMD_JSON run-external-agent stub fails the cursor/codex argv-shape validator. Implementing the plan literally either fails the tests or tempts a weakening of retry metadata validation.
- **Proposed resolution**: Keep OUTER_LAUNCHER as the real canonical scripts/launch-review.sh and keep real scripts/run-external-agent.sh. Use existing cursor/codex leaf stubs, then assert the retry .meta carries STDERR_SINK=<sink> or inspect leaf argv. Do not loosen collector validation.

### FINDING_10:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-review.sh:131, scripts/launch-review.sh:477, scripts/launch-review.sh:905
- **Concern**: The plan records --risk in outer metadata but does not make launch-review.sh honor low risk for effort selection. Scenario: After the PR, a retry can pass --risk low and write OUTER_LAUNCHER_RISK=low, but Codex still calls agent-model-args.sh --with-effort and Cursor still wraps every prompt with /max-mode on. The documented contract in docs/configuration-and-permissions.md:174 remains false.
- **Proposed resolution**: Capture and normalize RISK, then gate the existing effort/max-mode paths on RISK=high. Add low-risk assertions that Codex omits the effort arg and Cursor omits the max-mode wrapper, not just that .meta says low.

### FINDING_11:
- **Reviewer(s)**: Codex-Requirements, Codex-dyn-meta-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:595-617
- **Concern**: Plan tells the collector outer-retry test to set OUTER_LAUNCHER to an argv-recording stub, but the collector only accepts the canonical scripts/launch-review.sh path and rejects noncanonical or symlink launchers.. Scenario: The planned runtime test either fails as invalid retry metadata or pressures the implementation to weaken the existing canonical-launcher hardening, which is scope creep for this SIMPLE fix.
- **Proposed resolution**: Keep OUTER_LAUNCHER pointed at scripts/launch-review.sh, stub only the leaf CLI via PATH, and assert forwarding by inspecting the retry output meta for STDERR_SINK=$sink or another real run-external-agent artifact. For CMD_JSON, keep the real scripts/run-external-agent.sh path and assert its retry .meta records STDERR_SINK.

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-meta-contract
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-collect-agent-retry.sh:29-31 / scripts/collect-agent-results.sh:595-617
- **Concern**: Outer-launcher runtime case points OUTER_LAUNCHER at an argv-recording stub. Scenario: Collector rejects non-canonical OUTER_LAUNCHER (must be real repo launch-review.sh; no symlinks). A stub path fails case-s2-style validation or never exercises the real replay chain.
- **Proposed resolution**: Keep OUTER_LAUNCHER=$REPO_ROOT/scripts/launch-review.sh (mirror case Q). Assert forwarding via retry artifact: STDERR_SINK= on ${retry_output}.meta and/or --stderr-sink on run-external-agent (extend HELPER logging only for CMD_JSON path).

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-meta-contract
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-review.sh:131-131; scripts/launch-review.sh:477-477; scripts/launch-review.sh:672-672; scripts/launch-review.sh:905-905
- **Concern**: The plan captures --risk only for OUTER_LAUNCHER_RISK metadata, but launch-review still ignores the parsed risk when choosing Codex effort and Cursor max-mode.. Scenario: A collector retry with OUTER_LAUNCHER_RISK=low invokes launch-review.sh --risk low, yet Codex still calls agent-model-args.sh --with-effort and Cursor still wraps with /max-mode on, so the plan's caller's risk-gated effort claim remains false while the proposed meta-only test passes.
- **Proposed resolution**: Use the captured RISK in both launch-review lanes: omit Codex --with-effort and skip Cursor max-mode wrapping for risk=low, or narrow the plan/docs/tests to claim metadata preservation only rather than risk-gated effort preservation.

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-harness-realism
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-launch-review.sh:1372-1386, scripts/launch-review.sh:537-551, scripts/launch-review.sh:970-984
- **Concern**: The proposed primary-run assertion points at the leaf CLI argv logs, but --stderr-sink is consumed by run-external-agent.sh before codex or cursor is execed.. Scenario: The test either fails even when forwarding is correct, or falls back to the existing .meta grep and still passes from the outer metadata append instead of proving wrapper argv delivery.
- **Proposed resolution**: Assert an artifact only run-external-agent.sh can write, such as STDERR_SINK appearing in the pre-CMD_JSON metadata block for the same run, while keeping the outer metadata check separate.

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-harness-realism
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/test-collect-agent-retry.sh:625-641, scripts/collect-agent-results.sh:592-617, scripts/collect-agent-results.sh:1023-1050
- **Concern**: The outer-launcher retry test plan says to point OUTER_LAUNCHER at an argv-recording stub, but collector validation only accepts canonical scripts/launch-review.sh.. Scenario: The retry is rejected before launch, so the test never observes --stderr-sink delivery on the intended outer-launcher path.
- **Proposed resolution**: Keep OUTER_LAUNCHER as the real canonical launch-review.sh, stub only the leaf CLI through PATH, then assert the retry .meta shows run-external-owned STDERR_SINK before CMD_JSON.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-harness-realism
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/collect-agent-results.sh:475-496, scripts/collect-agent-results.sh:1083-1157, scripts/test-collect-agent-retry.sh:117-125
- **Concern**: The CMD_JSON retry test plan treats CMD_JSON as a way to invoke a run-external-agent stub, but CMD_JSON is the inner vendor command and must pass the cursor or codex shape allowlist.. Scenario: A CMD_JSON containing run-external-agent.sh is rejected as the wrong argv shape, or tests an unrelated path instead of collector forwarding into the real wrapper.
- **Proposed resolution**: Use a valid cursor or codex CMD_JSON fixture and assert the generated retry .meta contains the wrapper-owned STDERR_SINK entry.

### FINDING_17:
- **Reviewer(s)**: Cursor-dyn-doc-sync
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:23-25; scripts/test-launch-review.sh:184-201,301-311
- **Concern**: FINDING_1/2 cites `$ARGV` / codex stub line 301 as recording `run-external-agent.sh` argv, but `CODEX_STUB_ARGV_LOG` only logs the leaf `codex exec` argv. Scenario: Implementer adds `grep --stderr-sink` on `$ARGV` and gets a false failure, or drops the runtime assertion and keeps ineffective coverage
- **Proposed resolution**: Prefer asserting the sink file receives wrapper stderr after `--stderr-sink`, or add a dedicated `run-external-agent` argv log stub; for cursor, follow case AK1 `CURSOR_STUB_ARGV_LOG` only if testing leaf argv—otherwise mirror the sink-file or wrapper-stub approach (`scripts/test-run-external-agent.sh` ~465-497)

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-doc-sync
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-review.sh:131-132,477-478,672-673,905-906; docs/configuration-and-permissions.md:174
- **Concern**: The plan captures --risk only for OUTER_LAUNCHER_RISK but leaves initial launch effort unconditional. Scenario: After the proposed change, launch-review.sh --risk low records OUTER_LAUNCHER_RISK=low for retry, while the first Codex run still calls agent-model-args.sh --with-effort and the first Cursor run still wraps with /max-mode on; this conflicts with the documented --risk low contract and can make initial and retry attempts use different effort settings
- **Proposed resolution**: Gate the initial Codex --with-effort call and Cursor max-mode wrapping on the parsed normalized RISK, then document that launch-review --risk controls both initial launch effort and retry replay; or explicitly narrow all docs if retry-only behavior is intended

### OOS_1:
- **Description**: Retry section documents `STDERR_SINK` / `--stderr-sink` replay but not `OUTER_LAUNCHER_RISK` / `--risk`, while `collect-agent-results.sh` already replays `--risk` (e.g. 638-655). Scenario: After launch-review starts writing caller risk into meta, operators reading only the collector doc see half the outer-retry argv contract
- **Reviewer**: Cursor-dyn-doc-sync
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/collect-agent-results.md:38; plan.txt:34-35
- **Phase**: design
