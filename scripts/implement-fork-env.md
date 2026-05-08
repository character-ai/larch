# scripts/implement-fork-env.sh — contract

`scripts/implement-fork-env.sh --tmpdir PATH` is the single pre-setup helper permitted by `/implement --forked`.

It fails closed unless an `upstream` remote exists, resolves `origin` and `upstream` through `scripts/github-remote-repo.sh`, writes `PATH/caller-env.sh` atomically with only `REPO=<fork-owner>/<fork-repo>`, and emits fork metadata on stdout as `KEY=value` lines:

```
FORK_REPO=<owner/repo>
UPSTREAM_REPO=<owner/repo>
FORK_OWNER=<owner>
FORKED_TARGET=true
SLACK_ENABLED=false
```

The caller passes `PATH/caller-env.sh` to `session-setup.sh --caller-env` so the existing `REPO` short-circuit targets the fork. Fork-specific metadata remains orchestrator-local; it is not written to session-env.

Harness: `scripts/test-implement-fork-env.sh`.
