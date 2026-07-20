# Migration Governance Audit

`python3 python/cli.py issue migration-audit` runs the aggregate migration audit.
It reads GitHub and repository evidence, invokes the canonical repository lint
owners, and emits one stable report. It never edits an issue, pull request,
branch, or repository file.

## Usage

```bash
python3 python/cli.py issue migration-audit \
  --repo owner/name \
  --chief 7687
```

The command requires the repository's `larch-lint` executable on `PATH`. It
fails with exit `2` when the executable or required GitHub or repository
evidence is unavailable. Production Python does not build the executable or
invoke Cargo or a `target/` path.

The active GitHub CLI identity needs read access to issues, issue dependencies,
and pull requests for `owner/name`. An explicit output file also needs a
non-symlinked writable parent directory. No GitHub write permission is needed.

By default, compact JSON goes to stdout and a count table goes to stderr. Use
`--output FILE` to write JSON with an atomic, no-follow write. Use
`--table-output stderr|stdout|none` to select the table channel. Table output
on stdout requires `--output FILE`, so stdout never mixes JSON and prose.

## Report schema

Schema version `1` has these top-level fields:

- `schema_version`: the integer `1`
- `repository`: the validated `owner/name` input
- `chief_issue`: the positive issue number passed with `--chief`
- `snapshot_timestamp`: the UTC time captured before evidence collection
- `counts`: the fixed count object below
- `findings`: sorted bounded evidence rows
- `issues`: sorted per-issue plan and reason rows

`counts` always contains these keys:

- `executable_leaves`
- `valid_plans`
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

Reasons come from the existing migration owners. They include plan defects,
blocker and receipt tokens, owner-admission tokens, stale-lease tokens, and
canonical `larch-lint` diagnostics. The aggregate calls these lint surfaces by
their installed executable name:

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

Blocker and receipt findings use `missing-native-blocker-edge issue=#N`,
`undocumented-native-blocker-edge issue=#N`,
`closed-blocker-edge-retained issue=#N`, `stale-plan-body`,
`stale-plan-base-scope`, `stale-blocker-snapshot`, and
`stale-owner-snapshot`.

Owner and lease findings use `missing-owner-block`,
`owner-block-invalid defect=TOKEN`,
`reuse-source-unavailable owner=KEY issue=#N`,
`reuse-owner-snapshot-invalid owner=KEY issue=#N`,
`reuse-missing-native-blocker owner=KEY issue=#N`,
`active-owner-conflict owner=KEY issue=#N`, and
`stale-implementation-lease issue=#N age_hours=H`.

Repository findings preserve the exact canonical `larch-lint` line. Stable
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

The command captures open issues, referenced issues, native dependency edges,
open pull request branches, the Git commit, and tracked paths before it builds
the report. Every issue check uses that immutable snapshot. The command rejects
a Git commit change during the run.

GitHub transport uses read helpers only. The aggregate has no issue-mutation
owner and no write fallback. Its temporary command-audit input contains only
typed issue state and validated registry selectors. It rejects malformed,
truncated, or unavailable evidence instead of treating it as empty.

The stale-lease finding prints the exact operator command already owned by the
tracking-issue lifecycle. The audit does not run that command.

## Workflow handoff

A scheduled workflow may consume the JSON, upload it as an artifact, and update
one marker-keyed Chief issue comment. That workflow owns the comment mutation.
The aggregate remains read-only and does not accept a comment or mutation flag.
