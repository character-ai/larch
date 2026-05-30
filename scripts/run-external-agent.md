# scripts/run-external-agent.sh — contract

Monitored wrapper for external agents. It launches a command, writes `<output>.meta`, writes `<output>.done` on exit, enforces a timeout, and emits human-readable progress.

## Tool labels

`--tool` is intentionally permissive at the registry level: callers SHOULD pass a registered name (the canonical external-tool name set lives in `scripts/external-tool-registry.sh`), but this wrapper does not enforce that, so out-of-tree callers can pass arbitrary provenance tags. The raw `--tool` value is used as-is in human-readable log messages.

Before writing `.meta`, the wrapper sanitizes the `TOOL=` value through a label-safe allowlist (alphanumerics, `.`, `_`, `-`); any other byte — control characters, `=`, whitespace, and any non-ASCII byte (including Unicode line/paragraph separators U+2028/U+2029) — is translated to `_`. Translation (rather than deletion) preserves length so an adversarial label cannot collapse into the canonical tool ids consumed by `collect-agent-results.sh::derive_tool()`; for example, `cu\nrsor` becomes `cu_rsor`, not `cursor`. If sanitization yields an empty string, the `.meta` field falls back to `sanitized-empty` (a distinct sentinel from `unknown`, which `derive_tool()` uses for unclassifiable tools) so the retry path — which skips when `META_TOOL` is empty — stays functional.

This script is listed under `Related` in `scripts/external-tool-registry.md`, not under `Sourced by`: it is NOT sourced from the registry, does not validate `--tool` against it, retains the raw label in human-facing logs, and sanitizes the `.meta` `TOOL=` field as described above.

## `--output` invariants

`--output` is rejected during argv validation if it is empty or contains any byte outside `[A-Za-z0-9._/-]`; the wrapper exits 1 with an `ERROR:` line on stderr before `rm -f`, trap installation, `.meta` writes, or child launch. The accepted alphabet is deliberately narrower than "not a control byte and not `=`": `OUTPUT_FILE=` stores the path raw, and `CMD_JSON=` stores argv as JSON strings, but the retry reader retargets output paths by element-wise equality. Production callers that need retry retargeting MUST pass output paths as standalone argv elements (`--output X`), not embedded in one token (`--output=X`) or inside prompt text.

The current line parser in `scripts/collect-agent-results.sh` uses `${meta_line%%=*}` / `${meta_line#*=}`, so embedded `=` in the value is not lost by that parser. `=` is still rejected as defense-in-depth for ad-hoc consumers and future metadata readers, and because it falls outside the narrowed shell-quote-passthrough alphabet.

## Output capture modes

- Default: the child manages its own output path; wrapper stdout/stderr are not captured into `--output`.

- `--capture-stdout`: redirect the child's stdout and stderr together to `--output` (`> "$OUTPUT_FILE" 2>&1`).

- `--capture-stdout-only`: redirect stdout to `--output` and stderr to `<output>.diag`. This is the shape used for JSON-on-stdout protocols (for example Cursor CI via `launch-cursor-ci.sh`) so stderr noise cannot corrupt the parse.

- `--stderr-sink PATH` (default mode only): optional path to the file where wrapper and inherited child stderr are captured when a launcher redirects fd2 to a custom sink (for example `$SIDECAR_LOG` or `codex.wrapper.log`). Rejected with the same `[A-Za-z0-9._/-]` allowlist as `--output` when set. Omitted lanes behave byte-identically to the pre-flag contract. Capture-mode and Cursor lanes intentionally omit this flag because child stderr already lands in `<output>` or `<output>.diag`.

The capture flags are mutually exclusive. Metadata includes both `CAPTURE_STDOUT` and `CAPTURE_STDOUT_ONLY`; retry callers must preserve the original mode.

### Codex stdin contract

When `--tool codex` is used, every background spawn redirects stdin from `/dev/null`. The implementation lives at the launch site in `scripts/run-external-agent.sh` for the default and `--capture-stdout` branches, and inside `_launch_capture_stdout_only` for both the `stdbuf` and non-`stdbuf` arms. Codex keeps stdin open for possible interactive input; if it inherits the parent shell's stdin during a background run, parent-shell EOF can surface as `write_stdin failed: stdin is closed for this session` (#2962 / #2973). Other tools, including Cursor, continue to inherit stdin because they have not shown this Codex-specific stdin-close failure mode.

### Line buffering / `stdbuf` (`RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF`)

When `--capture-stdout-only` is active, the wrapper spawns the child with shell redirect `> "$OUTPUT_FILE" 2> "${OUTPUT_FILE}.diag"`. libc may fully buffer the writer even when the tool uses unbuffered Python (`-u`), so poll-based stall monitors that watch the output file's byte size can observe false stalls. If `RUN_EXTERNAL_AGENT_CAPTURE_STDOUT_STDBUF` is set to `1` and `stdbuf(1)` is on `PATH`, the wrapper wraps the child with `stdbuf -o0 -e0` for that capture path so line-buffered writers flush promptly (common on Linux CI). When `stdbuf` is unavailable or the env var is unset / not `1`, the wrapper runs the command without `stdbuf` (typical macOS).

## Inner-sentinel mode

`RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX` is an optional launcher-integration
knob. When unset, the wrapper preserves the public completion contract and
writes `<output>.done` from its `EXIT` trap. When set to the only accepted value,
`.inner.done`, the trap writes `<output>.inner.done` instead; a wrapping launcher
is then responsible for publishing `<output>.done` after its own post-processing
has completed. Any other value is rejected with an `ERROR:` line on stderr and
exit 1 before stale-file cleanup, trap installation, `.meta` writes, or child
launch. Stale cleanup always removes both `<output>.done` and
`<output>.inner.done`, regardless of mode, so switching modes cannot reuse an old
sentinel.

