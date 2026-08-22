# Migration Governance Audit

`scripts/larch.sh issue migration-audit` runs the aggregate migration audit.
It reads GitHub and repository evidence, invokes the canonical repository lint
owners, and emits one stable report. It never edits an issue, pull request,
branch, or repository file.

## Usage

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" issue migration-audit \
  --repo owner/name \
  --chief 7687
```

The command enters through the verified Rust bootstrap. It gathers evidence
through the typed GitHub, Git, and filesystem adapters and runs the canonical
repository lint owners in process. It fails with exit `2` when required GitHub
or repository evidence is unavailable. Its exhaustive historical issue scan is
separately bounded to 100 pages and 10,000 raw REST rows, with a 256 KiB
per-field cap for historical plan bodies. Each page read, including its bounded
retry sequence, keeps the ordinary 60-second deadline; the complete snapshot
has a fixed three-minute aggregate deadline. A larger corpus, field, or
deadline overrun refuses rather than silently narrowing the report. No
production caller invokes a `target/` executable directly or falls back to
Python behavior; the workflow supplies its freshly built path only to the
bootstrap, which verifies it before execution.

The active GitHub CLI identity needs read access to issues, issue dependencies,
and pull requests for `owner/name`. An explicit output file also needs a
non-symlinked writable parent directory. No GitHub write permission is needed.

By default, compact JSON goes to stdout and a count table goes to stderr. Use
`--output FILE` to write JSON with an atomic, no-follow write. Use
`--table-output stderr|stdout|none` to select the table channel. Table output
on stdout requires `--output FILE`, so stdout never mixes JSON and prose.

## Report schema

Schema version `2` has these top-level fields:

- `schema_version`: the integer `2`
- `repository`: the validated `owner/name` input
- `chief_issue`: the positive issue number passed with `--chief`
- `snapshot_timestamp`: the UTC time captured before evidence collection
- `counts`: the fixed count object below
- `findings`: sorted bounded evidence rows
- `issues`: sorted per-issue plan and reason rows

`counts` always contains these keys:

- `executable_leaves`
- `valid_plans`
- `historical_managed_leaves`
- `historical_missing_plan_evidence`
- `historical_unverified_rust_line_budgets`
- `historical_recorded_rust_line_budget_deviations`
- `missing_or_stale_blockers`
- `active_owner_conflicts`
- `stale_implementation_leases`
- `registry_state_violations`
- `missing_caller_surfaces`
- `python_retirement_violations`
- `clean_install_coverage_gaps`
- `production_runtime_escape_hatches`

Each finding contains `category`, nullable `issue`, and `reason`. A stale lease
also contains `cleanup_command`. Each issue row contains `number`, nullable
`plan_valid`, and `finding_reasons`. The report excludes issue titles, bodies,
comments, credentials, and arbitrary GitHub error text.

Historical managed leaves are closed direct umbrella leaves that name the Chief
umbrella, or whose durable parent umbrella declares that Chief relationship.
Their four counts and per-issue reasons are report-only: they do not become gate
findings or make the audit fail. `historical_unverified_rust_line_budgets` means
no durable matching budget record is available; it does not claim that a
historical PR exceeded the limit. `historical_recorded_rust_line_budget_deviations`
counts only explicit durable records. The audit never writes retrospective plans,
approvals, or deviations.

Reasons come from the existing migration owners. They include plan defects,
blocker and receipt tokens, owner-admission tokens, stale-lease tokens, and
canonical `larch lint` diagnostics. The Rust command runs these canonical lint
owners in process:

- `rule command-registry`
- `command-registry audit`
- `rule production-cargo-run`

The command-registry results cover registry state, caller surfaces, Python
retirement, and clean-install coverage. The production rule covers runtime
Cargo and `target/` escape hatches.

### Reason tokens

Plan findings use these exact tokens:

- `missing-plan-block`
- `multiple-plan-blocks`
- `missing-firm-scope`
- `missing-ordered-implementation`
- `missing-acceptance`
- `missing-closed-decisions`
- `missing-breaking-migration`
- `missing-diff-lines`
- `empty-plan-glob`
- `missing-updated-plan-path`
- `existing-new-plan-path`
- `unsafe-plan-path`

Historical report-only reasons use `historical-plan-evidence-missing
defects=TOKEN[,TOKEN]` and `historical-rust-line-budget-unverified`, optionally
with `defects=TOKEN` when a durable deviation section is malformed.

Blocker and receipt findings use `missing-native-blocker-edge issue=#N`,
`undocumented-native-blocker-edge issue=#N`,
`closed-blocker-edge-retained issue=#N`, `stale-plan-body`,
`stale-plan-base-scope`, `stale-blocker-snapshot`, and
`stale-owner-snapshot`, plus `plan-base-scope-unavailable` when live scope
evidence cannot be read.

