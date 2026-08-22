# Rust Command Registry

`crates/larch-lint/data/command-registry.toml` is the migration source of
truth for larch commands and production callers. Each command pair appears
once. Its row records the current owner, machine-stdout contract, required
`planning_issue`, optional exact `migration_issue`, implementation parity,
consumer cutover, Python removal, and an optional `clean_install_test` fixture
ID. The planning issue locates the command on the migration roadmap. The
migration issue names only the executable leaf accountable for its atomic
cutover; it stays absent until that leaf exists.

## Update workflow

Use one workflow for registry or caller changes:

1. Edit the Python or Rust command implementation and every affected
   production caller.
2. Refresh imported command metadata and caller rows. Pass the issue that owns
   any newly added command:

   ```bash
   cargo run --quiet --locked --package larch-cli -- lint command-registry sync --planning-issue ISSUE
   ```

3. Edit only the affected command rows to advance `owner`,
   `implementation_parity`, `consumer_cutover`, or `python_removal`. Sync keeps
   these fields and existing issue values unchanged. For a newly registered
   command, sync records the supplied roadmap owner as `planning_issue` and
   leaves `migration_issue` absent. Add the latter only when a filed executable
   leaf accepts responsibility for the eventual atomic cutover.
4. Validate the ledger and render the Chief issue progress block:

   ```bash
   cargo run --quiet --locked --package larch-cli -- lint rule command-registry
   cargo run --quiet --locked --package larch-cli -- lint command-registry report
   ```

5. For issue-registry parity audits, build schema-v1 JSON with
   `larch_core::build_command_audit_issue` and
   `render_command_audit_input`, then run:

   ```bash
   cargo run --quiet --locked --package larch-cli -- lint command-registry audit --input INPUT.json
   ```

The caller ledger inventories `skill`, `hook`, `script`, `ci`, `agent`, and
`python-runtime` paths. Python modules that build a command with the shared
`larch.core.repo_roots.larch_entrypoint` resolver are Rust callers because the
resolver returns the verified `scripts/larch.sh` bootstrap. Syntax-aware
inspection recognizes resolver and module aliases while ignoring comments and
unexecuted string literals. The same scanner inventories in-process Python
ownership of corrected issue commands: imports or references to the deleted
execution module select `execution-issues *`, and non-footer behavior in the
retained tracking module selects `tracking-issue *`. Module aliases and
`from` imports cannot hide either caller class. Pure pull-request footer helpers
remain outside that command-equivalence boundary.

The rule fails for missing or duplicate command rows, stale Python target or
machine-stdout metadata, invalid status combinations, caller drift, unknown
caller selectors, incomplete Python retirement evidence, and missing
clean-install coverage. Every command names a roadmap owner in
`planning_issue`; the #7687 chief umbrella is too broad even for that field.
`migration_issue` may be absent while a Python-owned command awaits an
executable cutover leaf, but it must never name a migration umbrella. Completed
commands retain the exact leaf that landed their atomic cutover, and completed
migration state without that leaf fails lint. Every Rust-owned command with a
production caller must
name one unique fixture from `CLEAN_INSTALL_CASES` in
`crates/larch-cli/tests/parity.rs`. The shared matrix starts without
`bin/larch`, validates the local binary version and target through
`scripts/larch.sh`, and reaches the named Rust selector.

The clean-install diagnostic is
`clean-install-coverage-missing <domain> <verb>`. The issue audit reports
`migration-issue-command-drift issue=#N command=<domain> <verb>` when a
canonical issue `COMMAND` row, its plan mention, or the registry's
`migration_issue` disagrees. An absent `migration_issue` therefore cannot
silently satisfy an issue that claims the command. Registry-to-issue checks
apply only to assigned open executable leaves after the audit input enables
rollout.

## Final release and upgrade boundary

`larch lint rule release-python-free` pins the final #7674 command set. It
requires every `release` and `upgrade-larch` row, plus `plugin read-version`,
to keep Rust ownership, complete parity, complete caller cutover, complete
Python removal, and its owning leaf. It also pins each applicable clean-install
fixture.

The rule rejects a restored Python registration or command entrypoint, a
Python or direct-binary caller, and a release implementation that starts `gh`
instead of using the typed GitHub service. `scripts/larch.sh` remains the sole
direct executable owner and the no-binary bootstrap exception from #7670. The
release asset workflow may run its newly built `target/release/larch` because
that workflow constructs and verifies the release executable.

`/release` Step 7 builds the candidate executable, passes it to
`scripts/larch.sh` through the validated `LARCH_BINARY` override, and supplies
the separately validated installed cache root to `upgrade-larch run`. This
keeps executable identity bound to the released working tree without treating
the active old-session root as the executable owner.

