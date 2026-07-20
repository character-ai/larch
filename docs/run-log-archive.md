# Run-log archive format

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
`--staging-root` when that pending state exists.

An existing remote key succeeds only when its downloaded bytes match the
pending archive; different content fails closed. A new upload is verified by
remote metadata. The normal success path copies the sanitized staging tree
directly into
`${XDG_CACHE_HOME:-$HOME/.cache}/larch/run-logs/<repo>/<skill>/<run-id>/`,
without downloading or decompressing the archive. Retry without staging safely
materializes the durable archive instead. A per-run lock covers upload,
collision verification, cache promotion, and atomic retirement of pending
state.

`python3 python/cli.py run-log sync --repo-root <root>` lists the complete
`run-logs/` remote prefix once, including every provider pagination page. It
downloads and safely materializes only runs without a valid local directory.
Valid cached runs remain untouched. Invalid entries are quarantined under the
per-run publication lock, replaced atomically after validation, and restored if
repair fails. Interrupted download, materialization, promotion, and quarantine
entries are removed before the next attempt.

The command returns the unpacked repository corpus at
`${XDG_CACHE_HOME:-$HOME/.cache}/larch/run-logs/<repo>/`. The shared
`run_log_corpus.synchronized_run_log_root` API performs the same one-time sync
and returns that root. An analyzer must retain the returned path and use normal
local file reads for all later files and waves in the same invocation.
