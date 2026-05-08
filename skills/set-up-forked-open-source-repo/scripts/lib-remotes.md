# lib-remotes.sh

Pointer-only sibling for `lib-remotes.sh`.

The normative contract for URL normalization, remote-state classification,
clone locking, linked-worktree probes, journaling, rollback, harness coverage,
and edit-in-sync requirements lives in
[`setup-forked-open-source-repo.md`](setup-forked-open-source-repo.md). This
library is sourced by `setup-forked-open-source-repo.sh` and is not invoked
directly.

High-signal contracts exposed by this library:

- `normalize_github_url` returns `<host>\t<owner/repo>` for supported
  GitHub-compatible URL shapes and rejects non-parseable hosts.
- `acquire_clone_lock` / `release_clone_lock` reserve FD 9 for the optional
  `flock` layer while using the `mkdir` lock directory as the correctness
  guard.
- `assert_all_worktrees_clean` and
  `assert_all_worktrees_no_op_in_progress` parse `git worktree list
  --porcelain` record-by-record and skip prunable records.
