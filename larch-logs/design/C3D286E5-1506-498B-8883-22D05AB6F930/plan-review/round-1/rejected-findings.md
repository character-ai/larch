### [Plan Review] FINDING_1

### FINDING_1: launch-review preserves low risk in metadata but still runs high-effort paths
- **Reviewer(s)**: Codex-Arch, Codex-Innovation, Codex-Pragmatic, Codex-dyn-meta-contract, Codex-dyn-doc-sync
- **Severity**: important
- **Concern**: `--risk low` is recorded as retry/outer metadata, but the live Codex and Cursor launch paths still unconditionally use high-effort behavior via Codex `--with-effort` and Cursor `/max-mode`, so metadata can claim low risk while execution remains high risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Capture RISK in both lanes and use it at the existing effort gates: omit Codex --with-effort when RISK=low, and skip cursor-wrap-prompt.sh max-mode wrapping when RISK=low. Add the planned meta tests plus a live argv or prompt assertion for low risk.
  - From Codex-Innovation: Add parsed RISK gating around the model-args call and test that --risk low omits Codex effort args, not only that the .meta value is low
  - From Codex-Pragmatic: Capture and normalize RISK, then gate the existing effort/max-mode paths on RISK=high. Add low-risk assertions that Codex omits the effort arg and Cursor omits the max-mode wrapper, not just that .meta says low.
  - From Codex-dyn-meta-contract: Use the captured RISK in both launch-review lanes: omit Codex --with-effort and skip Cursor max-mode wrapping for risk=low, or narrow the plan/docs/tests to claim metadata preservation only rather than risk-gated effort preservation.
  - From Codex-dyn-doc-sync: Gate the initial Codex --with-effort call and Cursor max-mode wrapping on the parsed normalized RISK, then document that launch-review --risk controls both initial launch effort and retry replay; or explicitly narrow all docs if retry-only behavior is intended


### [Plan Review] FINDING_5

### FINDING_5: unrelated cursor launcher call-site edits expand a SIMPLE fix without proving behavior
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Concern**: The cursor implement/CI empty-argument changes touch extra files as behavior-neutral future-proofing, do not fix the discarded `launch-review --risk` behavior, and passing an empty fifth arg still allows inherited `RISK` fallback behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Drop the launch-cursor-implement.sh and launch-cursor-ci.sh call-site edits from this PR unless a current failing contract requires them### OOS_1:
- **Description**: Retry section documents `STDERR_SINK` / `--stderr-sink` replay but not `OUTER_LAUNCHER_RISK` / `--risk`, while `collect-agent-results.sh` already replays `--risk` (e.g. 638-655). Scenario: After launch-review starts writing caller risk into meta, operators reading only the collector doc see half the outer-retry argv contract
- **Reviewer**: Cursor-dyn-doc-sync
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/collect-agent-results.md:38; plan.txt:34-35
- **Phase**: design


