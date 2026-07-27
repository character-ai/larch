# GitHub Service Migration Inventory

This inventory separates Rust implementation parity, production consumer
cutover, and Python removal. A Rust adapter does not transfer command ownership
or authorize deletion of the Python path. It records every GitHub service
operation, the adapter method that owns it, the command that owns it today, and
the roadmap issues responsible for planning later cutovers. Exact atomic leaf
ownership lives separately in the command registry.

## Checked scope

The scan covered production Rust, Python, skills, agents, hooks, scripts, and CI
configuration. It excluded documentation, fixtures, historical run logs, and the
generated `plugin/` projection. `service-ownership` in `crates/larch-lint`
mechanically holds the boundary this inventory records: concrete clients,
service request surfaces, and `gcloud` stay inside `crates/larch-adapters`.
The #7843 refresh ran after the Actions-log, pull-request merge,
issue-dependency, and credential-contract repairs. It explicitly covered `gh`,
`gh api`, `gh auth token`, GitHub and Google service hosts, GraphQL documents,
concrete clients, `gcloud`, and service-credential propagation.

## Concrete client owner

`crates/larch-core/src/github_auth.rs` owns the single typed `gh auth token`
credential lookup. `crates/larch-adapters/src/github/mod.rs` is the single
concrete GitHub client owner. `OctocrabGitHubService::from_gh` builds the one
private Octocrab client from the core-owned result and pins the
`api.github.com` and `github.com` host allowlist. It verifies that pinned
Octocrab supplies one API version header. Other adapters layer typed operations
over that client and hide REST URLs, GraphQL documents, and the client. Only
`crates/larch-adapters` imports Octocrab or names GitHub hosts and GraphQL.

## Adapter operation ownership

The tab-separated matrix below is the linted ownership contract. Operation
groups are unique. Adapter paths must exist, planning owners must be concrete
roadmap or completed-leaf issues, and every listed command must match the
recorded owner and the three independent migration milestones. A command may
appear in more than one row when it consumes several typed adapter operations.
Issue-dependency adapter parity landed in #7841; #7682 plans the later command
cutover without pretending that an executable atomic leaf is already assigned.

<!-- markdownlint-disable MD010 -->
<!-- github-service-ownership:start -->
```text
operation	adapter_owner	current_owner	planning_issues	implementation_parity	consumer_cutover	python_removal	commands
actions	crates/larch-adapters/src/github_actions.rs	rust	#7676	complete	complete	complete	gh run-logs,gh workflow-path
attestations	crates/larch-adapters/src/github/attestation.rs	rust	#7674	complete	complete	complete	release validate-assets
comments	crates/larch-adapters/src/github_rest.rs	python	#7680,#7682	pending	pending	pending	clarify *,issue *,tracking-issue *
dependency-consumers	crates/larch-adapters/src/github/operations.rs	python	#7682	pending	pending	pending	deps *
issue-dependencies	crates/larch-adapters/src/github/operations.rs	python	#7682	complete	pending	pending	block-issue *
issues	crates/larch-adapters/src/github_rest.rs	python	#7682	pending	pending	pending	audit-runs *,combine-issues *,deps *,issue *,triage *
label-dependency-mutations	crates/larch-adapters/src/github_rest.rs	python	#7682	complete	pending	pending	block-issue *
labels	crates/larch-adapters/src/github_rest.rs	python	#7680,#7682	pending	pending	pending	clarify label,issue *
pull-request-implement	crates/larch-adapters/src/github/operations.rs	python	#7681	pending	pending	pending	implement checks-commit-route,implement checks-result-identity,implement checks-step5-resume,implement cleanup,implement clone-tag,implement commit,implement commit-route,implement kill-active-leg,implement normalize-coder-scout,implement preflight,implement recovery-paths,implement run-dispatch,implement run-step-checks,implement scope-disposition,implement step-0-bootstrap,implement step-0-degraded-gate,implement step-16,implement step-16-16a,implement step-16-17,implement step-17,implement step-18,implement step-2-post-dispatch,implement step-5-resume,implement step-5-review,implement step-6-entry,implement step-7a,implement step-8-oos-checkpoint,implement step-8-python-guard,implement step-8-seed-initial,implement step-8-ship,implement step2-dispatch
pull-request-implement-retired	crates/larch-adapters/src/github/operations.rs	retired	#7681	not-applicable	complete	complete	implement step-18-gate-finalize
pull-request-implement-terminal	crates/larch-adapters/src/github/operations.rs	python	#7995	pending	pending	pending	implement step-18-gate-logs-flush,implement step-19
pull-requests	crates/larch-adapters/src/github/operations.rs	python	#7680,#7681	pending	pending	pending	ci *,design *,pr *,ship *
releases	crates/larch-adapters/src/github/release.rs	rust	#7674	complete	complete	complete	release *
repository-metadata	crates/larch-adapters/src/github/mod.rs	rust	#7676	complete	complete	complete	gh remote-repo,gh resolve-repo
```
<!-- github-service-ownership:end -->
<!-- markdownlint-enable MD010 -->

`crates/larch-lint/data/command-registry.toml` is the authoritative per-command
ledger. Its required `planning_issue` records roadmap placement, while optional
`migration_issue` records only the exact executable leaf accountable for the
atomic cutover. Pending rows without a filed leaf leave `migration_issue`
absent instead of assigning a broad umbrella. Each eventual leaf implements
Rust parity, switches every consumer, and removes the Python command in one PR.
The `command-registry` rule rejects a Rust owner whose Python removal is
incomplete, so a partial cutover cannot land.

## Completed shared cutovers

`gh remote-repo`, `gh resolve-repo` (#7764) and `gh run-logs`, `gh workflow-path`
(#7765) have Rust parity, consumer cutover, and Python removal complete. No
Python registration or superseded command implementation remains for them. Their
callers now invoke the larch `gh` subcommand through `scripts/larch.sh`; that
larch subcommand is native repository and run-log resolution, not a GitHub CLI
shell-out.

## CLI independence and the bootstrap exception

The only production Rust invocation of `gh` is the core-owned, fixed
`gh auth token --hostname github.com` credential lookup. Rust performs GitHub
API operations only through the authenticated Octocrab adapter. Residual `gh`
CLI callers in Python, scripts, skills, and CI belong to commands still owned by
Python and migrate with their own leaves. The `gh-argv-literal` rule keeps raw
`gh` construction inside approved wrappers. The clean-install `gh` usage in
`scripts/larch.sh` downloads and verifies the release binary before runtime.

## Redaction and diagnostics

The credential is held by a non-`Debug` wrapper and omitted from the typed child
environment allowlist. Authorization diagnostics pass through an
invocation-owned redactor, and errors retain only stable failure classes.
Diagnostics, session files, published logs, and snapshots contain no tokens,
authorization headers, or access tokens.
