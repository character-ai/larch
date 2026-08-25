# GitHub Release Service Inventory

This ledger records the GitHub release and asset service operations. Its
completion columns retain the historical cutover evidence, while the
[command registry](rust-command-registry.md) and the
[Google service inventory](google-service-inventory.md) record current owners.

## Checked scope

The inventory was checked for issue #7752. Production publication and
promotion now enter Rust through `scripts/larch.sh release finish`,
`scripts/larch.sh release promote`, and
`scripts/larch.sh release promote-latest`. The retired Python implementations
and registrations are removed.

## Operation ledger

| Service category | Current production operations | Production callers | Adapter parity | Consumer cutover | Python removal |
| --- | --- | --- | --- | --- | --- |
| Release reads | List releases, tag-reference resolution, immutable-release policy, Latest | Rust `release stage`, `release finish`, `release promote`, `release promote-latest` | Landed (#7738) | Complete (#7752) | Complete (#7752) |
| Release mutations | Create draft, publish without Latest, promote to Latest | Rust `release stage`, `release finish`, `release promote`, `release promote-latest` | Landed (#7738) | Complete (#7752) | Complete (#7752) |
| Asset operations | Asset metadata, upload, bounded download | Rust `release stage`, `release finish` | Landed (#7738) | Complete (#7752) | Complete (#7752) |
| Attestation verification | Artifact provenance and immutable-release tag, commit, and asset-set verification | Rust `release stage`, `release finish`, bootstrap | Landed (#7755) | Complete (#7752) | Complete (#7752) |

The Rust adapter now owns the typed release and asset operations behind the
hardened Octocrab client from #7724: `larch-core` carries the effect-free
domain types, release selection, ambiguous-mutation reconciliation, and bounded
asset-stream enforcement; `larch-adapters` carries the download host policy, the
injectable transport seam, the typed operations, and the Octocrab-backed
transport. Offline fixtures exercise drafts, immutable releases, missing and
duplicate assets, digest and size validation, redirects, partial streams, rate
limits, permissions, cancellation, and timeout through a fake transport. No
operation shells out to `gh` or exposes an arbitrary API path.

The attestation adapter builds on that transport. `larch-core` owns validated
tag, commit, asset-subject, request, and verified-result types.
`larch-adapters` owns the fixed GitHub attestation routes, bounded compressed
bundle retrieval, Sigstore verification, certificate-extension policy, hosted
provenance checks, and immutable-release asset-set binding. Real larch
`v53.1.24` bundles provide offline cryptographic fixtures for both trust
domains. The adapter does not accept caller-supplied repositories, workflows,
issuers, signer identities, trust roots, or URLs.

The publication state machine uses typed GitHub, pull-request, Git, and
attestation services. It publishes a validated draft with `make_latest=false`,
revalidates the resulting immutable release, verifies its attestation, and only
then promotes it with `make_latest=true`. Ambiguous promotion outcomes read back
Latest before any retry. A failed verification or promotion leaves the prior
Latest release unchanged. Recovery accepts the same already-published immutable
release and resumes verification and promotion without creating a tag, release,
or asset.
