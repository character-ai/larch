# test-release-set-version.sh — harness contract

Offline regression tests for `release-set-version.sh` without network access.

## Cases

1. Writes `.version`, preserves other JSON keys.
2. Output file retains trailing newline.
3. Invalid semver exits non-zero; `plugin.json` unchanged.
4. Downgrade refused; file unchanged.
5. No-op refused.
6. `jq` failure → non-zero exit; `plugin.json` byte-identical (atomic write).

Harness sets `LARCH_RELEASE_SET_VERSION_PLUGIN_JSON` to the temp fixture file (not the live checkout).

## Invocation

```bash
make test-release-set-version
```

## Edit-in-sync

- `.claude/skills/release/scripts/release-set-version.sh`