## Run-log, report, and rendering boundary

`larch lint rule reporting-python-free` pins the closed #7683 command set:
the 46 rows that still name the umbrella as their roadmap owner plus the nine
rows its leaves migrated for an earlier owner: `run-log lifecycle-*` under
issue 7826, `run-log checkpoint` and `run-log prepare-terminal-snapshot` under
issue 7995, `gantt render` under issue 7680, and `analyze-issues render-chart`
under issue 7682. Every pinned row must stay Rust-owned, or retired for
`run-log flush`,
with complete parity, consumer cutover, and Python removal, and must keep its
exact migration leaf and its retired Python target. The rule rejects a restored
Python registration in `python/larch/cli.py`, a restored module-level Python
entrypoint, and any other ledger row that still names #7683 as its planning
issue. It also rejects a production Python run-log manifest writer, direct use
of the retired manifest mutation helpers, a durable write from the Python
manifest compatibility module, and every production Python progress-state
writer or caller, or timing-ledger writer or caller; production callers must
invoke the Rust `run-log manifest`, `progress`, or `timing` entrypoint.

That last check is what keeps a hand-off honest. #7683 owns no unmigrated
command, so a row that still points at it is either a missed migration or a
hand-off nobody wrote down. The audit in #8093 repointed 37 such rows to the
umbrella that owns their remaining consumers:

| Surface | Rows | Owning issue | Basis |
| --- | ---: | --- | --- |
| `execution-issues append`, `flush`, `flush-safety-net`, `refresh` | 4 | #7682 | Migrated by #8176 and completed by corrective leaf #8347, which removed the retained Python mutation and caller paths. |
| `redact secrets`, `tmpdir-paths`, `scrub-log-secrets`, `scrub-submodule-paths` | 4 | #7681 | Migrated by #8796. Live callers now enter through `scripts/larch.sh`; Python retains only its in-process compatibility library. |
| `render reviewer`, `lane-status`, and `findings-view` | 3 | #7684 | Research and analytical presentation consumers. |
| `render plan-review` | 1 | #7680 | The remaining consumer is the design workflow. |
| `render specialist` | 1 | #7681 | The remaining consumer is implementation code review. |
| `render voter` | 1 | #7686 | Shared design and implementation consumers make this a final-cutover surface. |
| `render scope-anchor` | 1 | #7680 | Both callers are `/design` Step 3 scripts, and all four `scope-anchor` verbs already sit at #7680. |
| `render run-summary` | 1 | #7680 | Recorded in the retained-surface table below as a bounded `/design` payload. |
| `token check-budget`, `compute-pr-line-counts`, `compute-pr-lines` | 3 | #8797 | Rust CLI cutover with in-process callers, Python entrypoint removal, and clean-install coverage. |
| `token claude-source` | 1 | #7684 | Read-only token-source analysis used by review reporting. |
| `token cost`, `token render-cost-line`, `token report` | 3 | #8507 | Rust CLI cutover with caller replacement, Python entrypoint removal, and clean-install coverage. |
| The remaining 6 `measure-*` `token` verbs | 6 | #7684 | The remaining deterministic analytics and report-input scope. |

Both surfaces this umbrella touched are now closed. #8268 settled the plot
question #8088 deferred: `report-tokens analyze` renders its trend chart in
process, so no arbitrary-script process class was added and
`skills/report-tokens/SKILL.md` no longer runs a step 2 child. #8267 deleted the
two modules the audit found orphaned,
`python/larch/report/run_log_commit.py` and
`python/larch/report/run_log_legacy_archive.py`.

This rule proves the closed #7683 command and mutation boundary. It does not
prove that all Python reporting, rendering, analytics, or compatibility code
has disappeared. The bounded surfaces below have other named owners and cannot
be treated as a fallback implementation for any closed command.

Direct `bin/larch` execution stays outside this umbrella's surfaces. The
`larch-runtime-entrypoint` rule already rejects it in `python/larch/**`,
`skills/`, `.claude/skills/`, `agents/`, `hooks/`, and `scripts/*.sh`, and no
tracked file in those roots references the binary.

### Closed #7684 analytics boundary

`larch lint rule analytics-7684-closure` closes the evidence loop for #7684.
It reuses the command-registry closure projection for every #7684 row, the
retained issue-module ownership table, and the canonical GitHub-service and
Git inventory parsers. It fails closed on incomplete phases, missing or
umbrella migration leaves, restored Python registration, entrypoint, caller,
or retained-module ownership, and incomplete inventory evidence. Its
syntax-aware prompt check requires `/fluff-analysis` and `/voter-calibration`
to invoke their `scripts/larch.sh` Rust owners and rejects the retired
standalone Python analyzer paths. The generated plugin projection is validated
separately with `release plugin-runtime --check`.

