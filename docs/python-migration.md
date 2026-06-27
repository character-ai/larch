# Python Migration Playbook (sh-to-py)

This document describes how to port a bash script domain into the larch Python
runtime and retire the old bash surface. Every subsequent sh-to-py issue follows
this recipe.

## Decision log

- **No shims for migration cutover**: when retiring a bash domain or making a voluntary port, consumers call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]` directly. Do not add intermediate `.sh` forwarding stubs as migration cutover aids. Delete retired bash per recipe steps 4-6. This prohibition does not forbid forward-looking thin glue wrappers governed by the Python-first policy: thin environment-plus-`cli.py` delegation wrappers, Claude Code hooks, and pre-commit or CI glue.
- **Python-first for new scripts**: new larch script logic lives in `python/` behind `python3 python/cli.py`. Bash is allowed only for thin environment-plus-`cli.py` delegation wrappers, Claude Code hooks, and pre-commit or CI glue. This complements [recipe step 4](#per-domain-migration-recipe), **Cut ALL consumers to direct `cli.py` calls**, so migration and voluntary-port cutover keep direct `cli.py` calls while forward-looking glue-wrapper permissions stay separate. See [AGENTS.md](../AGENTS.md) and [`.claude/rules/python-first-scripts.md`](../.claude/rules/python-first-scripts.md).
- **Hard cutover**: once a domain is registered in `cli.py`, all consumers (skills, docs, Makefile, CI) are repointed in the same commit. No `LARCH_*_IMPL`-style selectors.
- **Hooks stay bash**: Claude Code hooks remain bash pending a separate overhaul.
- **Package layout** (completed via issues #4982 + #5175): all runtime modules live under coherent `larch.*` sub-packages inside `python/larch/`. New packages are `larch.rendering`, `larch.release`, `larch.lint`, `larch.research`, and `larch.calibration`; existing packages (`larch.core`, `larch.design`, `larch.issue`, `larch.implement`, `larch.review`, `larch.report`) absorbed the remaining flat modules. The dispatcher is now `larch.cli`; `python/cli.py` is a thin entry-point shim. Backward-compat re-export stubs remain at the old flat locations for test compat. New modules go directly into the appropriate package; the flat root is no longer the target.
- **Stdlib-only, Python ≥ 3.11**: the runtime must not import third-party packages; dev/CI linters (ruff, pyright, pylint) and pytest are installed separately via requirements files.
- **`cli.py` is the canonical entrypoint** for all external consumers. Adopted modules MAY keep `if __name__ == "__main__":` blocks as compatibility pass-throughs; `cli.py` becomes canonical via consumer cutover + docs + lint, not by disabling module execution.
- **fd-3 via `quiet_init`/`contract_stream`/`emit_kv`**: KV output intended for the .md orchestrator always goes to the contract stream (fd 3 after `quiet_init`, else stdout). Post-quiet human diagnostics go through `BreadcrumbWriter` (never raw `print(file=sys.stderr)` after `quiet_init`).

- **G1 review pipeline port (#3692)**: `python/review_pipeline.py` owns `gather-context`, `dispatch-panel`, `collect-findings`, `check-reviewer-failure-threshold`, `core`, and `reviewer-prune` in-process. `python/review_aggregate.py`, `python/review_tally.py`, and `python/compose_review.py` own aggregate, nit-prune, tally, emit, log-phase, and compose behavior in-process.

- **C3a1 plan-review CLI façade (#3680)**: `python/plan_review.py` and `python/plan_review_panel.py` register the shipped `plan-review` verbs but delegate loop, emit/finalize/preview, state, timing, Gate B dedup, panel dispatch, and voter dispatch to gzip-embedded retired bash via `_run_legacy()` / `_materialize_legacy_root()`. The `tally` verb is ported in-process to `python/plan_review_tally.py` (the gzip-embedded `tally-plan-review.sh` body is retained for contract tests but no longer executed). Treat the remaining delegated Python entry points as CLI entrypoints and contract relays, not as the implementation authority for Step 3 loop bodies, panel dispatch, or voter dispatch until a follow-up issue ports them in-process. Operator docs should name `python/cli.py plan-review <verb>` (with an explicit delegation note where relevant) rather than deleted script paths.

## Per-domain migration recipe

1. **Port functions** into a new or existing `python/<module>.py`. Keep the module
   stdlib-only; rely on `larch.core.proc` for subprocess calls,
   `larch.core.logging_util` for observability, and `larch.core.config` for
   tunables.

2. **Register CLI subcommands** — add a `("<domain>", "<verb>"): ("<module>", "main")`
   entry to `_REGISTRY` in `python/cli.py`. Keep top-level imports in `cli.py`
   limited to `argparse`, `importlib`, and `sys`.

3. **Write colocated pytest** in `python/test_<module>.py`. Subprocess cases derive
   the CLI path from `Path(__file__).with_name("cli.py")`. Cover the fd-3 contract,
   quiet mode behavior, and edge cases. Do NOT include retired-path literals in test
   fixtures; build paths at runtime instead.

4. **Cut ALL consumers to direct `cli.py` calls** — skill `.md` files, docs, Makefile
   targets, CI workflow steps, and any bash helper that invoked the old script. Change
   every `scripts/old-script.sh` or `python/old_module.py` invocation to
   `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]`.
   Bash callers should derive the plugin root from their local script directory
   first (falling back to `${CLAUDE_PLUGIN_ROOT}`) so direct execution from a
   checkout does not depend on a prehydrated environment variable.

5. **Run retargeted `test-*.sh` harnesses once as a parity gate** — after consumer
   cutover, confirm the bash integration harnesses still pass against the new CLI
   surface before deleting the old bash files.

6. **Delete bash script + harness + `.md` siblings** — remove the old
   `.sh`, `.md`, and test harness files. Do not leave stubs.

7. **Append to manifest** — add the deleted paths to `python/migrated-scripts.tsv`
   (full repo-relative path in column 1, `#<issue>` in column 2). This is how
   `make lint-retired-scripts` knows what to check for lingering references.

