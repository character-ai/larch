# launch-claude-subprocess.sh Contract

`scripts/launch-claude-subprocess.sh` launches a Claude CLI reviewer subprocess for `/review` fallback slots.

Primary callers: `skills/review/scripts/dispatch-panel.sh` for Claude reviewer slots and `skills/review/scripts/tally-votes.sh` for tie-breaker voting.

Invariants:

- Stdout is a bounded `KEY=value` envelope: `STATUS`, `OUTPUT_FILE`, `ELAPSED`.
- The launcher writes `${OUTPUT_FILE}.done` only after promoting the temporary output file into place.
- It writes `${OUTPUT_FILE}.meta` with `OUTER_LAUNCHER=claude`, `TOOL=claude`, `TIMEOUT`, and `CMD_JSON` for collector compatibility.
- It writes `${OUTPUT_FILE}.dirty-tree` so review dirty-tree aggregation can treat Claude subprocesses like external reviewers.
- Prompt and context paths must be regular non-symlink files under the plugin root or the output session directory. Context is capped at 20 files and 256 KB each.
- Read-only posture is prompt-level only; the Claude CLI has no mechanical read-only flag in this wrapper.

Harness: `scripts/test-launch-claude-subprocess.sh`, wired into `make lint` through `test-launch-claude-subprocess`.

Edit in sync: update this file, the harness, `SECURITY.md`, and `skills/review/scripts/dispatch-panel.sh` when argv grammar, sidecar grammar, path validation, or read-only wording changes.
