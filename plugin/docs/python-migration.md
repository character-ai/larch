# Python Migration Playbook (sh-to-py)

This document describes how to port a bash script domain into the larch Python
runtime and retire the old bash surface. Every subsequent sh-to-py issue follows
this recipe.

## Decision log

- **No shims for migration cutover**: when retiring a bash domain or making a voluntary port, consumers call `python3 "${CLAUDE_PLUGIN_ROOT}/python/cli.py" <domain> <verb> [args...]` directly. Do not add intermediate `.sh` forwarding stubs as migration cutover aids. Delete retired bash per recipe steps 4-6. This prohibition does not forbid forward-looking thin glue wrappers governed by the Python-first policy: thin environment-plus-`cli.py` delegation wrappers, Claude Code hooks, and pre-commit or CI glue.
- **Python-first for new scripts**: new larch script logic lives in `python/` behind `python3 python/cli.py`. Bash is allowed only for thin environment-plus-`cli.py` delegation wrappers, Claude Code hooks, and pre-commit or CI glue. This complements [recipe step 4](#per-domain-migration-recipe), **Cut ALL consumers to direct `cli.py` calls**, so migration and voluntary-port cutover keep direct `cli.py` calls while forward-looking glue-wrapper permissions stay separate. See [AGENTS.md](../AGENTS.md).
- **Hard cutover**: once a domain is registered in `cli.py`, all consumers (skills, docs, Makefile, CI) are repointed in the same commit. No `LARCH_*_IMPL`-style selectors.
- **Hooks stay bash**: Claude Code hooks remain bash pending a separate overhaul.
- **Package layout** (completed via issues #4982 + #5175): all runtime modules live under coherent `larch.*` sub-packages inside `python/larch/`. New packages are `larch.rendering`, `larch.release`, `larch.lint`, `larch.research`, and `larch.calibration`; existing packages (`larch.core`, `larch.design`, `larch.issue`, `larch.implement`, and `larch.report`) absorbed the remaining flat modules. The temporary `larch.review` migration package was retired by #8452. The dispatcher is now `larch.cli`; `python/cli.py` is a thin entry-point shim. Backward-compat re-export stubs remain at the old flat locations for test compat. New modules go directly into the appropriate package; the flat root is no longer the target.
- **`skills/**/*.py` importer scan scope** (#5698): Python scripts under `skills/` and `.claude/skills/` may add `python/` to `sys.path` at runtime (the `sys.path.insert(0, python_dir)` bootstrap pattern), making flat-root module names importable directly. When retiring a flat module, scan `python/ skills/ .claude/skills/ --include="*.py"` for importers — not `python/` alone. Confirm zero matches before deletion. See recipe step 4.
- **Stdlib-only, Python ≥ 3.11**: the runtime must not import third-party packages; dev/CI linters (Ruff and Pyright) and Pytest are installed separately via requirements files.
- **`cli.py` is the canonical entrypoint** for all external consumers. Adopted modules MAY keep `if __name__ == "__main__":` blocks as compatibility pass-throughs; `cli.py` becomes canonical via consumer cutover + docs + lint, not by disabling module execution.
- **fd-3 via `quiet_init`/`contract_stream`/`emit_kv`**: KV output intended for the .md orchestrator always goes to the contract stream (fd 3 after `quiet_init`, else stdout). Post-quiet human diagnostics go through `BreadcrumbWriter` (never raw `print(file=sys.stderr)` after `quiet_init`).

### Run-log Python-to-Rust handoff

The run-log domain is mixed-runtime. Rust owns initialization, entry writes,
mutable checkpoint and terminal flushes, transcript capture, manifest updates,
breadcrumb publication, archive creation, materialization, cache promotion,
storage preflight, shared lifecycle operations, standalone publication,
synchronization, historical layout migration, and retroactive repair sweeps.
Python retains bounded compatibility consumers and payload producers owned by
the #7679, #7680, #7681, #7684, and #7685 umbrellas. A renderer invoked by Rust
produces a payload only. It is not a fallback command owner. The current command
and compatibility inventory lives in [Rust command registry](rust-command-registry.md#retained-python-surfaces-outside-the-closed-7683-boundary).

Before a Rust cutover, pass the shared
`tests/fixtures/run-log-object-store-contract-v1.json` fixture plus archive,
materialization, publication, and sync parity tests. Then make one atomic
change that:

1. switches every skill, hook, script, and Python runtime caller to
   `${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`;
2. removes the Python registrations and superseded implementation;
3. updates the command registry to Rust-owned with no pending removal; and
4. proves clean-install execution through the verified bootstrap.

Do not add a compatibility shim, bridge, dual-write path, implementation
selector, runtime fallback, or staged consumer split. The storage contract in
`docs/run-log-archive.md` survives the owner change; the Python implementation
does not.

### Implement bootstrap and preflight cutover

Issue #8609 moved exactly five commands to Rust: `implement clone-tag`,
`implement normalize-coder-scout`, `implement step-0-degraded-gate`,
`implement step-0-bootstrap`, and `implement preflight`. Callers enter through
`scripts/larch.sh`, `python/larch/implement/dispatch_bootstrap.py` and
`python/larch/implement/preflight.py` are deleted, the `clone_tag_main` and
`normalize_coder_scout_main` CLI entry points are removed, and the registry
milestones are complete. `crates/larch-cli/src/implement_commands.rs` owns the
four bootstrap-side verbs and `crates/larch-cli/src/implement_preflight_commands.rs`
owns preflight.

`dispatch_helpers.py` and `dispatch_manifest.py` stay: `dispatch_ship.py` still
calls `_clone_expected_tmpdir_prefix`, and Step 2 still calls the in-process
`normalize_coder_scout()` library function. Preflight reads issues through the
Octocrab `GitHubService` per the #7672 spike instead of shelling out to
`gh issue view`, and resolves the repository root through `gix` per #7671.
Three siblings remain Python and are invoked through `python_verb`:
`issue governance-gate` (extended additively with `--preflight-envelope`),
`scout filter-manifest`, and `ci main-health`.

### Stall-recovery mixed-runtime cutover

Issue #8064 moved exactly six commands to Rust: `clear-stall`,
`seed-terminal-state`, `validate-token`, `validate-terminal-state`,
`validate-tier-b-public-file`, and `is-larch-dev-clone`. Their callers use
`scripts/larch.sh`, their Python registrations and command implementations are
removed, and their registry milestones are complete. Issue #8065 moves the
eight classification, attempt, normalization, and escalation commands to Rust
under the same atomic-cutover contract. Issue #8066 moves the four report
commands—`compose-report`, `dedup-tier-a-report`, `chat-print`, and
`populate-sensitive-corpus`—to Rust. All eighteen runtime commands now use
`scripts/larch.sh`; their Python registrations and implementations are removed,
and their registry milestones are complete. Only the contract-only `lint`
command remains Python-owned. Shared Python token helpers remain because that
lint consumes them; they are not fallback implementations for Rust commands.

**Initialization and entry writes cut over in #8073.** `run-log init`, `write`,
`write-round`, `append`, `append-entry`, `append-failure`, `exists`, and
`verify-completeness` are Rust-owned; `crates/larch-core/src/run_log/` owns the
batch registry, sanitizers, execution-issue composition, round-artifact tables,
and the verify-completeness reachability chain, and
`crates/larch-cli/src/run_log_entry_commands.rs` owns the command boundaries.
`python/larch/report/run_logs.py` survives only as a Rust consumer: its
`log_init` / `log_write` / `log_append` / `log_write_round` /
`log_append_failure` helpers build an argv, execute `scripts/larch.sh`, and
translate the exit code into the `ValueError` / `OSError` contract their
existing callers already handle. Manifest mutation completed its separate
cutover in #8072 and #8289: `scripts/larch.sh run-log manifest` is the only
production writer, while `python/larch/report/run_log_manifest.py` keeps only
read-only parsing and state compatibility helpers.

Two parts of `larch.report.run_log_batch` outlive their production callers on
purpose. The batch registry still backs bounded Python compatibility consumers
and the retained historical migration reader, and
`python/tests/report/test_run_log_batch_registry_parity.py` fails if it drifts
from the authoritative Rust table. The round-artifact tables and
`_stage_round_artifact` have no Python production caller left; they are retained
only as the shared source for the `run-log write-round` test double in
`python/tests/support/rust_agent_stub.py`, so the double cannot become a second
implementation. They are not a remaining run-log command owner.

**Publication and synchronization cut over in #8080.** `run-log publish` and
`run-log sync` are Rust-owned through
`crates/larch-adapters/src/run_lifecycle.rs` and
`crates/larch-cli/src/run_log_publication_commands.rs`. The leaf moved durable
pending state, create-only remote verification, cache promotion, paginated
inventory validation, interrupted-transfer cleanup, quarantine/restore, and
archive materialization behind the shared Rust object-store port. It removed
the Python command registrations and the superseded Python publication and
synchronization implementations. `python/larch/report/run_log_corpus.py` is a
typed Rust consumer for analyzer callers; `run_log_publish.py` and
`storage_config.py` retain bounded path, lock, configuration, and error support
used by those compatibility callers. The legacy `object_store.py` adapter is
for compatibility/test callers only. The offline adapter double covers
retry/resume, redaction before egress, and cold/warm sync.

**Breadcrumb publication cut over in #8074.** `run-log publish-breadcrumbs` is
Rust-owned. `larch_adapters::run_lifecycle::publish_breadcrumbs` is the single
owner: the already-migrated lifecycle terminalizer calls it directly, and
`crates/larch-cli/src/run_log_commands.rs` exposes it as the command boundary.
The same leaf deleted the superseded Python Git-commit implementation in
`python/larch/report/run_log_commit.py` — `_commit_run`, `larch_log_commit_main`,
`commit_larch_logs`, `_larch_log_commit`, `prepare_run_tree_for_publication`,
the repo-copy and volatile-cleanup helpers, and the pre-commit retry ladder had
no production caller after the flush retirement in #7995. #8267 deleted the
whole module once `prepare_run_for_archive`, its scrub helpers, and
`_publish_breadcrumbs_with_warning` also lost their last production importer.

**Mutable flush cut over in #8078.** `run-log checkpoint`, `refresh`,
`prepare-terminal-snapshot`, and `capture-transcript` are Rust-owned.
`crates/larch-cli/src/run_log_flush_commands.rs` owns the command boundaries,
batch staging, manifest reconciliation, and vendor-diagnostic aggregation.
All production callers use `scripts/larch.sh`; the Python registrations and
`python/larch/report/run_log_flush.py` are removed. Remaining Python report
helpers retain their bounded report and tracker side effects under Rust
orchestration and never delegate these commands.

**Archive creation and materialization cut over in #8079.** `run-log archive`
and `run-log materialize` are Rust-owned through
`crates/larch-adapters/src/run_lifecycle.rs` and
`crates/larch-cli/src/run_log_commands.rs`; every public caller enters through
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`. The Python registrations and command
entrypoints are removed. `larch.report.run_log_archive` is only a typed Rust
consumer for bounded compatibility callers. The historical migration-only
reader stayed isolated in `run_log_legacy_archive.py` until #8267 deleted it,
after #8081 moved the last legacy inventory consumer to Rust.

**Historical layout migration and retro sweeps cut over in #8081.**
`run-log migrate-layout`, `retro-v3-sweep`, and `retro-fix-cursor` are
Rust-owned through `crates/larch-cli/src/run_log_migration_commands.rs`. The
layout command preserves its create-only S3 plan/apply/verify contract and the
retro sweeps use root-confined, atomic local rewrites. All three Python command
registrations and implementations are removed; a dry run names the exact files
a live retro sweep would modify.

**Implement-run cleanup cut over in #8082.**
`run-log cleanup-implement-logs` is Rust-owned through
`crates/larch-cli/src/run_log_cleanup_commands.rs`. It selects runs through the
shared typed corpus reader, cleans only completed local implement runs, and
requires a present durability marker to say `state=committed` (publication also
requires that marker). It revalidates each confined destructive action. The
Python registration, implementation, and test are removed. Dry-run and live
output name the same planned local changes.

**Timing capture and timing reports cut over in #8083.**
`timing mark`, `record-vendor-task`, `record-round`, `dump`, `report`,
`harness-mark`, `telemetry-mark`, and `task-kinds` are Rust-owned through
`crates/larch-cli/src/timing_commands.rs` over the pure rules in
`crates/larch-core/src/report/timing.rs`. Ledger rows, the dump, and the
rendered report keep every machine field and the readable prose contract,
including Python's `json.dumps(..., sort_keys=True)` spacing. Appends take an
exclusive `flock`, so concurrent marks from separate processes never lose or
corrupt a row, and every clock value arrives through the injected
`BusinessClock`, so tests pin time instead of sleeping. The Python
registrations and the superseded command implementations are removed;
`python/larch/report/timing.py` keeps only a read-only path resolver for review
consumers, while Rust owns every ledger mutation. `timing harness-mark`
reaches the Rust-owned dependency-free `larch-harness-mark` boundary through
the Makefile `HARNESS_MARK` variable. The released `larch` command forwards to
the same owner for compatibility, while the developer/CI binary avoids a cold
full-CLI build and emits separate cold-or-warm bootstrap timing diagnostics.
One deliberate difference: the Rust report parses the ledger once, so a
malformed row now warns once instead of once per internal read.

- **G1 review pipeline port (#3692, #8445, #8451, #8452)**: `review gather-context`, `review dispatch-panel`, `review collect-findings`, `review check-reviewer-failure-threshold`, `review aggregate-findings`, `review prune-nit-findings`, `review reviewer-prune`, `review tally-code-votes`, `review emit-tally`, `review log-phase`, `review core`, `review compose-findings`, and the Rust-owned `review-and-fix` repair verbs are reached through `scripts/larch.sh`. The closeout audit pins all 79 commands migrated by #7679's executable leaves, removes their superseded Python pipeline, and rejects any live runtime reference to the retired review package. Pure compatibility readers moved to `larch.core.findings`, `larch.calibration.voting`, `larch.calibration.voter_calibration`, and `larch.rendering.findings_ledger`; their remaining consumers belong to #7680, #7681, #7684, or the final #7686 cutover. Separately scoped loop-identity and rendering commands remain Python-owned only under those receiving umbrellas.

- **C3a1 plan-review CLI façade (#3680, #8446, #8448, #8449)**: `crates/larch-cli/src/plan_review_commands.rs` owns panel and voter dispatch, tally and audit commands, the Step 3 loop and continuation, finalize/preview, entry/state, normalization, persistence utilities, and round-artifact filters. Their Python registrations and superseded `plan_review.py` / `plan_review_loop.py` owners are removed. The loop-identity verbs remain in `larch.core.process_identity`, and `step35-settle` remains in `larch.design.design_settle`. Operator docs use `scripts/larch.sh plan-review <verb>` for Rust-owned commands.

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
   When the cutover retires a flat-root module, widen the importer scan to cover
   `skills/` and `.claude/skills/` alongside `python/`: scripts under those directories
   may add `python/` to `sys.path` and import flat names directly. Run
   `grep -r 'from <module> import\|import <module>' python/ skills/ .claude/skills/ --include='*.py'`
   and confirm zero matches before committing the deletion.

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
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" report-tokens analyze [args...]
cargo run --quiet --locked --package larch-cli -- lint rule retired-scripts
```

The Python CLI's `--help` flag lists all registered domain/verb pairs without importing any
domain module (lazy import).

## Rate-override environment variables

For `report-tokens analyze` and `final-report`, cost calculations use
`larch_core::report::RATE_TABLE`. The Python `report_tokens_cost.py` helper
remains only for the #7680 compatibility payload and #7684 token pricing
commands. Both paths accept the rate-override environment variables documented
in `docs/configuration-and-permissions.md`.

## Decision log — B6 prompt rendering and generators

- Prompt rendering, Mermaid sanitization, and diagrams upsert live in `python/rendering.py` behind `python3 python/cli.py render ...`, `mermaid sanitize`, and `diagrams upsert`; generated-artifact regeneration lives in `crates/larch-cli/src/rendering_commands.rs` behind `generate ...`. `render findings-view`, `render lane-status`, and `render reviewer` (#8556) are Rust-owned in that same module behind `scripts/larch.sh render ...`; `render specialist`, `render voter`, `render plan-review`, and `render scope-anchor` remain Python.
- Payload-routing parity is intentional: `render voter` and `render plan-review` write prompt/KV payloads directly to stdout; the remaining Python verbs initialize quiet-mode and emit machine KVs through the contract stream. The Rust owners of `render findings-view`, `render lane-status`, and `render reviewer` write the same observable stdout/stderr bytes directly.
- Generated artifact headers deliberately retain the historical Python CLI regeneration text for byte stability. `scripts/generators.tsv` registers `generate <verb>` rows and `cargo run --quiet --locked --package larch-cli -- generate check` runs the Rust drift walker in-process.
- The leaf dispatch slice now lives in `crates/larch-core/src/review_dispatch.rs`, `crates/larch-adapters/src/vendor_diagnostics.rs`, and `crates/larch-cli/src/agent_commands.rs` with CLI verbs `agent wait-reviewers`, `agent classify-diff`, `agent gather-branch-context`, and `agent compose-collector-failure-log`. Callers use `scripts/larch.sh`; `agent classify-diff` emits `DIFF_MODE=` and fails closed when its plugin-root `scripts/generators.tsv` manifest is missing or malformed.

## P4 dev-only skills migration

Most release helpers remain behind `python/cli.py`. Every audit-runs verb is Rust-owned behind `scripts/larch.sh audit-runs`, including report titles, title matching, the non-mutating backlog advisory, and prior-report closure. `analyze-issues {fetch,run,analyze}`, `plugin read-version`, `release classify-bump`, `release prepare`, `release set-version`, and the four release asset construction commands (`asset-candidate`, `package-asset`, `collect-assets`, `validate-assets`) are Rust-owned; live callers use `scripts/larch.sh` except the tag-triggered asset workflow, which invokes the staged release binary. `classify-bump.md` remains the classification contract. The set-version command owns the checked atomic transaction across both plugin manifests, workspace and internal dependency versions, and `Cargo.lock`. The six OOS commands migrated by #8178 and #8179 are Rust-owned; the remaining `skills/implement/scripts/oos-disposition-*.sh` files are thin `scripts/larch.sh` delegation wrappers only. Runtime hooks and `skills/combine-issues/scripts/search-implementing-issue.sh` remain Bash and out of scope. Audit scan OOS disposition lives in Rust core; git-log inline-triage fallback remains runtime-gate-only.

## Decision log — G13 ci/pr/merge/push/gh hard cutover

- Live ci/pr/merge/push/gh consumers now call `python3 python/cli.py <domain> <verb>` directly.
- The checkpoint probe behavior lives in `python/cli.py push checkpoint-probe`, including fork defaulting, `ROUTE=` routing, and larch-log conflict recovery.
- Retired helper and harness paths are recorded in `python/migrated-scripts.tsv` with `#4642`; treat those rows as history, not active runtime surfaces.

## Decision log — F3e tracking issue lifecycle

- Tracking issue read/write/summary verbs live behind `scripts/larch.sh tracking-issue ...` in Rust (#8346). Typed wrappers in `python/larch/core/rust_runtime.py` replace the former in-process Python workflow entry points, including local sentinel reads, and external command consumers keep entering through the same script. `final-report write` calls the same Rust tracking owner in process so its own output contract remains isolated. `python/larch/issue/tracking_issue.py` keeps only pure PR-footer helpers.
- The four `execution-issues` verbs live behind `scripts/larch.sh execution-issues ...` in Rust (#8176, completed by #8347). The shared Rust run-log entry owner serializes category-keyed Markdown chunk deduplication, atomic live-ledger replacement, and lock-protected compare-and-clear after a flush so a concurrent append remains pending. Typed wrappers in `python/larch/core/rust_runtime.py` replaced every in-process Python caller, and `python/larch/issue/execution_issues.py` is gone. `flush` and `flush-safety-net` re-enter `scripts/larch.sh` for the batch append, and `refresh` re-enters it for `tracking-issue upsert-summary`, so each child's `KEY=value` rows land in the caller's capture file instead of the verb's own contract stream.
- The five OOS batch verbs live behind `scripts/larch.sh oos ...` in Rust (#8178): `materialize-manifest`, `issue-cap`, `file-conflict-deps`, `disposition-gate`, and `disposition-checkpoint`. `crates/larch-cli/src/oos_commands.rs` owns the drivers; `oos_batch`, `oos_conflict`, `oos_disposition`, and `oos_record` in `larch_core::issue` own their composition and policy. The rejected-marker reader #8177 left split is reconciled in `larch_core::issue::oos_disposition`; see `docs/rust-command-registry.md`.
- `oos file`, the post-ship accepted-OOS filing driver, lives behind `scripts/larch.sh oos file` in Rust (#8179). `larch_core::issue::oos_filing` owns the stable-identity model, the sentinel and run-log records, and the body-splitting rules; `crates/larch-cli/src/oos_file_commands.rs` owns the driver behind one `FilingGateway` seam. `python/larch/issue/oos_filer.py` is gone: retained #7684 `larch.issue._oos` owns the three identity helpers it borrowed, and the retained #7681 `larch.implement.dispatch_ship` workflow owns Step 8 checkpoint routing and post-pass bookkeeping.
- `python/larch/issue/file_oos.py` is not a live command implementation or fallback. Its surviving in-process consumers use OOS block parsing and counting for the design workflow, title normalization for compatibility analysis, and run-id resolution for Step 8 bookkeeping. The receiving umbrella for this retained issue/OOS library is #7680, as recorded by `larch lint rule issue-python-free`; later library cutover does not return command ownership to Python.
- The six dependency-audit verbs live behind `scripts/larch.sh deps ...` in Rust (#8180): `resolve-repo`, `fetch`, `explicit-refs`, `write-proposals`, `plan`, and `apply`. `larch_core::issue::deps_audit` owns the grouping rules, the untrusted prose scans, the plan the operator approves, and the apply-time revalidation; `crates/larch-cli/src/deps_audit_commands.rs` owns the six drivers behind one `DepsGateway` seam.
- The ten combine-issues verbs live behind `scripts/larch.sh combine-issues ...` in Rust (#8181): `fetch`, `fetch-deps`, `list-open`, `close-eligible`, `plan-inherited`, `prose-audit`, `plan-audit`, `apply`, `close-sources`, and `close-stale`. `crates/larch-cli/src/combine_issues_commands.rs` owns their JSON planning contracts and typed GitHub effects; `IssueMutationOwner` owns issue creation and closure, while the typed dependency adapter proves re-added native blocker edges. `python/larch/issue/combine_issues.py` and its Python blocker parser are gone. `python/larch/issue/open_rows.py` remains only as #7681 governance-gate support.
- `issue migration-audit` lives behind `scripts/larch.sh issue migration-audit` in Rust (#8392). `crates/larch-cli/src/migration_audit_commands.rs` collects a bounded immutable snapshot through the typed GitHub, Git, filesystem, and in-process lint owners, while `larch_core::migration_audit` preserves the schema-v2 report and governance policy. The Python registration and audit implementation are gone; `python/larch/issue/migration_governance.py` and its `issue_block` and `open_rows` support remain only for the distinct #7681 `issue governance-gate` policy consumer.
- `tracking-issue read` preserves stdout failure envelopes for shell-level usage and validation failures; parser-level missing option values remain stderr-only.
- Write-verb usage errors remain stderr-only. `tracking-issue upsert-summary` keeps non-usage failure envelopes on stderr so existing stderr capture files remain authoritative.
- Retired shell helper paths are recorded in `python/migrated-scripts.tsv`; keep future prose on the live CLI surface so `make lint-retired-scripts` stays path-clean.

### Plan-quality domain migration

- Added `python/plan_quality.py` under the existing `plan` CLI domain for command parsing, validation, plan-size checks, revision, auto-fix, optional trailers, and plan-goals composition.
- Surviving Bash callers invoke `python3 scripts/larch.sh plan ...` directly. No shim layer is added.
- Drift baseline write-once moved to `scripts/larch.sh plan-review drift-baseline`; see **C3a1 design plan-review cutover** below.
- `plan validate` preserves `VALIDATE_LOG_FILE`: it writes `$DESIGN_TMPDIR/validate-plan-commands.log` when possible, otherwise a stable temp log.
- `python/cli.py design driver` bootstraps `PLUGIN_ROOT` when `CLAUDE_PLUGIN_ROOT` is unset.
- Step 3 keeps `RUN_STEP3_REVISE_PLAN_WITH_WATERFALL_SH` as an override while defaulting to `plan revise-waterfall`.
- `scripts/scripts/larch.sh plan step1-log` defaults to `plan compose-goals-test` without a retired executable guard.
- Absorbed shell harness targets now select `python/test_plan_quality.py`; survivor harnesses remain for shell call sites.

### C3c design decomposition and scout cutover

The C3c slice moves /design decomposition helpers to `python/decompose.py`, dynamic archetype scouting to `python/plan_scout.py`, scope-anchor handoff and rendering to `python/rendering.py`, and the findings-classification TSV header to `python/voting.py`. `/review` dynamic scout dispatch and drafter `filter-manifest` callers now use direct `python/cli.py` verbs so the retired shell wrappers are not kept as shims.

### C3a1 design plan-review cutover

- The plan-review loop enters through `scripts/larch.sh plan-review run`. `crates/larch-cli/src/plan_review_commands.rs` owns its rounds, continuation, normalization, entry/state, finalize/preview, persistence, panel/voter dispatch, tally, emit, Gate B, accepted-audit, and round-artifact filtering contracts.
- `design-step3-review.sh` remains the process-group wrapper for Step 3 and calls the Rust command surface through the verified bootstrap.
- The Python review package is removed. Shared compatibility parsing, calibration analysis, and prompt-ledger rendering now live with their receiving packages and expose no migrated review command.
- `dedup-plan-lines.py` remains in place. The migration does not add a standalone `snapshot-plan-round` verb and does not migrate Step 3.6 assessor scripts.
- Step 3 report evidence and result-env recovery are Rust-owned; `design-step3-review.sh` does not source a loop controller on result-env read failure.

### C3b design lifecycle direct CLI

- `/design` lifecycle wrappers now call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design <verb>` for argv parsing, routing, run-params init, postplan emission, publish, pause/resume, log publish, final summary, and OOS filing.
- Pause/resume marker bytes and `docs/issue-anchored-plan.md` payload fields remain compatible with in-progress sessions.
- `scripts/read-result-env.sh` now delegates allowlisted sourceable output generation to `python/design_terminal.py`.

### C1a5 waterfall dispatcher

- Ported the waterfall dispatcher to `agent dispatch-waterfall` and cut live callers over to the CLI verb.
- `decompose.py` uses explicit `in os.environ` override detection instead of `get` with a truthy default path.
- Embedded plan-review blobs call the verb through argv arrays.
- Audit predicates accept the renamed aggregator warning plus historical wording.
- POSIX ERE patterns are translated for Python `re`.
- Per-phase launch-all-then-collect-once concurrency, phase-3 failure finalization, and tail `collect-results` replay are preserved.
- The aggregate alternation gate and grouped-reuse artifact guard were pinned by the Python waterfall harness; both moved to `crates/larch-cli/tests/waterfall_commands.rs` when #8116 made the dispatcher Rust-owned.

### G5 design Step 2 drafter and validator cutover

- Step 2a, Step 2b drafter/prelude, Step 2b postplan, Step 2b.5, and validator-autofix bodies now run in-process through `python/cli.py design ...` and `scripts/larch.sh plan validator-autofix`.
- The design launcher maps the retired wrapper names to CLI verbs with `"$@"` forwarding so launcher-owned session rehydration and caller flags are preserved.
- The shared postplan helper calls `postplan_emit_main` and `pause_save_main` in-process. Rehydration exports merged session keys to `os.environ` before those calls.
- The thin-wrapper rc contract is preserved: nonfatal postplan outcomes emit stdout rows and exit 0, fatal emit rc `1` or `2` maps to process exit 1, and pause paths `sys.exit` after pause-save.
- Structure and pytest harnesses now target the Python authorities while the launcher remains the compatibility fence for prompt-side calls.

## E3 terminal Bash sweep

E3 retires terminal shared Bash libraries after a strict runtime-consumer pass. A shell or include file outside the residual inventory must be ported to `python/cli.py`, deleted when it has no live runtime consumer, or recorded as a blocker before merge.

The residual inventory is manifest-driven. `scripts/residual-bash-paths.txt` lists kept residual Bash only: hooks, bash-targeting linters and pre-commit wrappers, thin `scripts/larch.sh` delegation fences, `scripts/sleep-seconds.sh`, the combine-issues helper, residual harnesses, and manifest-listed `*.inc.bash` when a live runtime consumer remains. Live orchestration bodies and sourced helper libraries are out of scope. `scripts/larch.sh residual-bash paths [--root PATH]` reads that manifest; bash-targeting linters and CI shellcheck enumerate through it instead of rediscovering repo-wide shell files. Residual includes appear only when a kept residual executable still sources them.

Retired terminal helpers, orphan includes, and the PR-body `Closes #N` helper are recorded in `python/migrated-scripts.tsv` after reference cleanup passes `make lint-retired-scripts`. `python/cli.py pr closes-issue` is the remaining `Closes #N` extraction authority.

Contract-bearing hooks now own their stdout streams locally. `scripts/deny-edit-write.sh`, `scripts/sessionstart-health.sh`, and `skills/implement/scripts/hook-stop-fail-close.sh` emit hook JSON through per-hook `hook_emit` functions. `scripts/sessionstart-health.sh` keeps a stdout fallback when stripped PATH prevents quiet setup.

Agent-lint owns Bash 3.2 and dynamic-AWK portability through G010 and G011. Its explicit `script-inventory` is `scripts/agent-lint-script-inventory.txt`, which duplicates the residual-Bash inventory and adds standalone source `.awk` helpers; its test keeps the Bash portion complete. CI shard rebalance is deferred to `/rebalance-tests` and is not part of this sweep.
