# launch-claude-subprocess.sh Contract

`scripts/launch-claude-subprocess.sh` launches a Claude CLI reviewer subprocess for `/review` fallback slots.

Primary callers: `skills/review/scripts/dispatch-panel.sh` for Claude reviewer slots and `skills/review/scripts/tally-votes.sh` for tie-breaker voting.

Invariants:

- Stdout is a bounded `KEY=value` envelope: `STATUS`, `OUTPUT_FILE`, `ELAPSED`.
- The launcher writes `${OUTPUT_FILE}.done` only after promoting the temporary output file into place.
- It writes `${OUTPUT_FILE}.meta` with `OUTER_LAUNCHER=claude`, `TOOL=claude`, `TIMEOUT`, and `CMD_JSON` for collector compatibility.
- It writes `${OUTPUT_FILE}.dirty-tree` so review dirty-tree aggregation can treat Claude subprocesses like external reviewers.
- It writes `${OUTPUT_FILE}.pid` containing the script's own PID (`$$`) before launching the subprocess, and removes it in the EXIT trap. `wait-for-reviewers.sh` reads this sidecar on timeout and sends SIGTERM to that PID to terminate the stuck subprocess. A SIGTERM trap in the script kills the background subprocess before exiting.
- Prompt and context paths must be regular non-symlink files under the plugin root or the output session directory. Context is capped at 20 files and 256 KB each.
- Read-only posture is prompt-level only; the Claude CLI has no mechanical read-only flag in this wrapper.

Harness: `scripts/test-launch-claude-subprocess.sh`, wired into `make lint` through `test-launch-claude-subprocess`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Edit in sync: update this file, the harness, `SECURITY.md`, and `skills/review/scripts/dispatch-panel.sh` when argv grammar, sidecar grammar, path validation, or read-only wording changes. The `.pid` sidecar is paired with `scripts/wait-for-reviewers.sh`; changes to the sidecar filename convention must be mirrored there.
