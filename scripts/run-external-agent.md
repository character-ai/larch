# scripts/run-external-agent.sh — contract

Monitored wrapper for external agents. It launches a command, writes `<output>.meta`, writes `<output>.done` on exit, enforces a timeout, and emits human-readable progress.

## Tool labels

`--tool` is intentionally permissive at the registry level: callers SHOULD pass a registered name (the canonical external-tool name set lives in `scripts/external-tool-registry.sh`), but this wrapper does not enforce that, so out-of-tree callers can pass arbitrary provenance tags. The raw `--tool` value is used as-is in human-readable log messages.

Before writing `.meta`, the wrapper sanitizes the `TOOL=` value through a label-safe allowlist (alphanumerics, `.`, `_`, `-`); any other byte — control characters, `=`, whitespace, and any non-ASCII byte (including Unicode line/paragraph separators U+2028/U+2029) — is translated to `_`. Translation (rather than deletion) preserves length so an adversarial label cannot collapse into the canonical tool ids consumed by `collect-agent-results.sh::derive_tool()`; for example, `cu\nrsor` becomes `cu_rsor`, not `cursor`. If sanitization yields an empty string, the `.meta` field falls back to `sanitized-empty` (a distinct sentinel from `unknown`, which `derive_tool()` uses for unclassifiable tools) so the retry path — which skips when `META_TOOL` is empty — stays functional.

This script is listed under `Related` in `scripts/external-tool-registry.md`, not under `Sourced by`: it is NOT sourced from the registry, does not validate `--tool` against it, retains the raw label in human-facing logs, and sanitizes the `.meta` `TOOL=` field as described above.

## `--output` invariants

`--output` is rejected during argv validation if it is empty or contains any byte outside `[A-Za-z0-9._/-]`; the wrapper exits 1 with an `ERROR:` line on stderr before `rm -f`, trap installation, `.meta` writes, or child launch. The accepted alphabet is deliberately narrower than "not a control byte and not `=`": `CMD=` is serialized with `printf '%q'`, while `OUTPUT_FILE=` stores the path raw, and `collect-agent-results.sh` reconstructs retry commands with literal substring substitution. Spaces, UTF-8 bytes, and other shell-quoted characters would make the raw `OUTPUT_FILE=` value differ from its appearance in `CMD=`, so retry substitution could miss.

The path is rejected rather than transformed because the same byte string is used for the real output file, `<output>.done`, `<output>.diag`, `<output>.meta`, and the retry-substituted `CMD=` field. A `.meta`-only transform would split the recorded path from the on-disk path and from the bytes embedded in the shell-quoted command. The shared validator lives in `scripts/lib-validate-meta-path.sh`; `scripts/launch-gemini-review.sh` applies the same rule before its own side effects.

The current line parser in `scripts/collect-agent-results.sh` uses `${meta_line%%=*}` / `${meta_line#*=}`, so embedded `=` in the value is not lost by that parser. `=` is still rejected as defense-in-depth for ad-hoc consumers and future metadata readers, and because it falls outside the narrowed shell-quote-passthrough alphabet.

## Output capture modes

- Default: the child manages its own output path; wrapper stdout/stderr are not captured into `--output`.
- `--capture-stdout`: redirects child stdout and stderr to `--output`. Cursor uses this mode.
- `--capture-stdout-only`: redirects child stdout to `--output` and child stderr to `<output>.diag`. Gemini review uses this mode so JSON stdout is not corrupted by diagnostic noise; Gemini implementation uses `--capture-stdout` because the dispatcher consumes the on-disk manifest rather than stdout JSON.

The capture flags are mutually exclusive. Metadata includes both `CAPTURE_STDOUT` and `CAPTURE_STDOUT_ONLY`; retry callers must preserve the original mode.

## .meta sidecar grammar

