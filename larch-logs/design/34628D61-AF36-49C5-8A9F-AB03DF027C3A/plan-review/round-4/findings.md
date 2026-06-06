### FINDING_1:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: agent-lint.toml
- **Concern**: Plan omits agent-lint dead-script exclusions for new Makefile/pre-commit-only surfaces. Scenario: `make lint` / `pre-commit run agent-lint` can flag `scripts/lint-codex-exec-auth.sh`, its harness/docs, and `scripts/test-launch-codex-exec.sh` / `scripts/test-lint-codex-exec-auth.sh` as unreachable; `launch-codex-exec.sh` may also be unreachable when fences use `${CLAUDE_PLUGIN_ROOT}` indirection (same pattern as `launch-codex-implement.sh`)
- **Proposed resolution**: Add an `agent-lint.toml` subsection mirroring `lint-bare-grep-probe.sh` / `launch-codex-implement.sh`: exclude the lint script + harness + sibling `.md` files, both new test harnesses, and `launch-codex-exec.sh` (+ `launch-codex-exec.md`) with a reachability comment citing markdown-fence and `lint-fix-loop.sh` indirection

### FINDING_2:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-lint-fix-loop.sh:14-15
- **Concern**: Plan under-specifies lint-fix-loop harness migration after Codex routing moves behind launch-codex-exec.sh. Scenario: The UPDATED test-lint-fix-loop.sh bullet covers routing/LAUNCHER_EXIT only; the harness still structurally requires run_codex to pass --stderr-sink to run-external-agent (lines 14-15) and case0a-0b still assert codex.events.jsonl / codex.wrapper.log with LINT_FIX_LOOP_RUN_EXTERNAL_AGENT_SH stubs (lines 543-653)—all incompatible once run_codex calls the launcher instead
- **Proposed resolution**: Expand the plan test section to explicitly drop/replace the stderr-sink structural pin, introduce a launch-codex-exec stub hook (mirror LINT_FIX_LOOP_RUN_EXTERNAL_AGENT_SH or document real-launcher+stub-codex), and retarget case0a-0b artifact checks to ${run_dir}/codex.log.events.jsonl and ${run_dir}/codex.log.sidecar

### FINDING_3:
- **Reviewer(s)**: Cursor-dyn-sidecar-contract
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/launch-review.sh:262-282
- **Concern**: Plan promotes inner sentinel only via an explicit post-loop codex_launcher_promote_inner_done call and does not install an EXIT trap like launch-review _codex_exit_dispatcher. Scenario: If post-processing after the final run-external-agent attempt aborts (set -e, signal, OOM) before the explicit promote runs, only ${OUTPUT}.inner.done exists and collect-agent-results.sh / wait-for-reviewers.sh poll ${OUTPUT}.done until timeout
- **Proposed resolution**: Mirror launch-review.sh:262-282: install an EXIT trap that always calls codex_launcher_promote_inner_done before exit, with the explicit post-loop promote kept as the normal-path fast path

### FINDING_4:
- **Reviewer(s)**: Cursor-dyn-lint-scope
- **Severity**: latent
- **Focus area**: correctness
- **Location**: scripts/lint-codex-exec-auth.sh (proposed)
- **Concern**: Shell rule matches only when codex exec is the line command word after leading VAR=value stripping; same-line argv embedding after run-external-agent.sh -- is invisible. Scenario: Post-PR a contributor can copy the established one-line launcher shape (e.g. CODEX_HOME=… run-external-agent.sh … -- codex exec … as in launch-codex-implement runtime logs) into a non-allowlisted scripts/*.sh file and make lint-codex-exec-auth pass while leaving OPENAI_API_KEY unwired
- **Proposed resolution**: Also flag lines where a stripped prefix is followed by a command and the line contains a -- codex exec token (or extend the harness with a same-line fixture); keep negotiation on its own codex exec command-word line with pragma

### FINDING_5:
- **Reviewer(s)**: Cursor-dyn-doc-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:173
- **Concern**: Failure mode 3 mitigation says update external-reviewers.md (unqualified). Scenario: FM3 can steer implementers to docs/external-reviewers.md for negotiation exit-code prose while FM6 and the UPDATED docs/external-reviewers.md step forbid that and pin orchestrator exit grammar to skills/shared/external-reviewers.md:114
- **Proposed resolution**: Change FM3 mitigation to name skills/shared/external-reviewers.md:114 (orchestrator exit grammar) plus run-negotiation-round.md; keep docs/external-reviewers.md auth-scope-only per lines 133-137 and 176

### FINDING_6:
- **Reviewer(s)**: Cursor-dyn-doc-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:131-133
- **Concern**: Consumer auth-scope rewrite lists only newly swept surfaces. Scenario: The UPDATED docs/external-reviewers.md step enumerates /research lanes validation voter/judge lint-fix-loop run-negotiation-round launch-codex-exec but not the five pre-existing covered dispatchers (launch-review launch-codex-ci launch-codex-implement check-reviewers review-and-fix) or health probe
- **Proposed resolution**: A single canonical post-PR covered-path bullet in Approach and require each consumer doc rewrite (docs/external-reviewers.md docs/configuration-and-permissions.md SECURITY.md) to name the full merged set: prior five plus health probe plus the six swept surfaces

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-doc-parity
- **Severity**: latent
- **Focus area**: architecture
- **Location**: plan.txt:139-145
- **Concern**: OPENAI_API_KEY doc steps lack pinned enumeration. Scenario: docs/configuration-and-permissions.md and SECURITY.md updates say only expanded covered-path/surface list without the six-surface inventory used at docs/external-reviewers.md:131-133
- **Proposed resolution**: Reuse the same canonical bullet from Finding 2 in both ### UPDATED steps so env-key docs cannot drift from docs/external-reviewers.md
