# Review Round 5

- Mode: `diff`
- 14 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: CI monitor can treat failed launcher tiers as winners
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `_make_default_launch_fn` parses `LAUNCHER_EXIT` only from captured stdout and stderr, but launcher contract KVs are emitted on fd 3. A failed child can leave `.done=1` while the wrapper returns 0, causing `run_waterfall` to accept a broken tier.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


### FINDING_10: Implement lint-fix Codex runs bypass Codex launcher auth prep
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_build_codex_argv` still launches raw `codex exec` through `run-external-agent` instead of the `agent launch-codex-exec` path. This can skip temporary `CODEX_HOME` auth prep and config stripping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Cursor CI model-arg failures lack launcher recovery contract
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Invalid `LARCH_CURSOR_MODEL` values can raise during model-arg handling and leave no standard sidecars or `LAUNCHER_EXIT` for recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_12: Context file paths are rendered before secret redaction
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Secret-shaped tokens in directory or file names can leak through the rendered path attribute sent to Claude because canonical paths are not redacted before XML escaping.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_14: Deleted run-external-agent harness coverage is not fully ported
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Several `test-run-external-agent.sh` contracts lack pytest equivalents, including unsafe output paths, sentinels, stdin redirect, stale cleanup, timeout stderr separation, stderr-tail selection, and failure-carrier ordering.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_15: Cursor prompt wrapping and Claude model reader lack pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: There are no tests for `agent cursor-wrap-prompt` or `agent read-claude-model`, leaving exact output bytes and fallback KV behavior unguarded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_16: Claude subprocess read-tools validation lacks pytest coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch-claude-subprocess --read-tools` and `--read-tools-add-dir` validation is not covered by pytest. Session-root escapes or missing add-dir handling could regress unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_17: Cursor CI stall-monitor pytest omits deleted harness assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Cursor CI stall-monitor pytest is thinner than the deleted Bash harness. It may miss argv validation, stall JSON schema regressions, or child-first kill behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_23: Implement structure test still pins retired degraded-tools-gate script text
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `scripts/test-implement-structure.sh` still requires the retired `degraded-tools-gate.sh` string even though step 0 now uses `python/cli.py agent degraded-tools-gate`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Docs still present deleted launcher scripts as live commands
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Operator docs still reference removed launcher scripts such as `run-external-agent.sh`, `launch-codex-ci.sh`, `launch-cursor-ci.sh`, and `launch-claude-ci.sh` as live surfaces. Users following those docs will run missing paths instead of the Python CLI verbs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_6: Live docs quote Python CLI agent commands as invalid executables
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Live markdown examples quote `python/cli.py agent ...` as one executable path or call `python/cli.py` as though it were executable. Copying these examples can try to run nonexistent paths instead of `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" agent ...`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_7: Codex usage parser changed retired jq precedence
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: The Python Codex usage parser suppresses sibling `msg.*` token fields when `msg.usage` is a zero placeholder. This changes retired jq precedence and can count lower-priority `usage.*` fields instead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_8: Retained harnesses assert stale helper diagnostic wording
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retained launch-review and implementer harness assertions still expect legacy helper names such as `agent-model-args.sh` and `parse-codex-usage.sh`, while implementation emits new Python diagnostic wording.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Invalid env overrides can crash external launches
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Invalid health-gate and serial-lock environment overrides now raise `ValueError` instead of falling back to Bash defaults. Bad values can crash launch paths before intended probes or spawns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


