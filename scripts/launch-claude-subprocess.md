# launch-claude-subprocess.sh Contract

`scripts/launch-claude-subprocess.sh` launches a Claude CLI reviewer subprocess for `/review` fallback slots.

Primary callers: `skills/review/scripts/dispatch-panel.sh` through waterfall Claude reviewer slots, `scripts/dispatch-code-voters.sh` for Claude voting slots, and `scripts/scout-dynamic-archetypes.sh` for dynamic-reviewer scout proposals.

Invariants:

- Stdout is a bounded `KEY=value` envelope: `STATUS`, `OUTPUT_FILE`, `ELAPSED`.
- The launcher writes `${OUTPUT_FILE}.done` only after promoting the temporary output file into place.
- It writes `${OUTPUT_FILE}.meta` with `OUTER_LAUNCHER=claude`, `TOOL=claude`, `TIMEOUT`, and `CMD_JSON` (argv without `--no-markdown`) for collector compatibility.
- It writes `${OUTPUT_FILE}.stderr` with any stderr emitted by the Claude CLI subprocess; useful for diagnosing unknown-option or refusal messages.
- When the Claude subprocess exits 0 but produces 0 bytes on stdout, the launcher reclassifies the result as `STATUS=ERROR` with `exit_code=99` (fail-loud guard). This catches silent unknown-flag failures that the CLI reports only to stderr.
- It writes `${OUTPUT_FILE}.dirty-tree` so review dirty-tree aggregation can treat Claude subprocesses like external reviewers.
- Prompt and context paths must be regular non-symlink files under an allowed root. Allowed roots: `PLUGIN_ROOT` (the installed plugin directory), `SESSION_ROOT` (the parent directory of `--output-file`), and any directories added via `--allow-root DIR` (repeatable; each must be an existing directory; canonical path is resolved via `cd`). Context path attributes in the rendered prompt are XML-escaped for `&`, `<`, `>`, and `"`, and context bodies are redacted, XML-escaped, and framed as untrusted input. Context is capped at 20 files and 1 MB each. The 1 MB per-file cap was raised from 256 KB in #2292 after real-world `/implement` runs on non-trivial PRs produced `git diff -U20 MERGE_BASE...HEAD` outputs above 256 KB (PR #2289 was 274 KB), tripping `context file exceeds 256 KB` for the diff context file silently because `dispatch-code-voters.sh` was swallowing the launcher's stderr. The new ceiling is well below Claude Sonnet 4-6's 200 K-token context window (≈ 800 KB after prompt overhead) while still bounding pathological inputs.
- `--allow-root DIR` is used by `dispatch-code-voters.sh` and `dispatch-panel.sh` to allow context files such as `review-diff.patch` that live under `IMPLEMENT_TMPDIR` rather than the launch session tmpdir.
- Read-only posture is prompt-level only for the default path; the Claude CLI has no mechanical read-only flag in this wrapper.
- Optional `--read-tools` with optional `--read-tools-add-dir DIR` (scout Claude tier): launches `claude --print --output-format json --add-dir <staged-context>` (default `$SESSION_ROOT/staged-context`), `--allowedTools "Read"`, `--permission-mode plan` without embedding `--context-files` in the rendered prompt. `DIR` must be a directory under the session root that owns `--output-file`. `CMD_JSON` records the tool-capable argv. Verified on dev hosts per `.claude/rules/verify-external-tool-invocations.md`.
- **Spawned-Claude token capture (issue #3637)**: both the default and `--read-tools` paths invoke the CLI with `--output-format json`. A successful run **must** promote a non-empty string `.result` over `${OUTPUT_FILE}` (so collectors keep seeing prose); the reported `.usage` (`input_tokens` / `output_tokens` / `cache_read_input_tokens` / `cache_creation_input_tokens`) is folded into the `claude_sub` ledger lane via `python3 python/cli.py token record-vendor claude_sub … raw=claude_<role>` **only after** that promotion succeeds. `<role>` is derived from `--timing-task-kind` by substring: `*scout*`→`claude_scout`, `*voter*`→`claude_vote` (covers `claude-code-voter`, `claude-plan-voter`), otherwise `claude_review`. **Fail-closed**: an `is_error:true` envelope, an empty/missing/non-string `.result`, or JSON-looking output that cannot be parsed writes a `CLAUDE_JSON_RESULT_INVALID` sentinel to the output, appends a diagnostic to `${OUTPUT_FILE}.stderr`, and reclassifies the run as `STATUS=ERROR` / `exit_code=99` with no ledger row — so collector-visible prose and token accounting cannot diverge. Non-JSON output (no leading `{`) with `jq` absent is left in place unchanged.

Harness: `scripts/test-launch-claude-subprocess.sh`, wired into `make lint` through `test-launch-claude-subprocess`.

On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout.

Edit in sync: update this file, the harness, `SECURITY.md`, `scripts/dispatch-code-voters.sh`, and `skills/review/scripts/dispatch-panel.sh` when argv grammar, sidecar grammar, path validation, or read-only wording changes.

## Vendor failure-diagnostics carrier (#3713 F7)

This launcher owns `${OUTPUT}`, so it clears `${OUTPUT}.failure-diag` at launch
start and on success (the retry-then-success guard), and composes the carrier via
`write_failure_diag` (sink = the subprocess `${OUTPUT}.stderr`) on any nonzero
exit. Site-aware execution-issues / batch logging is intentionally left to the
wrappers that know the tmpdir + site (`launch-claude-review.sh`,
`scout-dynamic-archetypes.sh`, `generate-code-flow-diagram.sh`). See
`docs/vendor-agent-diagnostics-audit.md`.
