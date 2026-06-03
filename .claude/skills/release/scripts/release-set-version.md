# release-set-version.sh — contract

Atomically sets `.claude-plugin/plugin.json` `.version` to a new semver. No git operations — the `/release` skill owns branch, add, and commit.

## Usage

```bash
.claude/skills/release/scripts/release-set-version.sh <X.Y.Z>
```

## Outputs (stdout KV)

| Key | Meaning |
|-----|---------|
| `PREVIOUS_VERSION` | Version before rewrite |
| `NEW_VERSION` | Version written |

## Validation

- Strict `X.Y.Z` semver.
- Refuses no-op (new equals current).
- Refuses downgrade (new &lt; current).
- Preserves all other JSON keys via `jq`; output file ends with a newline.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | Validation / jq failure |
| 2 | Usage error |

## Harness

`.claude/skills/release/scripts/test-release-set-version.sh`

## Edit-in-sync

- `.claude/skills/release/scripts/release-set-version.sh`
- `.claude/skills/release/SKILL.md` Step 5
