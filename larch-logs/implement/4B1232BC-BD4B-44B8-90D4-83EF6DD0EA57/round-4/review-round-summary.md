# Review Round 4

- Mode: `diff`
- 14 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Claude review context paths lack bash-compatible missing-file handling
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `launch_claude_review` forwards non-empty context paths without existence checks. Missing implicit paths can make Python subprocess validation exit 2 and drop the Claude slot, while bash skipped missing implicit context and only failed strict explicit context files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: CI launcher failures no longer append durable vendor diagnostics
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Python CI launchers can leave only local failure sidecars after Codex, Cursor, or Claude failures. Durable run-log artifacts such as vendor failure diagnostics and execution issues may miss the failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Shared CI prompt dropped role-specific recovery guidance
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The shared CI prompt no longer includes conflict continuation, local reproduction, and larch failure-pattern guidance. Resolve-conflict launches may omit required instructions such as adding resolved files and continuing the rebase.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_19: Codex exec preflight failure bundles lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No pytest covers Codex exec auth or model-args preflight failure bundles. Regressions that make preflights exit nonzero or skip sidecars can break collectors and review retries while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Claude JSON promotion failures use incompatible sentinel and exit code
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Claude subprocess JSON promotion failures now emit `CLAUDE_SUBPROCESS_*` sentinels and exit 1 instead of the bash `CLAUDE_JSON_RESULT_INVALID` sentinel and exit 99. Callers or tests keyed on the old contract can misclassify invalid-envelope failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: Trusted-instructions merge behavior lacks pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No pytest covers `--trusted-instructions-file` and `_prepare_codex_home` merge behavior. Config merge or instruction stripping regressions can break trusted-instructions flows without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_21: CI monitor tier availability and launcher argv drift lack coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_available_tiers` removed `launch-claude-ci.sh` existence gating, but `test_ci_monitor.py` was not updated. Waterfall tier availability and agent launcher argv construction can drift without pytest coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_22: Unsafe stderr sink validation is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Unsafe `--stderr-sink` validation before side effects lacks coverage. A validation bug could write `.meta` or `.done` for bad sinks and break collector retry metadata contracts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: Health-gate fast-fails can reuse stale stdout or stderr sidecars
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `run_external_agent` does not clean or truncate caller-supplied stdout and stderr paths before the health gate. A stale sidecar from an earlier auth or quota attempt can survive a later fast-fail and drive the wrong retry classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Codex usage JSONL malformed and empty-usage paths lack fail-closed behavior and coverage
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `parse_codex_usage_file` can skip malformed JSONL lines and emit partial usage instead of failing closed. Malformed-only or token-free usage streams also lack focused pytest coverage, so usage and cost recording regressions may pass CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Codex usage parsing treats explicit zeroes as missing
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Codex usage parsing uses truthiness coalescing instead of null-only coalescing. Explicit zero token values can be overridden by fallback fields, changing reported usage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_7: Darwin serial-lock release can be skipped on fast process exit
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The Darwin serial-lock release uses a daemon `Timer`. Fast launcher failures can exit before the timer runs, leaving the lock until TTL and delaying later launches.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_8: CI launchers lost missing-binary preflight classification
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: CI launchers no longer preserve missing-binary preflight and classification semantics. Missing `codex` in ship-pr CI fix mode can be classified as `other` and skip Cursor fallback.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_9: Claude CI no longer records timing or token sidecars
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_claude_ci_main` dropped Claude CI usage extraction, token-record sidecar writes, ledger append behavior, and vendor timing records. Successful Claude CI runs can complete without required accounting artifacts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


