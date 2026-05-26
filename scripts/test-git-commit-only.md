# test-git-commit-only.sh

Harness for `scripts/git-commit.sh --only --pathspec-from-file`.

It creates a scratch repository with pre-existing staged content, then commits a NUL-delimited recovery pathspec containing a tracked file and an untracked path with spaces. The assertions verify the new commit contains only the recovery paths and the unrelated staged file remains staged after the commit.

Run:

```bash
bash scripts/test-git-commit-only.sh
```

Primary script: `scripts/git-commit.sh`.
