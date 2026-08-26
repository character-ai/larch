# First projection release runbook

The release that ships the projection cutover is the first one cut with the
new `/release` flow, because `/release` runs from the working tree. Rehearse
the cut before making it, then cut it with the normal skill. This file is the
runbook for that release and the recovery plan for every later one.

Every fence runs from a clean `main` checkout of the larch repo root with the
working-tree driver built:

```bash
set -euo pipefail
WORKTREE_LARCH="$PWD/target/release/larch"
cargo build --quiet --locked --release --package larch-cli
REPO="$(CLAUDE_PLUGIN_ROOT="$PWD" LARCH_BINARY="$WORKTREE_LARCH" "$PWD/scripts/larch.sh" gh resolve-repo 2>/dev/null || echo "character-ai/larch")"
```

## Preconditions

Check all of these before the rehearsal and again before the cut.

- `git branch --show-current` prints `main` and `git status --porcelain` is empty.
- `origin/stable` resolves. Record its OID and its shape:

  ```bash
  git fetch origin main stable --quiet
  STABLE_OID="$(git rev-parse origin/stable)"
  if git merge-base --is-ancestor "$STABLE_OID" origin/main; then
    echo "STABLE_SHAPE=on-main (pre-cutover pin: expect a one-parent projection)"
  else
    echo "STABLE_SHAPE=projection (expect a two-parent projection)"
  fi
  ```

- No remote tag or Release exists for the version to cut:

  ```bash
  git ls-remote --tags origin "refs/tags/v${NEW_VERSION}"
  gh release view "v${NEW_VERSION}" --repo "$REPO" >/dev/null 2>&1 && echo "RELEASE_EXISTS=true" || echo "RELEASE_EXISTS=false"
  ```

  Both must be empty or `false`. Otherwise follow "Rollback before publication".

- `git worktree list --porcelain` names no `larch-release-projection-` path. Prune a stale one with `git worktree prune`.
- The ambient `CLAUDE_PLUGIN_ROOT` names an installed cache root
  (`.../.claude/plugins/cache/larch-local/larch/<version>`). In a Claude Code
  session this is the running install. The pin probe reads its cached
  `scripts/larch.sh`.

## Rehearsal

The rehearsal creates no tag, no draft, and no Release. It rebuilds the
projection of the last shipped release, whose merged commit is the current
`stable` tip when the pin still names a `main` commit. That is the exact shape
of the first cut.

### 1. Dry-run `release stage`

```bash
LAST_VERSION="$(gh release view --repo "$REPO" --json tagName --jq '.tagName' | sed 's/^v//')"
LAST_PR="$(gh pr list --repo "$REPO" --state merged --search "Release v${LAST_VERSION} in:title" --json number,title --jq "map(select(.title == \"Release v${LAST_VERSION}\")) | .[0].number")"
test -n "$LAST_PR"
stage_out="$(CLAUDE_PLUGIN_ROOT="$PWD" LARCH_BINARY="$WORKTREE_LARCH" "$PWD/scripts/larch.sh" release stage \
  --version "$LAST_VERSION" \
  --repo "$REPO" \
  --pr "$LAST_PR" \
  --dry-run)"
printf '%s\n' "$stage_out"
SOURCE_COMMIT="$(printf '%s\n' "$stage_out" | CLAUDE_PLUGIN_ROOT="$PWD" LARCH_BINARY="$WORKTREE_LARCH" "$PWD/scripts/larch.sh" kv get --key SOURCE_COMMIT --match first)"
RELEASE_COMMIT="$(printf '%s\n' "$stage_out" | CLAUDE_PLUGIN_ROOT="$PWD" LARCH_BINARY="$WORKTREE_LARCH" "$PWD/scripts/larch.sh" kv get --key RELEASE_COMMIT --match first)"
test -n "$SOURCE_COMMIT" && test -n "$RELEASE_COMMIT"
```

Require `DRY_RUN=true` and `DRAFT_READY=false` in `stage_out`. The verb runs
every stage proof (merged PR, `origin/main` ancestry, plugin version,
`origin/stable` resolution, projection build, `plugin/`-only drift, first
parent, projected version) and stops before the tag, push, and draft.

### 2. Inspect the projection commit

