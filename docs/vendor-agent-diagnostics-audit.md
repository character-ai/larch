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

`python/cli.py agent run-external-agent` is the single composed-carrier producer. On any
non-zero exit it composes a bounded, content-filtered `${OUTPUT}.failure-diag`
carrier inside its `EXIT` trap **before** writing `${OUTPUT}.done`, so a visible
`.done` always implies the carrier exists for failures. A retry that later
SUCCEEDS clears the carrier (entry-clear + success-clear), so retry-then-success
commits nothing. The carrier library (`python/larch/agents/agents.py`)
exposes `write_failure_diag`, `resolve_failure_diagnostic_source`,
`external_stream_reset` (per-attempt history archive), `append_vendor_failure_diagnostics`
(durable per-slot implement batch), and `resolve_execution_issues_log`.

Every launch that funnels through `python3 python/cli.py agent run-external-agent` therefore **inherits**
the saved carrier with no per-site change. `python/cli.py run-log append-failure` gains
a fail-closed backstop (missing / zero-byte `--output-file` → synthesize
`no diagnostics captured (exit N)`), so every `execution-issues.md` failure entry
is non-empty regardless of site. Raw streams (`*.sidecar`, `*.diag`,
`*.events.jsonl`, `*.sidecar.history`, `*.events.history`, scout `*.raw.*` stems)
stay publish-excluded; only the composed `*.failure-diag` carrier reaches git.

Routing key: **D** = directly fixed; **I** = inherits-via-`python3 python/cli.py agent run-external-agent`
(or via the now-fixed `python3 python/cli.py agent launch-claude-subprocess`); **R** = residual gap named
below.

## Table

