## Goal
Eliminate flush-only CI runs by adding paths-ignore to workflows and --no-push to flush sites

## Implementation Plan

Fix two collaborating causes of unnecessary CI runs from larch-log flush commits.

### Part 1 — Add paths-ignore to CI workflows (primary, ~6 lines YAML)

**`.github/workflows/ci.yaml`**: Add `paths-ignore: ['larch-logs/**']` under
both the `pull_request:` and `push:` event stanzas. `workflow_dispatch:` gets
no filter (it is an explicit manual trigger, not a push-driven one).

**`.github/workflows/release-tag.yaml`**: Add `paths-ignore: ['larch-logs/**']`
under the `push:` stanza.

Effect: commits that touch ONLY `larch-logs/**` skip both workflows. Commits
that touch any other path (even alongside `larch-logs/`) still trigger normally,
per GitHub's paths-ignore semantics (all changed paths must match the ignore
pattern to skip).

### Part 2 — Add --no-push to 2 of the 3 push-doing flush sites

**`scripts/ship-pr.sh` line 924 (ci-merge flush)**:
Add `--no-push`. The subsequent `rebase-push.sh` call inside `merge-pr.sh`
(which runs before the squash merge) will carry the flush commit to the remote
branch, making it part of the squash.

**`scripts/ship-pr.sh` line 1101 (postmerge flush)**:
Add `--no-push`. The teardown flush at `implement-finalize.sh:1590`
(`PR_CLOSED=true` path, which does push) runs after this and carries both
commits in one push.

**`scripts/implement-finalize.sh` line 1590 (teardown, PR_CLOSED=true)**:
Leave as-is — push is necessary here because the PR branch is already gone,
so there is no subsequent operation that can carry this commit. This is the
only remaining flush-only push; with Part 1 in place it no longer triggers CI.

### Documentation

**`scripts/larch-log.md`**: Add a `--no-push discipline` section explaining
the convention: callers must pass `--no-push` unless they are the last push
that can carry the commit (i.e., no subsequent push will run).

**`scripts/ship-pr.md`** and **`scripts/implement-finalize.md`**: Add a note
referencing the `--no-push` discipline for flush sites.


## Test plan

Run `/relevant-checks` (pre-commit + agent-lint). The actionlint step validates
the YAML workflow syntax.
