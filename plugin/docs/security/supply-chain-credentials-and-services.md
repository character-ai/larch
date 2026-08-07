# Supply Chain, Credentials, and Services

This document is the canonical security reference for larch release provenance,
dependency controls, bootstrap and upgrade verification, credential handling,
transport policy, and typed external service boundaries. The root
[`SECURITY.md`](../../SECURITY.md) keeps the public summary.

Use the existing operational and architecture documents with this reference:

- [`docs/installation-and-setup.md`](../installation-and-setup.md) owns
  credential setup, installation, and upgrade instructions.
- [`docs/configuration-and-permissions.md`](../configuration-and-permissions.md)
  owns credential-related environment variable configuration.
- [`ARCHITECTURE.md`](../../ARCHITECTURE.md) owns dependency direction, adapter
  structure, and release constraints.
- The [GitHub service inventory](../github-service-inventory.md) and
  [Google service inventory](../google-service-inventory.md) record current
  operation owners, consumer cutover, and mixed-runtime migration status.

## Supply Chain

### Dependency controls

Rust dependencies are reproducible through the tracked `Cargo.lock` and pinned
`rust-toolchain.toml`. CI's required `rust-gate` runs a full-SHA-pinned
`cargo-deny` action against `deny.toml`. It rejects known advisories, unapproved
licenses, duplicate versions, wildcard requirements, and unapproved registries
or Git sources. [`ARCHITECTURE.md`](../../ARCHITECTURE.md#dependency-policy)
owns contributor instructions for dependency changes.

### CI Rust tool bootstrap and caches

Rust CI caches Cargo registry and Git inputs separately from compiler output.
Its versioned keys bind the runner operating system and architecture, lockfile,
root and crate manifests, and pinned toolchain. They do not include Rust source
hashes. Every Rust lane restores those Cargo inputs through the restore-only
cache action. An explicit save can publish them only after a successful `main`
push on a primary-key miss, so pull requests and `workflow_dispatch` runs,
including manual coverage benchmarks, may restore inputs but cannot publish
them. The lint dependency cache is a separate `target/debug` entry. Before it
can be saved, the workflow removes workspace products with `cargo clean
--workspace`; it follows the same successful-`main`-push rule.

The coverage compiler-dependency cache is a separate, versioned
`target/llvm-cov-target` class. It is disabled until three comparable warm-cache
`main` samples beat a no-target-cache control end to end; a missing comparison
or an inconclusive result leaves it disabled. Its explicit key binds runner OS
and architecture, target triple, toolchain and manifests, coverage-tool
version, compiler-profile values, feature mode, linker choice, Cargo
configuration, and a schema version. It has no broad `restore-keys` fallback.
If evidence later activates it, pull requests may restore but cannot publish
it: only a successful `refs/heads/main` push on a primary-key miss may save
after the size guard passes. The initial size limit must come from a measured
dependency-only inventory; the current zero value is a fail-closed unmeasured
sentinel, not a permitted cache size. Any later bound above 2 GiB needs
explicit PR evidence that transfer cost remains net-positive.

Before an enabled target cache can save, the coverage report and verified Linux
executable artifacts have already uploaded, and the coverage executable has
already completed repository policy and plugin validation. The workflow then
removes profile data, reports, timing output, and workspace products, verifies
that no workspace binary or test executable remains, and uploads the resulting
directory inventory. Cache data is never an artifact-provenance substitute and
a cache hit never skips correctness checks or artifact handoff.

CI does not delete Actions caches as part of this policy. A future collector
must first establish repository quota pressure or eviction of useful immutable
entries, limit deletion to this repository's versioned Rust-cache prefixes,
protect current keys, run only from a scheduled or manual trusted event, and
exercise selection offline before a network mutation.

`cargo-nextest` and `cargo-llvm-cov` are independent, versioned Linux tool
caches. On a miss, CI downloads the exact pinned release archive with bounded
retries and timeouts, verifies its SHA-256 before extraction, accepts only the
expected regular archive member, and installs it with an explicit mode. Before
use, including after a cache restore, CI verifies the installed binary SHA-256
and reported version. Tool-cache publication is restricted to successful
`main` pushes. Coverage timing artifacts explicitly record cache restore and
whether cache save succeeded or was skipped; a manual dispatch is marked
`workflow_dispatch-read-only`. CI has no `cargo install` fallback for either
tool.

The coverage execution job builds the `larch` CLI under the same
instrumented target directory and Cargo test profile as its full workspace
tests. Before the job uploads `larch-linux-test-binary`, it fails closed unless
the coverage-target executable at `target/llvm-cov-target/debug/larch` is
runnable and reports its version. The same executable runs repository policy
and plugin projection validation before either it or the LCOV report is
uploaded. The `python-tests` job waits for the stable `rust-coverage` result and
downloads that named artifact; `if-no-files-found: error` prevents an absent
producer artifact from being treated as a successful handoff.

### Release provenance and attestations

The tag-triggered Rust asset workflow checks out the exact tag commit. It
requires the tag, `.claude-plugin/plugin.json`, and Cargo workspace version to
agree. It builds and runs the only supported target, `aarch64-apple-darwin`,
natively. The workflow packages only `larch` and `LICENSE` with normalized
archive metadata.

Each matrix job attests its archive through GitHub artifact attestations. The
collector accepts only one archive and one metadata fragment for each required
target. It rejects missing, duplicate, empty, unexpected, mismatched, or
non-deterministic inputs. It recomputes archive sizes and SHA-256 digests,
emits the schema-v1 manifest and checksum file, attests both, verifies all
three attestations through the typed Rust GitHub attestation capability, and
revalidates the final three-file allowlist before upload.

The attestation service verifies only `character-ai/larch` artifact provenance
and immutable-release attestations. Domain callers cannot set a repository,
workflow, issuer, signer identity, trust root, API path, or absolute URL.
Artifact verification requires a valid Sigstore chain, SCT and Rekor evidence,
the GitHub Actions OIDC issuer, exact release-workflow identity, repository,
tag ref, source commit, `github-hosted` runner evidence, and one matching named
SHA-256 subject. Immutable-release verification uses GitHub's separate embedded
trust root and release identity. It verifies the signed timestamp and signature
and requires the release tag, source commit, repository, and complete unique
asset name and digest set. Missing fields fail closed.

API bodies, bundle counts, compressed and decompressed bundle bytes, redirects,
and deadlines are bounded. A response-supplied bundle URL is accepted only on
the exact HTTPS `tmaproduction.blob.core.windows.net/attestations/` path family.
Cross-host redirects, URL credentials, fragments, loops, and hop overruns fail.
Authorization stays on `api.github.com` and is not attached to the bundle-store
request. Errors retain only a fixed class and optional HTTP status. Tokens,
authorization headers, signed query strings, certificate paths, and bundle
content do not enter diagnostics. Release publication consumes this service
directly in Rust. It has no Python or `gh` fallback.

GitHub provenance ties bytes to a commit and workflow, not source or
infrastructure trust. Checksums index integrity, not trust. `/release` uploads
only the validated three-file set to a mutable draft, gates merge on its digests
and attestations, and preserves the tagged candidate through a merge commit. It
rechecks ancestry and versions, publishes without Latest, verifies every
immutable asset, then promotes. Failures resume the same draft or release.
Published tags and assets never change. Installation verifies separately.

### Release content pin

A release version names one commit, and both halves of an install derive from
it. `.claude-plugin/marketplace.json` pins its `git-subdir` source to the
`stable` branch, so no merge to `main` can change what an install receives.
`release finish` fast-forwards that branch to the tagged commit last, only after
immutable publication, release and asset attestation verification, and Latest
promotion succeed, then re-reads the remote branch and fails the release when it
does not name the tagged commit. The push carries no force and no lease, so Git
rejects any non-fast-forward update and the pin can only advance. A published
release whose pin did not advance fails `release finish` rather than reporting
success, because no installer would see it.

Version-string equality is not content identity, so the pin is verified
separately at install time. See [`../../ARCHITECTURAL_INVARIANTS.md`](../../ARCHITECTURAL_INVARIANTS.md)
`I-Release-1`.

### Bootstrap and atomic installation

`scripts/larch.sh` is the only clean-install exec shim and uses no Python. It
maps the host target for binary identity checks, installs releases only on
Apple Silicon macOS (`aarch64-apple-darwin`) and fails release install and
preflight closed on every other host, and verifies the exact immutable
release, tag commit, asset allowlist, build attestations, strict manifest and
checksums, sizes, digests, platform identity, and raw USTAR layout. It rejects symlinks, special files,
traversal, extra members, malformed archives, and trailing data before
extracting only `larch`.

The staged binary must pass `--version` and compact-JSON
`larch bootstrap self-check`. A same-directory rename installs it atomically.
An existing regular binary retains a hard-link rollback through post-install
verification. A bounded `CLAUDE_PLUGIN_DATA/bootstrap.lock` serializes first
use, reclaims revalidated dead-owner locks, and makes waiters re-check before
downloading. Cleanup removes only process-owned state. Local `.git` checkouts
require an explicit matching `LARCH_BINARY` for direct shim use. The GCS
run-log adapter may lazily run the locked `larch-cli` release build in that
trusted checkout, then call the shim with the resulting path in a
process-scoped `LARCH_BINARY`. It never downloads a release into the checkout,
and installed plugin roots never take this build path.

These controls do not defend against a hostile same-UID process that can rewrite
plugin cache or data files. Runtime lints reject `cargo run` and `cargo install`
in production. They also reject `bin/larch` and
`target/{debug,release}/larch` execution. The GCS adapter confines its
`cargo build` output and does not execute the resulting binary directly. Only
verified bootstrap owners may do that. The command registry requires each live Rust-owned
selector to name a unique shared clean-install fixture. Those fixtures start
without `bin/larch`, verify version and target before dispatch, and invoke the
selector only through `scripts/larch.sh`. Issue-registry audit input is typed
JSON derived from the canonical owner and plan parsers. It is validation
evidence, not executable input.

The `service-ownership` rule rejects runtime `gcloud` execution. It also keeps
clean-install `gh` use in `scripts/larch.sh` separate from the fixed runtime
credential lookup. Neither path authorizes `gh` API calls from a runtime
adapter. Its GitHub operation matrix fails on ownership or migration-state
drift, including chief-issue placeholders, inventory gaps, and generic-token
fallback.

### Upgrade and rollback boundaries

`/upgrade-larch` never writes install stamps or recursively deletes, prunes, or
edits Claude-managed plugin version directories. Claude Code owns orphan
retention so active sessions keep their original roots. The installed Rust
driver invokes only Claude, validated larch executables, and the bounded
`scripts/larch.sh` bootstrap exception. It never invokes Python. Only bootstrap
children inherit the GitHub CLI auth and config allowlist. Claude and self-check
children do not.

Before any marketplace mutation, the current root's bootstrap verifies the
exact immutable stable release, complete asset allowlist, attestations,
manifest, checksums, archive, target, and staged binary identity in confined
`${CLAUDE_PLUGIN_DATA}` staging. It also verifies that the pinned `stable`
branch is at that release's tagged commit and reports the proof as
`LARCH_PREFLIGHT_PIN_VERIFIED=true`. The driver requires both that proof and the
preflighted version before it touches the marketplace, so a content-and-binary
mismatch is refused while the prior installation is still the active one rather
than after it has been replaced. First-use bootstrap does not gate on the pin,
because the branch moves ahead of installs that are deliberately on an older
release. The driver then uses supported Claude plugin
commands and resolves exactly one new cache root through
`claude plugin list --json`. Success requires the new root's manifest and
executable to report the expected version. A failure leaves the prior cache root
untouched and prints retry commands.

Bootstrap cleanup removes only its current staging directory and lock under
`${CLAUDE_PLUGIN_DATA}`, or its current same-filesystem binary stage. The
dev-only `/release` flow builds the released working-tree binary and routes it
through `scripts/larch.sh` with the validated `LARCH_BINARY` override. Its
internal `--plugin-root` argument keeps upgrade state bound to the separately
validated installed cache root. The `release-python-free` rule pins the final
command set and rejects Python, direct-binary, and direct-`gh` fallback drift.

### Release-version transaction

`release set-version` accepts one semantic version and a fixed repository-owned
file inventory. It validates the current plugin, workspace, internal path
dependency, member, lockfile, and optional runtime-projection versions before
writing. Each write uses the confined atomic UTF-8 adapter and preserves file
mode. A write or postcondition failure restores every original file in reverse
order and reports rollback failures. The command exposes no caller-selected
rewrite path or content surface.

A hard process termination between final-file publications can still leave a
partial update. Replay fails closed on inconsistent old versions instead of
continuing from mixed state.

## Credentials and Transport

### Google Application Default Credentials

Google credential configuration is trusted operator input. Larch accepts it
only through the standard Application Default Credentials search order:
`GOOGLE_APPLICATION_CREDENTIALS`, the well-known local ADC file, then the
attached-service-account metadata service. Repository content, issue text,
workflow data, API responses, and agent output cannot supply credential JSON,
paths, quota projects, scopes, endpoints, or universe domains.

Before the official Google authentication builder reads a selected ADC file,
larch bounds and parses it. External-account token exchange must use
`https://sts.googleapis.com/v1/token`. Impersonation must use the documented
`iamcredentials.googleapis.com` access-token path. AWS and Azure subject-token
URLs must match their documented metadata endpoints. Executable subject-token
sources and custom universe domains fail closed. Production rejects the
test-only `GCE_METADATA_HOST` override, so an inherited emulator setting cannot
redirect attached-service-account authentication.

`google-cloud-auth` owns access-token exchange, caching, and refresh. Larch does
not shell out to `gcloud`, copy ADC files, expose authorization headers, persist
tokens, or create a credential store. Errors retain only a stable failure class,
not credential values or credential paths. Concrete Google service clients are
added only for operations recorded in the
[Google service inventory](../google-service-inventory.md), with explicit
least-privilege scopes and IAM permissions. Offline tests use local fixtures.
Live ADC tests are ignored by default, require explicit opt-in, and do not render
credential headers.

### Vendor credential preflight and the reviewer-probe cache

`agent cursor-auth-preflight` runs in Rust through
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`. It proves that Cursor can
authenticate before a Cursor lane starts, so Cursor never fails in-process and
returns a canned, un-reviewed response. A usable `CURSOR_API_KEY` clears the
preflight without any keychain access, and a non-Darwin host has no keychain to
consult.

On Darwin with no usable `CURSOR_API_KEY`, the preflight reads the
`cursor-user` / `cursor-access-token` keychain item with `security
find-generic-password -w`. The read is bounded, read-only, and runs under the
shared vendor startup lock with a fixed attempt budget. `security` is a closed
`HostUtilityProgram` allowlist entry, so the read uses the one approved
external-process layer rather than a second spawn path. Reading the secret,
not testing for its existence, is required: an access-controlled item can pass
an existence check and still deny the read.

The Rust preflight never mutates its own process environment. A resolved token
lives only inside `CursorCredential`, which redacts itself in `Debug`
rendering, exposes its value through one explicit accessor, and rejects a value
carrying an embedded newline or carriage return so it cannot splice a second
assignment into a child environment. The credential reaches a vendor only as a
typed `CURSOR_API_KEY` child override on an approved process request. It never
enters stdout, an operator message, a probe stamp, or a gate-detail artifact.

The reviewer-probe cache stores verdicts and Codex gate details under one
user-scoped temporary root with mode `0600`. Every entry is confined before
use, and symlinked or non-regular entries are refused rather than followed. A
positive verdict and a failing verdict carry separate lifetimes, so caching a
failure can be disabled independently. Concurrent Codex probes serialize on a
per-identity exclusive lock, so exactly one probe runs and every waiter then
observes the same published gate detail. A cached gate detail is re-derived
against the canonical gate renderer on read, so a hand-edited or corrupted
cache entry cannot inject operator-facing text into the degraded-tools
explanation.

Isolation for a Cursor probe is owned by `CursorProbeSession`, which holds the
private configuration directory and the resolved credential together. Both are
released when the session value is dropped, so success, failure, timeout, and
cancellation take one cleanup path.

### Slack issue-announce webhook transport

`slack issue-announce` runs in Rust through
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`. It posts a short implement-run
announcement to the optional `LARCH_SLACK_WEBHOOK_URL` webhook. The URL is a
credential: the command never prints it, never writes it into STATUS/REASON/ERROR
rows, and redacts it from transport diagnostics before emission. Only `http` and
`https` schemes are accepted; other schemes fail closed. `--best-effort` maps
validation and transport failures to exit 0 while still emitting
`STATUS=failed`. The concrete HTTP client lives in
`crates/larch-adapters/src/http_client.rs`; core owns planning and redaction only.

### Object storage credentials and transport

Cloud Storage uses the larch-owned `ObjectStore` port, the official Rust client,
and the hardened ADC boundary above. S3 and R2 use standard AWS credential
resolution. R2 also requires a matching account ID and an HTTPS endpoint on the
account's Cloudflare host.

Repository-root `tools-config.toml` may select a credential-free storage base.
`LARCH_STORAGE_BASE_URI` may enable storage without a file value, but it never
hides an invalid present file. When neither source configures storage, remote
publication is disabled and larch constructs no provider adapter or command.
Larch still derives the client repository from local Git origin.

When storage is enabled, larch derives the fixed
`larch/<client-repo>/` scope. The provider credential remains the authority and
should grant list, read, and create-only write only for approved tool and
repository prefixes. Startup lists that exact prefix with a maximum of one
result; it never lists the bucket root or writes a probe. Any configured
provider failure blocks startup. The process ignores returned object names and
reduces provider failures to credential-free classes.

The provider-neutral transport accepts only validated bucket roots and object
keys. Uploads are create-only. Downloads use a private temporary file and atomic
promotion. Provider diagnostics are reduced to fixed, credential-free failure
classes. The [Google service inventory](../google-service-inventory.md) records
the Cloud Storage client, scope, permissions, operations, and mixed-runtime
consumer path.

Rust owns the shared run lifecycle, including terminal archive publication and
cache promotion. The standalone `run-log publish` and `run-log sync` commands
remain Python-owned until #8080. Rust uses the official Cloud Storage client;
S3/R2 lifecycle publication and startup preflight use the official AWS SDK with
the credential-process feature disabled. R2 suppresses the unsupported optional
AWS checksum headers; lifecycle publication still downloads the object and
verifies its complete SHA-256 digest when a create-only key already exists;
new objects are verified through returned and fetched remote metadata. The residual Python standalone
commands continue to use the AWS CLI until #8080. Both runtimes use the same
provider-neutral port, immutable-write rule, and machine error mapping. The
complete mixed-runtime and future hard cutover boundary lives in
[Run-log storage contracts](../run-log-archive.md#rust-handoff).

The one-time `character-ai/larch#7966` layout migration uses the same
normalized S3 transport. Live plan, apply, and verify operations accept only
the fixed old and tool-first roots for the larch and agent-lint client
repositories. Apply requires an explicit live-migration authorization flag.
Final report publication requires a separate authorization flag. Both archive
and report uploads are create-only. Source objects, target objects, provider
credentials, and provider diagnostics are never mutated or disclosed by the
migration report.

### GitHub credential and transport boundary

The Rust GitHub service acquires exactly one credential by invoking the fixed
`gh auth token --hostname github.com` command through the core-owned typed
process operation. The process runner uses a clean environment, permits the
GitHub CLI configuration selectors, and excludes `LARCH_GH_TOKEN`, `GH_TOKEN`,
and `GITHUB_TOKEN`. Missing `gh`, an inactive login, and empty, truncated, or
non-Unicode output fail before network access with fixed guidance. The
credential is held by a non-`Debug` wrapper, registered by exact value with an
invocation-owned redactor, and omitted from child environments. Authorization
diagnostics pass through that redactor. The Octocrab build excludes its tracing
feature.

The adapter constructs one private Octocrab client inside the larch Tokio
runtime. Octocrab is pinned with default features disabled and only its rustls
AWS-LC client, timeout, and required JWT support enabled. Octocrab 0.54 requires
a JWT backend even though this adapter exposes token authentication only. Larch
selects AWS-LC because the alternative RustCrypto RSA graph carries an unpatched
advisory. `aws-lc-sys` builds its bundled C and assembly with CMake and a
platform C compiler. It adds no dynamic system-library requirement and is built
by the existing target release matrix.

The fixed credential lookup is the only normal runtime `gh` invocation for
Rust GitHub service access. GitHub API operations use the authenticated adapter
directly; `gh api` is never a service fallback, and `gcloud` is never a runtime
service fallback.

Redirects and retries are disabled. Larch sets `User-Agent` and `Accept`.
Pinned Octocrab supplies one API-version header. Both bases are pinned to
`https://api.github.com/`. Response-supplied continuations must remain HTTPS on
the same approved origin. The host policy also recognizes
`https://github.com` for typed download boundaries, but does not permit a
continuation to cross between the two origins.

Connect, read, write, and overall deadlines are fixed. Overall execution is
cooperatively cancellable. Response bodies and pagination are bounded. Only
reviewed transient failures from idempotent reads are retry inputs. Uncertain
mutations route to typed reconciliation instead of automatic retry. The core
service port exposes policy and typed transport classifications, not raw URLs,
arbitrary GraphQL documents, or the concrete client. Operation code must add
typed paths and DTOs behind this adapter. The `service-ownership` repository rule
confines the Octocrab client, GitHub request hosts, and GraphQL documents to the
adapter crate. The [GitHub service inventory](../github-service-inventory.md)
names client and operation owners. Parity fixtures independently block all
GitHub credential variables.

Repository, issue, comment, label, and search responses are untrusted data. The
Rust operation adapter converts Octocrab models immediately into larch-owned
DTOs, rejects missing required fields and unknown states, and enforces
response-byte, page, item, string, and JSON-nesting limits before it returns
data to a caller. Pagination follows only parsed same-origin HTTPS
continuations. Issue titles, bodies, comments, labels, authors, URLs, and search
results must never become shell text, paths, format strings, or prompt
instructions.

Idempotent reads have bounded retry and honor a structured `retry_after` value
when GitHub supplies one. Mutations are serialized by their caller and are not
blindly retried. Issue edits and closes, comment edits and deletes, and label
changes read back the owning resource after an ambiguous transport outcome.
They return success only when the requested postcondition is present. Creates,
which lack a collision-free request identity, return a typed ambiguous-outcome
error instead of risking a duplicate issue, comment, or label.

## Typed Service Boundaries

The [GitHub service inventory](../github-service-inventory.md) is the canonical
mixed-runtime operation ledger. A Rust adapter does not transfer command
ownership or authorize Python removal. Each command stays with its recorded
owner until implementation parity, consumer cutover, Python removal, and
clean-install execution land atomically.

### Release and asset operations

The release boundary exposes typed methods for bounded listing, duplicate-safe
tag selection, policy reads and writes, draft create and update, publish,
upload, and bounded download. Draft validation binds version, PR head, tag,
exact run, mutable draft, three assets, digests, `LICENSE`, and attestations before
merge. Tags use the closed typed Git adapter. Callers use `scripts/larch.sh`.
They do not use Python, `gh`, raw Git, arbitrary HTTP, or a fallback.
Publication and installation stay with their owning callers.

Ambiguous create, upload, edit, publish, and Latest-promotion outcomes read back
the owning resource. A landed effect succeeds without another write. An
ambiguous draft create is not repeated when a temporary placeholder may still
be absent from the list response; a later staging run adopts it by identity.
Other mutations retry only after the owning read proves absence. Publication
preserves the prior Latest release. Promotion occurs only after immutable asset
and attestation verification, and verifies the final Latest postcondition.
Policy and draft edits always read back their state. Draft updates carry the
tag, target commit, title, and body together so a temporary GitHub
`untagged-*` association can be repaired by release id without creating a
second draft. Clear mutation responses are validated directly; ambiguous
responses still require an owning tag read. Body reconciliation accepts only
an exact match or GitHub's addition of one terminal newline.

Asset download uses an operation-specific host policy that differs from the
same-origin API continuation policy. A download may leave the API origin for a
signed content host. Each redirect hop must stay HTTPS, carry no embedded
credentials, never revisit a prior URL, and stay within the hop cap. The
credential is withheld on every cross-origin hop. The streamed body is bounded
by a per-asset byte cap, must advertise the binary octet-stream content type,
and is rejected if it ends before its declared length. Downloads are
deadline-bounded and cancellable.

### Pull-request, review, and dependency operations

Pull-request, review, and dependency operations expose typed inputs only. The
fixed review-state GraphQL query fails closed on any `errors` member, including
partial data. Create reconciles ambiguity before retry. Merge uses the
live-mutation gate and validated repository, PR, exact lowercase 40- or 64-byte
head, and closed method inputs. Merge sends at most one request, then uses
bounded exact-head read-back after uncertainty. Result classes are fixed, and
untrusted response text never egresses.

Release preparation uses typed, bounded reads for the Latest release, PRs, and
companion issue titles. Publication fetches through the typed Git CLI adapter,
checks ancestry through gix, and uses typed release and attestation services. It
publishes without changing Latest, verifies the immutable release, and only
then promotes it. Ambiguous promotion reads back Latest before a retry. The
final Latest state is verified. The release commands expose no raw Git, `gh`,
URL, GraphQL, or Python fallback.

Repository-policy setup reads the merge-commit and immutable-release settings
before it writes. It mutates only a setting that is disabled, so an already
compliant repository requires Administration read but not Administration write
on the active `gh` credential. Repairing a disabled setting requires
Administration write. Missing permission returns a fixed, secret-free policy
diagnostic. A
required mutation remains fail-closed, and every successful setup performs a
final read-back of both owning policy surfaces.

The dev-only release skill builds the current checkout before its first
Rust-backed release command and rebuilds immediately after the candidate
version write. Every working-tree release command still enters through
`scripts/larch.sh` with the checkout root and release binary supplied
explicitly. This prevents an installed or same-version stale binary from
owning either side of the candidate-version boundary.

Issue-dependency list, add, and remove use the shared live-mutation gate:
operator mode, or a regular non-symlink session file directly under a canonical
root that carries `LARCH_LIVE_MUTATION_OK=true` and the matching run ID. Writes
are idempotent and exact-read-back verified. Triage calls require expected
`updated_at`, re-read the client before writing, reject stale or protected
targets, and return a new non-empty timestamp. Before each Rust dependency
write, the triage-controlled path also rejects exact `security` or
`vulnerability` labels and security-sensitive terms in the title, body, or any
comment. Comment and dependency lists follow parsed same-origin HTTPS `Link`
continuations under shared byte, page, item, deadline, and cancellation bounds.
Malformed or incomplete comment evidence fails closed. Unavailable APIs and
transport errors are typed and redacted.

### Repository metadata reads

`larch_adapters::git::GixRepository` is the sole production implementation of
the core `RepositoryRead` port. It opens and discovers repositories with `gix`
ownership checks enabled, rejects reduced-trust ownership, and parses config in
strict mode. Each mutable-state query reopens through the same checks so later
ownership or config changes cannot reuse an earlier trusted handle. The
location method returns the immutable repository identity captured by the
trusted constructor.

`larch gh remote-repo` and `larch gh resolve-repo` parse remote names and URLs
through this typed gix port and optional `GitHubService` metadata. Malformed or
hostile remote strings never become subprocess argv. They fail closed with the
legacy stderr contract. Service setup and metadata failures are retained for
origin fallback diagnostics and are never treated as instructions. These
commands do not invoke `gh` or an untyped Git subprocess.

The adapter performs local reads only. It exposes no mutation, network,
credential, or arbitrary Git command surface. Results preserve object IDs,
paths, config values, and remote URLs as bytes. Errors use fixed classes and do
not include repository paths, config values, remote credentials, or upstream
library diagnostics.

Status and typed tree changes follow the same reopen rule. Status uses the full
configured `gix` iterator and never writes its optional index-stat refreshes.
The strict `RepositoryRead::status` operation returns `UnsupportedSemantics`
before iteration for repository and worktree clean or process filter config. It
also rejects repository attributes that select conversion or configured filter
behavior. Typed tree changes reject configured textconv and external diff
drivers. Callers that need exact diff interpretation must route those
byte-sensitive cases through the closed exact-diff Git CLI operation.
Compatibility callers that consume only status and untracked names use
`GixRepository::local_status`; it retains configured filters and does not
promise exact diff semantics. User and system filter definitions remain
operator-owned config. Effective conversion attributes are queried through the
configured attribute stack. Discovery does not follow symlinks and fails closed
when the worktree traversal exceeds its entry cap. Typed results contain paths,
modes, IDs, and flags, but no file content or upstream diagnostic text.

### Git mutation compatibility

`git stage`, `git commit`, and `git amend-add` run through
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`. The script is the sole production
bootstrap and version-validation entrypoint. Remaining Python callers resolve
that script. They do not select an implementation, execute `bin/larch`
directly, invoke Cargo, or fall back to Python command behavior.

Rust composes closed `AddRequest`, `CommitRequest`, and
`InterpretTrailersRequest` operations. The installed Git executable remains the
compatibility backend. Git owns hooks, clean and process filters, signing
programs, helpers, commit-message cleanup, index updates, refs, reflogs,
diagnostics, and exit status. Arguments are typed and byte-preserving. There is
no arbitrary Git argument surface. The process adapter clears ambient Git
repository overrides, inherits only its reviewed environment allowlist, sets
`GIT_TERMINAL_PROMPT=0`, bounds captured output, and terminates and reaps the Git
process group on timeout or cancellation.

All product Git mutations and network porcelain use the closed typed `GitCli`
adapter. Each method fixes its subcommand and validates refs, paths, remotes,
refspecs, config keys, and option combinations. Treat Git-launched hooks,
filters, signing tools, transports, credential helpers, merge drivers, and
editors as hostile. Bound and redact their output. Never accept a
repository-provided path as the `git` executable.

`docs/git-operation-inventory.md` is the checked ownership boundary.
`git-ownership` has no baseline or production suppression. It rejects inventory
or `gix` drift, direct or aliased Git construction, bound executables, raw or
generic argv, a widened typed surface, restored Python entrypoints or calls, and
the retired `push rebase` state machine. Only `#[cfg(test)]`,
`larch-test-support` fixture oracles, and the lint bootstrap are bounded
non-production exceptions.

Commit messages use a private temporary file. The command removes that file on
success, Git failure, hook rejection, signing failure, filter failure, and
cancellation. The default co-author trailer is prepared through Git's
`interpret-trailers` operation. `--no-trailer` skips only that operation.
Pathspec files may be absolute because recovery files live outside the
repository. Their paths reject empty, option-like, and NUL values. Repository
paths reject absolute paths, parent traversal, options, and NUL bytes.

Index-lock recovery is narrow. Larch removes only a regular, zero-byte
`.git/index.lock` after the repository's trusted Git directory is resolved and
no holder is found by `/proc` or the typed, bounded `lsof` host-utility probe. It
verifies removal, retries the failed Git operation once, and reports the
decision. Non-empty, held, unreadable, symlink, or unverifiable locks remain
untouched. Branch-write protection is checked before staging or committing,
including the persisted original-branch prohibition used by the ship workflow.

### GitHub Actions operations

The Actions operation port builds repository, workflow, run, job, and check
paths only from validated typed inputs. Reads retry a bounded transient set
within the overall deadline and cap pages, items, body bytes, strings, and JSON
nesting. Rerun and dispatch mutations are serialized. They honor numeric
`Retry-After` pacing before read-back and report an ambiguous outcome when the
read-back cannot prove the mutation happened.

Workflow log archives have a 64 MiB and 60 second limit. The adapter follows at
most three redirects and rejects loops, URL credentials, fragments, plaintext,
unexpected content types, and oversize or incomplete streams. Redirect hosts
are limited to the documented `*.actions.githubusercontent.com` suffix and the
`productionresultssa<digits>.blob.core.windows.net` storage family. Octocrab
adds authorization only for `api.github.com`, so cross-origin log requests do
not carry `Authorization`. They preserve the signed query. A production-auth
loopback test checks both hops. Failures return redacted errors.

`larch gh run-logs` emits selected failed-job log bytes unchanged to preserve
the legacy stdout contract. Callers must redact that output before writing it to
a model prompt, committed artifact, or other egress surface. The typed adapter
limits archive download and decompressed output to 64 MiB, limits archive
entries to 1,024, rejects malformed archives and oversized entries, and never
treats archive paths as local filesystem paths.

`larch ci-timing harness` and `larch ci-timing pytest` parse the same untrusted
workflow archives entirely in memory. They apply the shared 64 MiB and 1,024
entry limits, cap entry-name length, never extract archive paths, and emit only
the schema-v1 timing fields consumed by the rebalancer. One timing operation
accepts at most 20 runs and retains at most 100,000 rows, 32 MiB of label text,
and 16,384 bytes per target or nodeid. Harness input is also capped at 4,096
required targets. `larch ci-timing jobs` derives wall-clock durations from typed
Actions job records. All three commands use the Actions adapter and the fixed
GitHub credential boundary above; they do not call `gh api`, accept raw URLs,
or expose log text in their output.

## Implementation and Verification Owners

The implementation remains mixed-runtime. These owners and checks keep the
boundaries above discoverable without duplicating their operation ledgers:

| Boundary | Implementation and verification pointers |
| --- | --- |
| Release, attestations, bootstrap, upgrade | `.github/workflows/rust-release-assets.yaml`, `scripts/larch.sh`, `crates/larch-cli/src/release_plugin_runtime.rs`, `crates/larch-adapters/src/github/attestation.rs`, `python/tests/release/test_assets.py`, `python/tests/release/test_rust_bootstrap.py`, and the clean-install cases in `crates/larch-cli/tests/parity.rs` |
| GitHub credentials and operations | `crates/larch-adapters/src/github/`, `crates/larch-adapters/src/github_actions.rs`, the [GitHub service inventory](../github-service-inventory.md), and the `service-ownership` rule and tests in `crates/larch-lint/` |
| Google ADC | `crates/larch-adapters/src/google_auth.rs`, the [Google service inventory](../google-service-inventory.md), and the `service-ownership` rule and tests in `crates/larch-lint/` |
| Object storage | `crates/larch-core/src/object_store.rs`, `crates/larch-adapters/src/google_storage.rs`, `crates/larch-adapters/src/s3_storage.rs`, `crates/larch-adapters/src/run_lifecycle.rs`, `python/larch/report/object_store.py`, the [Google service inventory](../google-service-inventory.md), and their focused Rust and Python tests |
| Repository reads and Git compatibility | `docs/git-operation-inventory.md`, `crates/larch-adapters/src/git/`, `crates/larch-adapters/tests/git_repository.rs`, `crates/larch-lint/src/rules/git_ownership.rs`, and the command registry clean-install cases |