```bash
git cat-file -p "$RELEASE_COMMIT" | sed -n '/^tree /p;/^parent /p'
git diff --name-only "$SOURCE_COMMIT" "$RELEASE_COMMIT" | command grep -v '^plugin/' || echo "NON_PLUGIN_DRIFT=none"
git show "$RELEASE_COMMIT:plugin/.claude-plugin/plugin.json" | jq -r '"PROJECTED_VERSION=" + .version'
git diff --stat "origin/stable:plugin" "$RELEASE_COMMIT:plugin" | tail -1
```

Expected:

- `PROJECTION_PARENTS` in `stage_out` lists `SOURCE_COMMIT` first. It is the
  only parent when `STABLE_SHAPE=on-main`. It is followed by `STABLE_OID` when
  `STABLE_SHAPE=projection`.
- The only line after `git diff --name-only` is `NON_PLUGIN_DRIFT=none`.
- `PROJECTED_VERSION` equals `LAST_VERSION`.
- The last `git diff --stat` line compares the `plugin/` tree an installer
  fetches today with the rebuilt one. It is empty when the projection rules
  did not change since the last release. Otherwise every listed file must
  trace to a projection-rule change merged since `v$LAST_VERSION`:

  ```bash
  git log --oneline "v${LAST_VERSION}..origin/main" -- crates/larch-cli/src/release_plugin_runtime.rs
  ```

  The rehearsal applies the working-tree rules to the last release's tree. A
  real cut builds the driver from the release branch, so rules and tree always
  match there.

### 3. Prove the cached pin check accepts a projection tip

Every installed bootstrap verifies the pin with its cached
`verify_release_pin`, which compares the `refs/heads/stable` SHA with the tag
commit SHA and nothing else. Run that cached function against the rehearsal
commit with `gh` stubbed, so no network or plugin state is touched:

```bash
CACHED_ROOT="${CLAUDE_PLUGIN_ROOT:?set CLAUDE_PLUGIN_ROOT to an installed larch cache root}"
case "$CACHED_ROOT" in
  */.claude/plugins/cache/larch-local/larch/*) ;;
  *) echo "CLAUDE_PLUGIN_ROOT is not a larch cache root: $CACHED_ROOT" >&2; exit 1 ;;
esac
INSTALLED_VERSION="${CACHED_ROOT##*/}"
PROBE="$(mktemp)"
{
  cat <<'PROBE_PRELUDE'
die() { printf 'DIE: %s\n' "$*" >&2; exit 1; }
gh() { printf '%s\n' "$PIN_COMMIT"; }
RELEASE_PIN_REF=stable
PROBE_PRELUDE
  printf 'RELEASE_REPO=%s\n' "$REPO"
  sed -n '/^require_commit_sha() {/,/^}/p;/^verify_release_pin() {/,/^}/p' "$CACHED_ROOT/scripts/larch.sh"
  printf 'verify_release_pin "v%s" "%s"\n' "$LAST_VERSION" "$RELEASE_COMMIT"
} > "$PROBE"
echo "cached $INSTALLED_VERSION, pin == projection:"
PIN_COMMIT="$RELEASE_COMMIT" bash "$PROBE"
echo "cached $INSTALLED_VERSION, pin == merged main commit:"
PIN_COMMIT="$SOURCE_COMMIT" bash "$PROBE" || echo "REFUSED_AS_EXPECTED=true"
rm -f "$PROBE"
```

Expected: the first run prints `LARCH_PREFLIGHT_PIN_VERIFIED=true`; the second
prints a `DIE:` line and `REFUSED_AS_EXPECTED=true`. `release finish`
fast-forwards `stable` to the tagged projection commit, so the first case is
what every 57.x install sees after the cut.

### 4. Confirm the install layout

`claude plugin install larch@larch-local` fetches `path: plugin` at
`ref: stable` through `git-subdir`, and the cutover changes neither field.
Step 2 proved the fetched tree is byte-identical to the current pin. Confirm
the on-disk cache matches that tree, apart from installer-owned entries:

```bash
LAYOUT_DIR="$(mktemp -d)"
git archive "$RELEASE_COMMIT" plugin | tar -x -C "$LAYOUT_DIR"
diff -rq "$LAYOUT_DIR/plugin" "$CACHED_ROOT" || true
rm -rf "$LAYOUT_DIR"
```

Expected: `Only in $CACHED_ROOT: .in_use` and `Only in $CACHED_ROOT: bin`,
both written by the installer and the bootstrap, plus the files the previous
step traced to projection-rule changes.

