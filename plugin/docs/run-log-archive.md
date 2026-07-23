# Run-log storage contracts

This document defines the language-neutral run-log storage boundary. Python owns
the workflow; a narrow Rust transport owns GCS authentication and requests only.

The shared provider fixture is `tests/fixtures/run-log-object-store-contract-v1.json`.
Python and the Rust GCS transport both load it in tests. A later runtime
migration must preserve this contract or version it explicitly.

## Configuration resolution

Resolve the storage root from the current repository in this order:

1. Use a non-empty `LARCH_LOGS_URI`.
2. Otherwise read `[logs].uri` from repository-root `config.toml`.
3. Fail when neither source supplies a value. Do not infer a bucket, provider, or prefix.

The environment value replaces the file value. The two values are not merged.
The resolved URI is the larch storage root. It is not the `run-logs/` prefix,
an archive path, or a bucket-root URI.

The checked-in configuration is `[logs]` with `uri = "s3://zhupanov/larch"`.
This repository also owns a versioned `[logs.legacy_migration]` descriptor for
the one-time historical larch migration. It pins the inventory key, inventory
SHA-256, source commit, storage root, and schema. Consumer repositories without
that descriptor do not enable legacy archive handling.

Accept only `gs://`, `s3://`, and `r2://`. Require a plain non-empty bucket
authority and at least one non-empty prefix segment. Reject credentials, ports,
queries, fragments, whitespace, control characters, empty segments, `.`, and
`..`. Preserve accepted bucket and prefix text. Do not hash or silently rewrite
it.

## Remote and local layout

For storage root `<URI>`, the only run-archive layout is
`<URI>/run-logs/<skill-name>/<run-id>.tar.gz`. For the checked-in root, a design
archive is `s3://zhupanov/larch/run-logs/design/<run-id>.tar.gz`.

Only skill directories exist directly below `run-logs/`. Mutable analyzer
state, ledgers, reports, and measurements never appear there.

The unpacked cache layout is
`${XDG_CACHE_HOME:-$HOME/.cache}/larch/run-logs/<repo-name>/<skill-name>/<run-id>/`.

Keep repository, skill, and run names as validated literal directory names. Do
not hash them. The cache is a private local copy, not a second publication
target.

Content-pinned retry state lives outside the cache at
`${XDG_STATE_HOME:-$HOME/.local/state}/larch/run-log-pending/`.

## Provider operations

Every provider implements the same operations:

| Operation | Contract |
|---|---|
| `preflight_bucket` | List the bucket root and decide success from exit or provider status only. Ignore stdout. Do not list the configured prefix, inspect contents or permissions, call a head-bucket substitute, or write a probe object. |
| `list` | List the requested prefix through every page. Return relative keys, byte sizes, and optional opaque ETag and version values. Reject malformed pages, repeated page tokens, and keys outside the configured root. |
| `upload_create` | Create one object only if absent. Never replace an existing object. Return normalized metadata. |
| `metadata` | Return normalized metadata for one exact key. |
| `download` | Write to a private sibling temporary file and atomically promote it. Never merge with a destination. |

For `s3://zhupanov/larch`, startup preflight is equivalent to
`aws s3 ls s3://zhupanov`.

S3 and R2 use the AWS CLI transport and standard AWS credential discovery. R2
also requires `LARCH_R2_ACCOUNT_ID` and `LARCH_R2_ENDPOINT`. The endpoint must
be `https://<account-id>.r2.cloudflarestorage.com`, and the account ID must
match the host. GCS uses the narrow Rust transport through
`${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh` and standard Google Application Default
Credentials.

## Machine-readable errors

Provider diagnostics are untrusted and may contain credentials. Adapters reduce
them to this closed set before orchestration consumes them:

| Kind | Meaning | GCS transport exit |
|---|---|---:|
| `transport` | Request launch, timeout, network, or unclassified provider failure | 1 |
| `invalid-response` | Invalid request shape or malformed provider response | 2 |
| `authentication` | Credentials are missing, invalid, expired, or denied | 3 |
| `already-exists` | A create-only destination already exists | 4 |
| `not-found` | The requested bucket or object does not exist | 5 |
| `local-io` | A local source, destination, or atomic file operation failed | 6 |

Python also uses `configuration` before transport selection. In memory, an
error carries only `kind`, `provider`, and `operation`. The Rust GCS command
uses the fixed exit mapping above. Its stderr label for `invalid-response` is
`invalid-request-or-response`; Python normalizes exit 2 back to
`invalid-response`. Do not parse provider stderr or expose it as the machine
contract.

## Archive, publication, and synchronization

`python3 python/cli.py run-log archive` packages one completed, sanitized
staging tree as `<run-id>.tar.gz`. The source tree is not changed.