## Closed #7682 issue-domain boundary

`larch lint rule issue-python-free` is the mechanical closeout for #7682. It
pins the 96 commands migrated by its atomic leaves, including the ten
issue-domain commands whose surviving `/design` callers make #7680 their
roadmap owner. Every pinned row remains Rust-owned with complete implementation
parity, consumer cutover, and Python removal; it also retains the exact
migration leaf and retired Python target. The rule rejects a restored
`python/larch/cli.py` registration, a restored module-level entrypoint, or any
other row left at `planning_issue = 7682`. `command-registry` proves the broader
production-caller cutover, and `larch-runtime-entrypoint` proves that callers
enter the installed runtime only through `scripts/larch.sh`.

The audit also names every boundary this umbrella does not own. The listed
owner is the umbrella that owns the surviving command or library cutover, not a
temporary compatibility alias.
Shared libraries may still serve callers from more than one workflow while
those workflows remain Python-owned; their listed receiving umbrella coordinates
the next cutover and does not create a second implementation.

| Receiving umbrella | Deliberate hand-off |
| --- | --- |
| #7678 | No `python/larch/issue/` command survives here. Vendor launch and lane-rendering surfaces remain in the vendor-orchestration umbrella. |
| #7679 | No pending issue command remains after the #8452 review-boundary audit. |
| #7680 | `oos serialize` and `oos normalize-header` stay in the design workflow. `render run-summary` and the retained issue wire, OOS, title, and mutation payload libraries serve that workflow. The `clarify` verbs and `design clarify` are Rust-owned as of #8587, and `design publish` as of #8591. |
| #7681 | `pr compose-summary` and `tracking post-issue` are Rust-owned after #8789; the token-budget and PR line-count commands after #8797; and `issue governance-gate` and `plan-receipt refresh` after #8799. The former `larch.issue.execution_issues` hand-off ended in #8347. |
| #7683 | `analyze-issues render-chart` is Rust-owned but remains planned by its reporting leaf #8092; report, diagram, and chart rendering do not return to #7682. |
| #7684 | Rejected-finding and merged-change analysis commands, the remaining `measure-*` token analytics, and their analytical issue helpers remain research-owned. |
| #7685 | `issue migration-audit` is Rust-owned by #8392. #8799 removed the adjacent Python governance-gate boundary and its `issue_block` and `open_rows` support; #7685 retains no Python issue-module ownership. |
| #7686 | The final runtime and package retirement sweep owns deletion once no retained consumer remains; it is not an issue-command fallback. |

The rule's retained-module list permits the package initializer and the named
`python/larch/issue/**/*.py` libraries only. Every listed module carries a
non-empty reason and a receiving umbrella. Discovery is recursive, so a new
module or nested package initializer fails until the rule records its distinct
purpose and receiving owner; stale inventory rows fail as the boundary shrinks.

### #7682 terminal completion record

The #8350 audit revalidated the issue-domain boundary on final `main`. This was
not a source-text-only check:

- `issue-python-free` pins all 96 migrated selectors at Rust ownership with
  parity, caller cutover, and Python removal complete. The count includes the
  ten tracking and execution selectors completed by #8346 and #8347.
- `command-registry` validates registrations, exact migration leaves,
  production callers, in-process command equivalents, and clean-install
  fixtures. `larch-runtime-entrypoint` proves those callers enter through the
  verified `scripts/larch.sh` bootstrap.
- The recursive retained-module inventory accounts for 20 Python issue
  modules, plus the structural package initializer. Each module has a
  reason-bearing receiving umbrella; restored tracking or execution behavior,
  alias imports, and nested unowned modules fail the lint.
- `service-ownership` and `issue-mutation-owner` keep the typed GitHub adapter
  and the fail-closed issue mutation owner unique. The shared mutation gate,
  bounded pagination, freshness checks, redaction, and exact read-back remain
  the security contract documented in
  [`workflow-trust-and-mutations.md`](security/workflow-trust-and-mutations.md).
- The parity matrix covers issue reads, writes, dependencies, inputs, wire
  formats, triage, and umbrella commands through a clean-install bootstrap.
  Focused tracking and execution contract tests cover their in-process
  replacements. Issue creation, OOS filing, and combination tests cover
  rollback, interruption, and partial-batch cleanup.
- The OOS operator guidance now names the Rust owner and distinguishes the
  retained #7680 parsing helpers. No migrated OOS command uses those helpers as
  a live implementation or fallback.

