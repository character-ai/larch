# resolve-upstream-larch-repo.sh

`resolve-upstream-larch-repo.sh` delegates to `scripts/larch.sh plugin resolve-repository`, which reads `.claude-plugin/plugin.json` and emits the canonical upstream GitHub repository for public stall recovery filing.

## Contract

- Stdout is exactly `OWNER/REPO` on success.
- Stderr is a short diagnostic on failure.
- The script exits non-zero on missing, non-GitHub, malformed, newline-bearing, traversal-like, or multi-value metadata.

## Resolution policy

The resolver uses plugin metadata instead of a pinned repository constant. That keeps cross-repo failure filing aligned with plugin marketplace metadata when the upstream repository is renamed or transferred.

Accepted forms are GitHub HTTPS URLs, SSH URLs, `git+https` URLs, and plain `OWNER/REPO` values. A trailing `.git` suffix is stripped.

## Failure mode

Callers must not guess a fallback repository. When resolution fails, Tier B `/implement` stall recovery skips cross-repo filing and prints the already sanitized report for manual filing.
