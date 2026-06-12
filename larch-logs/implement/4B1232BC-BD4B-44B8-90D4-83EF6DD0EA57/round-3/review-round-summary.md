# Review Round 3

- Mode: `diff`
- 13 accepted, 2 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Claude subprocess publishes `.done` before failure diagnostics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_claude_subprocess_main` can write `.done` before `.stderr-tail` or `.failure-diag` on failure. Collectors may unblock on `.done` before diagnostic carriers exist, causing missing or incorrect failure reporting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_10: Cursor usage parsing can crash on malformed usage fields
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cursor usage parsing has unguarded integer conversions. A successful Cursor run with malformed usage fields may crash the wrapper before `.done` promotion and `LAUNCHER_EXIT` emission.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Missing Claude binary can crash without sidecars
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `_run_claude_with_stdin` does not catch a missing `claude` executable. Claude CI or subprocess fallback may raise an uncaught exception before normal output, done sidecars, diagnostics, or `LAUNCHER_EXIT=127` are written.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt: Address the concern above.


### FINDING_12: Cursor auth preflight failure is classified as unknown
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Cursor auth preflight failures may be emitted as `other/unknown` instead of health or auth failures. A Darwin auth setup failure may short-circuit fallback rather than waterfalling to another vendor.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_13: Health-gate fast-fail behavior is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No test covers health-gate fast-fail exits `7` and `8` with no child spawn. `run_external_agent` may regress to spawning unhealthy Codex or Cursor children, or using wrong exit codes, while CI stays green.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_14: Claude voter parse-rate retry path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Claude voter retry now uses `agent launch-claude-review`, but tests only stub `launch-review.sh` for Codex and Cursor. A Claude parse-rate retry could call the wrong entrypoint or drop flags without test failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_2: Default-mode external agents inherit quiet logs instead of redirected streams
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `agent run-external-agent` default-mode children inherit the quiet log instead of the caller’s redirected stdout and stderr. Codex JSON events and sidecar stderr may be lost, breaking usage parsing, auth retry, and quota classification.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_20: Claude subprocess dropped `STATUS`, `OUTPUT_FILE`, and `ELAPSED` stdout KVs
- **Reviewer(s)**: codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `launch_claude_subprocess_main` no longer emits `STATUS`, `OUTPUT_FILE`, and `ELAPSED` stdout key-values. `scout-dynamic-archetypes` may misclassify Claude timeouts as `claude-failed`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_3: Claude review launcher drops diff, plan, feature, and scope context
- **Reviewer(s)**: codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `launch_claude_review_main` drops context-file arguments instead of forwarding them to the Claude subprocess. Claude voters and fallback reviewers may no longer receive required diff, scope, plan, feature, or explicit context contents.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.


### FINDING_4: Claude CI promotes error or invalid JSON envelopes as success
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `launch_claude_ci_main` can treat `is_error`, empty-result, malformed, or raw JSON envelopes as successful launcher output. CI collectors may receive JSON instead of prose, mis-route the waterfall, or treat a failed Claude tier as successful.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_5: CI prompt sends plan-file secrets without redaction
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_ci_prompt` inlines `--plan-file` content without applying `redact.secrets`. Plan-file secrets may reach external CI agents in plaintext.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: `launch_codex_exec_main` lacks regression coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: No pytest coverage protects `launch_codex_exec_main` after removal of the bash harness. Regressions in preflight bundles, trusted-instructions temp `CODEX_HOME`, `inner.done` promotion, post-child ordering, design auto-fix, collector replay, and `OUTER_LAUNCHER_*` metadata may ship unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt: Address the concern above.


### FINDING_9: Claude subprocess prompts lost the read-only reviewer preamble
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Claude subprocess prompts no longer include the old always-on read-only preamble. A normal `launch-claude-review` path may invoke `claude --print` without explicit no-edit, no-write, or no-bash instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Address the concern above.