| Call site | Saved | Logged | Flushed | Class | Notes |
|---|---|---|---|---|---|
| `python/cli.py agent run-external-agent` | ✅ | n/a (callers log) | ✅ batch+publish | **D** | Central carrier producer; health-gate fast-fail echoes stderr. |
| `python/larch/agents/agents.py` | ✅ | — | — | **D** | Carrier library: compose / resolve / reset / append / log-resolver. |
| `python/cli.py run-log append-failure` | — | ✅ never-empty | — | **D** | Fail-closed backstop synthesizes a line for missing/zero-byte input. |
| `python/cli.py agent launch-review` (codex) | ✅ | ✅ | ✅ | **D** | `external_stream_reset` at truncations; verdict-before-reset; give-up resolves carrier + `append_vendor_failure_diagnostics`. |
| `python/cli.py agent launch-review` (cursor) | ✅ | ✅ | ✅ | **D** | Same as codex lane; `.diag` archived before truncation. |
| `python/cli.py agent launch-claude-subprocess` | ✅ | via wrappers | ✅ | **D** | F7 carrier on the direct-Claude path: entry-clear, compose-on-failure, clear-on-success. Site-aware logging owned by wrappers. |
| `scripts/flush-vendor-failure-diagnostics.sh` | — | — | ✅ | **D** | Merges per-slot parts → batch; clear-after-success. |
| `python/cli.py design log-publish` | — | — | ✅ design | **D** | Stages `*.failure-diag` (redacted); denies raw `*.sidecar.history` / `*.raw.cursor` / `*.raw.claude` / `scout-plan-manifest.json.raw.*`. |
| `python/run_logs.py` | — | — | ✅ implement | **D** | `vendor-failure-diagnostics .txt replace none` slug. |
| `python/cli.py run-log` | — | — | ✅ implement | **D** | Keeps `*.failure-diag` / `*.sidecar.history` / `*.events.history` denied in `round_artifact_included` (batch is the sole durable path; F14). |
| `python/plan_review.py` | ✅ | — | ✅ design | **D** | Preserves `*.failure-diag` in plan-review round snapshots. |
| `skills/implement/scripts/step-7a.sh` | — | — | ✅ | **D** | Pre-ship flush of the vendor-failure batch. |
| `python/cli.py run-log flush` | — | — | ✅ | **D** | Commit-tail flush. |
| `python/cli.py run-log refresh` | — | — | ✅ | **D** | CI-retry / rebase pre-push flush. |
| `python3 python/cli.py implement-finalize` (teardown) | — | — | ✅ | **D** | Safety-net flush mirroring `flush_execution_issues_safety_net` (F13). |
| `python/cli.py agent launch-codex-implement` | ✅ inherit | ✅ backstop | ✅ batch | **I/D** | Step 2 implementer routes through the Python external-agent helper (carrier saved); `append_launch_failure` now appends the diagnostic source to the durable batch. |
| `python/cli.py agent launch-cursor-implement` | ✅ inherit | ✅ backstop | ✅ batch | **I/D** | As codex implementer (launcher parity). |
| `python/cli.py agent launch-codex-ci` | ✅ inherit | ✅ backstop | R batch | **I/R** | CI-fix launcher routes through `python3 python/cli.py agent run-external-agent`. |
| `python/cli.py agent launch-cursor-ci` | ✅ inherit | ✅ backstop | R batch | **I/R** | As codex CI launcher. |
| `python/cli.py agent launch-claude-ci` | ✅ inherit | ✅ backstop | R batch | **I/R** | Direct-Claude CI lane via `python3 python/cli.py agent launch-claude-subprocess` (carrier saved). |
| `python/cli.py agent launch-codex-exec` | ✅ inherit | ✅ backstop | R batch | **I/R** | Wrapper path inherits; preflight/no-wrapper exits are a residual carrier gap. |
| `python/cli.py plan-review voter-dispatch` | ✅ inherit | ✅ backstop | R batch | **I/R** | Voter launches inherit the carrier; dropped-slot give-up batch append is residual. |
| `python/cli.py agent dispatch-voters` | ✅ inherit | ✅ backstop | R batch | **I/R** | Voter 1 failure site token: `agent dispatch-voters voter1`. |
| `python/cli.py agent dispatch-waterfall` | ✅ inherit | ✅ backstop | R batch | **I/R** | Waterfall dropped-slot output-path exposure is residual. |
| `python/cli.py review-and-fix apply-findings` | ✅ inherit | ✅ backstop | R batch | **I/R** | `run_coder_dispatch_*` give-up inherits; per-tool sink + batch append is residual. |
| `python/cli.py scout dynamic-archetypes` | ✅ inherit | ✅ backstop | R | **I/R** | Cursor tier via `agent launch-review` (**D**), Claude tier via `launch-claude-subprocess.sh` (**D**). Tier-specific raw stems + direct-Claude site-aware logging are residual; stale Codex-scout row is the incident's dropped path. |
| `scripts/generate-code-flow-diagram.sh` | ✅ inherit | R | R | **I/R** | Claude subprocess via `launch-claude-subprocess.sh` (carrier saved); `code-flow-diagram.raw.md` site-aware execution-issues + batch is residual. |
| `python/cli.py checks lint-fix` | ✅ inherit | ✅ backstop | R batch | **I/R** | Codex/Cursor dispatch inherits; per-tool carrier resolve + batch is residual. |
| `python3 python/cli.py agent compose-collector-failure-log` / `python/larch/agents/review_dispatch.py` | ✅ inherit | ✅ | R | **R** | Collector failure log composition now lives in the Python CLI/module surface. |

## Named residual {saved, logged, flushed} gaps

The central carrier (`python3 python/cli.py agent run-external-agent`) + the `python3 python/cli.py agent launch-claude-subprocess`
F7 path mean **Saved** holds at every site above. The
`run-log append-failure` backstop means **Logged** is never-empty at every site
that logs through it. The remaining residuals are **Flushed-to-batch** and
**real-diagnostics-at-give-up** gaps, all on the implement side where the carrier
is on disk but the launcher's own give-up has not yet been updated to (a) resolve
the carrier into its `run-log append-failure` source and (b) call
`append_vendor_failure_diagnostics`:

1. `python3 python/cli.py agent launch-codex-ci` / `python3 python/cli.py agent launch-cursor-ci` / `python3 python/cli.py agent launch-claude-ci` give-up:
   source the carrier lib and append the diagnostic source to the durable batch
   (the implement-side `agent launch-codex-implement` / `agent launch-cursor-implement`
   give-up already do this).
3. `python3 python/cli.py agent launch-codex-exec` preflight / no-wrapper branches: ordering-A carrier
   compose before exit.
4. `dispatch-plan-voters.sh` / `python/cli.py agent dispatch-voters` /
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
9. `python3 python/cli.py agent compose-collector-failure-log`: prefer `${REVIEWER_FILE}.failure-diag` via
   the resolver, including retry / ns-retry candidates (F9).
These are tracked as residual-OOS for follow-up; none regress the prior behavior,
and all benefit from the central **Saved** carrier and never-empty **Logged**
backstop already in place.
