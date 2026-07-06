# python/check_topology_rule_paths.py contract

`python3 python/cli.py lint topology-rule-paths` validates `skills/shared/topology.tsv` directly. The command name stays `topology-rule-paths` for compatibility, but the TSV is now the source of truth; the retired rule frontmatter parser no longer exists and no rule file is read.

## Caller surface

Primary callers are the `agent-sync` job, the local `check-topology-rule-paths` pre-commit hook, `make test-check-topology-rule-paths`, and manual local runs.

`--root PATH` overrides the checkout root. The default is the repository parent of this module. Harness fixtures pass `--root "$dir"` so `skills/shared/topology.tsv` and referenced authority files resolve inside isolated temp trees. Production callers omit `--root`.

## TSV authority checks

Every non-comment data row must have exactly four tab-separated columns with non-empty key, value, and `runtime_authority` columns. `runtime_authority` must be a repo-relative, contained path with LF line endings and no path traversal, duplicate slash, pathspec-magic prefix, leading dash, or symlink escape.

For each distinct row authority, the lint verifies that the authority exists, is a regular file, and contains the row's `value` text. When `--root` points at a git work tree, the authority must also be tracked by git. That tracked-by-git assertion is skipped for isolated non-git fixture trees; real-registry smoke runs without `--root` against the live checkout so git tracking assertions execute.

## Fixture contract

Each fixture creates a temp root, writes `skills/shared/topology.tsv`, writes the referenced authority files containing the row value, and optionally runs `git init && git add` when testing tracked-by-git behavior. Missing authority files, authority files that do not contain the row value, untracked authority files in a git fixture, symlink escapes, path grammar failures, malformed TSV rows, CRLF, and empty TSVs must fail.

## Edit-in-sync

Update this contract with parser or CLI changes. Keep `scripts/test-check-topology-rule-paths.sh` as the black-box regression authority.
