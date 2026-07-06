# test-check-topology-rule-paths.sh

Regression harness for `python3 python/cli.py lint topology-rule-paths`.

The harness builds throwaway fixture trees under `mktemp -d`, lays out canonical inputs (`skills/shared/topology.tsv` plus the authority files named in its fourth column), and invokes `python3 "$REPO_ROOT/python/cli.py" lint topology-rule-paths --root "$dir"` from each fixture cwd. Real-registry and non-root-cwd smokes invoke the CLI without `--root` so they validate the live checkout.

Coverage includes: happy path, missing authority file, authority file missing the row value, untracked authority in a git fixture, tracked authority in a git fixture, TSV CRLF, malformed row shape, empty required columns, path grammar failures, trailing whitespace, symlink escape, in-repo symlink-as-authority rejection, comments and blanks, live registry smoke, empty TSV, and non-root cwd resolution.

The tracked-by-git assertion is skipped for non-git fixture roots and active for git fixture roots and the live checkout.

Keep this file in sync with `python/check_topology_rule_paths.md` and the Python lint implementation.
