# Vendor-agent diagnostics audit (#3713)

This table classifies every vendor-agent launch site against the three
properties the issue requires for published run logs:

- **Saved** — on failure, the agent's stderr / tool-native diagnostic streams are
  preserved into files that survive the run (not truncated by retry loops, not
  deleted before publish).
- **Logged** — the failure lands in `execution-issues.md` (or the equivalent run
  log) with **non-empty** diagnostics whenever any diagnostic stream had content.
- **Flushed** — those diagnostics reach the published archive (design:
  `design log-publish` staging; implement: the `vendor-failure-diagnostics` batch and/or the
  `execution-issues` batch), redacted via `redact secrets` /
  `redact tmpdir-paths`.

## Design

`scripts/larch.sh agent run-external-agent` is the public composed-carrier producer.
On any non-zero exit it composes a bounded, content-filtered `${OUTPUT}.failure-diag`
carrier **before** writing `${OUTPUT}.done`, so a visible `.done` always implies the
carrier exists for failures. The remaining Python shared launcher uses the same
artifact schema for commands that have not migrated yet. A retry that later
SUCCEEDS clears the carrier (entry-clear + success-clear), so retry-then-success
publishes nothing. The carrier library (`python/larch/agents/agents.py`)
exposes `write_failure_diag`, `resolve_failure_diagnostic_source`,
`external_stream_reset` (per-attempt history archive), `append_vendor_failure_diagnostics`
(durable per-slot implement batch), and `resolve_execution_issues_log`.

Every direct launch through `scripts/larch.sh agent run-external-agent` therefore
**inherits** the saved carrier with no per-site change. `scripts/larch.sh run-log append-failure` gains
a fail-closed backstop (missing / zero-byte `--output-file` → synthesize
`no diagnostics captured (exit N)`), so every `execution-issues.md` failure entry
is non-empty regardless of site. Raw streams (`*.sidecar`, `*.diag`,
`*.events.jsonl`, `*.sidecar.history`, `*.events.history`, scout `*.raw.*` stems)
stay publish-excluded; only the composed `*.failure-diag` carrier reaches the
published run archive.

Routing key: **D** = directly fixed; **I** = inherits via the shared launcher carrier
(the Rust public command for direct callers, or the remaining Python library for
unmigrated launcher commands); **R** = residual gap named below.

## Table