The following provenance matrix covers every direct leaf. `R` means #8350
verified the final shipped GitHub surface retrospectively against #7672 and
the #7888 credential supersession; it does not claim those inputs were read
before implementation, and the original closing PR omitted both citations.
`C` means the corrective PR cited both inputs and #8350 reverified the final
surface. `A` is the #8350 closeout itself, which read both inputs and cites them
in its closing PR. `N/A` means the leaf has no production GitHub call.

| Leaf | Shipped surface | Implementation evidence | Provenance |
| --- | --- | --- | --- |
| #8163 | Offline issue fixtures and parity harness | PR #8196 | N/A |
| #8164 | Typed GitHub sub-issue adapter | PR #8205 | R; the leaf body named both inputs |
| #8165 | Issue wire and identity core | PR #8207 | N/A |
| #8166 | Fail-closed issue mutation owner | PR #8206 | R |
| #8167 | Issue query, freshness, and context | PR #8199 | R |
| #8168 | Issue input and candidate allocation | PR #8239 | R |
| #8169 | Issue creation, sentinels, and cleanup | PRs #8242 and #8244 | R |
| #8170 | Dependency and sub-issue commands | PR #8244 title and diff; its stale body said `Fixes #8169`, so GitHub has no closing-PR edge for #8170 | R |
| #8171 | Plan, named, and untrusted blocks | PR #8245 | R |
| #8172 | Triage inspect, probe, and apply | PR #8253 | R |
| #8173 | Umbrella preparation and proposals | PR #8255 | R |
| #8174 | Umbrella mutations and verification | PR #8259 | R |
| #8175 | Tracking-issue lifecycle | PR #8260; corrected by PR #8354 | R, then C |
| #8176 | Execution-issue lifecycle | PR #8262; corrected by PR #8357 | R, then C |
| #8177 | OOS record and disposition core | PR #8263 | N/A |
| #8178 | OOS manifests and disposition gate | PR #8265 | N/A |
| #8179 | OOS filer | PR #8270 | R |
| #8180 | Dependency audit | PR #8279 | R |
| #8181 | Issue combination | PR #8304 | R |
| #8182 | Issue ground-truth and report core | PR #8208 | N/A |
| #8183 | Issue backlog analysis | PR #8315 | R |
| #8184 | Bug-sweep prefetch and ledger | PR #8318 | R |
| #8185 | Bug-sweep runtime and report | PR #8321 | N/A |
| #8186 | Learn-from-bugs preparation | PR #8322 | R |
| #8187 | Learn-from-bugs validation and filing dependencies | PR #8332 | R |
| #8188 | Run-audit scan and mapping | PR #8333 | R |
| #8189 | Run-audit issue titles, nudges, and closure | PR #8336 | R |
| #8190 | Mechanical issue-domain closeout lint | PR #8338 | N/A |
| #8346 | Tracking-issue corrective cutover | PR #8354 | C |
| #8347 | Execution-issue corrective cutover | PR #8357 | C |
| #8348 | OOS ownership documentation correction | PR #8372 | N/A; the PR also cited both inputs |
| #8349 | In-process and nested-module ownership lint | PR #8376 | N/A |
| #8350 | Terminal metadata, graph, and provenance closeout | Closing PR for #8350 | A |

`complete-umbrella` graph reads treat every CLOSED direct leaf as resolved and
exclude it from candidacy, without requiring an exact `[DONE] [LEAF OF N]`
title. Open leaves still need a valid lifecycle title and first-line body.
`verify-child` keeps the strict `[DONE]` assertion for the leaf the run just
shipped. `finish` still requires every direct leaf to be closed before any
parent mutation, but closed-leaf title drift no longer refuses completion.
Issue #8629 also moved `complete-umbrella ship-leaf` to the Rust command tree.
Its standalone state, five-minute CI cadence, merge handling, and post-merge
verification remain independent of `/implement`; the Python owner and callers
were removed atomically.

## Closed #7679 review boundary

`larch lint rule review-python-free` pins the 79 command selectors migrated by
Issue #7679's executable leaves. That set includes the three calibration-replay
commands migrated by #8439 under #7679, and every row must retain its exact
migration leaf, Rust ownership, complete parity, complete consumer cutover, and
complete Python removal. The rule also rejects any remaining Python source in
the retired review package and any live Python, skill, hook, or script
reference to that package. The shared command-registry closure scanner
independently rejects a restored Python registration, implementation
entrypoint, or production caller for the 79 final rows planned by #7679.

The audit reassigned 42 pending rows according to their live consumers:

- #7680 owns design assessment reads and persistence, plan-review identity and
  settlement, OOS serialization, and the plan-review prompt renderer.
- #7681 owns implementation assessments, review-and-fix identity, and the code
  specialist renderer.