`scripts/launch-review.sh --tool cursor` uses this mode so its JSON `.result`
extraction and token-ledger scrape complete before collectors observe the public
sentinel. Non-wrapping callers keep the default `<output>.done` behavior.

## .meta sidecar grammar

The `<output>.meta` sidecar is a line-oriented file: one `KEY=VALUE` record per physical line, parsed by `scripts/collect-agent-results.sh` with the first `=` separating the key from the value. Values therefore must not embed physical newlines or Unicode line-break code points such as U+2028/U+2029.

- `TOOL` follows the allowlist contract in "Tool labels" above.
- `TIMEOUT` is accepted only after `--timeout` validates as a positive integer. Empty, non-numeric, and zero-valued digit strings (`0`, `00`, `000`, ...) are rejected; valid leading-zero positive values such as `010` remain accepted.
- `CAPTURE_STDOUT` and `CAPTURE_STDOUT_ONLY` are wrapper-owned booleans, not caller-controlled byte strings.
- `OUTPUT_FILE` is the wrapper's `--output` argument. Production callers pass internal session-tmpdir paths and are responsible for not embedding physical newlines or Unicode line-break code points (U+2028/U+2029); the wrapper does not re-sanitize this path before metadata emission.
- `CMD_JSON` is serialized as a single-line compact JSON array of post-`--` argv strings with `jq -cn --args '$ARGS.positional' -- "$@"`. The wrapper computes it in a guarded assignment (`if ! META_CMD_JSON=$(jq ...); then exit 1; fi`) because `printf 'CMD_JSON=%s\n' "$(jq ...)"` would not propagate `jq` failure under `set -e`. Missing or broken `jq` is a hard wrapper failure: the child is not launched, and stderr receives a clear `ERROR:` line.

There is no backward compatibility with the old `CMD=` metadata line. A collector that sees only `CMD=` treats retry metadata as invalid and fails closed.

## Invariants

- Always remove stale `<output>`, `<output>.done`, `<output>.inner.done`, `<output>.meta`, `<output>.diag`, and `<output>.stderr-tail` before launch.
- Always write `<output>.done` via the exit trap in default mode, or `<output>.inner.done` when `RUN_EXTERNAL_AGENT_INNER_SENTINEL_SUFFIX=.inner.done`.
- The trap writes the value of `EXIT_CODE`, which defaults to `99` ("wrapper crashed before capturing real exit code"). Failure paths between trap installation and child launch (e.g. `CMD_JSON` serialization) must assign `EXIT_CODE` to the real exit value before calling `exit`, so the sentinel matches the process exit status; the `99` default is reserved for unhandled crashes.
- If the wrapper exits while the child PID is still alive (for example, because a wrapping launcher signaled the wrapper), the trap kills and reaps the child before writing the sentinel. This keeps launcher-owned public sentinel publication from racing a still-running tool process.
- Keep `set -euo pipefail`; child exit codes are captured via guarded `wait`.
- Diagnostic text is appended to `<output>.diag` so stdout-only capture can retain child stderr.
- On non-zero exit or timeout, the wrapper writes a redacted, bounded stderr tail to `<output>.stderr-tail` (see `scripts/lib-failed-agent-stderr-tail.md`) and emits a fenced block to FD 2. Source order is mode-aware: default mode prefers a non-empty `--stderr-sink` file first, then `<output>.sidecar`, then `<output>`, then `<output>.diag`; `--capture-stdout` prefers merged `<output>` before `.diag` and ignores `--stderr-sink`; `--capture-stdout-only` prefers `.diag` before `<output>` and ignores `--stderr-sink`. Verdict lines and `.diag` content are unchanged (additive contract).
- `jq` is a hard prerequisite for this wrapper, in addition to the repo-wide `jq` dependency used by other larch scripts.

## Poll interval (`RUN_EXTERNAL_AGENT_POLL_INTERVAL`)

Seconds between `kill -0` polls in the wrapper's wait loop (and the cadence for per-minute progress lines). Default **10**. The value must be a positive number; decimals are allowed (for example **0.05** in harnesses) so stub agents that exit quickly do not sleep a full 10s per iteration. The same variable name is read by `cursor_launcher_run_stall_monitor` in `scripts/lib-cursor-launcher-common.sh` when launchers align stall polling with the wrapper.

## Call sites

Production entry points include `scripts/launch-review.sh` (per-tool review lanes), `scripts/launch-cursor-implement.sh`, `scripts/launch-codex-implement.sh`, `scripts/launch-cursor-ci.sh`, `scripts/launch-codex-ci.sh`, `scripts/dispatch-plan-voters.sh`, and `skills/review-and-fix/scripts/review-and-fix.sh` (indirectly via those launchers). Prefer the sibling launcher `.md` files for argv and timeout specifics.

## Test harness

`scripts/test-run-external-agent.sh` exercises timeout behavior, sentinel contracts, `CMD_JSON` failure paths, and related edge cases. Stall-detection integration for Cursor CI lives in `scripts/test-launch-cursor-ci.sh`.

## Edit-in-sync

Keep this file aligned with `scripts/run-external-agent.sh`, `scripts/collect-agent-results.sh` (`.meta` / retry reader), and any launcher that changes capture or sentinel semantics.