| Call site | Saved | Logged | Flushed | Class | Notes |
|---|---|---|---|---|---|
| `scripts/larch.sh agent run-external-agent` | ✅ | n/a (callers log) | ✅ batch+publish | **D** | Central carrier producer; policy-rejection fast-fail writes the diagnostic marker. |
| `python/larch/agents/agents.py` | ✅ | — | — | **D** | Carrier library: compose / resolve / reset / append / log-resolver. |
| `scripts/larch.sh run-log append-failure` | — | ✅ never-empty | — | **D** | Fail-closed backstop synthesizes a line for missing/zero-byte input. |
| `scripts/larch.sh agent launch-review` (codex) | ✅ | ✅ | ✅ | **D** | `external_stream_reset` at truncations; verdict-before-reset; give-up resolves carrier + `append_vendor_failure_diagnostics`. |
| `scripts/larch.sh agent launch-review` (cursor) | ✅ | ✅ | ✅ | **D** | Same as codex lane; `.diag` archived before truncation. |
| `scripts/larch.sh agent launch-claude-subprocess` | ✅ | via wrappers | ✅ | **D** | F7 carrier on the direct-Claude path: entry-clear, compose-on-failure, clear-on-success. Site-aware logging owned by wrappers. |
| `scripts/larch.sh run-log prepare-terminal-snapshot` | — | — | ✅ | **D** | Rust sorts and merges per-slot parts, then atomically replaces the batch. |
| `python/cli.py design log-publish` | — | — | ✅ design | **D** | Stages `*.failure-diag` (redacted); denies raw `*.sidecar.history` / `*.raw.cursor` / `*.raw.claude` / `scout-plan-manifest.json.raw.*`. |
| `python/larch/report/run_logs.py` | — | — | ✅ implement | **D** | `vendor-failure-diagnostics .txt replace none` slug. |
| `scripts/larch.sh run-log write-round` | — | — | ✅ implement | **D** | Rust `round_artifact_included` keeps `*.failure-diag` / `*.sidecar.history` / `*.events.history` denied (batch is the sole durable path; F14). |
| `scripts/larch.sh plan-review run` | ✅ | — | ✅ design | **D** | Preserves `*.failure-diag` in plan-review round snapshots. |
| `skills/implement/scripts/step-7a.sh` | — | — | ✅ | **D** | Pre-ship flush of the vendor-failure batch. |
| `scripts/larch.sh run-log checkpoint` | — | — | ✅ | **D** | Rust-owned mutable recovery checkpoint. |
| `scripts/larch.sh run-log refresh` | — | — | ✅ | **D** | Rust-owned CI-retry / rebase pre-push flush. |
| `python3 python/cli.py implement-finalize` (teardown) | — | — | ✅ | **D** | Safety-net flush routes through Rust `scripts/larch.sh execution-issues flush-safety-net` (F13). |
| `scripts/larch.sh agent launch-codex-implement` | ✅ inherit | ✅ backstop | ✅ batch | **I/D** | Step 2 implementer routes through the approved external-process layer (carrier saved); the launch-failure record appends the diagnostic source to the durable batch. |
| `scripts/larch.sh agent launch-cursor-implement` | ✅ inherit | ✅ backstop | ✅ batch | **I/D** | As codex implementer (launcher parity). |
| `scripts/larch.sh agent launch-codex-ci` | ✅ inherit | ✅ backstop | R batch | **I/R** | CI-fix launcher uses the shared external-agent carrier. |
| `scripts/larch.sh agent launch-cursor-ci` | ✅ inherit | ✅ backstop | R batch | **I/R** | As codex CI launcher. |
| `scripts/larch.sh agent launch-claude-ci` | ✅ inherit | ✅ backstop | R batch | **I/R** | Direct-Claude CI lane via `scripts/larch.sh agent launch-claude-subprocess` (carrier saved). |
| `python/cli.py agent launch-codex-exec` | ✅ inherit | ✅ backstop | R batch | **I/R** | Wrapper path inherits; preflight/no-wrapper exits are a residual carrier gap. |
| `scripts/larch.sh plan-review voter-dispatch` | ✅ inherit | ✅ backstop | R batch | **I/R** | Voter launches inherit the carrier; dropped-slot give-up batch append is residual. |
| `scripts/larch.sh agent dispatch-voters` | ✅ inherit | ✅ backstop | R batch | **I/R** | Voter 1 failure site token: `agent dispatch-voters voter1`. |
| `scripts/larch.sh agent dispatch-waterfall` | ✅ inherit | ✅ backstop | R batch | **I/R** | Waterfall dropped-slot output-path exposure is residual. |
| `scripts/larch.sh review-and-fix apply-findings` | ✅ inherit | ✅ backstop | R batch | **I/R** | The Rust repair owner forwards through the typed vendor launchers; per-tool sink + batch append is residual. |
| `python/cli.py scout dynamic-archetypes` | ✅ inherit | ✅ backstop | R | **I/R** | Cursor tier via `agent launch-review` (**D**), Claude tier via `scripts/larch.sh agent launch-claude-subprocess` (**D**). Tier-specific raw stems + direct-Claude site-aware logging are residual; stale Codex-scout row is the incident's dropped path. |
| `scripts/generate-code-flow-diagram.sh` | ✅ inherit | R | R | **I/R** | Claude subprocess via `scripts/larch.sh agent launch-claude-subprocess` (carrier saved); `code-flow-diagram.raw.md` site-aware execution-issues + batch is residual. |
| `python/cli.py checks lint-fix` | ✅ inherit | ✅ backstop | R batch | **I/R** | Codex/Cursor dispatch inherits; per-tool carrier resolve + batch is residual. |
| `scripts/larch.sh agent compose-collector-failure-log` / `crates/larch-adapters/src/vendor_diagnostics.rs` | ✅ inherit | ✅ | R | **R** | Collector failure log composition now lives in the Rust adapter/CLI surface. |

## Named residual {saved, logged, flushed} gaps

The central carrier (`scripts/larch.sh agent run-external-agent`) + the `scripts/larch.sh agent launch-claude-subprocess`
F7 path mean **Saved** holds at every site above. The
`run-log append-failure` backstop means **Logged** is never-empty at every site
that logs through it. The remaining residuals are **Flushed-to-batch** and
**real-diagnostics-at-give-up** gaps, all on the implement side where the carrier
is on disk but the launcher's own give-up has not yet been updated to (a) resolve
the carrier into its `run-log append-failure` source and (b) call
`append_vendor_failure_diagnostics`:

1. `scripts/larch.sh agent launch-codex-ci` / `scripts/larch.sh agent launch-cursor-ci` / `scripts/larch.sh agent launch-claude-ci` give-up:
   source the carrier lib and append the diagnostic source to the durable batch
   (the implement-side `scripts/larch.sh agent launch-codex-implement` / `scripts/larch.sh agent launch-cursor-implement`
   give-up already do this).
3. `python3 python/cli.py agent launch-codex-exec` preflight / no-wrapper branches: ordering-A carrier
   compose before exit.
4. `dispatch-plan-voters.sh` / `scripts/larch.sh agent dispatch-voters` /
   `agent dispatch-waterfall` dropped-slot give-up: resolve from `VOTER_*_PATH`
   then batch-append; expose the dropped-slot output path.
5. `review-and-fix CLI` `run_coder_dispatch_*` give-up: explicit per-tool sinks +
   batch append.
6. `plan_scout.py`: tier-specific raw stems
   (`${OUTPUT}.raw.cursor` / `.raw.claude`) + direct-Claude tier site-aware
   logging.
7. `generate-code-flow-diagram.sh`: resolve `code-flow-diagram.raw.md` carrier +
   site-aware execution-issues + batch (F2).
8. `python/cli.py checks lint-fix`: per-tool carrier resolve + execution-issues + batch (F3).
9. `scripts/larch.sh agent compose-collector-failure-log`: prefer `${REVIEWER_FILE}.failure-diag` via
   the resolver, including retry / ns-retry candidates (F9).
These are tracked as residual-OOS for follow-up; none regress the prior behavior,
and all benefit from the central **Saved** carrier and never-empty **Logged**
backstop already in place.
