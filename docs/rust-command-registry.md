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
   `migration_governance.build_command_audit_issue` and
   `render_command_audit_input`, then run:

   ```bash
   cargo run --quiet --locked --package larch-cli -- lint command-registry audit --input INPUT.json
   ```

The caller ledger inventories `skill`, `hook`, `script`, `ci`, `agent`, and
`python-runtime` paths. Python modules that build a command with the shared
`larch.core.repo_roots.larch_entrypoint` resolver are Rust callers because the
resolver returns the verified `scripts/larch.sh` bootstrap. Syntax-aware
inspection recognizes resolver and module aliases while ignoring comments and
unexecuted string literals.

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

## Library parity pending consumers

Some leaves land Rust library parity without a command cutover. Until the last
Python consumer moves, the Python module remains the production owner.

| Library (Rust module) | Planning leaf | Pending Python consumers | Consumer cutover leaves |
| --- | --- | --- | --- |
| `larch.report.markdown_block` (`larch_core::report`) | #8089 | `larch.report.tokens`, `larch.report.timing` | #8088 (`report-tokens`), #8083 (`timing`) |
| `larch.report.exec_issue_detail` (`larch_core::report`) | #8089 | `larch.report.final_report`, `larch.design.design_summary`, `larch.issue.execution_issues`, `larch.report.run_log_manifest`, `larch.core.architectural_guidelines` | #8090 (`final-report`), #7682 (issue surfaces), later run-log leaves |
| `larch.report.run_log_batch` (registry/read subset; `larch_core::report`) | #8075 | `larch.report.run_logs`, `larch.report.run_log_manifest`, `larch.report.run_log_commit`, `larch.report.run_log_archive`, `larch.report.run_log_publish`, `larch.report.run_lifecycle`, and their producer helpers | #8073–#8080 and later report cutovers |
| `larch.report.run_log_corpus` (`larch_core::report`) | #8075 | `larch.report.report_tokens_scan`, `larch.report.tokens`, `larch.issue.analyze_issues`, `larch.issue._ground_truth`, `larch.issue.audit_runs`, `larch.issue.rejected_analysis`, `larch.issue._oos`, `larch.issue.file_oos`, `larch.review._voting_calibration`, `larch.implement.checks_run_relevant` | #7684, #8086, #8088, and later report/analytics cutovers |
| `larch.report.report_tokens_scan`, `larch.report.report_tokens_models`, and the extraction subset of `larch.report.tokens` (`larch_core::report` token scan) | #8086 | `larch.report.report_tokens_scan`, `larch.report.report_tokens_models`, `larch.report.tokens`, `larch.report.report_tokens_cost` | #8090 (`final-report`), #7682 (issue surfaces), later `token` cutovers |
| `larch.report.report_tokens_cost` and the pricing subset of `larch.report.tokens` (`larch_core::report` token cost) | #8087 | `larch.report.tokens`, `larch.git.pr_body`, `larch.report.final_report`, `larch.design.design_summary`, `larch.calibration.difficulty_calibration`, `larch.issue.analyze_bugs` | #8090 (`final-report`), #7682 (`pr create`), later `token cost` and `token render-cost-line` cutovers |
| `larch.issue.issue_blocks`, `larch.issue.title_match`, and the wire subset of `larch.issue.issue_wire` and `larch.issue.open_rows` (`larch_core::issue`) | #8165 | `larch.issue.issue_blocks`, `larch.issue.title_match`, `larch.issue.open_rows`, `larch.issue.combine_issues`, `larch.issue.deps_audit`, `larch.issue.tracking_issue` | #8175 (tracking-issue titles), #8180 (`deps`), #8181 (`combine-issues`) |
| `larch.issue.issue_wire.extract_scope_paths` (`larch_core::plan_scope`) | #8171 | `larch.design.decompose`, `larch.implement.dispatch_step2`, `larch.implement.scope_disposition` | #7680 (`/design` decompose), #7681 (`/implement` dispatch and scope disposition) |
| `larch.issue.oos`, `larch.issue.oos_priority`, `larch.issue.oos_disposition`, and the conflict and create-ordering subsets of `larch.issue.file_oos` and `larch.issue.oos_filer` (`larch_core::issue` OOS core) | #8177 | `larch.issue.oos`, `larch.issue.oos_priority`, `larch.issue.oos_disposition`, `larch.issue.file_oos`, `larch.issue.oos_filer`, `larch.issue._oos`, `larch.design.design_oos`, `larch.issue.audit_runs` | #8178 (`oos materialize-manifest`, `oos issue-cap`, `oos file-conflict-deps`, `oos disposition-gate`, `oos disposition-checkpoint`), #8179 (`oos file`), #7681 (`oos serialize`, `oos normalize-header`, and `larch.review.review_types`), #8188 (run audit counters) |
| `larch_core::vendor::waterfall` | #8110 | `larch.git.rebase`, `larch.implement.ci_monitor`, and compatibility-only `larch.agents._claude_runner` helpers | Later CI and waterfall cutovers |

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