8. **`make lint-retired-scripts`** — run (or let CI run) `make lint-retired-scripts`
   to confirm no tracked file still references any of the retired paths.

## Manifest format

`python/migrated-scripts.tsv` — tab-separated, `path<TAB>retired_by`:

```
# Retired script manifest for the sh-to-py migration.
# Format: path<TAB>retired_by
scripts/old-helper.sh    #1234
```

Rules:

- **Path-precise references plus scoped dev-skill basenames.** The linter matches
  the full repo-relative manifest path everywhere and same-directory
  `$SCRIPT_DIR/<basename>.sh` / `${SCRIPT_DIR}/<basename>.sh` forms derived from
  that manifest path. It also matches bare basenames only in same-directory
  `.claude/skills/**/*.md` dev-skill docs when no live sibling `.sh` exists.
  Repo-wide bare basenames outside that scoped branch are not matched, so a live
  file at `other/path/run-analysis.sh` will not be flagged for a retired path at
  `scripts/old/run-analysis.sh`.
- Retired path references are deletion blockers whenever they match the manifest
  path or same-directory invocation forms. Comment and prose references are
  scanned the same way as code unless they fall under the exclusions below.
- Exclusions from scanning: any file under a `larch-logs/` path segment,
  `CHANGELOG.md`, and the manifest file itself are never scanned.
- **Do NOT write retired-path literals in test fixtures.** Build fixture paths
  programmatically at runtime so tests remain valid if the manifest changes.

## Lint invocation

```bash
# Check for stale references to retired paths.
make lint-retired-scripts
```

Wired into `make lint` and `.pre-commit-config.yaml`.

## Consumer invocation pattern

```bash
# Direct call — no shim.
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" ship pr [args...]
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" report-tokens analyze [args...]
python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" lint retired-scripts [args...]
```

The `--help` flag lists all registered domain/verb pairs without importing any
domain module (lazy import).

## Rate-override environment variables

For `report-tokens analyze`, cost calculations use the rates in `python/larch/core/config.py`.
Override them per-run with environment variables documented in
`docs/configuration-and-permissions.md`.

## Decision log — B6 prompt rendering and generators

- Prompt rendering, Mermaid sanitization, diagrams upsert, and generated-artifact regeneration now live in `python/rendering.py` behind `python3 python/cli.py render ...`, `mermaid sanitize`, `diagrams upsert`, and `generate ...` verbs.
- Payload-routing parity is intentional: `render voter` and `render plan-review` write prompt/KV payloads directly to stdout; the other verbs initialize quiet-mode and emit machine KVs through the contract stream.
- Generated artifact headers name the Python CLI regeneration command. `scripts/generators.tsv` now registers `generate <verb>` rows and `python3 python/cli.py generate check` runs the drift walker in-process.
- The leaf dispatch slice now lives in `python/larch/agents/review_dispatch.py` with CLI verbs `agent wait-reviewers`, `agent classify-diff`, `agent gather-branch-context`, and `agent compose-collector-failure-log`. `classify_diff(path)` is the silent importable API; `agent classify-diff` is the `DIFF_MODE=` CLI API. Generated-path classification resolves `scripts/generators.tsv` from the plugin repo root, not caller cwd.

