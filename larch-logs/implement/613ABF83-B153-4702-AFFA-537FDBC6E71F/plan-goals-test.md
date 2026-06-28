## Goal
Implement issue #5732: [IMPLEMENTING] [BUG] Step 7a code flow diagram: health/auth rc=124, empty diagnostic tail, auth env conflict in launch-claude-subprocess.

## Implementation Plan
## Summary

Step 7a code flow diagram generation fails with `rc=124 tail=stderr:` on at least 27 distinct implement runs in the committed run logs. When auth signals are detected in the claude subprocess output the failure is additionally labeled `health/auth`. The failure is non-blocking but the warning is uninformative and the root cause (auth state mismatch between the parent Claude process and the spawned diagram subprocess) is not surfaced to the operator.

## Original report

Step 7a — code flow diagram: generation-failed health/auth rc=124 tail=stderr:

## Reproduction scenario

Run `/implement` (or `/im`) on any issue. At Step 7a, `generate_code_flow_diagram` spawns `python/cli.py agent launch-claude-subprocess`, which in turn spawns a `claude` subprocess for diagram generation. If the spawned subprocess encounters an auth degradation signal within `_CLAUDE_AUTH_FAST_FAIL_WINDOW` (60 s), it is killed and `EXIT_TIMEOUT (124)` is returned. The failure reason then reads `generation-failed health/auth rc=124 tail=stderr:`.

Frequency: approximately 27 of the recent committed run logs show `rc=124 tail=stderr:` in Step 7a execution-issues entries. The subset labeled `health/auth` matches runs where the auth fast-fail fired.

## Expected behavior

- Code flow diagrams generate successfully, OR
- When the subprocess fails, the warning message includes actionable diagnostic text (the actual stderr from the `claude` binary) so the operator can identify the auth root cause.

## Observed behavior

- The subprocess exits with rc=124 (timeout/auth-fast-fail).
- The `tail` field in the warning message is always `stderr:` with nothing after it. This is because `generate_code_flow_diagram` reads `completed.stderr` from the `launch-claude-subprocess` Python process, which emits nothing to its own stderr. The actual `claude` binary stderr is written to a sidecar file (`.stderr`) by `launch-claude-subprocess` but is not surfaced in the warning message.
- The `health/auth` label is classified by `classify_launch_failure` in `agents.py`: `auth_verdict == "auth"` takes priority over `EXIT_TIMEOUT`, so even a 180 s full timeout that happens to have auth-like content in the sidecar files is labeled `health/auth`.

## Root cause analysis

Two likely causes (uncertain which dominates):

1. **Auth environment conflict**: `launch-claude-subprocess` spawns a new `claude` process in the same environment as the parent. If `ANTHROPIC_API_KEY` is set in the environment (used by the orchestrator session), the child `claude` process prints a degraded-auth warning such as "takes precedence over your claude.ai login" or "auth source takes precedence" (patterns in `_CLAUDE_DEGRADED_AUTH_RE`). The polling loop in `_run_claude_with_stdin` detects this within `_CLAUDE_AUTH_FAST_FAIL_WINDOW = 60 s`, kills the process, and returns `EXIT_TIMEOUT`. The result is classified as `health/auth`.

2. **Diagnostic gap**: Even when the full 180 s timeout fires (not auth-related), `generate_code_flow_diagram` reads `completed.stderr` (the Python launcher's stderr — always empty) rather than the actual `claude` binary stderr stored in the `.stderr` sidecar. So `tail=stderr:` is always empty regardless of what the claude binary printed.

## Evidence

- `_CODE_FLOW_DIAGRAM_TIMEOUT_SECONDS = 180` in `python/larch/git/pr_body.py:53`
- `_CLAUDE_AUTH_FAST_FAIL_WINDOW = 60.0` in `python/larch/agents/agents.py:56`
- `_CLAUDE_DEGRADED_AUTH_RE` patterns (lines 61–67) include: `"takes precedence over your claude\.ai login"`, `"auth source takes precedence"`, `"apiKeyHelper failed"`, `"did not return a value"`
- `classify_launch_failure` at agents.py:520: `if auth_verdict == "auth": return LaunchFailure(failure_class="health", reason="auth")` — auth takes priority over EXIT_TIMEOUT check at line 528
- `_emit_claude_subprocess_failure_fields` at agents.py:2300 reads from sidecar files (`.stderr`, `.stderr-tail`, `.failure-diag`) and the output file to determine `auth_verdict`
- `generate_code_flow_diagram` at pr_body.py:953: `diagnostic, tail = _diagram_failure_capture(returncode=completed.returncode, stderr=completed.stderr)` — reads `completed.stderr` (Python launcher stderr) which is always empty; does NOT read the `.stderr` sidecar file that `launch-claude-subprocess` writes
- 27 recent implement run logs contain `generation-failed.*rc=124 tail=stderr:` in Step 7a execution-issues entries

## Affected files

- `python/larch/git/pr_body.py` — `generate_code_flow_diagram` reads `completed.stderr` (empty) instead of the `.stderr` sidecar file; fix should read the sidecar for diagnostic content
- `python/larch/agents/agents.py` — `_run_claude_with_stdin` fast-fail loop; `_emit_claude_subprocess_failure_fields`; `classify_launch_failure`; `_CLAUDE_DEGRADED_AUTH_RE` patterns

## Suggested fix(es)

1. **Diagnostic fix (low risk)**: In `generate_code_flow_diagram`, after the subprocess exits non-zero, read the `.stderr` sidecar file that `launch-claude-subprocess` writes (`output_file.with_suffix(output_file.suffix + ".stderr")`) and pass its content to `_diagram_failure_capture` instead of `completed.stderr`. This alone would make `tail=<actual-auth-message>` instead of `tail=stderr:`, giving the operator a clear signal.

2. **Auth environment fix (higher risk)**: In `launch-claude-subprocess`, strip `ANTHROPIC_API_KEY` from the environment before spawning the `claude` subprocess for diagram generation, or add a flag `--strip-api-key` so callers that rely on claude.ai login can opt in. This would prevent the auth conflict but requires careful evaluation of which auth path diagram generation should use.

3. **Retry on transient failure**: Add retry logic to `generate_code_flow_diagram` for `rc=124` exits: **4 retries, 10 seconds apart** (5 total attempts). A transient network or auth hiccup may resolve on a subsequent attempt. Log each retry attempt and the final outcome so operators can distinguish "succeeded on retry N" from "failed all 5 attempts". If all retries are exhausted with `health/auth`, give up and emit the warning.

4. **Silent skip on auth failure**: Instead of emitting a warning when the failure class is `health/auth`, silently skip diagram generation and omit the warning entry. This reduces noise but hides the problem.

Fix 1 is the safest and most immediately useful; Fix 3 (retries) addresses transient auth glitches; Fix 2 addresses a permanent auth root cause but needs auth-path analysis first.

## Open questions

- Does `launch-claude-subprocess` need `ANTHROPIC_API_KEY` in its environment, or does diagram generation specifically rely on claude.ai login? If the latter, stripping the key would fix the fast-fail.
- Is the 180 s diagram timeout appropriate, or should it be reduced to fail faster when auth issues are expected?
- Are all 27 affected runs auth-related (fast-fail within 60 s), or are some genuine full-timeout cases? The empty `tail` makes it impossible to distinguish without the sidecar file.

## Test plan
(no test plan section in plan-file)
