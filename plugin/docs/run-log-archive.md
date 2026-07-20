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
