# launch-claude-subprocess.sh Contract

`scripts/launch-claude-subprocess.sh` launches a Claude CLI reviewer subprocess for `/review` fallback slots.

Primary callers: `skills/review/scripts/dispatch-panel.sh` for Claude reviewer slots and `scripts/dispatch-code-voters.sh` for Claude voting slots.

Invariants:

- Stdout is a bounded `KEY=value` envelope: `STATUS`, `OUTPUT_FILE`, `ELAPSED`.
- The launcher writes `${OUTPUT_FILE}.done` only after promoting the temporary output file into place.
- It writes `${OUTPUT_FILE}.meta` with `OUTER_LAUNCHER=claude`, `TOOL=claude`, `TIMEOUT`, and `CMD_JSON` (argv without `--no-markdown`) for collector compatibility.
- It writes `${OUTPUT_FILE}.stderr` with any stderr emitted by the Claude CLI subprocess; useful for diagnosing unknown-option or refusal messages.
- When the Claude subprocess exits 0 but produces 0 bytes on stdout, the launcher reclassifies the result as `STATUS=ERROR` with `exit_code=99` (fail-loud guard). This catches silent unknown-flag failures that the CLI reports only to stderr.
- It writes `${OUTPUT_FILE}.dirty-tree` so review dirty-tree aggregation can treat Claude subprocesses like external reviewers.
- Prompt and context paths must be regular non-symlink files under an allowed root. Allowed roots: `PLUGIN_ROOT` (the installed plugin directory), `SESSION_ROOT` (the parent directory of `--output-file`), and any directories added via `--allow-root DIR` (repeatable; each must be an existing directory; canonical path is resolved via `cd`). Context is capped at 20 files and 1 MB each. The 1 MB per-file cap was raised from 256 KB in #2292 after real-world `/implement` runs on non-trivial PRs produced `git diff -U20 MERGE_BASE...HEAD` outputs above 256 KB (PR #2289 was 274 KB), tripping `context file exceeds 256 KB` for the diff context file silently because `dispatch-code-voters.sh` was swallowing the launcher's stderr. The new ceiling is well below Claude Sonnet 4-6's 200 K-token context window (≈ 800 KB after prompt overhead) while still bounding pathological inputs.
- `--allow-root DIR` is used by `dispatch-code-voters.sh` and `dispatch-panel.sh` to allow context files such as `review-diff.patch` that live under `IMPLEMENT_TMPDIR` rather than the launch session tmpdir.
- Read-only posture is prompt-level only; the Claude CLI has no mechanical read-only flag in this wrapper.

Harness: `scripts/test-launch-claude-subprocess.sh`, wired into `make lint` through `test-launch-claude-subprocess`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Edit in sync: update this file, the harness, `SECURITY.md`, `scripts/dispatch-code-voters.sh`, and `skills/review/scripts/dispatch-panel.sh` when argv grammar, sidecar grammar, path validation, or read-only wording changes.
