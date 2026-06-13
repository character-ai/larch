# Python Migration Playbook (sh-to-py)

This document describes how to port a bash script domain into the larch Python
runtime and retire the old bash surface. Every subsequent sh-to-py issue follows
this recipe.

## Decision log

- **No shims**: consumers call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]` directly — no intermediate .sh wrapper files, ever.
- **Hard cutover**: once a domain is registered in `cli.py`, all consumers (skills, docs, Makefile, CI) are repointed in the same commit. No `LARCH_*_IMPL`-style selectors.
- **Hooks stay bash**: Claude Code hooks remain bash pending a separate overhaul.
- **Flat layout**: all Python modules live directly under `python/` (no sub-packages).
- **Stdlib-only, Python ≥ 3.11**: the runtime must not import third-party packages; dev/CI linters (ruff, pyright, pylint) and pytest are installed separately via requirements files.
- **`cli.py` is the canonical entrypoint** for all external consumers. Adopted modules MAY keep `if __name__ == "__main__":` blocks as compatibility pass-throughs; `cli.py` becomes canonical via consumer cutover + docs + lint, not by disabling module execution.
- **fd-3 via `quiet_init`/`contract_stream`/`emit_kv`**: KV output intended for the .md orchestrator always goes to the contract stream (fd 3 after `quiet_init`, else stdout). Post-quiet human diagnostics go through `BreadcrumbWriter` (never raw `print(file=sys.stderr)` after `quiet_init`).

- **C1b review CLI façade (#3677)**: `python/review_pipeline.py`, `python/review_aggregate.py`, `python/review_tally.py`, and `python/compose_review.py` register the shipped `review` verbs but delegate runtime behavior to `python/legacy_review_shell/*.sh` via `run_legacy()`. Treat those Python modules as CLI entrypoints and contract relays, not as the implementation authority for scout framing, aggregation, tally, or JSONL redaction. Security and operator docs name the legacy shell scripts (or `python/cli.py review <verb>` with an explicit delegation note) until a follow-up issue ports the bodies in-process.

- **F2 session/state scope (#3668)**: invoke-style session/state helpers are now `python/session_env.py` under the `session` domain. Four sourced-only bash libraries are intentionally deferred because surviving bash still sources them: `scripts/lib-design-tmpdir.sh`, `scripts/lib-validate-meta-path.sh`, `skills/implement/scripts/lib-resolve-implement-tmpdir.sh`, and `scripts/lib-finalize-state-keys.sh` (follow-up tracked in #3780, blocked by the consumer-owning migration phases). `session_env.py` preserves per-verb emitter routing instead of applying a global fd-3 policy, keeps the cleanup tempdir predicate separate from the session-writer target validator and finalize cleanup gate, uses a dedicated hardcoded-home design-env symlink validator, and keeps `restore-finalize-state` on the 20-key bash allowlist until the final ship-pr bash sourcer is retired.

## Per-domain migration recipe

1. **Port functions** into a new or existing `python/<module>.py`. Keep the module
   stdlib-only; rely on `proc.py` for subprocess calls, `logging_util.py` for
   observability, and `config.py` for tunables.

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
- **`scripts/ship-pr.sh` retention carve-out.** Because the legacy bash driver
  remains live during staged migration, matches in `scripts/ship-pr.sh` are
  deletion blockers only when they look like live invocation/source forms.
  Comment or prose mentions do not block retirement by themselves.
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

For `report-tokens analyze`, cost calculations use the rates in `python/config.py`.
Override them per-run with environment variables documented in
`docs/configuration-and-permissions.md`.

## Decision log — B6 prompt rendering and generators

- Prompt rendering, Mermaid sanitization, diagrams upsert, and generated-artifact regeneration now live in `python/rendering.py` behind `python3 python/cli.py render ...`, `mermaid sanitize`, `diagrams upsert`, and `generate ...` verbs.
- Payload-routing parity is intentional: `render voter` and `render plan-review` write prompt/KV payloads directly to stdout; the other verbs initialize quiet-mode and emit machine KVs through the contract stream.
- Generated artifact headers name the Python CLI regeneration command. `scripts/generators.tsv` now registers `generate <verb>` rows and `python3 python/cli.py generate check` runs the drift walker in-process.
- The leaf dispatch slice now lives in `python/review_dispatch.py` with CLI verbs `agent wait-reviewers`, `agent classify-diff`, `agent gather-branch-context`, and `agent compose-collector-failure-log`. `classify_diff(path)` is the silent importable API; `agent classify-diff` is the `DIFF_MODE=` CLI API. Generated-path classification resolves `scripts/generators.tsv` from the plugin repo root, not caller cwd.

## P4 dev-only skills migration

Release, audit-runs, combine-issues fetch/apply, and analyze-issues helper surfaces now live behind `python/cli.py`. `classify-bump.md` remains the release classification authority. Runtime hooks and runtime OOS gates remain bash. `.claude/skills/combine-issues/scripts/search-implementing-issue.sh` remains bash and out of scope. Audit scan OOS disposition lives in `python/oos_disposition.py`; git-log inline-triage fallback remains runtime-gate-only.

## Decision log — F3e tracking issue lifecycle

- Tracking issue read/write/summary helpers now live behind `python3 python/cli.py tracking-issue ...` verbs.
- `tracking-issue read` preserves stdout failure envelopes for shell-level usage and validation failures; parser-level missing option values remain stderr-only.
- Write-verb usage errors remain stderr-only. `tracking-issue upsert-summary` keeps non-usage failure envelopes on stderr so existing stderr capture files remain authoritative.
- Retired shell helper paths are recorded in `python/migrated-scripts.tsv`; keep future prose on the Python CLI surface so `make lint-retired-scripts` stays path-clean.

### Plan-quality domain migration

- Added `python/plan_quality.py` under the existing `plan` CLI domain for command parsing, validation, plan-size checks, revision, auto-fix, optional trailers, and plan-goals composition.
- Surviving Bash callers invoke `python3 python/cli.py plan ...` directly. No shim layer is added.
- `lib-drift-baseline.sh` remains deferred. Plan-size inlines only the baseline env semantics it needs.
- `plan validate` preserves `VALIDATE_LOG_FILE`: it writes `$DESIGN_TMPDIR/validate-plan-commands.log` when possible, otherwise a stable temp log.
- `design-driver.sh` bootstraps `PLUGIN_ROOT` when `CLAUDE_PLUGIN_ROOT` is unset.
- Step 3 keeps `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` as an override while defaulting to `plan revise-waterfall`.
- `scripts/run-step1-plan-log.sh` defaults to `plan compose-goals-test` without a retired executable guard.
- Absorbed shell harness targets now select `python/test_plan_quality.py`; survivor harnesses remain for shell call sites.

### C3c design decomposition and scout cutover

The C3c slice moves /design decomposition helpers to `python/decompose.py`, dynamic archetype scouting to `python/plan_scout.py`, scope-anchor handoff and rendering to `python/rendering.py`, and the findings-classification TSV header to `python/voting.py`. `/review` dynamic scout dispatch and drafter `filter-manifest` callers now use direct `python/cli.py` verbs so the retired shell wrappers are not kept as shims.

### C3a1 design plan-review cutover

- The plan-review loop now enters through the `plan-review` CLI domain, split between `python/plan_review.py` for loop mechanics and `python/plan_review_panel.py` for panel and voter dispatch.
- Bash wrappers call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" plan-review ...` directly. `design-step3-review.sh` remains the process-group wrapper for Step 3.
- `dedup-plan-lines.py` remains in place. The migration does not add a standalone `snapshot-plan-round` verb and does not migrate Step 3.6 assessor scripts.
- `step3_record_report_evidence` moved into `python/plan_review.py`; `design-step3-review.sh` no longer sources the Step 3 loop controller on result-env read failure.