A valid plan without `larch:plan-receipt` is not an audit defect. Receipt
scope drift remains visible to audit; `/implement` may refresh it only at
Preflight after an independent bounded semantic-materiality check. Malformed
receipts, stale plan bodies, snapshots, and unavailable base-scope evidence
remain fail-closed.

`scripts/larch.sh plan-receipt refresh` accepts only the exact Preflight plan,
prior receipt base, and current target SHA. It rejects a moving base or any
changed plan, receipt, blocker, or owner input before mutation. A successful
read-back replaces Preflight's issue snapshot and produces one bounded,
JSON-quoted path-only drift record for Step 0 to append once under `Warnings`.

Owner and lease findings use `missing-owner-block`,
`owner-block-invalid defect=TOKEN`,
`reuse-source-unavailable owner=KEY issue=#N`,
`reuse-owner-snapshot-invalid owner=KEY issue=#N`,
`reuse-missing-native-blocker owner=KEY issue=#N`,
`active-owner-conflict owner=KEY issue=#N`, and
`stale-implementation-lease issue=#N age_hours=H`.

Repository findings preserve the exact canonical `larch lint` line. Stable
families include `migration-issue-command-drift`, `non-atomic-rust-owner`,
`production caller`, `ledger caller`, `python-entrypoint-still-present`,
`python-entrypoint-still-imported`, `python-entrypoint-still-called`, and
`clean-install-coverage-missing`. Production-runtime lines retain the canonical
repository-relative path, line number, and rule message.

## Exit codes

- `0`: the audit completed with no findings
- `1`: the audit completed and reported at least one finding
- `2`: arguments, required evidence, redaction, or a tool invocation failed

## Snapshot and mutation boundary

The command captures open and closed issues, referenced issues, native
dependency edges for executable leaves, open pull request branches, the Git
commit, and tracked paths before it builds the report. Every issue check uses
that immutable snapshot. The command rejects a Git commit change during the
run.

GitHub transport uses read helpers only. The aggregate has no issue-mutation
owner and no write fallback. Its temporary command-audit input contains only
typed issue state and validated registry selectors. It rejects malformed,
truncated, or unavailable evidence instead of treating it as empty.

The stale-lease finding prints the exact operator command already owned by the
tracking-issue lifecycle. The audit does not run that command.

### Rust admission core boundary

`larch-core` provides the typed, effect-free migration-governance partition for
blocker parity, receipt freshness, owner admission, and gate formatting. Its
callers supply immutable issue, dependency, pull-request, and tree snapshots;
the core has no Git, GitHub, network, filesystem, process, or mutation owner.

The Rust `issue migration-audit` adapter owns aggregate evidence collection.
The Rust `issue governance-gate` and `plan-receipt refresh` adapter owns the
issue #8799 workflow cutover, bounded live evidence reads, and the refresh
mutation.
Command adapters validate data at transport boundaries before passing
immutable snapshots to the core.

`larch-core::migration_audit` is the report-only companion core. It accepts
already-collected issue, dependency, plan, lease, registry, and repository-rule
evidence; reuses the admission core above; and deterministically renders the
existing report schema. It owns no collection, command cutover, workflow,
GitHub, Git, network, filesystem, process, or issue mutation behavior.

## Workflow handoff

`.github/workflows/migration-governance.yaml` runs every day at 07:17 UTC and
supports `workflow_dispatch`. It checks out the audited commit, loads the
pinned Rust toolchain, builds the `larch-cli` package from the lockfile, and
verifies the `larch` binary. It creates the repository's private GitHub CLI
configuration for the typed client, then selects that binary with
`LARCH_BINARY` and runs through the verified bootstrap:

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh" issue migration-audit \
  --repo character-ai/larch \
  --chief 7687 \
  --output "$RUNNER_TEMP/migration-governance.json" \
  --table-output stderr
```

Each run uploads `migration-governance.json` for 30 days when the file exists.
This includes clean and finding reports. An audit failure also uploads a report
if the command produced one before failing. Exit `0` passes the workflow. Exit
`1` publishes the finding report and then fails the workflow. Exit `2`, or an
unexpected exit, fails the workflow as an unavailable audit.

The aggregate's count-table renderer supplies the bounded Chief summary. The
workflow passes that file to `tracking-issue upsert-summary`, which redacts
secrets and temporary paths before publication. The comment starts with the
exact marker `<!-- larch:migration-governance v1 chief=7687 -->`. A missing
marker creates the comment. One matching marker updates it. Duplicate markers
fail closed without another mutation.

The workflow has repository-level `contents: read` and `issues: write` only.
Its only issue mutation is the marker-keyed comment upsert on #7687. It does not
edit titles, bodies, labels, blockers, registries, owner rows, leases, pull
requests, branches, or repository content. Concurrency cancels a stale run and
allows only one run in the group, so comment writes do not overlap.

To recover from an unavailable audit, artifact failure, or comment-upsert
failure, correct the reported cause and dispatch the workflow again. Do not
repair findings from the workflow. Resolve them through their owning migration
surface, then dispatch a fresh audit.
