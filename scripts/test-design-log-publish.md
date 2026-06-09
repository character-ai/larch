# test-design-log-publish.sh

Regression harness for `scripts/design-log-publish.sh`. See
`scripts/design-log-publish.md` for the primary contract.

Coverage includes dry-run preflight, invalid args, trim/redact fail-closed
paths, PR create/list/view/merge recovery behavior, render-cache recursive
staging, render-cache symlink rejection (root, dangling root, intermediate
directory, leaf file, regular-file root, find-to-stage race), suffix deny-list
exclusions, and the strict `plan-review/` allowlist for
`round-<N>/findings-classification.tsv` (including unexpected-path, symlink,
and regular-file root rejection).

Ancestor-directory-race cases (separate from leaf symlink-race cases): the
`make_find_ancestor_race_stub` helper swaps `ANCESTOR_RACE_PARENT` at the `-type f`
enumeration pass while `-type l` stayed clean. Each case captures publish output
with merged `2>&1` (stderr not discarded) and asserts the matching
`... ancestor became a symlink before staging` `larch_err` substring (not
`PUBLISH_OK=false` alone). Plan-review layout uses allowlisted
`round-1/findings-classification.tsv` with `ANCESTOR_RACE_PARENT` set to the
physical `round-1` directory (no disallowed `round-1/sub/` segment).

Run via:

```bash
bash scripts/test-design-log-publish.sh
```

Or `make test-design-log-publish`.

## Recent contract coverage

- Covers malformed `--repo` as an exit-1 structural argv failure while valid `owner/repo` and omitted `--repo` remain accepted.
- Covers the Python bridge used after required-check registration: child stdout is parsed for `PUBLISH_OK=`, failures preserve the recovery branch, and legacy `gh pr checks --required --watch --fail-fast` expectations are absent.
- Covers repository resolution before the CI/merge gate, including unresolved-repository failure without invoking the Python bridge.
- Covers required-check-only Python/gh-stub polling, bounded failed-run rerun fixtures, final already-merged guard fixtures, and `gh pr merge --admin --squash --delete-branch` running from `$REPO_ROOT` rather than the disposable worktree.
- Covers quiet-capture behavior: the parent parses `PUBLISH_OK=` from captured child stdout and does not replay the child's output.
- Covers pause publish staging for `step-*` sentinels and the four driver
  phase-sentinel basenames while rejecting arbitrary `.completed/` basenames.
