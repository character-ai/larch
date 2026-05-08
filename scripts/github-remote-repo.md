# scripts/github-remote-repo.sh — contract

`scripts/github-remote-repo.sh` resolves one GitHub remote name or remote URL to `owner/repo` on stdout. It accepts GitHub HTTPS URLs, SSH scp-style URLs, `ssh://`, and `git://` URLs; strips a trailing slash before stripping `.git`; rejects non-`github.com` hosts; and validates owner/repo components against GitHub-style `[A-Za-z0-9._-]+` tokens.

The helper prints parse failures to stderr after redacting URL userinfo so credential-bearing HTTPS remotes do not leak to transcripts.

## Callers

- `scripts/implement-fork-env.sh` uses the helper for `/implement --forked` origin / upstream parsing.
- `scripts/session-setup.sh` uses the helper in Section 4's fallback after `gh repo view` fails. It suppresses helper stderr and treats exit-code 2 as `REPO_UNAVAILABLE=true` instead of a hard abort.

Harness: `scripts/test-github-remote-repo.sh`.
