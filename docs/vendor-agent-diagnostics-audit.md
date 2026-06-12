# Vendor-agent diagnostics audit (#3713)

This table classifies every vendor-agent launch site against the three
properties the issue requires for committed run logs:

- **Saved** — on failure, the agent's stderr / tool-native diagnostic streams are
  preserved into files that survive the run (not truncated by retry loops, not
  deleted before publish).
- **Logged** — the failure lands in `execution-issues.md` (or the equivalent run
  log) with **non-empty** diagnostics whenever any diagnostic stream had content.
- **Flushed** — those diagnostics reach git (design: `design-log-publish.sh`
  staging; implement: the `vendor-failure-diagnostics` batch and/or the
  `execution-issues` batch), redacted via `redact secrets` /
  `redact tmpdir-paths`.

## Design

`scripts/run-external-agent.sh` is the single composed-carrier producer. On any
non-zero exit it composes a bounded, content-filtered `${OUTPUT}.failure-diag`
carrier inside its `EXIT` trap **before** writing `${OUTPUT}.done`, so a visible
`.done` always implies the carrier exists for failures. A retry that later
SUCCEEDS clears the carrier (entry-clear + success-clear), so retry-then-success
commits nothing. The carrier library (`scripts/lib-failed-agent-stderr-tail.sh`)
exposes `write_failure_diag`, `resolve_failure_diagnostic_source`,
`external_stream_reset` (per-attempt history archive), `append_vendor_failure_diagnostics`
(durable per-slot implement batch), and `resolve_execution_issues_log`.

Every launch that funnels through `run-external-agent.sh` therefore **inherits**
the saved carrier with no per-site change. `python/cli.py run-log append-failure` gains
a fail-closed backstop (missing / zero-byte `--output-file` → synthesize
`no diagnostics captured (exit N)`), so every `execution-issues.md` failure entry
is non-empty regardless of site. Raw streams (`*.sidecar`, `*.diag`,
`*.events.jsonl`, `*.sidecar.history`, `*.events.history`, scout `*.raw.*` stems)
stay publish-excluded; only the composed `*.failure-diag` carrier reaches git.

Routing key: **D** = directly fixed; **I** = inherits-via-`run-external-agent.sh`
(or via the now-fixed `launch-claude-subprocess.sh`); **R** = residual gap named
below.

## Table

