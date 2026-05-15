## Goal
Re-add .claude/skills/release/ with two bug fixes in promote-latest-release.sh

## Implementation Plan

Re-add the `.claude/skills/release/` directory (reverted as OOS in 028b06b9) with two bug fixes applied to `promote-latest-release.sh`.

### Files to create

1. `.claude/skills/release/SKILL.md` — restore verbatim from the reverted version (unchanged)
2. `.claude/skills/release/scripts/promote-latest-release.md` — restore with one prose update to match the fixed verification approach (gh release list instead of gh release view)
3. `.claude/skills/release/scripts/promote-latest-release.sh` — restore with two bug fixes:

### Bug fixes in promote-latest-release.sh

**Bug 1 (lines 69–70):** `jq -er` on boolean fields causes `set -e` abort when value is `false`.

```bash
# BEFORE:
was_prerelease="$(printf '%s\n' "$latest_json" | jq -er '.isPrerelease')"
was_latest="$(printf '%s\n' "$latest_json" | jq -er '.isLatest')"
# AFTER:
was_prerelease="$(printf '%s\n' "$latest_json" | jq -r '.isPrerelease')"
was_latest="$(printf '%s\n' "$latest_json" | jq -r '.isLatest')"
```

**Bug 2 (lines 89–97):** `gh release view --json` does not support `isLatest` field, causing "Unknown JSON field: isLatest" error. Replace the verification step with `gh release list | jq select(.tagName == $tag)` and use `jq -r` for boolean fields.

```bash
# BEFORE:
verified_json="$(gh release view "$tag" \
  --repo "$REPO" \
  --json tagName,isPrerelease,isLatest)" || { ... }
is_prerelease="$(printf '%s\n' "$verified_json" | jq -er '.isPrerelease')"
is_latest="$(printf '%s\n' "$verified_json" | jq -er '.isLatest')"

# AFTER:
verified_json="$(gh release list --repo "$REPO" --limit 100 --exclude-drafts \
  --json tagName,isPrerelease,isLatest | \
  jq -cer --arg tag "$tag" '.[] | select(.tagName == $tag)')" || { ... }
is_prerelease="$(printf '%s\n' "$verified_json" | jq -r '.isPrerelease')"
is_latest="$(printf '%s\n' "$verified_json" | jq -r '.isLatest')"
```

### Testing strategy

Run `/relevant-checks` after the changes. The `agent-lint.toml` likely has entries for these files (since the original commit had them), so linting should pass. Manual verification would require a real GitHub release, so we rely on the script's own error handling and the lint checks.

## Test plan
(no test plan section in plan-file)