- #7684 owns research renderers, findings presentation, and `token
  claude-source`.
- #7686 owns the shared voter renderer whose consumers span workflows.

The package deletion does not pretend that compatibility readers are commands.
`larch.core.findings`, `larch.calibration.voting`,
`larch.calibration.voter_calibration`, and
`larch.rendering.findings_ledger` preserve their surviving in-process contracts
under the receiving umbrellas. None is registered as a migrated review command.

## State transitions

Keep `owner = "python"` and `consumer_cutover = "pending"` while Python owns
production behavior. A parity implementation may set
`implementation_parity = "complete"` without changing ownership.

Cut over one command atomically: complete parity, update all production callers,
remove the Python registry row and module-level entrypoint, remove every
production import and call of that symbol, set `owner = "rust"`, and mark both
completion fields `complete`. There is no Rust-owned pending-removal state.
`python_module` and `python_function` remain in the ledger after deletion so
the rule can continue proving that the retired entrypoint is absent.

A Rust owner becomes valid only in the PR that completes all of those changes.
Adapter parity alone does not transfer command ownership. For local Git, the
`git-ownership` rule also pins the complete #7675 command set and compares
[`docs/git-operation-inventory.md`](git-operation-inventory.md) with live
production surfaces. It calls this registry's syntax-aware Python retirement
proof for those commands, so restored definitions, imports, references, and
calls fail both ownership surfaces. It separately rejects the retired
`push rebase` Python state-machine symbols. Commands assigned to a later domain
stay Python-owned until that domain's issue performs the same atomic
transition.

The atomic-owner diagnostic is
`non-atomic-rust-owner <domain> <verb>: python removal is not complete`.
Retirement evidence uses `python-entrypoint-still-present` for a remaining
registration or module-level definition, `python-entrypoint-still-imported`
for an import or attribute reference, and `python-entrypoint-still-called` for
a direct or qualified call. Each diagnostic includes the selector and path.

For retirement, remove every caller and Python registry entry, set
`owner = "retired"`, `implementation_parity = "not-applicable"`, and mark both
completion fields `complete`.

Caller selectors may use `domain *` only when a production wrapper chooses the
verb dynamically. Such a selector conservatively blocks Rust ownership for
every command in that domain until the wrapper moves or becomes exact.

## Retained Python surfaces outside the closed #7683 boundary

This inventory covers the Python readers, renderers, and compatibility facades
that remain adjacent to the closed #7683 runtime. A listed Python surface has a
bounded role. The final Rust command owner or the umbrella that owns its later
cutover is named in the last column.

| Python surface | Bounded purpose | Owner or follow-up |
| --- | --- | --- |
| `larch.report.run_logs`, `run_log_archive`, and `run_lifecycle` | Typed facades that invoke `scripts/larch.sh` and translate the established Python error contract for existing callers. | Rust `run-log` entry, archive, materialization, and lifecycle commands: #8073, #8079, and #8080. |
| Reporting methods in `larch.core.rust_runtime` | Typed ship-facing facade for Rust `run-log refresh`, `final-report write`, and `progress` commands. It preserves existing Python result and error contracts but stages no reporting artifact itself. | Rust flush (#8078), final report (#8090), and progress (#8290) command owners. |
| `larch.report.run_log_manifest` | Parses existing manifests and reads state only. It has no durable-write API. | Rust `run-log manifest`, completed in #8289. |
| `larch.report.progress_file` and `timing` | Resolve a persisted run identity or an existing ledger path without changing either file. | Rust `progress` (#8290) and `timing` (#8291). |
| `larch.report.run_log_batch` | Parity mirror for bounded local compatibility callers, the historical migration reader, and the Rust test double. It is not a durable run-log writer. | `larch_core::run_log::batch` and Rust `run-log write` / `append`, completed in #8073. |
| `larch.report.run_log_corpus`, `run_log_publish`, `object_store`, and `storage_config` | Analyzer-side corpus reads plus bounded configuration, path, lock, and error support. The legacy `object_store` adapter has only compatibility/test callers; none is a production archive, sync, lifecycle, or storage-preflight command owner. | Rust archive, publication, sync, and storage-preflight boundary: #8079 and #8080; their analytics callers are #7684. |
| `larch.report.analysis_state`, `markdown_block`, and `run_log_tolerance` | Local analyzer state, bounded Markdown fragments, and read-only tolerance predicates. They have no #7683 command entrypoint. | Their analytics and audit callers belong to #7684 and #7682. |
| `larch.report.exec_issue_detail`, `review_phase_detail`, and `design_diagram_log` | Parser and renderer helpers for issue warnings, review-phase rows, and design-diagram diagnostics. They are not durable run-log writers. | Their analytical, design, and issue callers belong to #7684, #7680, and #7682. |
| `larch.report.report_tokens_models`, `report_tokens_scan`, `report_tokens_cost`, and `tokens` | Input, pricing, and state helpers for bounded compatibility consumers and remaining Python token analytics. The seven token measurements are Rust-owned after #8508, #8507 removed their `token report`, `token cost`, and `token render-cost-line` entrypoints, and #8797 removed the budget and PR line-count entrypoints. They do not implement those commands, `report-tokens analyze`, or a final-report writer. | #7684 owns the remaining token analytics. |
| `larch.git.pr_body.render_run_summary` and `larch.design.design_summary` | The `render run-summary` compatibility payload for `/design`. It shares the marker grammar but is not an `/implement` final-report fallback. | #7680 owns `render run-summary` and its `/design` caller. |
| `architectural-assessment final-report-sections` | Read-only architectural-assessment payload consumed by Rust `final-report write`. | #7681. |
| `larch.rendering.rendering` | Prompt and diagram payload renderers outside the closed commands. | Its exact registry rows belong to #7678, #7680, #7681, #7684, or #7686; committed-artifact generation is Rust-owned by #8100. |

Issue 8086 ports the scanning half of the token pipeline: ledger and transcript
discovery, per-model usage extraction, cache-read and cache-write accounting,
vendor usage records, and the run-record scan over
`larch_core::report::RunLogCorpus`. It adds no command, and it keeps model ids
and usage fields exact: an unrecognized model keeps its recorded spelling, and
a defaulted, normalized, unpinned, or unconsumed field is reported through
`TokenObservations` instead of being dropped. `larch_core::vendor_model` is the
single Rust owner of the `claude_sub` model default and the long-context ledger
alias, which `larch_adapters::phase_detail` now reuses. Pricing stays with issue
8087, and `report-tokens analyze` switches in issue 8088.

One extraction contract point changed deliberately, recorded here as well as at
`crates/larch-core/src/report/token_scan.rs`. Python's `_epoch` resolves a
timestamp with no UTC designator through `datetime.fromisoformat(...).timestamp()`,
which reads it in the process's local zone; the port reads such a timestamp as
UTC so extraction is deterministic across machines. Every timestamp larch writes
carries an explicit `Z`, so no recorded run changes.

Issue 8087 ports the pricing half: the per-model rate table, per-tier cache
rates, environment rate overrides, the bucket-to-counts mapping, Python's
rounding, and per-run cost aggregation. It adds no command either.
`larch_core::report::RATE_TABLE` is the single Rust owner of every token rate,
and `larch_core::vendor_model` gains the GLM main-agent id and its long-context
alias. A model priced by another model's rate row, including a display bucket
that folds one model onto another, is recorded as
`TokenObservationKind::UnpricedModel` rather than passing silently. The #8507
Rust CLI owns `token cost` and `token render-cost-line`; neither is the rate
authority for `report-tokens analyze` or `final-report`.

Issue 8088 moved `report-tokens analyze` to Rust and deleted
`larch.report.report_tokens_cli`, `report_tokens_render`, `report_tokens_plot`,
and `report_tokens_issue`. The command owns corpus synchronization through
`synchronized_corpus_root`, repository resolution through the shared ambient
resolver, the scan and pricing passes, the report render, the temporary-root
lifecycle, and the analysis-issue post. Rendering is pure, and the fixtures
under `crates/larch-core/tests/data/token_report` were recorded from the Python
owner over the same records.

Two boundaries moved deliberately. The issue post now runs through
`IssueMutationOwner`, so it inherits the live-mutation authorization gate and
outbound redaction every other larch issue write uses; the retired Python owner
shelled out to `gh issue create` with no gate at all, and `/report-tokens`
authorizes its own post with `--operator-invoked` because it is a direct
operator-requested command. And the matplotlib plot child moved from the CLI to
step 2 of `skills/report-tokens/SKILL.md`, because larch's process policy has no
arbitrary-script class and adding one for a chart renderer belonged to its own
reviewed leaf rather than to a renderer port.

Issue 8268 settled that deferred decision the other way and deleted the child.
`larch_core::report::cost_plot` renders the trend chart, over the small RGB
canvas and PNG encoder in `larch_core::report::raster`, and
`report-tokens analyze` writes the PNG beside its NDJSON cache. No
arbitrary-script process class was added: the program principle is to spawn only
true external products, a chart renderer is not one, and the alternative would
have widened the process policy permanently for one image. The deleted
`skills/report-tokens/scripts/plot-cost-over-time.py`, its contract file, and the
`plot-input.json` handoff go with it, so `/report-tokens` is a single command
again and the plugin's last matplotlib requirement is gone.

Three contract points changed with the renderer. Stdout advertises
`Plots written to:` with the PNG paths where it advertised
`Plot input written to:` with the JSON path. The chart title separates its series
label with a colon rather than matplotlib's em dash, which larch's readability
style bans from user-facing output. And date labels stay horizontal, thinned to
whatever fits the axis, rather than rotating every label 45 degrees.

`report_tokens_cost`, `report_tokens_models`, `report_tokens_scan`, and
`analysis_state` remain Python helpers for the #7680 compatibility payload and
the remaining #7684 analytics. Issue #8507 moved `token report`, `token cost`,
and `token render-cost-line` to Rust. Issue 8090 removed
`larch.report.final_report` from their consumer set by pricing the terminal
report through `larch_core::report::token_cost` directly. They are not a Python
implementation of `/report-tokens` or `final-report`.

Issue 8090 moved `final-report write` and `final-report step18b` to Rust and
deleted `larch.report.final_report` plus the `larch.git.pr_body` final-report
compatibility wrappers. `larch_core::report::run_summary` is the single Rust
owner of the `## /<skill> run <id>: <outcome>` block, and
`larch_core::report::final_report` owns the derived tally, duration, difficulty,
dynamic-archetype, out-of-scope, outcome-backstop, stalled-summary, and
token-pricing-argument derivations. The command layer reuses
`larch_adapters::phase_detail` for the review-phase prefix,
`larch_core::report::exec_issue_detail` for the issue-detail prefix,
`larch_adapters::stall_recovery` for the normalized outcome, and
`larch_adapters::run_log_manifest` for the terminal manifest stamp.

