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

### Implement Step 18 and Step 19 terminal cutover

Issue #8614 moved five commands to Rust: `implement step-18`,
`implement step-18-gate-logs-flush`, `implement step-19`,
`implement checks-result-identity`, and `checks self-edit-log`. Callers enter
through `scripts/larch.sh`; `python/larch/implement/dispatch_step18.py`,
`dispatch_step19.py`, and `checks_result_identity.py` are deleted;
`checks_self_edit_log_main` and the five CLI registrations are removed; and the
registry milestones are complete.
`crates/larch-cli/src/implement_terminal_commands.rs` owns the three terminal
verbs, `crates/larch-cli/src/checks_identity_commands.rs` owns the two identity
verbs, and `larch_core::implement::{identity, self_edit_log}` own the pure
fingerprint, classifier, and attribution-log logic. A new `checks` domain
carries only `self-edit-log`.

`python/larch/implement/self_edit_log.py` stays. The leaf body listed it as
superseded, but `checks_run_relevant.py`, `checks_lint_fix.py`, and
`dispatch_commit_route.py` still call `record_self_edits`, `digest_paths`,
`file_sha256`, and `read_self_edits` in process, and those modules belong to
later leaves. Only the CLI verb flipped.

Three boundaries moved deliberately. The four Rust `delegate_python` identity
call sites in `implement_dispatch_commands.rs` became in-process core calls,
because Python can no longer own a flipped command.
`dispatch_commit_route.py::_session_validated_repo_root` now runs
`implement checks-result-identity resolve-repo-root` through the shared
`_invoke_larch` resolver, which chief #7687 defines as a Rust consumer rather
than a fallback. And the Step 18 `token report` mark now runs through
`scripts/larch.sh` with the rest of the closing quartet; the retired owner sent
it to `python/cli.py`, where the verb has not been registered since #8507, so it
could only ever fail silently.

`implement-finalize teardown` stays Python-owned and is reached through the one
`python_verb` seam. The fingerprint keeps schema token `v1` and its byte-for-byte
input order, so a result env persisted before the flip still classifies as
`matching`; `ExactDiffRequest` gained closed `binary` and `no_ext_diff` fields
rather than argv forwarding, and untracked enumeration moved to
`RepositoryRead::status`, whose file set matches porcelain `--untracked-files=all`.
The bounded diff capture fails closed instead of fingerprinting truncated bytes.

The `show` token documented for `checks self-edit-log` is dropped. The retired
`argparse` parser declared no positional, so
`checks self-edit-log show --tmpdir ...` always exited 2.

### Rust clippy gate and rust-policy candidate cutover

