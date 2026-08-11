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
`gh api`, `gh auth token --hostname github.com`, GitHub and Google service
hosts, GraphQL documents, concrete clients, `gcloud`, and service-credential
propagation.

## Concrete client owner

`crates/larch-core/src/github_auth.rs` owns the single typed
`gh auth token --hostname github.com` credential lookup.
`crates/larch-adapters/src/github/mod.rs` is the single concrete GitHub client
owner. `OctocrabGitHubService::from_gh` builds the one private Octocrab client
from the core-owned result and pins the
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
Issue-dependency adapter parity landed in #7841, and sub-issue adapter parity
in #8164. The `issue-reads` row records the #7682 command cutovers so far: the
issue query verbs moved to Rust in #8167, and `issue list-issues` plus
`issue fetch-issue-details` followed in #8168. The shared typed list operation
returns a bounded result that separates returned issue rows from raw REST rows
scanned and reports truncation, so each caller declares exhaustive or
bounded-partial intent rather than treating every page-bound refusal as a
transport failure; the contract is canonical in
[`supply-chain-credentials-and-services.md`](security/supply-chain-credentials-and-services.md). The `issue-creation` row records
the #8169 cutover of `issue create-one`, `issue write-sentinel`, and
`issue cleanup-failed`; its writes run through the shared issue-mutation owner,
and `write-sentinel` is grouped with them because it is the receipt a completed
filing run publishes, not because it reaches GitHub. The `issue-dependencies`,
`issue-sub-issues`, and `label-dependency-mutations` rows record the #8170
cutover of `issue add-blocked-by`, `issue add-sub-issue`, and both
`/block-issue` dependency mutations; all four now drive the typed issue-graph
adapter operations rather than raw `gh api` REST and GraphQL calls, which is
why they no longer appear in the `comments`, `issues`, and `labels` rows. The
`issue-body-blocks` row records the #8171 cutover of `named-block write`,
`plan-block read`, and `plan-block write`: the two writers drive the shared
issue-mutation owner and the reader drives the typed issue read, so the
`/design` to `/implement` plan handoff no longer reaches GitHub through raw
`gh` calls. The same leaf moved `issue insert-signal-marker`,
`issue title-archival-jq`, and `issue title-eligibility` to Rust; they reach no
GitHub service at all, so they left the `comments`, `issues`, and `labels` rows
without joining another. The `umbrella-conversion` row records the #8174
cutover of `umbrella mutate`, the one live write `/umbrella` performs: it
drives the shared issue-mutation owner's field-scoped compare-and-swap, and the
managed-to-umbrella carve-out is the conversion field that owner already
validates. The same leaf moved `umbrella verify` and
`umbrella verify-completion` to Rust; both prove a completed run entirely from
recorded artifacts and reach no GitHub service, so neither joins a row.

The three `tracking-issue-*` rows record the corrected atomic cutover in #8346
of the six tracking-issue lifecycle verbs. `tracking-issue-comment-reads`
covers the three verbs that list comments: `read` renders the issue and its
human comments into an untrusted-input task file, `append-comment` checks for
an idempotent replay, and `upsert-summary` resolves the comment its marker owns.
`tracking-issue-comment-mutations` covers the latter two verbs' verified
comment creation, replacement, and deletion.
`tracking-issue-lifecycle` covers the three that change issue identity:
`create-issue` files one through the mutation owner's redacting create, and
`rename` and `mark-false-positive` apply a title as a freshness-checked
compare-and-swap. `rename --run-id` and the `upsert-summary` lease heartbeat
also refresh the implementation lease, which the same owner binds to the run
that already holds it. Lease initialization binds the preflight title, body,
and admission-relevant label hashes, timestamp lower bound, base-target SHA,
plan receipt, active title, and lease body in one mutation. A metadata comment
may advance `updatedAt`, but the command admits that drift only while those
preflight issue fields remain exact.
Comment create and edit operations use the same mutation owner and verify both
their mutation echo and a same-surface comment-list read-back; deletion verifies
absence from that list. Issue creation verifies its response with an exact
same-issue GET and names an unverified orphan for best-effort closure. Former
in-process Python workflow callers and external command consumers enter through
`scripts/larch.sh`; `final-report write` calls the same Rust tracking owner in
process so its own output envelope stays unpolluted. The retained tracking
module contains no GitHub behavior. The rows that still name Python-owned issue
commands enumerate them instead of claiming the whole domain.