### 5. Record the rehearsal

Post the `stage_out` KV block, the parent line, and the four expected results
as a comment on the umbrella issue. Then run the ordinary `/release`.

## Cutting the release

Run `/release` unchanged. Watch these points:

- Step 5 `release stage` output must show `RELEASE_COMMIT` different from
  `SOURCE_COMMIT`, `DRY_RUN=false`, `DRAFT_READY=true`, and the parent shape
  predicted by `STABLE_SHAPE`.
- Step 6 `release finish` must print `RELEASE_PIN_REF` and `RELEASE_PIN_OID`
  equal to `RELEASE_COMMIT`.
- Step 7 `/upgrade-larch` must print `LARCH_PREFLIGHT_PIN_VERIFIED=true`.

After publication, repeat the cached-install probe for real. This downloads
and verifies the published assets into a staging directory and mutates no
plugin state:

```bash
CLAUDE_PLUGIN_ROOT="$CACHED_ROOT" CLAUDE_PLUGIN_DATA="$(mktemp -d)" \
  "$CACHED_ROOT/scripts/larch.sh" --preflight-release "$NEW_VERSION"
```

Expected: `LARCH_PREFLIGHT_PIN_VERIFIED=true` then
`LARCH_PREFLIGHT_VERSION=<NEW_VERSION>`.

## Rollback before publication

Until `release finish` publishes, the release is a draft, the tag is mutable,
and `stable` still names the previous release. No install can see the new
version, so rolling back is safe:

```bash
gh release view "v${NEW_VERSION}" --repo "$REPO" --json isDraft --jq '.isDraft' | command grep -qx true
gh release delete "v${NEW_VERSION}" --repo "$REPO" --yes
git push origin --delete "refs/tags/v${NEW_VERSION}"
git tag -d "v${NEW_VERSION}" 2>/dev/null || true
```

The first line refuses to continue when the Release is not a draft. Then fix
the cause and re-run Step 5 from its stage fence with the same `NEW_VERSION`,
`PR_NUMBER`, and `REPO`. The merged release PR stays merged and already carries
the version bump. Never run `release set-version` again, never open a second
release PR, and never cut a second version for the same window. `release
stage` rebuilds the projection and tags it again. The rebuilt commit has a new
OID because Git restamps the committer time, which is fine: nothing references
the deleted one.

After `release finish` publishes, the Release is immutable and GitHub protects
its tag. There is no rollback. Ship a follow-up patch release instead.

## `stable` advanced but the tag is missing or differs

`release stage` pushes the tag before it creates the draft, and `release
finish` re-verifies the tag before it fast-forwards `stable` as its last step.
So `stable` cannot advance ahead of a tag push in the normal flow. The state is
reachable only by hand: a deleted tag, or a manual `stable` push. Detect it:

```bash
PIN_OID="$(gh api "repos/$REPO/git/ref/heads/stable" --jq '.object.sha')"
TAG_OID="$(git ls-remote --tags origin "refs/tags/v${NEW_VERSION}^{}" | cut -f1)"
echo "PIN_OID=$PIN_OID TAG_OID=${TAG_OID:-missing}"
```

While the two differ, every `/upgrade-larch` preflight refuses, so no install
is harmed, and `release finish` refuses too. Resolve in this order:

1. **The projection commit still exists** (`git cat-file -e "$PIN_OID"`
   succeeds locally or the Release names it as `target_commitish`): restore the
   tag at that commit, which is what `stable` already names.

   ```bash
   git fetch origin "$PIN_OID" --quiet
   git push origin "$PIN_OID:refs/tags/v${NEW_VERSION}"
   ```

   `release stage` then accepts the remote tag as structurally matching and
   `release finish` proceeds.

2. **The projection commit is lost**: re-run the Step 5 stage fence. It builds
   a new projection whose second parent is the current `stable` tip, so the pin
   still fast-forwards. Delete the draft first if its `target_commitish` names
   the lost commit.

3. **`stable` names a commit that is not a projection** (someone pushed a
   `main` commit): `release finish` will refuse to fast-forward to a projection
   that does not descend from it. Do not force-push `stable`. Every cached
   bootstrap reads its SHA, and a force push can strand an in-flight upgrade.
   Re-run the stage fence: the new projection records that commit as its
   second parent, and `stable` fast-forwards from it.
