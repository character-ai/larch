# scripts/implement-fork-env.sh — contract

`scripts/implement-fork-env.sh` is the single pre-setup helper permitted by `/implement --forked`. It runs as the ONE pre-Step-0 exception in `/implement` Step 0 (before the canonical three-call setup) and is otherwise out of scope for the protocol-execution directive.

## Behavior

The helper:

1. Fails closed (exit 1) unless an `upstream` remote exists. The error message points operators at `docs/installation-and-setup.md` (Fork CI dry-runs) and the explicit `git remote add upstream …` contract — no slash-command pointer.
2. Resolves `origin` and `upstream` URLs through `scripts/github-remote-repo.sh`. Parse failure exits non-zero with redacted stderr (the URL parser owns userinfo redaction).
3. Allocates a **bootstrap tmpdir** via `mktemp -d` under `${TMPDIR:-/tmp}/larch-fork-bootstrap.XXXXXX`. (Optional `--tmpdir PATH` override is preserved for tests; production callers SHOULD omit it so the helper picks the path itself — the canonical `/implement` Step 0 ordering does not have an `IMPLEMENT_TMPDIR` available yet at this point.)
4. Writes `<bootstrap>/caller-env.sh` atomically containing only `REPO=<fork-owner>/<fork-repo>`. This is the file passed to `session-setup.sh --caller-env` so the existing `CALLER_REPO` short-circuit targets the fork.
5. Emits fork metadata on stdout as `KEY=value` lines (one per line):

```
BOOTSTRAP_TMPDIR=<absolute-path>
CALLER_ENV_PATH=<absolute-path>
FORK_REPO=<owner/repo>
UPSTREAM_REPO=<owner/repo>
FORK_OWNER=<owner>
FORKED_TARGET=true
```

## Caller contract

The orchestrator captures stdout and parses these fields. It then invokes the canonical Step 0 sequence with `session-setup.sh --caller-env "$CALLER_ENV_PATH"`. Fork-specific metadata (`FORK_REPO`, `UPSTREAM_REPO`, `FORK_OWNER`, `FORKED_TARGET`) stays orchestrator-local — none of it is persisted in `session-env.sh` (Round 1 plan-review FINDING_1).

After session-setup creates the real `SESSION_TMPDIR` and the orchestrator sets `IMPLEMENT_TMPDIR=SESSION_TMPDIR`, the bootstrap directory is no longer needed; the orchestrator may `rm -rf "$BOOTSTRAP_TMPDIR"` immediately, or leave it for OS tmp cleanup. `IMPLEMENT_TMPDIR` is never the bootstrap path.

## Why a self-allocated bootstrap

Step 0's atomic three-call setup (`create-branch.sh --check` → `session-entry-gate.sh` → `session-setup.sh`) creates `SESSION_TMPDIR` only inside the third call. The fork bootstrap must run BEFORE that sequence so `--caller-env` can be passed through to `session-setup.sh`. There is no `IMPLEMENT_TMPDIR` yet. Forcing the orchestrator to allocate a bootstrap tmpdir before the fork-env helper would expand the pre-Step-0 surface unnecessarily; the helper owns its own bootstrap.

## Exit codes

- `0`: success.
- `1`: `upstream` remote not configured. Operator error; recovery is `git remote add upstream <url>`.
- `2`: argument error or remote-URL parse failure. The URL parser (`scripts/github-remote-repo.sh`) emits redacted stderr.

## Harness

`scripts/test-implement-fork-env.sh` (regression coverage: missing-upstream → exit 1, malformed-`origin` → exit 2, malformed-`upstream` → exit 2 even when origin is valid, success path emits BOOTSTRAP_TMPDIR + CALLER_ENV_PATH + FORK_REPO + UPSTREAM_REPO + FORK_OWNER + FORKED_TARGET, and writes `caller-env.sh` containing only `REPO=...`). Wired into `make lint` via `test-implement-fork-env`.
