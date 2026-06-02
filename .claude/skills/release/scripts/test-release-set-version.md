# test-release-set-version.sh — harness contract

Offline regression tests for `release-set-version.sh` without network access.

## Cases

1. Writes `.version`, preserves other JSON keys.
2. Output file retains trailing newline.
3. Invalid semver exits non-zero; `plugin.json` unchanged.
4. Downgrade refused; file unchanged.
5. No-op refused.

## Invocation

```bash
make test-release-set-version
```

## Edit-in-sync

- `.claude/skills/release/scripts/release-set-version.sh`
