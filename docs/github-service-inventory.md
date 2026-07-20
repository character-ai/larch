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

## Concrete client owner

`crates/larch-adapters/src/github/mod.rs` is the single concrete GitHub client
owner. `OctocrabGitHubService::from_environment` builds the one private Octocrab
client, reads exactly `LARCH_GH_TOKEN`, and pins the `api.github.com` and
`github.com` host allowlist. It verifies that pinned Octocrab supplies one API
version header. Other adapters layer typed operations over that client and hide
REST URLs, GraphQL documents, and the client. Only
`crates/larch-adapters` imports Octocrab or names GitHub hosts and GraphQL.

## Adapter operation ownership

| Operation group | Adapter owner | Current command owner | Later atomic cutover |
|---|---|---|---|
| Repository metadata | `github/mod.rs` (`OctocrabGitHubService`) | Rust `gh remote-repo`, `gh resolve-repo` | Complete (#7764) |
| Actions run status, cancel, logs, workflow path | `github_actions.rs` (`GitHubActionsService`) | Rust `gh run-logs`, `gh workflow-path` | Complete (#7765) |
| Issue get, list, search, create, edit, close | `github_rest.rs` (`GitHubService`) | Python issue, deps, triage, audit-runs, combine-issues commands | #7687 chief umbrella (per-domain leaf) |
| Comment list, create, edit, delete | `github_rest.rs` (`GitHubService`) | Python issue, clarify, tracking-issue commands | #7687 chief umbrella (per-domain leaf) |
| Label list, create, add, remove | `github_rest.rs` (`GitHubService`) | Python issue, block-issue commands | #7687 chief umbrella (per-domain leaf) |
| Pull request, review, merge state, merge mutation | `github/operations.rs` (fixed GraphQL document and typed merge request) | Python ci, design, release commands | #7687 chief umbrella (per-domain leaf; merge consumer cutover) |
| Issue-dependency list, add, remove | `github/operations.rs`, `github/mutation_auth.rs` gate | Python `block-issue`, `deps` commands | #7682 issue-workflow umbrella; its named command-migration leaf performs the atomic cutover. Adapter parity: #7841 |
| Release listing, draft, publish, Latest promotion, asset upload, asset download | `github/release.rs` (`OctocrabReleaseTransport`) | Rust release commands; Python gc-run-logs commands | Release cutover complete (#7752); remaining domains under #7687 |
| Artifact and immutable-release attestation verification | `github/attestation.rs` (`OctocrabAttestationTransport`) | Rust bootstrap and release commands | Complete (#7752) |

`crates/larch-lint/data/command-registry.toml` is the authoritative per-command
ledger. Each later-domain command stays Python-owned until its named leaf
implements Rust parity, switches every consumer, and removes the Python command
in one PR. The `command-registry` rule rejects a Rust owner whose Python removal
is incomplete, so a partial cutover cannot land.

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
