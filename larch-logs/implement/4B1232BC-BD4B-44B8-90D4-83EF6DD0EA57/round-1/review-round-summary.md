# Review Round 1

- Mode: `diff`
- 13 accepted, 4 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Codex exec publishes public `.done` before launcher post-processing finishes
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_codex_exec_main` does not use the inner sentinel. Collectors can observe public `.done` before usage, timing, and `OUTER_LAUNCHER_*` metadata are appended.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Conflict file validation accepts unsafe paths
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Conflict-file validation allows `..` and absolute paths. Unsafe paths can be injected into resolve-conflict CI prompts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Claude read grants are not constrained to the session root
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Claude read-tools allow roots are no longer constrained to the canonical session root. A caller can grant Claude read access to broad local directories.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Cursor auth normalization preserves blank API keys
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cursor auth normalization can leave whitespace-only `CURSOR_API_KEY` values in the environment. Cursor can inherit the invalid key and fail instead of falling back to keychain or login auth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_15: Codex exec auth lint fixtures miss unscanned Python paths
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The allowlist test writes to an unscanned path, and negative fixtures for raw Codex exec in new Python modules are missing. New raw Codex exec calls outside `agents.py` may escape lint coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Claude review `--agent-file` drops rendered context
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_claude_review_main` copies the raw agent file instead of rendering the specialist prompt with diff, context flags, implicit context files, and allow roots. Claude fallback reviewers can run without the task context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_21: Retained lint-fix-loop harness still expects deleted `_SH` launcher seam
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-lint-fix-loop.sh` still asserts the deleted `_SH` launcher seam. `make test-lint-fix-loop` can fail immediately and block `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Claude subprocess output path validation is unsafe
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_claude_subprocess_main` writes to `--output-file` without canonical session-root containment and symlink rejection. A bad output path can overwrite files outside the intended session tmpdir.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_4: Claude subprocess exposes full prompt through argv and metadata
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Claude subprocess passes rendered prompt and context through argv and records them in `CMD_JSON`. This can exceed `ARG_MAX` and leak prompt contents through process listings or sidecar metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_5: Auth-classified retry loops are missing from Python launchers
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Python launcher paths dropped bounded auth retry behavior. Transient Codex auth startup failures or Cursor keychain races can now fail immediately instead of honoring `LARCH_EXTERNAL_AUTH_RETRIES`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_6: Cursor CI lost stall monitoring and launcher parity diagnostics
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_cursor_ci_main` omits retired launcher behavior for stall monitoring, child-first termination, stall JSON sidecars, timing or token sidecars, and inner done promotion. Stalled runs can wait for the full timeout and lose expected diagnostics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_8: Codex CI does not isolate and prepare `CODEX_HOME`
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `launch_codex_ci_main` runs with ambient Codex configuration and misses auth preparation, config stripping, quota mirroring, and related retry behavior. User config or stale env can break auth fallback or inject unintended local configuration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_9: CI prompt embeds failure logs without containment or redaction
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_ci_prompt` embeds raw failure-log content without validating it under `IMPLEMENT_TMPDIR` or redacting secrets. CI log secrets can reach external agent prompts and vendor logs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