The archive is a POSIX PAX tar stream inside gzip. Every member has a
normalized slash-separated NFC path. Members are ordered by that normalized
path, use timestamp `0`, owner and group `0`, empty owner/group names, and
normalized modes: `0644` for non-executable files and `0755` for directories
and executable files. Gzip metadata uses timestamp `0` and no filename.

Only regular files and directories are accepted. Symlinks, devices, FIFOs,
sockets, reserved paths, and Unicode-normalization collisions fail closed.

Each archive has a root `archive-manifest.json` member. It is UTF-8 canonical
JSON with schema version `1`, the skill and run ID, and one entry per source
tree member. File entries include their byte size and SHA-256 digest; directory
entries record size `0` and no digest. The manifest does not describe itself,
avoiding a recursive digest. The command emits SHA-256 digests for both the
complete archive and its manifest so later publication can use the archive
digest for idempotence.

`python3 python/cli.py run-log materialize` validates an archive before it
writes run files. It rejects unsafe paths, collisions, links, special files,
malformed contents, and integrity mismatches. Defaults limit archives to
10,000 members, 256 MiB per member, 1 GiB expanded, and a 1,000:1 ratio.

Materialization writes into a private temporary sibling, verifies the complete
tree, renames it into place, and verifies it again. Failures remove the staged
tree. It never merges with or replaces a destination. Cache entries contain ordinary files and the manifest.

`python3 python/cli.py run-log publish --repo-root <root> --skill <skill>
--run-id <run-id> --staging-root <tree>` persists the archive before attempting
the create-only upload to `run-logs/<skill>/<run-id>.tar.gz`. Failed attempts
remain under `${XDG_STATE_HOME:-$HOME/.local/state}/larch/run-log-pending/`
with content-pinned retry metadata. Repeating the command may omit
`--staging-root` when that pending state exists. When pending state already
exists, the publisher retries and populates the cache from that archive. It
does not use a later mutable staging tree as the retry source.

An existing remote key succeeds only when its downloaded bytes match the
pending archive; different content fails closed. A new upload is verified by
remote metadata. The normal success path copies the sanitized staging tree
directly into
`${XDG_CACHE_HOME:-$HOME/.cache}/larch/run-logs/<repo>/<skill>/<run-id>/`,
without downloading or decompressing the archive. Retry without staging safely
materializes the durable archive instead. A per-run lock covers upload,
collision verification, cache promotion, and atomic retirement of pending
state. Any failure returns nonzero, retains pending state, and prevents clean
workflow success.

`python3 python/cli.py run-log sync --repo-root <root>` lists the complete
`run-logs/` remote prefix once, including every provider pagination page. It
downloads and safely materializes only runs without a valid local directory.
Valid cached runs remain untouched. Invalid entries are quarantined under the
per-run publication lock, replaced atomically after validation, and restored if
repair fails. Interrupted download, materialization, promotion, and quarantine
entries are removed before the next attempt.

The checked-in legacy migration descriptor is a narrow compatibility boundary.
Sync first applies the normal `archive-manifest.json` contract. Only a readable
archive with no root archive manifest can trigger legacy lookup. Sync then
downloads the pinned migration inventory at most once for that repository sync,
verifies its SHA-256, and validates its bounded schema, source commit, storage
root, object identities, source-file rows, and totals. The archive must have an
exact inventory record, and its byte size and SHA-256 must match that record.

Legacy extraction accepts only inventory-covered regular PAX members with safe
canonical paths, supported modes, matching sizes, and matching SHA-256 digests.
It rejects links, devices, special files, collisions, traversal, extra or
missing members, corrupt streams, and expansion-limit violations. After private
extraction succeeds, sync writes a local schema-version-1
`archive-manifest.json`, verifies the complete directory, and promotes it
atomically. It never writes, replaces, renames, or deletes a remote object.
Later syncs validate the local directory and perform listing only.

The command returns the unpacked repository corpus at
`${XDG_CACHE_HOME:-$HOME/.cache}/larch/run-logs/<repo>/`. The shared
`run_log_corpus.synchronized_run_log_root` API performs the same one-time sync
and returns that root. An analyzer must retain the returned path and use normal
local file reads for all later files and waves in the same invocation.

## Rust handoff

Python owns configuration, archive, publication, cache, sync, and orchestration.
Rust owns only the narrow GCS authentication transport. That split does not
authorize another archive, layout, error, or provider contract.

When the run-log domain migrates, follow `docs/python-migration.md` and
I-Cutover-1. In one change, prove Rust parity against the shared fixtures,
switch every production caller to `${CLAUDE_PLUGIN_ROOT}/scripts/larch.sh`,
remove the Python registration and implementation, and prove clean-install
execution. Do not add a compatibility shim, bridge, implementation selector,
fallback, or dual-write period. Rust must consume the same repository-owned
legacy migration descriptor and enforce the same inventory, archive, extraction,
and synthesized-manifest validation contract. The hard cutover must not retain
an undocumented Python-only exception.
