### FINDING_1: panel [code-review/accepted]

## **Important** correctness `skills/upgrade-larch/scripts/upgrade-larch.sh:29-31`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** correctness `skills/upgrade-larch/scripts/upgrade-larch.sh:29-31`      The release query only inspects the first `gh api repos/character-ai/larch/releases` page, and when no stable release appears there the jq expression emits literal `null`, which the script treats as a real target version. This repo creates prerelease releases on every main merge, so after enough prereleases since the last promotion the script will say it is upgrading to `null`, miss the idempotency check, and emit a bogus post-install warning. Use pagination or `/releases/latest`, and reject `null` the same as an empty result before setting `LATEST_STABLE`.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** correctness `skills/upgrade-larch/scripts/upgrade-larch.sh:75-85`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** correctness `skills/upgrade-larch/scripts/upgrade-larch.sh:75-85`      The prune step keeps the two highest version-numbered cache directories, not the resolved latest stable release plus its predecessor. If the cache contains newer prerelease directories like `27.5.11` and `27.5.12` while `LATEST_STABLE=27.5.10`, a successful stable install is verified at line 61, then the prune pipeline deletes `27.5.10`, breaking the version the user just upgraded to. Fix by building an explicit keep set around `$LATEST_STABLE` and the previous stable release, or skip pruning unless the verified target is included in the retained directories.
- **Suggested revision**: Address the concern above.

### FINDING_23: panel [code-review/accepted]

## risk-integration: skills/upgrade-larch/scripts/upgrade-larch.sh:59-86

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Prune runs even after version mismatch warning. Rollback dirs removed while install is suspect. Skip prune on failed verification or gate with a flag.
- **Suggested revision**: Address the concern above.

### FINDING_28: panel [code-review/accepted]

## security: skills/upgrade-larch/scripts/upgrade-larch.sh:29-31,61-62

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] LATEST_STABLE from GitHub tag_name is used in a filesystem path without validating it is a safe single segment. Unusual or malicious tag metadata (e.g. path separators or parent segments) can make path checks and verification misleading or refer outside the intended cache subtree. Validate tag/version string (strict semver regex or reject /, .., and control characters) before any use in path construction.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** correctness `skills/upgrade-larch/scripts/upgrade-larch.sh:78`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** correctness `skills/upgrade-larch/scripts/upgrade-larch.sh:78`      With `set -euo pipefail`, the version-count assignment exits nonzero when the glob has no matches because `ls -d "$LARCH_CACHE_DIR"/[0-9]*/` fails before `wc -l` returns `0`. In a checkout or unexpected cache layout with no numeric version directories, the script reaches pruning after install and then triggers the recovery trap instead of printing “No old versions to prune.” Guard the glob before the pipeline, or append a controlled fallback so the no-match case produces `VERSION_COUNT=0`.
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Nit** correctness `skills/upgrade-larch/SKILL.md:21`  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Nit** correctness `skills/upgrade-larch/SKILL.md:21`      The skill still tells the assistant to confirm a new version and tell the user to restart even when the new idempotency path exits with no changes. Update the skill instructions to detect the “Already at latest stable” message and report that no restart is needed.
- **Suggested revision**: Address the concern above.