PR line counts kept their Python owner until #8797 moved the bounded GitHub read,
aggregation, and final-report consumer into Rust. Architectural assessment
sections (`architectural-assessment final-report-sections`) remain composed
through their separately owned in-process Rust path. The plan-coverage line
was the third until #8612 completed the atomic cutover of
`implement scope-disposition`; `final-report write` now reads it in process from
`implement_scope_disposition_commands::plan_coverage_report_line`, so a returned
error is a coverage-integrity failure rather than an unreachable helper.
`token claude-source` was a #7684
fallback reader for a missing manifest until #8557 completed its atomic cutover;
like `tracking-issue upsert-summary` after the corrected atomic cutover in #8346,
it is now Rust-owned and called in process by `final-report write`. Python
workflow consumers use typed `rust_runtime` wrappers that enter through
`scripts/larch.sh`. Neither path adds a second implementation: the logic has
exactly one Rust home.

One contract point changed deliberately. A `PR_URL` absent from
`ship-pr-state.sh` now falls through to `finalize-state.sh` before the report
prints `N/A`, matching how the same command already resolves `PR_NUMBER`. The
retired Python owner wrote the fallback but could never reach it: its first read
defaulted to the truthy string `N/A`, which short-circuited the `or`, so a run
that recorded its PR during finalization printed `N/A` for a PR that existed.

