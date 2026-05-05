# scripts/check-remote-branch.sh — contract

`scripts/check-remote-branch.sh` is the wrapper around `git ls-remote --exit-code --heads <remote> <branch>` that `/implement` Step 8b uses to decide between force-pushing a locally-rebased feature branch (branch already on origin) and letting `create-pr.sh` perform the initial push (branch absent on origin). The wrapper also surfaces transport / auth / network failures distinctly so Step 8b can bail to cleanup instead of silently degrading to a stale-remote path — see issue #818 for the historical failure mode that motivated the trichotomy.

## Inputs

- `--branch BRANCH` (required) — branch ref to probe (without `refs/heads/` prefix).
- `--remote ORIGIN` (optional, default `origin`) — remote name.

## Outputs

Always exits 0. The state is in stdout:

- `STATE=present` + `RC=0` — branch found on remote.
- `STATE=absent` + `RC=2` — branch positively confirmed absent (this is `git ls-remote --exit-code`'s "not found" signal, not a transport error).
- `STATE=error` + `RC=<git-rc>` + `ERROR=<flattened-stderr>` — any other non-zero exit from `git ls-remote` (typically 128 on transport / auth / network failures).

The exit-0-always rule keeps callers parsing the envelope rather than `$?`. Step 8b branches on `STATE=` and only logs `RC=` for diagnostics.

## Why this trichotomy

`git ls-remote --exit-code` overloads `2` with "ref not found" and other transport errors with `128` / `129` etc. Conflating them led to the bug described in issue #818: a transient GitHub API outage caused `gh pr view` (the previous implementation) to behave as if the PR existed, and `create-pr.sh` then swallowed the subsequent non-fast-forward push failure under its existing-PR fast-path. Step 8b's correct response is "bail to cleanup" on transport error — never silently degrade.

## When to update

Update this file when Step 8b's gate evolves (e.g., requiring fetch + diff before force-push), when `git ls-remote`'s exit-code semantics change (unlikely), or when adding fields like `REMOTE_SHA=` for callers that want to compare against `HEAD`. Keep the wrapper terse: the trichotomy is the load-bearing contract — adding fields without changing it does not require Step 8b updates.

## Test harness

No sibling regression harness — the wrapper is one `git ls-remote` call. Adversarial coverage (transport-error path) requires either a controlled remote-down test environment or a `git` shim, neither of which CI currently supports.
