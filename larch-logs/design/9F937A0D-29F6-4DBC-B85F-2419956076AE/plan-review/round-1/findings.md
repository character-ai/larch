### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh:1
- **Concern**: Global set -euo pipefail on the helper conflicts with the inline fence errexit model. Scenario: Inline block (skills/implement/SKILL.md:1193-1282) only uses set +e around the gate; fallible reads (missing session-id, grep/find pipelines, missing accepted files) tolerate failure. A standalone helper with errexit+pipefail can abort early with exit 1/127 instead of the intended 0/1/2 contract
- **Proposed resolution**: Mirror the fence: keep input resolution under set +e (or explicit || true/-f guards on every fallible step), then set +e only around the gate call; drop global pipefail unless every pipeline is audited like the inline block

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:1258-1261; skills/implement/scripts/oos-disposition-checkpoint.sh:1
- **Concern**: New checkpoint script is invoked directly, but the plan does not require executable mode. Scenario: If the new file lands as 0644, Step 8+ gets permission denied before the helper runs, so the OOS gate does not execute or log as intended
- **Proposed resolution**: Commit oos-disposition-checkpoint.sh as executable 100755 or invoke it through bash; keep the harness aligned with the runtime invocation

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh (planned)
- **Concern**: Decision 2 logging does not specify a guaranteed on-disk diag file for pre-gate failures. Scenario: append-tool-failure.sh requires an existing --output-file (scripts/append-tool-failure.sh:100-104); pre-gate paths only printf to stderr today and may not run the gate, so reusing oos-disposition-gate.stderr.log can be missing or stale
- **Proposed resolution**: Pre-gate exit 2 logs nothing or logs a prior gate failure; harness assertions on execution-issues.md become flaky Tee pre-gate/CLI errors to a dedicated <implement-tmpdir>/oos-disposition-checkpoint.stderr.log (touch if needed, per step-7a.sh:43) and pass that path to append-tool-failure; only use the gate stderr log after gate invocation

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:73-77 planned replacement; skills/implement/scripts/oos-disposition-checkpoint.sh
- **Concern**: New checkpoint is invoked as an executable, but the plan does not require the new file to be executable or require tests to exercise direct execution. Scenario: If the new script lands with default 0644 mode, Step 8+ gets permission denied/exit 126 before the helper can log via append-tool-failure, so the promised 0/1/2 branch contract is bypassed
- **Proposed resolution**: Specify the mode/call contract: either add the executable bit and have the harness invoke CHECKPOINT directly, or invoke it with bash consistently from SKILL.md and tests

### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh planned from plan.txt:34-40
- **Concern**: Bare git/find probes under set -euo pipefail can bypass the helper 0/1/2 and logging contract. Scenario: Outside a git tree or with a missing larch-logs/implement directory, git rev-parse or find can terminate the helper before the gate runs and before append-tool-failure logs the validation failure
- **Proposed resolution**: Preserve the current tolerant wrappers from skills/implement/SKILL.md:1201-1218: use 2>/dev/null || true for git rev-parse, merge-base, session-id reads, and find pipeline probes, then convert intended validation failures to logged exit 2

### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/append-tool-failure.sh:100-104; skills/implement/scripts/oos-disposition-checkpoint.sh (NEW, plan §NEW)
- **Concern**: Pre-gate exit-2 logging has no required --output-file artifact. Scenario: Decision 2 logs all non-zero exits via append-tool-failure, but pre-gate paths (ambiguous ndjson, missing ndjson precondition, CLI usage) only printf to stderr today; append-tool-failure exits 2 when --output-file is missing, so set -e can abort before returning the intended checkpoint rc 2 and tests expecting execution-issues.md entries fail
- **Proposed resolution**: Mirror gate failures: tee pre-gate/usage diagnostics into <implement-tmpdir>/oos-disposition-gate.stderr.log (or a checkpoint diag file) before append; document the path in oos-disposition-checkpoint.md