Issue 8091 moved `run-log render-session-transcript` to Rust and deleted
`larch.rendering.render_session_transcript`.
`larch_core::report::session_transcript` is the single Rust owner of the schema-v3
chat view: record parsing, turn and block rendering, tool-result classification,
and reference-read normalization. `run-log checkpoint` and `run-log refresh` now
render in process instead of through the `python_verb` seam, so transcript
capture no longer spawns a child. The prompt renderers in
`larch.rendering.rendering` keep their separately registered Python owners
under #7678, #7680, #7681, #7684, and #7686. Issue #8100 moved the committed-artifact
generator registry to Rust.

Three contract points changed deliberately, each named by the leaf's acceptance.
Rendered strings escape `U+0085`, `U+2028`, and `U+2029`, which JSON leaves bare
but Python's `str.splitlines` treats as record breaks, so transcript content can
no longer forge a header or turn line; the recorded Python output for the hostile
fixture does split into forged lines, and the parity test pins both halves. An
input past 512 MiB is refused rather than rendered in part, and a record past
8 MiB is skipped and counted. Records with invalid UTF-8 are still decoded with
replacement, but the count now reaches stderr and the capture's execution-issue
warnings instead of vanishing.

`larch.report.tokens` kept the one helper it imported from the deleted module,
`strip_plugin_cache_read_suffix`, as its own function. That is a Python-side
move, not a second owner of anything Rust holds: the Rust renderer needs the same
rule and states it once in `session_transcript`.

Issue 8092 moved `gantt render` and `analyze-issues render-chart` to Rust and
deleted `larch.rendering.gantt` with both Python registrations.
`larch_core::report::gantt` owns the ASCII Gantt renderer and its rows-TSV
grammar, and `larch_core::report::growth_chart` owns the cumulative-growth
chart. The same leaf finished the port of `larch.report.design_diagram_log` into
`larch_core::report::diagram_log`, which now holds the bounded warning bullet and
the bounded failure sidecar alongside the capture sanitizers that
`larch_core::run_log::diagram_capture` held before.

