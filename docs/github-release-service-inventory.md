# GitHub Release Service Inventory

This ledger records the GitHub release and asset service operations for
issue #7738. It separates adapter parity, consumer cutover, and Python
removal so implementation parity can land before #7674 cuts its release
state machine over to the Rust boundary. The three milestones advance
independently, mirroring the [command registry](rust-command-registry.md)
and the [Google service inventory](google-service-inventory.md).

## Checked scope

The inventory was checked against main commit `8f0cbbd47` and the issue branch.
The current production callers are the Python release helpers, which reach
GitHub through `gh api` and `gh release` subprocesses:

- `python/larch/release/release_finish.py` lists releases for duplicate-safe
  tag selection, resolves the remote tag object id, reads the
  immutable-release policy, stages a draft, and downloads release assets.
- `python/larch/release/promote_release.py` edits a release to clear the
  pre-release flag and mark it latest.

The release state machine, asset packaging, attestation verification, and
installation workflow stay with #7674 and are not ported by this leaf.

## Operation ledger

| Service category | Current production operations | Production callers | Adapter parity | Consumer cutover | Python removal |
| --- | --- | --- | --- | --- | --- |
| Release reads | List releases, tag-reference resolution, immutable-release policy | `release_finish.py` | Landed (#7738) | Pending #7674 | Pending |
| Release mutations | Create draft, publish or edit release | `release_finish.py`, `promote_release.py` | Landed (#7738) | Pending #7674 | Pending |
| Asset operations | Asset metadata, upload, bounded download | `release_finish.py` | Landed (#7738) | Pending #7674 | Pending |

The Rust adapter now owns the typed release and asset operations behind the
hardened Octocrab client from #7724: `larch-core` carries the effect-free
domain types, release selection, ambiguous-mutation reconciliation, and bounded
asset-stream enforcement; `larch-adapters` carries the download host policy, the
injectable transport seam, the typed operations, and the Octocrab-backed
transport. Offline fixtures exercise drafts, immutable releases, missing and
duplicate assets, digest and size validation, redirects, partial streams, rate
limits, permissions, cancellation, and timeout through a fake transport. No
operation shells out to `gh` or exposes an arbitrary API path.

Consumer cutover is deferred: #7674 continues to own the release state machine
and its `gh`-backed callers until it repoints them at this boundary. Python
removal follows cutover; the Python release helpers remain the production path
until then. Before advancing either milestone, update this ledger and add a
default-ignored, opt-in, credential-free live test alongside the offline
fixtures.