Issue 8087 ports the pricing half: the per-model rate table, per-tier cache
rates, environment rate overrides, the bucket-to-counts mapping, Python's
rounding, and per-run cost aggregation. It adds no command either.
`larch_core::report::RATE_TABLE` is the single Rust owner of every token rate,
and `larch_core::vendor_model` gains the GLM main-agent id and its long-context
alias. A model priced by another model's rate row, including a display bucket
that folds one model onto another, is recorded as
`TokenObservationKind::UnpricedModel` rather than passing silently. Python keeps
`token cost` and `token render-cost-line` until a later cutover leaf moves them.

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
operator-requested command. And the matplotlib plot child now runs from step 2
of `skills/report-tokens/SKILL.md` against the `plot-input.json` the CLI writes,
rather than from the CLI: larch's process policy has no arbitrary-script class,
and adding one for a chart renderer is a security-relevant change that belongs
to its own reviewed leaf, not to a renderer port.

`report_tokens_cost`, `report_tokens_models`, `report_tokens_scan`, and
`analysis_state` stay Python-owned. They serve consumers outside
`/report-tokens` whose cutovers belong to #8090 and #7682, so `token cost` and
`token render-cost-line` stay Python-owned with them.

Issue 8089 ports parse/load/render and Markdown block upsert only. Claude assessment
subprocess launching stays injectable for later consumer cutover; Python
`assess_issue_details` remains until those consumers move.

Issue 8177 ports the OOS record, its priority classification, the disposition
counters and state, and the file-conflict and create-ordering model. It adds no
command. `larch_core::issue` becomes the single Rust owner of the canonical
`### OOS_<n>:` / `### FINDING_<n>:` block, so #8178 and #8179 consume it rather
than defining a second record model.

Two commands stay Python-owned deliberately. `oos serialize` and
`oos normalize-header` are review-pipeline entry points whose remaining Python
callers live behind `larch.review`, so #7681 migrates them together with
`larch.review.review_types`; the Rust library parity they need is already here.
The review pipeline's `finding-heading` and `level-three-heading` block
boundaries stay with `larch.review.review_types` for the same reason.

`larch_core::text::file_reference_alternatives` is the single owner of the
reviewer file-reference grammar ported from `larch.review.voting`. The
ground-truth evidence reader and the OOS conflict model both compose it, and
they differ only in whether extension matching folds case.

One reader difference is load bearing and is not reconciled here.
`larch.issue.oos_disposition` and `larch.issue.file_oos` count rejected OOS
markers with slightly different section-end and case rules, and
`larch.io.read_text` does not translate line endings where `Path.read_text`
does. `larch_core` ports the `oos_disposition` spelling and exposes
`larch_core::text::universal_newlines`, so #8178 chooses each reader's
translation explicitly instead of inheriting one by accident.

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
