# GitHub Service Migration Inventory

This inventory separates Rust implementation parity, production consumer
cutover, and Python removal. A Rust adapter does not transfer command ownership
or authorize deletion of the Python path. It records every GitHub service
operation, the adapter method that owns it, the command that owns it today, and
the exact issue that will perform any later atomic cutover.

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

`crates/larch-adapters/src/github/mod.rs` is the single concrete GitHub client
owner. `OctocrabGitHubService::from_environment` builds the one private Octocrab
client, reads exactly `LARCH_GH_TOKEN`, and pins the `api.github.com` and
`github.com` host allowlist. It verifies that pinned Octocrab supplies one API
version header. Other adapters layer typed operations over that client and hide
REST URLs, GraphQL documents, and the client. Only
`crates/larch-adapters` imports Octocrab or names GitHub hosts and GraphQL.

## Adapter operation ownership

The tab-separated matrix below is the linted ownership contract. Operation
groups are unique. Adapter paths must exist, migration owners must be concrete
domain or completed-leaf issues, and every listed command must match the
recorded owner and the three independent migration milestones. A command may
appear in more than one row when it consumes several typed adapter operations.
Issue-dependency adapter parity landed in #7841; #7682 owns the later atomic
command cutover without changing the current Python ownership recorded below.

<!-- markdownlint-disable MD010 -->
<!-- github-service-ownership:start -->
```text
operation	adapter_owner	current_owner	migration_issues	implementation_parity	consumer_cutover	python_removal	commands
actions	crates/larch-adapters/src/github_actions.rs	rust	#7765	complete	complete	complete	gh run-logs,gh workflow-path
attestations	crates/larch-adapters/src/github/attestation.rs	rust	#7747	complete	complete	complete	release validate-assets
comments	crates/larch-adapters/src/github_rest.rs	python	#7680,#7682,#7787	pending	pending	pending	clarify *,issue *,tracking-issue *
dependency-consumers	crates/larch-adapters/src/github/operations.rs	python	#7682	pending	pending	pending	deps *
issue-dependencies	crates/larch-adapters/src/github/operations.rs	python	#7682	complete	pending	pending	block-issue *
issues	crates/larch-adapters/src/github_rest.rs	python	#7682,#7787	pending	pending	pending	audit-runs *,combine-issues *,deps *,issue *,triage *
label-dependency-mutations	crates/larch-adapters/src/github_rest.rs	python	#7682	complete	pending	pending	block-issue *
labels	crates/larch-adapters/src/github_rest.rs	python	#7680,#7682,#7787	pending	pending	pending	clarify label,issue *
pull-requests	crates/larch-adapters/src/github/operations.rs	python	#7680,#7681	pending	pending	pending	ci *,design *,implement *,pr *,ship *
release-consumers	crates/larch-adapters/src/github/release.rs	python	#7683	pending	pending	pending	gc-run-logs run
releases	crates/larch-adapters/src/github/release.rs	rust	#7747,#7748,#7749,#7750,#7751,#7752	complete	complete	complete	release *
repository-metadata	crates/larch-adapters/src/github/mod.rs	rust	#7764	complete	complete	complete	gh remote-repo,gh resolve-repo
```
<!-- github-service-ownership:end -->
<!-- markdownlint-enable MD010 -->

`crates/larch-lint/data/command-registry.toml` is the authoritative per-command
ledger. Each later-domain command stays Python-owned until its domain migration
owner files and lands the atomic command leaf. The registry must never delegate
this responsibility to the #7687 chief umbrella. Each eventual leaf implements
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

No production runtime path shells out to `gh` from Rust. Rust reaches GitHub only
through the authenticated Octocrab adapter. Residual `gh` CLI callers in Python,
scripts, skills, and CI belong to commands still owned by Python and migrate with
their own leaves; the `gh-argv-literal` rule keeps raw `gh` construction inside
the Rust GitHub wrapper. The clean-install `gh` usage in `scripts/larch.sh`
downloads and verifies the release binary before any runtime; it is a separate
installer surface and does not authorize a runtime service adapter to shell out
to `gh`.

## Redaction and diagnostics

The credential is held by a non-`Debug` wrapper and omitted from the typed child
environment allowlist. Authorization diagnostics pass through an
invocation-owned redactor, and errors retain only stable failure classes.
Diagnostics, session files, committed logs, and snapshots contain no tokens,
authorization headers, or access tokens.