The `<output>.meta` sidecar is a line-oriented file: one `KEY=VALUE` record per physical line, parsed by `scripts/collect-agent-results.sh` with the first `=` separating the key from the value. Values therefore must not embed physical newlines or Unicode line-break code points such as U+2028/U+2029.

This grammar is shared by every script that writes a sidecar consumed by `scripts/collect-agent-results.sh`. Today that means this wrapper plus `scripts/launch-gemini-review.sh::write_meta()`, which emits the same key set with `TOOL=gemini`. Maintainers editing either writer (or adding a new one) must keep all writers consistent with this contract.

- `TOOL` follows the allowlist contract in "Tool labels" above.
- `TIMEOUT` is accepted only after `--timeout` validates as a positive integer.
- `CAPTURE_STDOUT` and `CAPTURE_STDOUT_ONLY` are wrapper-owned booleans, not caller-controlled byte strings.
- `OUTPUT_FILE` is the wrapper's `--output` argument. Production callers pass internal session-tmpdir paths and are responsible for not embedding physical newlines or Unicode line-break code points (U+2028/U+2029); the wrapper does not re-sanitize this path before metadata emission.
- `CMD` is serialized with Bash `printf '%q'`, which preserves argument boundaries and shell-escapes most metacharacters. Behavior on multi-byte UTF-8 sequences (including the UTF-8 encodings of U+2028/U+2029) follows the inherited locale; the wrapper does not force a byte-oriented locale around the `printf '%q'` call. Callers that need locale-deterministic quoting should set `LC_ALL=C` before invoking the wrapper.

## Invariants

- Always remove stale `<output>`, `<output>.done`, `<output>.meta`, and `<output>.diag` before launch.
- Always write `<output>.done` via the exit trap.
- Keep `set -euo pipefail`; child exit codes are captured via guarded `wait`.
- Diagnostic text is appended to `<output>.diag` so stdout-only capture can retain child stderr.

## Poll interval (`RUN_EXTERNAL_AGENT_POLL_INTERVAL`)

The wrapper polls the child PID with `kill -0` in a loop and `sleep`s `$RUN_EXTERNAL_AGENT_POLL_INTERVAL` seconds (default `10`) between checks. Production callers wrapping real agents leave the default — 10s polling keeps progress chatter human-readable and bounds time-to-notice-timeout. Test harnesses that wrap stub binaries which exit in microseconds (e.g. `skills/implement/scripts/test-cursor-implementer.sh`, `skills/implement/scripts/test-gemini-implementer.sh`, `scripts/test-launch-gemini-review.sh`, `scripts/test-check-reviewers.sh`) export `RUN_EXTERNAL_AGENT_POLL_INTERVAL=0.05` so each stub invocation does not pay a full 10s sleep cycle. The variable accepts integer or decimal seconds; values that are not strictly positive are rejected with exit 1. Progress messages still fire once per elapsed minute regardless of poll cadence (driven by bash's `$SECONDS` builtin).

## Call sites

- `scripts/launch-gemini-review.sh` — Gemini reviewer JSON stdout capture.
- `scripts/launch-gemini-implement.sh` — Gemini implementer transcript capture.

## Test harness

`scripts/test-run-external-agent.sh` owns direct wrapper coverage for accepted `--output` paths, unsafe path rejection before side effects, and the sourced-helper invariants. `scripts/test-run-external-agent-args.sh` owns wrapper-side argument validation (notably the `--timeout 0` rejection contract — closes the gap left by #1115/#1171). `scripts/test-launch-gemini-review.sh` owns the Gemini launcher-specific validation path and JSON normalization lifecycle. `scripts/test-check-reviewers.sh` and collector harnesses continue to cover downstream wrapper consumers.

## Edit-in-sync

Update `scripts/lib-validate-meta-path.sh`, `scripts/launch-gemini-review.sh`, `scripts/collect-agent-results.sh` retry metadata parsing, launch wrappers, and this contract when adding capture modes, metadata keys, or changing the `OUTPUT_FILE=` retry-substitution invariant.
