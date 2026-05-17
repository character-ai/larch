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

### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` [skills/upgrade-larch/scripts/upgrade-larch.sh:94](/Users/zhupanov/larch4/skills/upgrade-larch/scripts/upgrade-larch.sh:94)  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [skills/upgrade-larch/scripts/upgrade-larch.sh:94](/Users/zhupanov/larch4/skills/upgrade-larch/scripts/upgrade-larch.sh:94)      Post-install verification only checks whether `$LARCH_CACHE_DIR/$LATEST_STABLE` exists, so a stale cache directory can make the script report success even if the fresh `claude plugin install` installed a pre-release. Concrete scenario: latest stable `29.1.10` is already present from a previous run, the current session is still on `29.1.9`, and the reinstall unexpectedly installs `29.1.11-beta`; line 94 still verifies `29.1.10` and suppresses the warning required by the feature. Verify the actual installed plugin version after install, for example from `claude plugin list` or plugin metadata, before setting `VERIFIED_TARGET=true` and pruning.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## code-quality: skills/upgrade-larch/SKILL.md:3

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] SKILL YAML description still says latest/newest release. Skill marketplace text mis-describes stable-only behavior. Update description to latest stable semantics.
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## correctness: docs/installation-and-setup.md:38

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Doc says prune after successful upgrade gh missing or no LATEST_STABLE: install succeeds but prune skipped; contradicts plan edge case Align docs and plan with code or change pruning rules
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:113-126

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] PREVIOUS_STABLE empty keeps only one cache dir Multiple semver dirs but one GitHub stable line deletes valid predecessor Keep second newest on disk when API predecessor missing
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:24-77

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] get_stable_releases discards gh stderr; empty output is treated as no stable info. gh installed but failing (auth/network) yields unconditional upgrade and skipped stable verification without a clear error. Surface gh failure or warn when gh exists but no stable releases were parsed.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `risk-integration` [skills/upgrade-larch/scripts/upgrade-larch.sh:53](/Users/zhupanov/larch4/skills/upgrade-larch/scripts/upgrade-larch.sh:53)  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [skills/upgrade-larch/scripts/upgrade-larch.sh:53](/Users/zhupanov/larch4/skills/upgrade-larch/scripts/upgrade-larch.sh:53)      The runtime upgrade script now uses Bash 4-only `mapfile` at `skills/upgrade-larch/scripts/upgrade-larch.sh:53` and `skills/upgrade-larch/scripts/upgrade-larch.sh:111`, plus `declare -A` at `skills/upgrade-larch/scripts/upgrade-larch.sh:113`; it also uses GNU-only `sort -V` at `skills/upgrade-larch/scripts/upgrade-larch.sh:40`. On macOS’s default `/bin/bash` 3.2, running `/upgrade-larch` with `gh` installed exits immediately with `mapfile: command not found` before idempotency or upgrade logic runs. Rewrite this with Bash 3.2-compatible `while IFS= read -r` loops, indexed arrays or string membership, and portable version sorting.
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## correctness: skills/upgrade-larch/scripts/upgrade-larch.sh:98-100

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] ACTUAL_VERSION from cache sort tail Mismatch warning may name wrong version Use claude plugin list or install output
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## risk-integration: docs/installation-and-setup.md:26 area

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Idempotency documented without gh caveat Users without gh expect no-op idempotency; script always mutates Match wording to upgrade-larch.md gh requirements
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **`**Blocking**` `risk-integration`** — [`skills/upgrade-larch/scripts/upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh):53,111 — The script uses `mapfile` / `readarray`-class patterns that the repo explicitly forbids in runtime `scripts/**/*.sh` and `skills/**/*.sh`. **Concrete breakage:** [`scripts/test-agent-model-args.sh`](scripts/test-agent-model-args.sh):116-120 runs `rg '\b(mapfile|readarray)\b'` and fails the harness (`make test-agent-model-args`, wired into [`Makefile`](Makefile) `test-harnesses-2` / CI). **Suggested fix:** Read lines with a Bash-3.2-safe `while IFS= read -r` loop (same approach called out in [`.claude/skills/relevant-checks/scripts/run-checks.sh`](.claude/skills/relevant-checks/scripts/run-checks.sh):88).

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 1. **`**Blocking**` `risk-integration`** — [`skills/upgrade-larch/scripts/upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh):53,111 — The script uses `mapfile` / `readarray`-class patterns that the repo explicitly forbids in runtime `scripts/**/*.sh` and `skills/**/*.sh`. **Concrete breakage:** [`scripts/test-agent-model-args.sh`](scripts/test-agent-model-args.sh):116-120 runs `rg '\b(mapfile|readarray)\b'` and fails the harness (`make test-agent-model-args`, wired into [`Makefile`](Makefile) `test-harnesses-2` / CI). **Suggested fix:** Read lines with a Bash-3.2-safe `while IFS= read -r` loop (same approach called out in [`.claude/skills/relevant-checks/scripts/run-checks.sh`](.claude/skills/relevant-checks/scripts/run-checks.sh):88).
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **`**Important**` `risk-integration`** — [`skills/upgrade-larch/scripts/upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh):113-126 — `declare -A` is Bash 4+ only; stock macOS `/bin/bash` 3.2 errors on associative arrays. **Scenario:** Any environment where `bash` resolves to 3.2 reaches the prune block and fails after a successful `claude plugin install`. **Suggested fix:** Drop the associative array (e.g. keep two explicit version strings and compare with `case` / `=` loops), consistent with files like [`skills/issue/scripts/allocate-candidates.sh`](skills/issue/scripts/allocate-candidates.sh):46.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 2. **`**Important**` `risk-integration`** — [`skills/upgrade-larch/scripts/upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh):113-126 — `declare -A` is Bash 4+ only; stock macOS `/bin/bash` 3.2 errors on associative arrays. **Scenario:** Any environment where `bash` resolves to 3.2 reaches the prune block and fails after a successful `claude plugin install`. **Suggested fix:** Drop the associative array (e.g. keep two explicit version strings and compare with `case` / `=` loops), consistent with files like [`skills/issue/scripts/allocate-candidates.sh`](skills/issue/scripts/allocate-candidates.sh):46.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **`**Latent**` `correctness`** — [`skills/upgrade-larch/scripts/upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh):91-139 — When `LATEST_STABLE` is set but the expected cache directory is missing, the script emits warnings via `larch_err` yet still prints `Upgrade complete. Restart Claude Code…` and exits **0**. **Scenario:** Automation or the skill treats exit 0 as a fully successful upgrade while the cache holds a pre-release or wrong semver. **Suggested fix:** Exit non-zero (and/or branch the final banner) when verification fails so orchestrators and operators do not misread success.

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: 3. **`**Latent**` `correctness`** — [`skills/upgrade-larch/scripts/upgrade-larch.sh`](skills/upgrade-larch/scripts/upgrade-larch.sh):91-139 — When `LATEST_STABLE` is set but the expected cache directory is missing, the script emits warnings via `larch_err` yet still prints `Upgrade complete. Restart Claude Code…` and exits **0**. **Scenario:** Automation or the skill treats exit 0 as a fully successful upgrade while the cache holds a pre-release or wrong semver. **Suggested fix:** Exit non-zero (and/or branch the final banner) when verification fails so orchestrators and operators do not misread success.
- **Suggested revision**: Address the concern above.

