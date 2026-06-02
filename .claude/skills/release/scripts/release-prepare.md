# release-prepare.sh — contract

Read-only release preparation for the dev-only `/release` skill: resolve the unique GitHub **Latest** release tag, verify git state, extract merged PR metadata since that tag, and classify the aggregate semver bump.

## Usage

```bash
.claude/skills/release/scripts/release-prepare.sh \
  --out-dir <dir> \
  [--repo OWNER/REPO] \
  [--bump major|minor|patch]
```

Default `--repo`: `character-ai/larch` when the skill does not override.

## Outputs (stdout KV)

| Key | Meaning |
|-----|---------|
| `BASELINE_TAG` | Tag name of the sole `isLatest` release (e.g. `v47.0.56`) |
| `CURRENT_VERSION` | `.version` from `plugin.json` at classify time |
| `NEW_VERSION` | Proposed next version after bump |
| `BUMP_TYPE` | `MAJOR`, `MINOR`, `PATCH`, or `NONE` from classify-bump |
| `PR_COUNT` | Rows written to the PR list TSV |
| `PR_LIST_FILE` | Path to `<out-dir>/pr-list.tsv` |

## PR list TSV

Tab-separated columns: `number`, `title`, `labels` (comma-separated), `author`, `url`.

## Semantics

1. **Latest baseline** — paginated `gh api /repos/{owner}/{repo}/releases`; exactly one `is_latest=true` required; otherwise `ERROR=no-unique-latest-release` and `LATEST_COUNT=<n>` on exit **1**.
2. **Origin coupling** — `origin` remote owner/repo must match `--repo` or `ERROR=origin-repo-mismatch`.
3. **Fetch + verify tag** — `git fetch origin main --tags` must succeed; `git rev-parse --verify "$BASELINE_TAG^{commit}"` or `ERROR=baseline-tag-unresolvable`.
4. **Stale local main** — after fetch, `main^{commit}` must equal `origin/main^{commit}` or `ERROR=stale-local-main`.
5. **PR window** — `git log "$BASELINE_TAG"..origin/main` subjects; PR numbers from trailing `(#N)`. Any `gh pr view` failure → `ERROR=pr-metadata-incomplete` (no silent drops).
6. **Bump** — `classify-bump.sh --base "$BASELINE_TAG" --head origin/main` from repo root; optional `--bump` overrides type and recomputes `NEW_VERSION` (decimal-forced `10#` arithmetic).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success KV lines on stdout |
| 1 | Operational failure; `ERROR=<token>` on stdout, human detail on stderr |

## In-flight / duplicate cut guards

- Open `release/v*` PR on `--repo` → `ERROR=release-cut-in-progress`.
- `origin/main` version ahead of baseline with a `Release v*` commit → `ERROR=release-already-cut`.

## Zero PRs

`PR_COUNT=0` is valid; the skill warns at confirm time.

## Harness

`.claude/skills/release/scripts/test-release-prepare.sh` — offline PATH-shimmed `gh`/`git` fixtures.

## Edit-in-sync

- `.claude/skills/release/scripts/release-prepare.sh`
- `.claude/skills/release/SKILL.md` Step 2
- `.claude/skills/bump-version/scripts/classify-bump.sh` (`--base` consumer)
