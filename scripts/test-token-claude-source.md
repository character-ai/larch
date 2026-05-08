# test-token-claude-source.sh

**Purpose**: Offline regression harness for `scripts/token-claude-source.sh`.

It covers the `LARCH_CLAUDE_SOURCE_FILE` snapshot replay short-circuit (the durable fix for concurrent-Claude-session attribution) and the live mtime / `LARCH_CLAUDE_SESSION_ID` resolver. Snapshot tests run from outside any git repo so they exercise the short-circuit independently of resolver state. Live-resolver tests run with caller source/token env cleared, inside a fresh `git init` repo with a fake `$HOME` so `~/.claude/projects/<encoded>/` is under the harness's tmpdir.

Concurrent-session coverage (Test 9) asserts that a sticky snapshot binds the session to a specific transcript even when a newer transcript appears in the project dir afterwards — the documented fix for the resolver's "newest-by-mtime" attribution race.

The harness derives the encoded project-dir name from the canonicalized (`pwd -P`) repo root because `token-claude-source.sh` itself canonicalizes via `git rev-parse --show-toplevel` + `pwd -P` (relevant on macOS where `/var/folders/...` resolves to `/private/var/...`).

Run via `make test-token-claude-source` or the shard that includes it (`test-harnesses-4`).

Update this harness when `token-claude-source.sh` changes its snapshot grammar, env-var precedence, character-class allowlist for `LARCH_CLAUDE_SESSION_ID`, or the canonical failure-message wording.
