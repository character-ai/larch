# scripts/github-remote-repo.sh — contract

`scripts/github-remote-repo.sh` resolves one GitHub remote name or remote URL to `owner/repo` on stdout. It accepts GitHub HTTPS URLs, SSH scp-style URLs, `ssh://`, and `git://` URLs; strips a trailing slash before stripping `.git`; rejects non-`github.com` hosts; and validates owner/repo components against GitHub-style `[A-Za-z0-9._-]+` tokens.

Primary caller: `scripts/implement-fork-env.sh` for `/implement --forked` bootstrap. The helper prints parse failures to stderr after redacting URL userinfo so credential-bearing HTTPS remotes do not leak to transcripts.

Harness: `scripts/test-github-remote-repo.sh`.