## P4 dev-only skills migration

Release, audit-runs, combine-issues fetch/apply, and analyze-issues helper surfaces now live behind `python/cli.py`. `classify-bump.md` remains the release classification authority. Runtime hooks and runtime OOS gates remain bash. `.claude/skills/combine-issues/scripts/search-implementing-issue.sh` remains bash and out of scope. Audit scan OOS disposition lives in `python/oos_disposition.py`; git-log inline-triage fallback remains runtime-gate-only.

## Decision log — G13 ci/pr/merge/push/gh hard cutover

- Live ci/pr/merge/push/gh consumers now call `python3 python/cli.py <domain> <verb>` directly.
- The checkpoint probe behavior lives in `python/cli.py push checkpoint-probe`, including fork defaulting, `ROUTE=` routing, and larch-log conflict recovery.
- Retired helper and harness paths are recorded in `python/migrated-scripts.tsv` with `#4642`; treat those rows as history, not active runtime surfaces.

## Decision log — F3e tracking issue lifecycle

- Tracking issue read/write/summary helpers now live behind `python3 python/cli.py tracking-issue ...` verbs.
- `tracking-issue read` preserves stdout failure envelopes for shell-level usage and validation failures; parser-level missing option values remain stderr-only.
- Write-verb usage errors remain stderr-only. `tracking-issue upsert-summary` keeps non-usage failure envelopes on stderr so existing stderr capture files remain authoritative.
- Retired shell helper paths are recorded in `python/migrated-scripts.tsv`; keep future prose on the Python CLI surface so `make lint-retired-scripts` stays path-clean.

### Plan-quality domain migration

- Added `python/plan_quality.py` under the existing `plan` CLI domain for command parsing, validation, plan-size checks, revision, auto-fix, optional trailers, and plan-goals composition.
- Surviving Bash callers invoke `python3 python/cli.py plan ...` directly. No shim layer is added.
- Drift baseline write-once moved to `python/cli.py plan-review drift-baseline` (sourced by `python/cli.py design postplan-emit`); see **C3a1 design plan-review cutover** below.
- `plan validate` preserves `VALIDATE_LOG_FILE`: it writes `$DESIGN_TMPDIR/validate-plan-commands.log` when possible, otherwise a stable temp log.
- `python/cli.py design driver` bootstraps `PLUGIN_ROOT` when `CLAUDE_PLUGIN_ROOT` is unset.
- Step 3 keeps `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` as an override while defaulting to `plan revise-waterfall`.
- `scripts/python/cli.py plan step1-log` defaults to `plan compose-goals-test` without a retired executable guard.
- Absorbed shell harness targets now select `python/test_plan_quality.py`; survivor harnesses remain for shell call sites.

### C3c design decomposition and scout cutover

The C3c slice moves /design decomposition helpers to `python/decompose.py`, dynamic archetype scouting to `python/plan_scout.py`, scope-anchor handoff and rendering to `python/rendering.py`, and the findings-classification TSV header to `python/voting.py`. `/review` dynamic scout dispatch and drafter `filter-manifest` callers now use direct `python/cli.py` verbs so the retired shell wrappers are not kept as shims.

### C3a1 design plan-review cutover

