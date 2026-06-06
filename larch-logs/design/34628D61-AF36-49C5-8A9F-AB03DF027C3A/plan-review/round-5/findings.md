### FINDING_1:
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-collector-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/validation-phase.md:77-79
- **Concern**: Validation-lane fence omits required --output and --timeout. Scenario: launch-codex-exec.sh requires absolute --output (plan NEW section) and lists --timeout SECONDS with no default; Step 2.4 still collects "$RESEARCH_TMPDIR/codex-validation-output.txt" (line 180). Missing flags abort launch or write sidecars to the wrong path, so collect-agent-results.sh never sees the expected sentinel/output
- **Proposed resolution**: Add --output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800 to the validation-lane launch-codex-exec.sh example, matching research-phase.md and the unchanged COLLECT_ARGS path

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-codex-exec-auth.sh (new), Makefile:28, .pre-commit-config.yaml:1
- **Concern**: 1. New repo-wide codex-exec linter/pre-commit harness exceeds the SIMPLE minimum-change auth sweep. Scenario: Fixing six call sites now adds a new allowlist/pragma policy plus Makefile, pre-commit, agent-lint, docs, and harness maintenance surface; false positives can block unrelated work
- **Proposed resolution**: Drop the new linter and its wiring from this PR; keep the launcher/routing changes and targeted regression tests for the six swept call sites

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/run-negotiation-round.sh:68-93
- **Concern**: 2. Planned Codex auth temp home in negotiation has no cleanup contract. Scenario: The proposed branch creates a temp CODEX_HOME with copied config/auth material but does not state an EXIT cleanup, so failures or normal completion can leave auth side effects under /tmp
- **Proposed resolution**: Add branch-local cleanup for codex_home on all codex paths and assert removal in test-run-negotiation-round.sh

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/run-negotiation-round.sh:66-96
- **Concern**: Planned inline Codex auth path does not specify cleanup for temporary CODEX_HOME. Scenario: Each negotiation round can leave a temp Codex home behind with copied config.toml or an auth.json symlink, leaking auth-related filesystem state and accumulating stale dirs
- **Proposed resolution**: Add branch-local cleanup/trap immediately after mktemp -d and remove the temp CODEX_HOME on success, auth-prep failure, model-args failure, and codex exec failure, mirroring check-reviewers.sh cleanup behavior

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/run-negotiation-round.sh:70-99
- **Concern**: Codex negotiation temp CODEX_HOME has no planned cleanup. Scenario: The proposed inline auth path copies ~/.codex/config.toml into a temp home and may add auth material, but the plan does not remove that directory on success, auth-prep failure, or codex exec failure. A failed strip/setup path can leave copied credential-bearing config material under /tmp.
- **Proposed resolution**: Add a branch-local cleanup trap or cleanup function immediately after mktemp -d, and clear it only after rm -rf succeeds on every codex branch exit path.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: scripts/lint-codex-exec-auth.sh:1
- **Concern**: New repo-wide codex-exec linter is forward-looking scope creep for this auth sweep. Scenario: The PR goal is to wire six known call sites. Adding a new Markdown/shell scanner plus Makefile, pre-commit, docs, and harness wiring turns a targeted auth fix into a new enforcement subsystem that can block unrelated work on parser false positives or allowlist drift.
- **Proposed resolution**: Defer lint-codex-exec-auth and its pre-commit/Makefile/docs/harness wiring to a follow-up; keep this PR to the launcher/auth wiring and targeted tests for the changed call sites.

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/run-negotiation-round.sh:68-99
- **Concern**: Proposed Codex auth temp home lacks a cleanup contract. Scenario: The plan adds a temp CODEX_HOME in the negotiation Codex branch, and external_prepare_codex_auth may leave a copied config plus auth.json symlink there; without an EXIT cleanup this auth material can remain after success or failure
- **Proposed resolution**: Add a branch-local cleanup trap or explicit cleanup that removes the temp CODEX_HOME on every codex-branch exit path

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/validation-phase.md:77-79
- **Concern**: Validation-lane fence omits required launcher flags. Scenario: The UPDATED validation-phase snippet drops `--output "$RESEARCH_TMPDIR/codex-validation-output.txt"` and `--timeout 1800` while `launch-codex-exec.sh` requires an absolute `--output` and Step 1.4 still collects `$RESEARCH_TMPDIR/codex-validation-output.txt`
- **Proposed resolution**: Launcher arg validation fails or writes sidecars to the wrong stem; validation collection never sees the expected sentinel path Add `--output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800` to the validation-lane `launch-codex-exec.sh` invocation (matching research-phase and the unchanged COLLECT_ARGS path)

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: plan.txt:77-79
- **Concern**: Validation-phase launcher swap omits required launcher flags. Scenario: The proposed launch-codex-exec.sh requires --output and --timeout, so the validation lane command as planned would fail argv validation before launching Codex
- **Proposed resolution**: Add --output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800 to the validation-phase replacement command

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-auth-surface-sweep
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/run-external-agent.sh:190-204; scripts/collect-agent-results.sh:1093-1158; scripts/lib-external-launcher-common.sh:691-708
- **Concern**: The planned collect-managed launch-codex-exec retry path relies on CMD_JSON replay, which records only argv and not CODEX_HOME or auth prep state. Scenario: In login fallback, the first launch uses a stripped temp CODEX_HOME plus auth.json symlink, but an empty-output collector retry re-runs only codex exec argv and can drop the login-prep behavior or read ambient stale config; env-key retry survives only because provider args are in argv
- **Proposed resolution**: Add retry through launch-codex-exec outer metadata and collector allowlisting, or otherwise disable/qualify collector retry for this launcher until login fallback is replayed through external_prepare_codex_auth

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-auth-surface-sweep
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/check-reviewers.sh:208-223,255-263; scripts/run-negotiation-round.sh:68-99
- **Concern**: The run-negotiation-round.sh plan creates a temp CODEX_HOME but does not specify cleanup on all codex branch exits. Scenario: Login fallback may leave temp dirs containing copied config and an auth.json symlink after success or failure
- **Proposed resolution**: Add a codex branch cleanup trap/helper for codex_home and copied config, mirroring check-reviewers.sh cleanup paths before returning or exiting

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-collector-contracts
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/research/references/research-phase.md:73-75 (plan); skills/research/references/validation-phase.md:77-79 (plan); skills/shared/voting-protocol.md:81-83 (plan); skills/shared/dialectic-protocol.md:85-87 (plan)
- **Concern**: Proposed skill fences call bare scripts/launch-codex-exec.sh instead of ${CLAUDE_PLUGIN_ROOT}/scripts/launch-codex-exec.sh. Scenario: Consumer-repo /research and /design orchestration runs with cwd at the target repo; a relative scripts/ path misses the plugin tree and breaks background launch plus downstream .done collection
- **Proposed resolution**: Use the same ${CLAUDE_PLUGIN_ROOT}/scripts/launch-codex-exec.sh prefix as today's run-external-agent.sh fences in all four reference updates

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-collector-contracts
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/lint-fix-loop.sh:38,398-424; scripts/test-implement-structure.sh:291-296
- **Concern**: The plan says test-implement-structure should require run-external-agent.sh only inside launch-codex-exec.sh, but the proposed lint-fix-loop change rewrites only run_codex; run_cursor still legitimately uses RUN_EXTERNAL_AGENT_SH.. Scenario: The updated structural test would either fail on the existing Cursor dispatch path or force an unplanned Cursor refactor, which is scope creep for a Codex-auth sweep.
- **Proposed resolution**: Narrow the structural pin to the Codex branch/run_codex routing: require launch-codex-exec.sh for Codex, while still allowing lint-fix-loop.sh to reference run-external-agent.sh for run_cursor.