Three contract points changed deliberately, each named by the leaf's acceptance.
`--width` above 10000 is refused with a bounded usage error, because the Python
owner had no bound and died with `MemoryError`; no chart approaches that width.
A window bound or width outside `i64` is refused as an invalid int value rather
than carried as an arbitrary-precision Python integer. `analyze-issues
render-chart` reports one bounded `ERROR:` line at exit 1 where the Python owner
exited on an uncaught traceback, for an unreadable path, non-UTF-8 bytes, or a
non-integer bucket value.

`larch.rendering.render_chart` keeps only its pure `render_chart` function.
Issue #8183 moved `analyze-issues {fetch,run,analyze}` to Rust and deleted its
Python command owner; #8672 later retired the `larch.issue._ground_truth` /
`_report` analytics modules entirely. The Rust analyzer renders its growth
section through `larch_core::report::growth_chart`; the residual Python helper
is not an `analyze-issues` command surface. `larch.report.design_diagram_log`
likewise stays until #7680 moves `design publish` and #7681 moves the `pr`
verbs, the two in-process callers of its bounded logging.

Issue 8089 ports parse/load/render and Markdown block upsert only. Claude assessment
subprocess launching stays injectable for later consumer cutover; Python
`assess_issue_details` remains until those consumers move.

Issue 8177 ports the OOS record, its priority classification, the disposition
counters and state, and the file-conflict and create-ordering model. It adds no
command. `larch_core::issue` becomes the single Rust owner of the canonical
`### OOS_<n>:` / `### FINDING_<n>:` block, so #8178 and #8179 consume it rather
than defining a second record model.

Two commands stay Python-owned deliberately. `oos serialize` and
`oos normalize-header` serve the remaining design OOS workflow, so #8452 hands
them to #7680. The Rust library parity they need is already present. Their
compatibility `finding-heading` and `level-three-heading` block boundaries now
live in `larch.core.findings` until final consumer cutover.

`larch_core::text::file_reference_alternatives` is the single owner of the
reviewer file-reference grammar ported from `larch.calibration.voting`. The
ground-truth evidence reader and the OOS conflict model both compose it, and
they differ only in whether extension matching folds case.

Issue 8178 moves the five OOS batch verbs to Rust and reconciles the
rejected-marker reader #8177 left split. The single owner now folds case in the
outer presence check, because the per-line scan below it always did and a check
that disagrees with its own scan reports zero for a body it can read. It ends
the rejected section on any line opening with exactly two number signs, because
reading past a bare second-level heading with no space would count an accepted
item as rejected, which is the one direction that lets an undisposed run look
disposed. Line-ending translation is chosen per reader: the counters and the cap
read the way `Path.read_text` did, and `oos file-conflict-deps` reads bytes the
way `larch.io.read_text` did, because the batch grammar it feeds is byte
oriented.

Issue 8179 moves `oos file` behind `scripts/larch.sh` into
`crates/larch-cli/src/oos_file_commands.rs`. The driver composes the #8178 cap,
conflict, and disposition owners in process, and creates and wires issues
through the typed Rust mutation path without invoking `/issue`.
`larch_core::issue::oos_filing` owns stable filing identities and durable
records. The behavioral authority is `oos_file_commands::tests` plus the shared
core OOS tests. The former `larch.issue.oos_filer` command owner is gone;
retained #7680 `larch.issue.file_oos` keeps only its distinct in-process
parsing, identity, workflow-routing, and post-checkpoint responsibilities.
Issue #8622 retired `larch.implement.dispatch_ship`; #8672 retired
`larch.issue._oos`.

Issue 8165 ports the named-block grammar, the `larch:plan` marker, title
eligibility and matching, the open-issue row model, and the untrusted content
envelope. Issue 8171 then moves every command over that core — the three
`plan-block` verbs, `named-block write`, `plan scope-paths`, the three `issue`
title verbs, and the four `untrusted` verbs — and adds `larch_core::plan_scope`
as the single owner of the `## Files to modify/create` grammar that
`dirty-tree scope-check` and `plan scope-paths` both read. Three surfaces in
`larch.issue.issue_wire` stay Python-owned because in-process callers still
consume them: the canonical owner block, the implementation-lease marker, and
`validate_issue_plan` plus the `extract_scope_paths` reader over
`larch.design.plan_grammar`, which the design umbrella owns. `larch_core::report::markdown_block` remains the
Markdown block owner, and `larch_core::balanced_fence_line_indices` plus
`larch_core::split_lines_keep_ends` are the shared owners the `plan_grammar` port
reuses instead of creating a second fence scanner.