| Call site | Saved | Logged | Flushed | Class | Notes |
|---|---|---|---|---|---|
| `scripts/run-external-agent.sh` | ✅ | n/a (callers log) | ✅ batch+publish | **D** | Central carrier producer; health-gate fast-fail echoes stderr. |
| `scripts/lib-failed-agent-stderr-tail.sh` | ✅ | — | — | **D** | Carrier library: compose / resolve / reset / append / log-resolver. |
| `python/cli.py run-log append-failure` | — | ✅ never-empty | — | **D** | Fail-closed backstop synthesizes a line for missing/zero-byte input. |
| `scripts/launch-review.sh` (codex) | ✅ | ✅ | ✅ | **D** | `external_stream_reset` at truncations; verdict-before-reset; give-up resolves carrier + `append_vendor_failure_diagnostics`. |
| `scripts/launch-review.sh` (cursor) | ✅ | ✅ | ✅ | **D** | Same as codex lane; `.diag` archived before truncation. |
| `scripts/launch-claude-subprocess.sh` | ✅ | via wrappers | ✅ | **D** | F7 carrier on the direct-Claude path: entry-clear, compose-on-failure, clear-on-success. Site-aware logging owned by wrappers. |
| `scripts/flush-vendor-failure-diagnostics.sh` | — | — | ✅ | **D** | Merges per-slot parts → batch; clear-after-success. |
| `scripts/design-log-publish.sh` | — | — | ✅ design | **D** | Stages `*.failure-diag` (redacted); denies raw `*.sidecar.history` / `*.raw.cursor` / `*.raw.claude` / `scout-plan-manifest.json.raw.*`. |
| `python/run_logs.py` | — | — | ✅ implement | **D** | `vendor-failure-diagnostics .txt replace none` slug. |
| `python/cli.py run-log` | — | — | ✅ implement | **D** | Keeps `*.failure-diag` / `*.sidecar.history` / `*.events.history` denied in `round_artifact_included` (batch is the sole durable path; F14). |
| `scripts/lib-design-round-artifacts.sh` | ✅ | — | ✅ design | **D** | Preserves `*.failure-diag` in plan-review round snapshots. |
| `skills/implement/scripts/step-7a.sh` | — | — | ✅ | **D** | Pre-ship flush of the vendor-failure batch. |
| `python/cli.py run-log flush` | — | — | ✅ | **D** | Commit-tail flush. |
| `python/cli.py run-log refresh` | — | — | ✅ | **D** | CI-retry / rebase pre-push flush. |
| `scripts/implement-finalize.sh` (teardown) | — | — | ✅ | **D** | Safety-net flush mirroring `flush_execution_issues_safety_net` (F13). |
| `scripts/launch-codex-implement.sh` | ✅ inherit | ✅ backstop | ✅ batch | **I/D** | Step 2 implementer routes through `run-external-agent.sh` (carrier saved); `append_launch_failure` now appends the diagnostic source to the durable batch. |
| `scripts/launch-cursor-implement.sh` | ✅ inherit | ✅ backstop | ✅ batch | **I/D** | As codex implementer (launcher parity). |
| `scripts/launch-codex-ci.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | CI-fix launcher routes through `run-external-agent.sh`. |
| `scripts/launch-cursor-ci.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | As codex CI launcher. |
| `scripts/launch-claude-ci.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | Direct-Claude CI lane via `launch-claude-subprocess.sh` (carrier saved). |
| `scripts/launch-codex-exec.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | Wrapper path inherits; preflight/no-wrapper exits are a residual carrier gap. |
| `scripts/dispatch-plan-voters.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | Voter launches inherit the carrier; dropped-slot give-up batch append is residual. |
| `scripts/dispatch-code-voters.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | As plan voters. |
| `scripts/dispatch-with-waterfall.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | Waterfall dropped-slot output-path exposure is residual. |
| `skills/review-and-fix/scripts/review-and-fix.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | `run_coder_dispatch_*` give-up inherits; per-tool sink + batch append is residual. |
| `scripts/scout-dynamic-archetypes.sh` | ✅ inherit | ✅ backstop | R | **I/R** | Cursor tier via `launch-review.sh` (**D**), Claude tier via `launch-claude-subprocess.sh` (**D**). Tier-specific raw stems + direct-Claude site-aware logging are residual; stale Codex-scout row is the incident's dropped path. |
| `scripts/generate-code-flow-diagram.sh` | ✅ inherit | R | R | **I/R** | Claude subprocess via `launch-claude-subprocess.sh` (carrier saved); `code-flow-diagram.raw.md` site-aware execution-issues + batch is residual. |
| `scripts/lint-fix-loop.sh` | ✅ inherit | ✅ backstop | R batch | **I/R** | Codex/Cursor dispatch inherits; per-tool carrier resolve + batch is residual. |
| `scripts/compose-collector-failure-log.sh` | ✅ inherit | ✅ | R | **R** | Not yet updated to prefer `${REVIEWER_FILE}.failure-diag` via the resolver. |

## Named residual {saved, logged, flushed} gaps

The central carrier (`run-external-agent.sh`) + the `launch-claude-subprocess.sh`
F7 path mean **Saved** holds at every site above. The
`run-log append-failure` backstop means **Logged** is never-empty at every site
that logs through it. The remaining residuals are **Flushed-to-batch** and
**real-diagnostics-at-give-up** gaps, all on the implement side where the carrier
is on disk but the launcher's own give-up has not yet been updated to (a) resolve
the carrier into its `run-log append-failure` source and (b) call
`append_vendor_failure_diagnostics`:

1. `launch-codex-ci.sh` / `launch-cursor-ci.sh` / `launch-claude-ci.sh` give-up:
   source the carrier lib and append the diagnostic source to the durable batch
   (the implement-side `launch-codex-implement.sh` / `launch-cursor-implement.sh`
   give-up already do this).
3. `launch-codex-exec.sh` preflight / no-wrapper branches: ordering-A carrier
   compose before exit.
4. `dispatch-plan-voters.sh` / `dispatch-code-voters.sh` /
   `dispatch-with-waterfall.sh` dropped-slot give-up: resolve from `VOTER_*_PATH`
   then batch-append; expose the dropped-slot output path.
5. `review-and-fix.sh` `run_coder_dispatch_*` give-up: explicit per-tool sinks +
   batch append.
6. `scout-dynamic-archetypes.sh`: tier-specific raw stems
   (`${OUTPUT}.raw.cursor` / `.raw.claude`) + direct-Claude tier site-aware
   logging.
7. `generate-code-flow-diagram.sh`: resolve `code-flow-diagram.raw.md` carrier +
   site-aware execution-issues + batch (F2).
8. `lint-fix-loop.sh`: per-tool carrier resolve + execution-issues + batch (F3).
9. `compose-collector-failure-log.sh`: prefer `${REVIEWER_FILE}.failure-diag` via
   the resolver, including retry / ns-retry candidates (F9).
These are tracked as residual-OOS for follow-up; none regress the prior behavior,
and all benefit from the central **Saved** carrier and never-empty **Logged**
backstop already in place.