### FINDING_7:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh:new
- **Concern**: Planned set -euo pipefail helper leaves optional grep/git/find/tr probes described without guards. Scenario: Optional missing state keys, missing session-id, absent larch-logs directory, or merge-base failure exits the helper early with rc 1 before fallback/default/logging, so Step 8+ misclassifies or loses the validation audit trail
- **Proposed resolution**: Add explicit || true guards around every optional probe/pipeline, especially the grep state reads, session-id read, merge-base, and find fallback, while keeping validation failures on the deliberate logged exit-2 paths

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:planned Step 8+ helper call
- **Concern**: New helper is invoked by direct path but the plan does not pin executable mode. Scenario: If the new script lands 0644, the checkpoint returns shell rc 126 instead of the planned 0/1/2 contract and Step 8+ cannot run the gate
- **Proposed resolution**: Specify git mode 100755 and add a minimal [ -x "$CHECKPOINT" ] assertion/direct-path invocation in the existing harness, or invoke it via bash in SKILL.md and tests

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/test-oos-disposition-gate.sh (planned checkpoint cases)
- **Concern**: The test plan does not validate logging for checkpoint exit 1 even though the new helper owns append-tool-failure for all non-zero exits.. Scenario: A helper implementation could return 1 for a real OOS disposition gap but omit the step-8-oos-checkpoint Tool Failures entry, regressing the audit trail while still passing the planned rc-only disposition-gap test.
- **Proposed resolution**: Add a minimal assertion to the existing disposition-gap checkpoint case that fake execution-issues.md contains a Tool Failures entry with site step-8-oos-checkpoint and tool oos-disposition-checkpoint.sh; keep the existing exit-2 log assertions.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-extraction-parity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1197-1249
- **Concern**: Proposed helper adds set -euo pipefail but the plan does not explicitly preserve the current best-effort probe guards for state, git, session-id, and ndjson discovery. Scenario: Current inline fallback tolerates missing git context or missing log/session artifacts and reaches the documented HEAD/no-ndjson precondition path; an unguarded extracted probe can exit early before the gate stderr capture and before the intended rc 2 validation log
- **Proposed resolution**: Require the helper to keep the current guarded semantics: initialize defaults, use 2>/dev/null || true on git/session/find probes, tolerate absent state keys as false, then apply the existing ndjson precondition and gate call

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-extraction-parity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1268-1281; scripts/append-tool-failure.sh:100-129
- **Concern**: Exit-code mapping can drift if append-tool-failure.sh failure is not kept best-effort in the helper. Scenario: Current inline logging ends with || true before exiting; append-tool-failure.sh itself can exit 2 for output/redaction/log write failures, which would override a captured gate rc 1 or rc 2 under set -e and break the proposed 0/1/2 helper contract
- **Proposed resolution**: After capturing the original failure rc, call append-tool-failure.sh with || true and always exit the captured rc; keep the proposed site tokens unchanged

### FINDING_12:
- **Reviewer(s)**: Cursor-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh (planned); plan.txt:48-60,138-139; scripts/append-tool-failure.sh:100-104
- **Concern**: Pre-gate exit-2 logging has no stable capture file; append-tool-failure requires an existing --output-file. Scenario: Pre-gate paths (ambiguous ndjson, missing ndjson precondition, CLI usage) never run the gate, so oos-disposition-gate.stderr.log is not produced; append-tool-failure exits 2 when the output file is missing, so Decision 2 logging can fail and harness assertions for execution-issues.md may miss the real failure
- **Proposed resolution**: Specify a single implement-tmpdir diag path (e.g. oos-disposition-checkpoint.stderr.log): tee pre-gate stderr there before append-tool-failure; document it in oos-disposition-checkpoint.md

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1201-1211; <TMPDIR>/plan.txt:34-36
- **Concern**: Planned commit-range port omits the current nonfatal git fallbacks under set -euo pipefail. Scenario: The helper can abort before reaching the gate when outside a git work tree or when origin/main resolves but git merge-base has no common ancestor, instead of preserving the current HEAD or origin/main..HEAD fallback and logging a checkpoint validation failure
- **Proposed resolution**: Specify the current 2>/dev/null || true guards for git rev-parse and git merge-base in the helper, and add one checkpoint harness case for origin/main present with no merge-base

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1273-1281; scripts/append-tool-failure.sh:100-130; <TMPDIR>/plan.txt:55-60
- **Concern**: Planned helper logging does not state that append-tool-failure remains best-effort and must preserve the original checkpoint rc. Scenario: If append-tool-failure fails because the output file is missing or redaction fails, set -e can replace gate rc 1 or rc 2 with the logging helper's failure, breaking the planned 0/1/2 contract
- **Proposed resolution**: Add the current || true pattern inside the helper after saving the original rc, then always exit the saved rc

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:68-70; <TMPDIR>/plan.txt:83-90
- **Concern**: The plan says to keep NEVER #17/#18 prose even though #18 still names direct oos-disposition-gate.sh invocation as the required Step 8+ action. Scenario: After extraction, the load-bearing invariant can conflict with the new checkpoint entrypoint and prompt maintainers may bypass the helper-owned input plumbing and logging
- **Proposed resolution**: Minimally update NEVER #17/#18 to say the Step 8+ checkpoint helper invokes the gate and owns gate failure logging, while preserving the OOS_PENDING and run-statistics invariants
