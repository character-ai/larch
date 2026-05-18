# scripts/test-rebase-push-fork-mode.sh — contract

**Purpose**: regression test for `scripts/rebase-push.sh` fork-mode lease snapshot (issue #2322).

The harness builds two bare remotes (`origin.git` plus `upstream.git`) and a `work` clone whose `feature` branch is pushed to `origin` with tracking, mirroring `/implement --forked`'s topology. It then invokes `rebase-push.sh --base-remote upstream --base-ref main` and asserts:

1. The script exits 0.
2. `origin/feature` matches local `HEAD` after the push (the force-push targeted the fork).
3. `upstream` never received the topic branch (the push did not target the wrong remote).

Without the fix, the lease snapshot reads `upstream/feature` (which does not exist), produces an empty expected OID, and the resulting `--force-with-lease=refs/heads/feature:` is rejected by the remote (exit 2). With the fix, the lease snapshot reads `<branch>.remote` (`origin`) and the push succeeds.

## Wiring

Wired into `make lint` via the `test-rebase-push-fork-mode` target. Added to `agent-lint.toml`'s exclude list because agent-lint's dead-script rule does not follow Makefile-only references.

## Edit-in-sync rules

Update this harness when:

- `scripts/rebase-push.sh`'s push-remote resolution order (`pushRemote` → `remote` → `origin`) changes.
- `scripts/rebase-push.sh`'s lease snapshot, recovery fetch, or equality check switches between push and base remotes.
- Fork-mode topology assumptions for `/implement --forked` change (e.g., topic branches stop tracking `origin`).