- The plan-review loop now enters through the `plan-review` CLI domain, split between `python/plan_review.py` for loop mechanics and `python/plan_review_panel.py` for panel and voter dispatch.
- Bash wrappers call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review ...` directly. `design-step3-review.sh` remains the process-group wrapper for Step 3.
- **Gzip-shim façade (interim runtime):** most `plan-review` verbs still delegate through `_run_legacy()` to gzip-embedded retired bash bodies materialized at runtime (`EMBEDDED_LEGACY_REFS` in `python/plan_review.py`). Importable Python entrypoints exist for CLI routing, allowlist validation, drift-baseline write-once, round-artifact predicates, and `step3_record_report_evidence`; the `tally` verb is ported in-process (`python/plan_review_tally.py`), while loop/dispatch behavior remains bash until a follow-up in-process port lands; embedded plan-review assets rewrite reviewer pruning to `review reviewer-prune` before materialization. Regenerate embedded blobs from reviewable sources when absorbed bash behavior changes; `make lint-retired-scripts` guards deleted on-disk paths only.
- `dedup-plan-lines.py` remains in place. The migration does not add a standalone `snapshot-plan-round` verb and does not migrate Step 3.6 assessor scripts.
- `step3_record_report_evidence` moved into `python/plan_review.py`; `design-step3-review.sh` no longer sources the Step 3 loop controller on result-env read failure.

### C3b design lifecycle direct CLI

- `/design` lifecycle wrappers now call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design <verb>` for argv parsing, routing, run-params init, postplan emission, publish, pause/resume, log publish, final summary, and OOS filing.
- Pause/resume marker bytes and `docs/issue-anchored-plan.md` payload fields remain compatible with in-progress sessions.
- `scripts/read-result-env.sh` now delegates allowlisted sourceable output generation to `python/design_lifecycle.py`.

### C1a5 waterfall dispatcher

- Ported the waterfall dispatcher to `agent dispatch-waterfall` and cut live callers over to the CLI verb.
- `decompose.py` uses explicit `in os.environ` override detection instead of `get` with a truthy default path.
- Embedded plan-review blobs call the verb through argv arrays.
- Audit predicates accept the renamed aggregator warning plus historical wording.
- POSIX ERE patterns are translated for Python `re`.
- Per-phase launch-all-then-collect-once concurrency, phase-3 failure finalization, and tail `collect-results` replay are preserved.
- `python/test_agent_waterfall.py` pins the aggregate alternation gate and grouped-reuse artifact guard.

### G5 design Step 2 drafter and validator cutover

- Step 2a, Step 2b drafter/prelude, Step 2b postplan, Step 2b.5, and validator-autofix bodies now run in-process through `python/cli.py design ...` and `python/cli.py plan validator-autofix`.
- The design launcher maps the retired wrapper names to CLI verbs with `"$@"` forwarding so launcher-owned session rehydration and caller flags are preserved.
- The shared postplan helper calls `postplan_emit_main` and `pause_save_main` in-process. Rehydration exports merged session keys to `os.environ` before those calls.
- The thin-wrapper rc contract is preserved: nonfatal postplan outcomes emit stdout rows and exit 0, fatal emit rc `1` or `2` maps to process exit 1, and pause paths `sys.exit` after pause-save.
- Structure and pytest harnesses now target the Python authorities while the launcher remains the compatibility fence for prompt-side calls.

## E3 terminal Bash sweep

E3 retires terminal shared Bash libraries after a strict runtime-consumer pass. A shell or include file outside the residual inventory must be ported to `python/cli.py`, deleted when it has no live runtime consumer, or recorded as a blocker before merge.

The residual inventory is manifest-driven. `scripts/residual-bash-paths.txt` lists kept residual Bash only: hooks, bash-targeting linters and pre-commit wrappers, thin `python/cli.py` delegation fences, `scripts/sleep-seconds.sh`, the combine-issues helper, residual harnesses, and manifest-listed `*.inc.bash` when a live runtime consumer remains. Live orchestration bodies and sourced helper libraries are out of scope. `python/cli.py residual-bash paths [--root PATH]` reads that manifest; bash-targeting linters and CI shellcheck enumerate through it instead of rediscovering repo-wide shell files. Residual includes appear only when a kept residual executable still sources them.

Retired terminal helpers, orphan includes, and the PR-body `Closes #N` helper are recorded in `python/migrated-scripts.tsv` after reference cleanup passes `make lint-retired-scripts`. `python/cli.py pr closes-issue` is the remaining `Closes #N` extraction authority.

Contract-bearing hooks now own their stdout streams locally. `scripts/deny-edit-write.sh`, `scripts/sessionstart-health.sh`, and `skills/implement/scripts/hook-stop-fail-close.sh` emit hook JSON through per-hook `hook_emit` functions. `scripts/sessionstart-health.sh` keeps a stdout fallback when stripped PATH prevents quiet setup.

`lint-awk-multibyte-regex` has dual discovery. It scans residual shell and include paths from the manifest, and it still scans tracked standalone `*.awk` files outside the manifest. CI shard rebalance is deferred to `/rebalance-tests` and is not part of this sweep.