The three `issue-backlog-*` rows record the #8183 cutover of
`analyze-issues fetch` and `analyze-issues run`. They read bounded issue and
comment DTOs through the typed REST adapter, while the fixed closure-reference
GraphQL operation stays inside the operations adapter. The offline `analyze`
verb reads only its supplied snapshot and therefore has no GitHub-service row.

`audit-report-issues` records #8189's bounded audit advisory and prior-report
closure cutover. The advisory is read-only; prior closure uses the shared typed
issue-mutation owner for authorization and close read-back.

<!-- markdownlint-disable MD010 -->
<!-- github-service-ownership:start -->
```text
operation	adapter_owner	current_owner	planning_issues	implementation_parity	consumer_cutover	python_removal	commands
actions	crates/larch-adapters/src/github_actions.rs	rust	#7676,#7685,#8362	complete	complete	complete	ci-timing harness,ci-timing jobs,ci-timing merge-group-source,ci-timing pytest,gh run-logs,gh workflow-path
attestations	crates/larch-adapters/src/github/attestation.rs	rust	#7674	complete	complete	complete	release validate-assets
comments	crates/larch-adapters/src/github_rest.rs	python	#7680,#7685	pending	pending	pending	clarify *,issue migration-audit
dependency-consumers	crates/larch-adapters/src/github/operations.rs	rust	#7682	complete	complete	complete	deps *
issue-dependencies	crates/larch-adapters/src/github/operations.rs	rust	#7682	complete	complete	complete	block-issue *,issue add-blocked-by
issue-sub-issues	crates/larch-adapters/src/github/operations.rs	rust	#7682	complete	complete	complete	issue add-sub-issue
issue-creation	crates/larch-adapters/src/github/issue_mutation.rs	rust	#7682	complete	complete	complete	issue cleanup-failed,issue create-one,issue write-sentinel
issue-body-blocks	crates/larch-adapters/src/github/issue_mutation.rs	rust	#7680,#7682	complete	complete	complete	named-block write,plan-block read,plan-block write
issue-reads	crates/larch-adapters/src/github_rest.rs	rust	#7682,#7685	complete	complete	complete	gh agnix-issue,issue context,issue fetch-issue-details,issue info,issue list-issues,issue state,umbrella prepare
issue-backlog-reads	crates/larch-adapters/src/github_rest.rs	rust	#7682	complete	complete	complete	analyze-issues fetch,analyze-issues run
issue-backlog-comments	crates/larch-adapters/src/github_rest.rs	rust	#7682	complete	complete	complete	analyze-issues run
issue-backlog-closure-references	crates/larch-adapters/src/github/operations.rs	rust	#7682	complete	complete	complete	analyze-issues fetch,analyze-issues run
issues	crates/larch-adapters/src/github_rest.rs	python	#7685	pending	pending	pending	issue migration-audit
audit-report-issues	crates/larch-adapters/src/github_rest.rs	rust	#7682	complete	complete	complete	audit-runs bugs-backlog-nudge,audit-runs close-priors
audit-pull-requests	crates/larch-adapters/src/github/operations.rs	rust	#7682	complete	complete	complete	audit-runs map-runs,audit-runs preflight,audit-runs resolve-prs
combine-issues	crates/larch-adapters/src/github/issue_mutation.rs	rust	#7682	complete	complete	complete	combine-issues *
label-dependency-mutations	crates/larch-adapters/src/github_rest.rs	rust	#7682	complete	complete	complete	block-issue *
labels	crates/larch-adapters/src/github_rest.rs	python	#7680,#7685	pending	pending	pending	clarify label,issue migration-audit
agnix-label-provision	crates/larch-adapters/src/github_rest.rs	rust	#7685	complete	complete	complete	gh agnix-ensure-label
pull-request-implement	crates/larch-adapters/src/github/operations.rs	python	#7681	pending	pending	pending	implement checks-commit-route,implement checks-result-identity,implement checks-step5-resume,implement cleanup,implement clone-tag,implement commit,implement commit-route,implement kill-active-leg,implement normalize-coder-scout,implement preflight,implement recovery-paths,implement run-dispatch,implement run-step-checks,implement scope-disposition,implement step-0-bootstrap,implement step-0-degraded-gate,implement step-16,implement step-16-16a,implement step-16-17,implement step-17,implement step-18,implement step-2-post-dispatch,implement step-5-resume,implement step-5-review,implement step-6-entry,implement step-7a,implement step-8-oos-checkpoint,implement step-8-python-guard,implement step-8-seed-initial,implement step-8-ship,implement step2-dispatch
pull-request-implement-retired	crates/larch-adapters/src/github/operations.rs	retired	#7681	not-applicable	complete	complete	implement step-18-gate-finalize
pull-request-implement-terminal	crates/larch-adapters/src/github/operations.rs	python	#7995	pending	pending	pending	implement step-18-gate-logs-flush,implement step-19
pull-requests	crates/larch-adapters/src/github/operations.rs	python	#7680,#7681	pending	pending	pending	ci behind-count,ci decide,ci distill-log,ci failed-jobs,ci main-health,ci rerun-failed,ci status,ci wait,design *,pr *,ship *
releases	crates/larch-adapters/src/github/release.rs	rust	#7674	complete	complete	complete	release *
repository-metadata	crates/larch-adapters/src/github/mod.rs	rust	#7676	complete	complete	complete	gh remote-repo,gh resolve-repo
tracking-issue-comment-reads	crates/larch-adapters/src/github_rest.rs	rust	#7682	complete	complete	complete	tracking-issue append-comment,tracking-issue read,tracking-issue upsert-summary
tracking-issue-comment-mutations	crates/larch-adapters/src/github/issue_mutation.rs	rust	#7682	complete	complete	complete	tracking-issue append-comment,tracking-issue upsert-summary
tracking-issue-lifecycle	crates/larch-adapters/src/github/issue_mutation.rs	rust	#7682	complete	complete	complete	tracking-issue create-issue,tracking-issue mark-false-positive,tracking-issue rename
umbrella-conversion	crates/larch-adapters/src/github/issue_mutation.rs	rust	#7682	complete	complete	complete	umbrella mutate
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

`gh remote-repo`, `gh resolve-repo` (#7764), `gh run-logs`, `gh workflow-path`
(#7765), and `ci-timing harness`, `ci-timing jobs`, `ci-timing pytest` (#8098)
have Rust parity, consumer cutover, and Python removal complete. No Python
registration or superseded command implementation remains for them. Their
callers enter the single larch executable through `scripts/larch.sh`; the
subcommands use typed Rust adapters rather than GitHub CLI API shell-outs.

## CLI independence and the bootstrap exception

The only production Rust invocation of `gh` is the core-owned, fixed
`gh auth token --hostname github.com` credential lookup. Rust performs GitHub
API operations only through the authenticated Octocrab adapter, never through
`gh api`; `gcloud` is never a runtime service fallback. Residual `gh` CLI
callers in Python, scripts, skills, and CI belong to commands still owned by
Python and migrate with their own leaves. The `gh-argv-literal` rule keeps raw
`gh` construction inside approved wrappers. The clean-install `gh` usage in
`scripts/larch.sh` downloads and verifies the release binary before runtime.

## Redaction and diagnostics

The credential is held by a non-`Debug` wrapper and omitted from the typed child
environment allowlist. Authorization diagnostics pass through an
invocation-owned redactor, and errors retain only stable failure classes.
Diagnostics, session files, published logs, and snapshots contain no tokens,
authorization headers, or access tokens.