`checks rust-clippy`, `ci prepare-rust-integration-artifact`,
`ci stage-rust-policy-candidate`, and `ci promote-rust-policy-candidate` flipped
owner to Rust in one PR (#8617), retiring `python/larch/implement/rust_clippy.py`
and `python/larch/implement/rust_policy_candidate.py` with their four
registrations.

- `crates/larch-cli/src/checks_rust_clippy_commands.rs` owns the changed-path
  clippy selection: the `RUST_CLIPPY_CHANGED_PATHS`/`SELECTED_PACKAGES`/
  `SELECTED_TARGETS`/`COMMAND`/`HOOK_RAN` stdout grammar, the workspace-vs-package
  selection rules over `cargo metadata`, and the exit codes are byte-compatible
  with the retired owner. `cargo`/`clippy` remain child processes; the changed-set
  Git discovery reuses the typed repository port and `GitCommandRuntime`.
- `crates/larch-cli/src/ci_policy_candidate_commands.rs` owns the coverage-artifact
  writer, the fixed-provenance candidate stage, and the trusted-main promotion,
  preserving the bundle filenames, the `"{checksum}  larch\n"` grammar, the
  `current-checkout`/`merge-group`/`refs/heads/main` provenance strings, and the
  stable `CandidateError` messages. It is the new `global-input:rust-ci-workflow`
  selector input that the retired Python module was.
- Consumers cut to `scripts/larch.sh`: the `.github/actions/rust-coverage`,
  `ci.yaml`, and `main-cache-publication.yaml` steps set `LARCH_BINARY` to the
  coverage, integration-artifact, or promoted bundle executable; `Makefile`
  `rust-check` and the `.pre-commit-config.yaml` `cargo-clippy` hook build a local
  `larch` (via `make rust-clippy-binary`, never an inline `cargo build` in the
  bounded on-commit entry); and the still-Python `checks run-relevant` fallback
  execs `scripts/larch.sh checks rust-clippy`. The three shared helpers
  `is_rust_relevant_path`, `bounded_cargo_env`, and `changed_paths_from_git` that
  `checks_run_relevant.py` still needs moved into that module.

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

`dispatch_helpers.py` and `dispatch_manifest.py` stay for their surviving
Python consumers, and Step 2 still calls the in-process
`normalize_coder_scout()` library function. Preflight reads issues through the
Octocrab `GitHubService` per the #7672 spike instead of shelling out to
`gh issue view`, and resolves the repository root through `gix` per #7671.
Two siblings remain Python and are invoked through `python_verb`:
`issue governance-gate` (extended additively with `--preflight-envelope`) and
`ci main-health`. `scout filter-manifest` was the third until #8582 made it Rust.

### Plan scouting and archetype filtering cutover

Issue #8582 moved all three `scout` commands to Rust atomically:
`scout dynamic-archetypes`, `scout plan-archetypes`, and
`scout filter-manifest`. `crates/larch-core/src/design/plan_scout.rs` owns the
pure half — the reserved-slug tables, manifest validation, fenced-JSON salvage,
the untrusted-text checks, and byte-stable manifest rendering — while
`crates/larch-cli/src/scout_commands.rs` owns the three command lines and the
effectful Cursor-then-Claude waterfall. `python/larch/design/plan_scout.py` and
its pytest module are deleted and the registry milestones are complete.

The three Rust siblings that previously spawned `scout filter-manifest` through
Python now call the in-process `filter_manifest_paths` seam:
`implement_commands::normalize_scout_manifest`,
`review_dispatch_panel::filter_dynamic_manifest`, and
`drafter_commands::filter_drafter_scout`. Two of those three discarded the
subprocess's WARN stream, so the seam returns warnings rather than publishing
them and only the dispatch panel re-emits them. `review dispatch-panel` reaches
`scout dynamic-archetypes` through `run_verified_larch` instead, because that
verb's own `KEY=value` stream must stay captured rather than merge into the
panel's contract stdout.

### Implement Step 5-7a review-routing cutover

Issue #8613 moved five commands to Rust: `implement step-5-review`,
`implement step-5-resume`, `implement checks-step5-resume`,
`implement step-6-entry`, and `implement step-7a`. Callers enter through
`scripts/larch.sh`; the four `.sh` wrappers and the inline `step-7a` launch fence
delegate to the verified bootstrap, and the registry milestones are complete.
`crates/larch-cli/src/implement_review_commands.rs` owns all five verbs, reusing
the #8610 bgjob/identity/rejoin infrastructure in
`crates/larch-cli/src/implement_dispatch_commands.rs` and delegating the
still-Python composites (`implement commit-route`, `implement checks-commit-route`,
`checks run-relevant`, `diagram code-flow`, `diagrams upsert`) plus the
already-Rust verbs (`implement step-8-seed-initial`, `review-and-fix step5`,
`review-and-fix check-changes`, `push checkpoint-probe`, `execution-issues flush`,
`timing`). `python/larch/implement/step_7a.py` is deleted, and the four entry
points plus their exclusive helpers are removed from
`python/larch/implement/dispatch_commit_route.py`. That module stays for the
still-Python `commit`, `commit-route`, and `checks-commit-route` family.

### Relevant-checks selection cutover

Issue #8616 moved two commands to Rust: `checks run-relevant` and
`checks contains-pins`. Callers enter through `scripts/larch.sh`; the
`/implement` checks leg in `python/larch/implement/dispatch_commit_route.py`
now runs `checks run-relevant` through the verified bootstrap via the
`runtime="larch"` path of `_run_leg_with_timeout`, and the CI `contains-pins`
job builds the executable and dispatches through `scripts/larch.sh`.
`crates/larch-cli/src/checks_run_relevant_commands.rs` owns both verbs, reusing
the pure selection, coverage/phase derivation, failure-digest, and contains-pin
scanner in `crates/larch-core/src/implement/` and delegating the still-Python
`checks rust-clippy` fallback (#8617) through `run_python_verb`. It spawns
`pre-commit` through the new `HostUtilityProgram::PreCommit` process owner (see
the security note in `docs/security/workflow-trust-and-mutations.md`).

The Python `checks_run_relevant_main` entrypoint is deleted, and the
`check_contains_pins_main` entrypoint is renamed to the internal
`run_contains_pins_scan`; both the `run_relevant_checks` orchestration and that
internal scanner stay in `python/larch/implement/checks_run_relevant.py` because
`checks lint-fix`/`repair-loop` (#8625, #8627) still call them in process. Those
siblings retire the residual Python. The command-registry milestones are
complete, and the two CLI registrations plus the `checks.py` re-exports are
removed atomically.

### Implement Step 8 ship-dispatch cutover

Issue #8624 moved four commands to Rust: `implement step-8-python-guard`,
`implement step-8-seed-initial`, `implement step-8-ship`, and
`implement step-8-oos-checkpoint`. `crates/larch-cli/src/implement_ship_commands.rs`
owns their argument parsing, durable input resolution, bgjob dispatch, Python
runtime probe, phantom probe, OOS exit mapping, and post-checkpoint bookkeeping.
Callers and all four thin wrappers enter through `scripts/larch.sh`; the
surviving Python pre-driver reaches the guard and seeder only through that
verified bootstrap. The Python CLI registrations, re-exports, handlers, and
exclusive helpers are removed atomically, and the command-registry milestones
are complete.

The retained `ship seed-initial-state` and `ship pr` engines remain Python and
are reached only through the central Rust-to-Python migration seam. The Rust
ship parent composes the shared bgjob adapter with completed-result replacement;
the child reconstructs canonical argv and passes the adapter merge-result path
to `ship pr`. The delegated process uses the same six-hour budget as the Step 8
bgjob, so a valid 30-minute CI wait outlives the default short bridge deadline.
The Rust OOS router composes `oos disposition-checkpoint`, keeps the exact
`OOS_CHECKPOINT_RC` and `NEXT_ACTION` grammar, writes run statistics, stamps the
manifest, and atomically clears only `OOS_PENDING` after success.
`dispatch_ship.py` remains for `ship pre-driver`, `ship pre-fix-rebase`,
`ship route-exit`, and `ship normalize-assessment-handoff`.
`dispatch_ship_seed.py` remains for Step 2 seed-context helpers. No Python
fallback or dual owner remains for the four migrated commands.

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

### Debate Python-to-Rust cutover

Umbrella #8555 (chief #7687) ported the whole `/debate` runtime to Rust across
leaves #8597-#8604 and closed the Python boundary in leaf #8605. The removed
Python surface is `larch.debate.orchestrator` and `larch.debate.publication`
(deleted by #8678 and #8679), plus `larch.debate.protocol` and the package
`larch.debate.__init__`, which #8605 deleted along with
`python/tests/debate/test_protocol.py` and the sole `larch.debate` config value
`DEBATE_SUBJECT_VALUE_KEY`. Rust now owns every debate command and its wire
contract: `crates/larch-core/src/debate/` (protocol, state, and prompt modules)
and `crates/larch-cli/src/{debate_commands,debate_publication_commands,debate_state}.rs`.
Production callers enter through `${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh debate
<verb>`; no `python/cli.py debate` caller remains. All twelve debate rows in
`crates/larch-lint/data/command-registry.toml` are `owner = "rust"` with
`implementation_parity`, `consumer_cutover`, and `python_removal` all
`complete`; their historical `python_module` strings are provenance, not live
imports. Following #8678 and #8679, the removed debate `.py` paths are not added
to `python/migrated-scripts.tsv`, because the Rust sources cite their Python
provenance by path and `make lint-retired-scripts` matches those paths anywhere.

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

**The `/voter-calibration` analyzer cut over in #8672.** `voter-calibration
analyze` is Rust-owned: `crates/larch-core/src/voter_calibration.rs` owns TSV
schema detection, the shared agreement and severity math, false-negative YES
rates, and rendering behind
`crates/larch-cli/src/voter_calibration_commands.rs`, which also owns era
segmentation and optional realized-outcome enrichment by reusing the
analyze-issues typed fetch, filed-OOS, and ground-truth report owners. The leaf
deleted the standalone `skills/voter-calibration/scripts/voter-calibration.py`
and the four retained `larch.issue` analytics modules (`_ground_truth`, `_oos`,
`_report`, `_util`), frozen verbatim under
`fixtures/rust-parity/voter_calibration_frozen/` behind the
`fixtures/rust-parity/voter_calibration_reference.py` loader, and replaced the
synthetic bash harness with the black-box parity suite
`crates/larch-cli/tests/voter_calibration_parity.rs`. Two deliberate
differences from the retired Python: repository identity comes from `--repo`
or gix-typed ambient origin resolution (the plugin-root `git config` probe
collapsed with the Rust binary), and the optional ground-truth enrichment
section reuses the shipped Rust `analyze-issues` owner, whose corpus scan and
outcome-bucket heuristics supersede the retired Python module's.

**The `/fluff-analysis` analyzer cut over in #8671.** `fluff-analysis analyze`
is Rust-owned: `crates/larch-core/src/fluff_analysis.rs` owns extraction, the
multi-label classifier, assessment and ship-outcome coverage, false-negative
diagnostics, and rendering behind
`crates/larch-cli/src/fluff_analysis_commands.rs`. The leaf deleted the
standalone `skills/fluff-analysis/scripts/fluff-analysis.py` (frozen verbatim
as `fixtures/rust-parity/fluff_analysis_reference.py`), replaced the synthetic
bash harness with the black-box parity suite
`crates/larch-cli/tests/fluff_analysis_parity.rs`, repointed the corpus smoke
onto `scripts/larch.sh`, and retired the analyzer's
`voting compose-tally-record` subprocess seam in favor of the in-process core
call.

**The #7684 analytics closure stays mechanically guarded.**
`analytics-7684-closure` reuses the command registry and service/Git inventory
parsers to reject incomplete rows, missing or umbrella migration leaves,
restored Python registrations, entrypoints, callers, or retained #7684 module
ownership. It syntax-parses the `/fluff-analysis` and `/voter-calibration`
prompt command fences so their only shipped analyzer owner remains
`scripts/larch.sh`; the retired standalone Python analyzer paths are rejected.
Missing or malformed closure evidence fails the rule. The plugin copy is a
generated projection and is checked with `release plugin-runtime --check`.

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
- `implement scope-disposition` is Rust-owned behind `scripts/larch.sh implement scope-disposition` (#8612). `crates/larch-cli/src/implement_scope_disposition_commands.rs` owns coverage attribution, banding, fingerprinting, disposition recording, and ship validation. `python/larch/implement/scope_disposition.py` remains only as a thin consumer that shells out through `larch_entrypoint` and deserializes published wire artifacts for still-Python callers. The Python-unit-test bootstrap double loads the frozen pre-cutover owner at `fixtures/rust-parity/implement_scope_disposition_reference.py` when `LARCH_TEST_RUST_BINARY` is unset.
- The four `execution-issues` verbs live behind `scripts/larch.sh execution-issues ...` in Rust (#8176, completed by #8347). The shared Rust run-log entry owner serializes category-keyed Markdown chunk deduplication, atomic live-ledger replacement, and lock-protected compare-and-clear after a flush so a concurrent append remains pending. Typed wrappers in `python/larch/core/rust_runtime.py` replaced every in-process Python caller, and `python/larch/issue/execution_issues.py` is gone. `flush` and `flush-safety-net` re-enter `scripts/larch.sh` for the batch append, and `refresh` re-enters it for `tracking-issue upsert-summary`, so each child's `KEY=value` rows land in the caller's capture file instead of the verb's own contract stream.
- The five OOS batch verbs live behind `scripts/larch.sh oos ...` in Rust (#8178): `materialize-manifest`, `issue-cap`, `file-conflict-deps`, `disposition-gate`, and `disposition-checkpoint`. `crates/larch-cli/src/oos_commands.rs` owns the drivers; `oos_batch`, `oos_conflict`, `oos_disposition`, and `oos_record` in `larch_core::issue` own their composition and policy. The rejected-marker reader #8177 left split is reconciled in `larch_core::issue::oos_disposition`; see `docs/rust-command-registry.md`.
- `oos file`, the post-ship accepted-OOS filing driver, lives behind `scripts/larch.sh oos file` in Rust (#8179). `larch_core::issue::oos_filing` owns the stable-identity model, the sentinel and run-log records, and the body-splitting rules; `crates/larch-cli/src/oos_file_commands.rs` owns the driver behind one `FilingGateway` seam. `python/larch/issue/oos_filer.py` is gone: the three identity helpers it borrowed lived in `larch.issue._oos` until #8672 retired that module. The #8624 Rust Step 8 owner now handles checkpoint routing and post-pass bookkeeping.
- `python/larch/issue/file_oos.py` is not a live command implementation or fallback. Its surviving in-process consumers use OOS block parsing and counting for the design workflow and title normalization for compatibility analysis. The receiving umbrella for this retained issue/OOS library is #7680, as recorded by `larch lint rule issue-python-free`; later library cutover does not return command ownership to Python.
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

- `/design` lifecycle wrappers now call `python3 "$CLAUDE_PLUGIN_ROOT/python/cli.py" design <verb>` for postplan emission, publish, pause/resume, log publish, final summary, and OOS filing. Argv parsing, routing, and run-params init moved to Rust; see **Design argv, route, and run-params cutover** below.
- Pause/resume marker bytes and `docs/issue-anchored-plan.md` payload fields remain compatible with in-progress sessions.
- `scripts/read-result-env.sh` now delegates allowlisted sourceable output generation to `python/design_terminal.py`.

### Design argv, route, and run-params cutover

- `design parse-flags`, `design route`, and `design init-runparams` flipped owner to `crates/larch-cli/src/design_commands.rs` in one PR (#8577). Callers reach them through `scripts/larch.sh design ...`; `design_step0.py` and `design_step0_env.py` invoke the verified bootstrap directly.
- `design_argv.py` and `design_router.py` are removed. `design_core.py` absorbed the shared private router helpers (`_usage`, `_parse_stdout_kv`, `_write_kv_file`, `_extract_args`, `_normalize_step`) that the surviving design modules import; `design_core.py` itself retires with leaves 8578-8592.
- Route title filtering calls the larch-core title predicates in-process, so the Python `TITLE_FILTER_REASON=error` subprocess-failure branch is retired; `lifecycle` and `archival` reasons keep the stdout grammar. `design pause-load` stays Python-owned until leaf #8589 and is bridged through `run_python_verb`.
- Frozen parity references live at `fixtures/rust-parity/design_router_frozen/` behind `fixtures/rust-parity/design_router_migrated_reference.py`, exercised by `crates/larch-cli/tests/design_router_migrated_parity.rs` with goldens under `fixtures/rust-parity/goldens/design-*.golden.json`.

### Design Step 0 session, environment, abort, and settle cutover

- `design step0-parse`, `step0-session`, `step0-route`, `step0-clarify-hard-halt`, `step0-init`, `step0-abort-cleanup`, `step0-ap-continue`, `step0c`, and `settle-next-action` flipped owner to `crates/larch-cli/src/design_step0_commands.rs` in one PR (#8578). Implementation parity, consumer cutover, and Python removal are complete for all nine. Callers reach them through `scripts/larch.sh design ...`; the PID-keyed `design_run_launcher_text` execs the Rust entrypoint for the eight `step0-*` verbs, joined by `step1d5`/`step1d7`/`step1e-reentry` after leaf #8579.
- `python/larch/design/design_step0_env.py`, `design_step0.py`, and `design_session.py` are removed with their registrations. `design_core.py` absorbed the shared wrapper/env/pause library those modules exported to the surviving design modules (`_load_source_env`, `load_bash_quoted_env`, `_load_wrapper_env`, `_parse_wrapper_args`, `require_plugin_root`, `_require_design_tmpdir*`, `check_pause_and_exit`, `_derive_binary_found`, `_run_best_effort`, the `WrapperArgs`/`PostplanPaths`/`DesignSessionRequest` dataclasses, `step2b5_next_action_for`, `load_design_session_request`, `prelude_main`, `step3_continuation_entry_main`, and their private helpers). `design prelude` and `design step3-continuation-entry` keep Python ownership with `python_module = "larch.design.design_core"`.
- `design_settle.py` stops importing `settle_next_action_for` and instead invokes `"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" design settle-next-action --site ... --postplan-rc ...` as a Rust consumer, parsing `SETTLE_STATUS`/`SETTLE_NEXT_ACTION`/`SETTLE_EXIT_RC`. Python keeps no copy of the dispatch table.
- The `step0-route` GitHub read moved to the typed larch-owned service (`OctocrabGitHubOperations::issue_read`, per the #7672 canonical result); the retired Python `gh issue view` path is gone. `design pause-save` stays Python-owned (leaf #8589) and is bridged through `run_python_verb`; `design stage-terminal-state` is now Rust-owned (leaf #8580, below).
- Frozen parity references are byte-identical copies at `fixtures/rust-parity/design_step0_frozen/` behind `fixtures/rust-parity/design_step0_migrated_reference.py`, exercised by `crates/larch-cli/tests/design_step0_migrated_parity.rs` with goldens under `fixtures/rust-parity/goldens/design-step0-*.golden.json`.

### Design Step 1 driver and step-log cutover

- `design driver`, `design step1d5`, `design step1d7`, `design step1e-reentry`, and `plan step1-log` flipped owner to `crates/larch-cli/src/design_step1_commands.rs` in one PR (#8579), reusing the #8578 Step 0 wrapper library (`parse_wrapper_args`, `load_wrapper_env`, `require_plugin_root`, `require_design_tmpdir`, `check_pause_and_exit`, `derive_binary_found`, and the `Step0Runner` child seam) raised to crate visibility. Implementation parity, consumer cutover, and Python removal are complete for all five.
- Consumer edits cut every live caller to `scripts/larch.sh`: the PID-keyed `design_run_launcher_text` case for `step1d5|step1d7|step1e-reentry` now execs `scripts/larch.sh design ...` alongside the `step0-*` verbs, and `design-step3b-tail.sh` flips its `ACTION=FINALIZE` pipe from `python3 cli.py design driver` to `scripts/larch.sh design driver`. `plan step1-log` (/implement Step 1) already routed through `scripts/larch.sh`, so it needed no caller change.
- `python/larch/design/design_step1.py` and `design_step_log.py` are removed with their five registrations. The surviving `design_core.py` keeps the shared helpers they imported (`_normalize_step`, `_extract_args`, `append_failure`, `_run_best_effort`, plus the Step 0 wrapper library) and retires later at #8593.
- Frozen parity references are byte-identical copies at `fixtures/rust-parity/design_step1_frozen/` behind `fixtures/rust-parity/design_step1_migrated_reference.py`, exercised by `crates/larch-cli/tests/design_step1_migrated_parity.rs` with goldens under `fixtures/rust-parity/goldens/design-step1-*.golden.json`.

### Design terminal-state and failure-report cutover

- `design read-result-env`, `design stage-terminal-state`, `design failure-report`, and `design step-final-summary` flipped owner to `crates/larch-cli/src/design_terminal_commands.rs` in one PR (#8580), reusing the #8578 Step 0 wrapper library (`parse_wrapper_args`, `load_wrapper_env`, `require_plugin_root`, `env_get`, `exit_from_i32`, and the `Step0Runner` child seam) raised to crate visibility. Implementation parity, consumer cutover, and Python removal are complete for all four. The Rust owner reaches the already-Rust `stall-recovery` verbs the same way the frozen Python module did — by re-invoking the larch entrypoint through the `Step0Runner` subprocess seam — and bridges the still-Python `design render-final-summary` (#8581) and `design log-publish` (#8592) neighbors through `python_verb::run_python_verb`. The tier-A filing (`stall-recovery dedup-tier-a-report`) and tracking upsert (`tracking-issue upsert-summary`) are gated by `larch_adapters::github::check_live_mutation_auth`; the narrow failed-publish-tail reconcile posts and closes through `IssueMutationOwner::close_with_comment`.
- `python/larch/design/design_terminal.py` is removed with its four `python/larch/cli.py` registrations (the unregistered dead `json_get_bool`/`json_get_bool_main`, already Rust-owned as `plan-review json-get-bool`, are dropped with it). The surviving pure library helpers relocated verbatim into `design_core.py`: `phase_driver_read_result_env`, `phase_driver_write_result_env`, `phase_driver_recreate_result_env`, `clarify_failure_stage_args`, and `extend_publish_failure_stage_args`. In-process sibling callers (`clarify.py`, `design_publish.py`, `decompose.py`, `design_postplan.py`, `design_summary.py`, `design_step5c.py`) repoint to those `design_core` helpers or invoke the Rust verb through the new `design_core.run_design_verb`/`run_design_verb_captured` entrypoint bridges.
- **Ledgered temporary Python survival.** The three step-final-summary internals reused in-process by the unmigrated `design_step5c.py` (`_emit_final_summary_marked_from_disk`, `_emit_report_gate_sidecars_from_disk`, `_publish_terminal_final_summary`, plus their private support `_final_summary_stream`, `_final_summary_ready_rows`, `_upsert_final_summary_ready_into_merge_env`, `_persist_final_summary_readiness`, `_has_nonempty_final_summary`, `_parse_contract_value`) also relocated to `design_core.py`. This duplicates logic the Rust `step-final-summary` port contains; the duplication is the minimum needed to keep the unmigrated sibling working and is reconciled at #8586/#8593 when `design_step5c.py` and `design_core.py` retire.
- The frozen parity reference is a byte-identical copy at `fixtures/rust-parity/design_terminal_frozen/design_terminal.py` behind `fixtures/rust-parity/design_terminal_migrated_reference.py`, exercised by `crates/larch-cli/tests/design_terminal_migrated_parity.rs` with goldens under `fixtures/rust-parity/goldens/design-terminal-*.golden.json`. The symlink-primary `read-result-env` warning and the live-gh tier-A / reconcile branches are covered by inline `#[cfg(test)]` unit tests because the parity sandbox rejects tree symlinks and forbids live GitHub mutation.

### Design clarify state, comments, and labels cutover

- `clarify state`, `clarify comment-fetch`, `clarify comment-post`, `clarify label`, and `design clarify` flipped owner to `crates/larch-cli/src/clarify_commands.rs` and `crates/larch-cli/src/clarify_orchestrator.rs` in one PR (#8587). The pure marker/state machine is `crates/larch-core/src/design/clarify.rs`; the four verbs run through the `ClarifyEffects` GitHub seam over `OctocrabGitHubService` (no runtime `gh`), and the fetch/publish phase driver runs sibling verbs through the `SiblingRunner` seam. Implementation parity, consumer cutover, and Python removal are complete for all five.
- Consumers cut over to `scripts/larch.sh`: `skills/design/scripts/design-clarify.sh` execs `scripts/larch.sh design clarify`, and `skills/implement/references/preflight-plan-audit.md` calls `scripts/larch.sh clarify {state,comment-post,label}`. The publish orchestrator drives the Rust-owned sibling verbs (`named-block write`, `difficulty sync-labels`, `run-log write`/`append-failure`, `tracking-issue rename`/`upsert-summary`, and `design log-publish`) through `delegate_verified_larch` / `larch_entrypoint`, and the still-Python `stage-terminal-state`/`pause-save` through `run_python_verb`.
- `python/larch/design/clarify.py` and `python/tests/design/test_clarify.py` are removed with their five registrations; the two `design_summary.upsert_final_summary_from_disk` cases moved to `python/tests/design/test_design_summary.py`. The port also adds `rewrite_plan_difficulty` plus the `DESIGN_RAW_RATING_BASENAME`/`DIFFICULTY_RECORD_BASENAME` constants to `larch-core::difficulty`. Behavior is proven by the in-crate tests in `crates/larch-core/src/design/clarify.rs`, `crates/larch-cli/src/clarify_commands.rs`, and `crates/larch-cli/src/clarify_orchestrator/tests.rs`; no frozen reference is needed because no still-Python caller drives the verbs.

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
