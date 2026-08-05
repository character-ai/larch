# Rust Architecture

Larch ships one Rust executable named `larch`. The Rust workspace grows by
domain, not by copying the Python package tree. Python remains migration code
until each command moves directly to its Rust owner.

## Crates

| Crate | Responsibility | Allowed workspace dependencies |
|---|---|---|
| `larch-core` | Effect-free domain types, use cases, and narrow ports for Git, GitHub, Google services, process execution, storage, and time. | None. |
| `larch-adapters` | Concrete implementations of core ports. This includes filesystem and process boundaries, `gix`, Git CLI exceptions, GitHub and Google clients, and other external I/O. | `larch-core`. |
| `larch-cli` | The composition root and the only released binary. It parses arguments, constructs adapters, and invokes core use cases. Its binary target is named `larch`. | `larch-core`, `larch-adapters`. |
| `larch-lint` | Repository-only policy tooling. It is not linked into the product. | None of the product crates. |
| `larch-test-support` | Workspace-only fixture builders for files, environments, clocks, processes, and HTTP responses. Product crates may use it only as a dev-dependency. | `larch-core`. |

The product dependency direction is:

```text
larch-cli -> larch-adapters -> larch-core
          \-----------------> larch-core
```

Dependency direction applies to normal and build dependencies. Tests may use
dev-dependencies across layers when an integration test needs them. Product
crates must not depend on `larch-lint`.
`larch-test-support` also stays outside the product graph and release binary.

Add modules inside these crates. A new crate needs an independent ownership
boundary, dependency set, and test surface, plus updates to this file and the
`layering` rule. The [shared async model](docs/rust-async-runtime.md) defines
cancellation, task ownership, signals, and child shutdown.
The [Rust testing guide](docs/rust-testing.md) defines fixture ownership,
test boundaries, coverage, external access, and CI partitioning.

## Boundary rules

- Put domain request and response types and injected service traits in
  `larch-core`. Keep them small. Domain code must not import concrete Git,
  HTTP, GitHub, or Google clients.
- Put concrete effects in `larch-adapters`. Each operation has one production
  owner behind a core port. Callers cannot select between implementations.
- Keep `larch-cli` thin. It owns parsing and composition, not domain behavior.
- Preserve byte paths at repository boundaries. Parse external text once into
  typed data. Treat repository configuration, API responses, and workflow text
  as untrusted data.
- Cut migrated commands directly to Rust. Do not add Python, `gh`, `gcloud`, or
  Git fallbacks outside the approved compatibility boundaries.

## Command dispatch

The executable parses `larch <domain> <verb> [arguments]` with Clap. Domains
and verbs are closed enums. An unknown command is an error and never delegates
to Python or another executable. The `example echo` command is non-production;
it proves that the composition root dispatches into `larch-core` while command
ports migrate incrementally.

The workspace package version is the compiled binary version. The CLI test
suite checks it against `.claude-plugin/plugin.json`, which is the plugin
release version selected by the release and installation decision in #7670.

The migration-only command registry lives in
`crates/larch-lint/data/command-registry.toml`. It records one owner and three
independent milestones for each command: implementation parity, production
consumer cutover, and Python removal. `larch-lint` imports the Python registry,
inventories production callers, and blocks ownership or caller drift. Product
crates do not depend on this repository-only migration ledger. See
`docs/rust-command-registry.md` for the update workflow.

Before a command advances to implementation parity, exercise its Python and
Rust owners through the repository's [black-box parity
harness](docs/rust-parity-harness.md). Cases run in isolated roots with live
service credentials and endpoints disabled. They compare exit status, output,
files, and declared side-effect records against reviewed goldens.

## Dependency policy

`Cargo.toml` at the workspace root owns every crate version, feature set, and
path dependency. Member manifests use only `dependency.workspace = true`.
`Cargo.lock` records the resolved versions for reproducible executable builds.
The `workspace-dependency-policy` repository rule rejects member-local versions
and feature flags. The shared package version matches
`.claude-plugin/plugin.json`; the release flow updates both. `cargo deny`
continues to enforce licenses, sources, advisories, duplicate versions, and
wildcard requirements.

When adding or changing a dependency:

1. Confirm that the standard library and current workspace dependencies do not
   already own the behavior.
2. Prefer a maintained pure-Rust crate. Disable default features and enable
   only reviewed features. Network clients must use `rustls`, not native TLS.
3. Add the version and complete feature set once under
   `[workspace.dependencies]`. Inherit it from each member manifest.
4. Review the lockfile, license, advisories, MSRV, duplicate versions, binary
   size, and build time. Run `make rust-check`.
5. For a native dependency, document why pure Rust cannot meet the contract,
   list its system libraries and supported targets, and add release-platform
   build coverage before merging. Do not add a native dependency by default.

Feature flags describe real build variants. Do not add flags for speculative
future use or use a feature to weaken a security check. Keep release builds on
one reviewed feature set unless CI builds and tests every supported variant.

## Selected external boundaries

The completed spikes in issues #7670, #7671, and #7672 constrain later adapter
work:

- Git repository reads use `gix` 0.85.0 with default features disabled and
  only `sha1`, `sha256`, `revision`, and `status`. The workspace records that
  exact selection. Do not enable `gix` network, credential, archive, merge, or
  worktree-mutation features without a bounded design and parity evidence.
- `larch_core::RepositoryRead` owns the repository metadata read contract.
  `larch_adapters::git::GixRepository` is its sole production implementation.
  It reopens through strict config parsing and ownership checks before reading
  mutable repository state. Callers receive core byte types and cannot select
  `gix` or Git CLI reads.
