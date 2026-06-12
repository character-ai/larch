# scripts/lib-failed-agent-stderr-tail.sh - contract

Sourced-only library for redacted, bounded stderr tails on failed codex/cursor/claude subprocess exits (#3202). Sources `lib-quiet.sh` for `larch_err`, `sanitize_diagnostic_line`, and quiet-session-safe emission.

## Environment

- **`LARCH_FAILED_AGENT_STDERR_TAIL_LINES`** — tail line count (default **30**, chosen in design over issue #3202's 50). **`0`** disables capture and emission. Non-numeric values fall back to **30**.

## Limits

- Fixed **5120** byte ceiling after redaction (`failed_agent_stderr_byte_cap`).
- **`render_failed_agent_stderr_tail`** spools `tail | redact-tmpdir-paths.sh | redact-secrets.sh` to a temp file, then `head -c` from the spool (pipefail-safe).

## Sidecar

- **`write_failed_agent_stderr_tail`** writes `${output_file}.stderr-tail` atomically (`mktemp` + `mv`). Removes stale `${output_file}.stderr-tail` when disabled or empty.

## Signature

- **`failed_agent_stderr_signature`** — heuristic fingerprint (digit runs → `#`, hex `0x…` → `0x#`, tmp/session paths, output basenames normalized). Not semantic; used for collector dedup only.

## Collector tail resolution

- **`collector_stderr_tail_candidates`** — phase-fallback stems for `.stderr-tail` lookup.
- **`resolve_collector_stderr_tail_file`** — retry / NS-retry / phase `.stderr-tail` preference, then `${reviewer_file}.launch-stderr` on the primary stem only (no ancestor-phase launcher stderr).

## `select_failed_agent_stderr_source`

Optional 4th positional argument `explicit_sink`: in default (non-capture) mode, a non-empty, non-zero-size `explicit_sink` file is preferred before `<output>.sidecar`, `<output>`, and `<output>.diag`. Empty or missing explicit sinks fall back to the legacy order. `--capture-stdout` and `--capture-stdout-only` branches ignore `explicit_sink`.

## Callers

- `python/cli.py agent run-external-agent` — mode-aware source via `select_failed_agent_stderr_source` (passes `--stderr-sink` as the explicit sink); `emit_failed_agent_stderr_tail_raw` (non-quiet FD 2).
- `scripts/collect-agent-results.sh` — batch dedup emit via `larch_err`; delegates tail resolution to `resolve_collector_stderr_tail_file`.
- `python/cli.py agent launch-claude-subprocess` — pre-`.done` tail from `${OUTPUT}.stderr`; clears stale `${OUTPUT}.stderr-tail` at entry and on success.
- `python/cli.py agent launch-claude-review` — parent fallback from subprocess stderr capture; fenced tail via `emit_failed_agent_stderr_tail_larch_err` (quiet-safe).
- `skills/review/scripts/collect-findings.sh` — replay fallback uses `resolve_collector_stderr_tail_file`.

## Emission variants

- **`emit_failed_agent_stderr_tail_raw`** / **`emit_failed_agent_stderr_tail_file_raw`** — direct `>&2` fences (non-quiet `run-external-agent.sh` only).
- **`emit_failed_agent_stderr_tail_larch_err`** — fenced tail via `larch_err` (quiet-init callers).
- **`_emit_failed_agent_stderr_tail_line`** — single sanitized line via `larch_err` or `>&2` fallback.

## Vendor-agent failure-diagnostics carrier (#3713)

A second function family composes a single committed failure carrier so a failed
vendor launch at any site leaves enough committed diagnostics to distinguish
health-gate fast-fail vs mid-run crash vs timeout (124) vs auth vs quota.

- **`write_failure_diag OUTPUT [--sink P] [--history P] [--events P]`** — compose
  `${OUTPUT}.failure-diag` from the source list (`.sidecar.history`, filtered
  `.events.history`, `--sink`, `.sidecar`, `.diag`, filtered `.events.jsonl`,
  `.stderr`, `.launch-stderr`, `.launcher-stderr`) as labeled, bounded sections.
  Event / transcript streams are folded to failure-shaped lines only (success
  bulk stripped); diagnostic streams are included as bounded tails. Append-with-
  header when the carrier already exists. Returns 0 when the carrier is non-empty.
  Applies content folding + byte caps only — secret/tmpdir redaction happens
  downstream at publish / `append_vendor_failure_diagnostics`.
- **`resolve_failure_diagnostic_source OUTPUT [--sink P] [--history P] [--events P]`**
  — print the best available source: carrier first, else the first non-empty
  fallback across the source list (including `-retry` / `-ns-retry` carrier
  candidates). Returns 1 when all candidates are empty.
- **`external_stream_reset TARGET HISTORY [LABEL]`** — archive a bounded tail of a
  per-attempt stream to an append-only HISTORY (with an attempt header) when
  TARGET is non-empty, then truncate TARGET. Replaces bare `: > "$SIDECAR"`
  truncations so per-attempt stderr survives. `/dev/null` no-op.
- **`append_vendor_failure_diagnostics --source P --site L [--tmpdir D] [--exit-code N]`**
  — append a resolved, **redacted** excerpt as a per-slot part file under
  `$tmpdir/vendor-failure-diagnostics.parts/` (the SOLE durable implement flush
  path; `scripts/flush-vendor-failure-diagnostics.sh` merges parts → batch).
  Per-slot staging avoids interleaved concurrent appends without `flock`. Empty
  source → synthesized `no diagnostics captured (exit N)`. Best-effort.
- **`resolve_execution_issues_log`** — shared log-location resolver, precedence
  `LARCH_EXECUTION_ISSUES_LOG` → `dirname(SESSION_ENV_PATH)` → `IMPLEMENT_TMPDIR`
  → `DESIGN_TMPDIR` → `REVIEW_TMPDIR`.

Tunables: `LARCH_VENDOR_FAILURE_DIAG_SECTION_LINES` (default **120**) per-section
tail lines; `vendor_failure_diag_byte_cap` returns **16384**. Producers:
`python/cli.py agent run-external-agent` (central carrier in the EXIT trap),
`scripts/launch-review.sh`, `python/cli.py agent launch-claude-subprocess`, the implement
launchers. See `docs/vendor-agent-diagnostics-audit.md` for the per-site audit.

## Harness

`scripts/test-lib-failed-agent-stderr-tail.sh` — Makefile target `test-lib-failed-agent-stderr-tail`.