### FINDING_14:
- **Reviewer(s)**: Cursor-dyn-doc-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/validation-phase.md:136-180
- **Concern**: Validation-phase launcher swap omits required --output and --timeout. Scenario: The planned fence only shows --workdir --add-dir --prompt-file --usage-label. launch-codex-exec.sh requires --output, and Step 1.4 still collects $RESEARCH_TMPDIR/codex-validation-output.txt. Missing --output breaks collector paths; missing --timeout drops the 1800s contract.
- **Proposed resolution**: Add --output "$RESEARCH_TMPDIR/codex-validation-output.txt" --timeout 1800 to the validation-phase launch-codex-exec.sh example (mirror research-phase.md).

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-doc-contract-drift
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/research/references/research-phase.md:133-135
- **Concern**: F1: Plan leaves stale research token-telemetry prose while adding Codex usage recording. Scenario: The proposed launcher records usage for Codex research lanes, but the same scoped file still says external non-fallback Codex lanes are unmeasurable; users and token reports disagree after implementation.
- **Proposed resolution**: In the planned update to research-phase.md, revise line 135 to say Claude fallbacks write token-tally sidecars and Codex lanes get best-effort launcher usage records, or drop the unmeasurable sentence if no per-lane tally is promised.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-doc-contract-drift
- **Severity**: important
- **Focus area**: architecture
- **Location**: scripts/lib-external-launcher-common.md:11-13
- **Concern**: F2: Plan updates auth helper users but omits the helper sibling contract inventory. Scenario: Post-PR external_codex_auth_config_args will be used by launch-codex-exec.sh and run-negotiation-round.sh, and external_launcher_record_usage_from_events will be used by the new launcher paths, but the contract would still list only launch-review/implement/CI/check-reviewers/review-and-fix and review/implement/CI usage.
- **Proposed resolution**: Add scripts/lib-external-launcher-common.md to the UPDATED list and refresh the wired-call-site and usage-scraper bullets with the same merged inventory, or point them to the canonical docs if avoiding duplicate lists.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-doc-contract-drift
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: docs/installation-and-setup.md:157-163
- **Concern**: F3: Canonical auth inventory is updated in three consumer docs but not the install prerequisite doc. Scenario: After implementation, external-reviewers/configuration/SECURITY will say research, voting/judge, lint-fix, and negotiation are covered, while installation still says only covered launch/probe/review-fix surfaces use OPENAI_API_KEY.
- **Proposed resolution**: Add docs/installation-and-setup.md to the doc update set, preferably with a short wording that matches or links to the canonical inventory rather than duplicating another long list.