- Configured status iteration and tree changes return core-owned change sets.
  They preserve byte paths, modes, object IDs, conflict stages, ignored-entry
  safety classes, and the index flags needed to interpret status. Patch text,
  `--raw`, `--numstat`, textconv, and external-diff bytes remain owned by the
  typed exact-diff Git CLI method.
- Git mutations and network operations stay behind a closed, typed Git CLI
  compatibility adapter where installed-Git behavior is part of the contract.
  There is no public arbitrary-argv escape hatch.
- [`docs/git-operation-inventory.md`](docs/git-operation-inventory.md) records
  every production Git surface and its one owner. `larch-lint` rejects matrix
  drift, concrete `gix` use outside `larch-adapters`, duplicate Git owners,
  direct Rust Git processes, changes to the closed CLI operation set, and
  non-atomic final rows for the #7675 commands. A later-domain row remains
  Python-owned until its named migration issue performs the atomic cutover.
- Product child processes use the `ExternalProcessRunner` core port. Its closed
  enum permits typed Claude, Codex, Cursor, Git, the fixed GitHub credential
  lookup, and #7670 larch bootstrap or self-check operations. Larch program
  paths derive from validated plugin roots. The adapter accepts argument arrays
  only, rebuilds child environments from an allowlist, bounds output, and owns
  cancellation, timeout, termination, and reap.
  Repository-only lint bootstrap calls stay outside the product dependency
  graph and require reason-bearing lint suppressions.
- GitHub code uses a larch-owned core service port. A single core resolver
  acquires the active GitHub CLI credential through the fixed
  `gh auth token --hostname github.com` process operation. The clean child
  environment excludes `LARCH_GH_TOKEN`, `GH_TOKEN`, and `GITHUB_TOKEN`. The
  adapter uses that result to build a pinned Octocrab client with native TLS
  disabled and `rustls` enabled, and does not expose an arbitrary REST URL or
  GraphQL document to domain callers.
- Attestation domain inputs fix the repository to `character-ai/larch`, the
  release workflow to `.github/workflows/rust-release-assets.yaml`, GitHub's
  OIDC issuer and signer identities, and the trust roots. Callers provide only
  a validated release tag, source commit, and expected asset subjects. The
  adapter retrieves only the fixed repository attestation endpoint. A
  response-supplied compressed bundle may use only GitHub's exact
  `tmaproduction.blob.core.windows.net/attestations/` store, with bounded
  redirects, compressed bytes, decompressed bytes, and bundle count.
- Artifact provenance uses the embedded Sigstore public-good root and requires
  the signed SLSA workflow, repository, ref, commit, hosted-runner, subject,
  certificate identity, issuer, and transparency evidence. Immutable releases
  use the embedded GitHub Sigstore root and require GitHub's release identity,
  timestamp evidence, tag, commit, repository, and exact final asset set.
  `sigstore-verify`, `sigstore-types`, and `sigstore-trust-root` are pinned at
  `0.11.0` with default features disabled. `snap` is pinned at `1.1.2` for the
  API's bounded bundle encoding. Trust-root or verifier updates require the
  normal central dependency review and both checked-in cryptographic fixtures.
- Google code uses larch-owned core ports and official Rust clients with
  Application Default Credentials. `google-cloud-auth` is pinned centrally,
  uses rustls, and owns token caching and refresh. Larch validates external
  account and impersonation endpoints before construction, rejects executable
  subject-token sources, and disables metadata endpoint overrides in production.
  It never shells out to `gcloud` or stores access tokens. Credential
  configuration is trusted operator input, not repository or workflow data.
  The [Google service inventory](docs/google-service-inventory.md) must name a
  production operation before its larch-owned port or official service client
  is added.
  `google-cloud-auth`'s reviewed rustls provider compiles vendored AWS-LC into
  the executable. It needs a C/C++ compiler and CMake at build time, but adds no
  shared-library runtime dependency. The existing native release matrix builds
  and smoke-tests the supported macOS target.
- Service adapters apply fixed hosts, deadlines, response limits, same-origin
  redirect checks, bounded retries, mutation reconciliation, redaction, and
  child-environment allowlists. Tests inject fakes at core ports and do not
  require network access.
- The `service-ownership` repository rule holds this boundary mechanically. It
  confines Octocrab, `google-cloud-auth`, other HTTP clients, service request
  hosts, and GraphQL documents to `larch-adapters`, requires one concrete client
  owner per service, rejects `gcloud` and service-credential child environments
  in production shell, and requires the GitHub and Google service inventories to
  name each client owner. `gh-argv-literal` keeps raw `gh` construction in the
  wrapper, and `subprocess-via-runner` keeps process spawns behind the runner.

Do not add Octocrab or Google clients until their implementation leaf lands.
That leaf must centralize the reviewed version and rustls-only features in the
workspace root.

## Release constraints

The executable must build and run without Python. The only release target is
`aarch64-apple-darwin` (Apple Silicon macOS 11.0 or newer). Intel macOS,
Linux, and Windows are not release targets.

Release archives contain only `larch` and `LICENSE`. Builds use the pinned Rust
toolchain and lockfile. Release CI must build and smoke-test the supported
target without Python and must not introduce an undeclared native runtime
library. The thin residual `scripts/larch.sh` bootstrap verifies and atomically
installs the release-matched binary as specified by issue #7670. Its hidden
`larch bootstrap self-check` command reports the compiled version and target
for staged validation. Runtime use of `gh` is confined to the fixed credential
lookup. Service API operations remain owned by the typed Rust adapters.
