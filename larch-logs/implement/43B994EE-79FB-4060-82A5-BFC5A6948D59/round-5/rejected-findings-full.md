### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: .claude/skills/release/scripts/release-prepare.sh:250-261
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --bump override re-implements semver increment instead of reusing classify/apply-bump helpers. Operator override could compute a different NEW_VERSION than classify-bump for the same CURRENT_VERSION and BUMP_TYPE if arithmetic rules diverge. Extract shared bump increment helper or add classify-bump --force-bump-type and drop inline case block.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: .claude/skills/release/scripts/release-prepare.sh:175-177
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] PR extraction requires trailing (#N) in squash subject; other merges are omitted from notes. Merged work without (#N) suffix is missing from PR_COUNT/notes while still affecting classify-bump. Document operator convention or add fallback PR discovery for notes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: Makefile:110
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Four new harnesses added to test-harnesses-20 under 5m CI timeout. Shard 20 may approach timeout as harnesses grow; flaky CI on busy runners. Monitor CI duration; split shard or trim if needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: .claude/skills/release/scripts/release-finish.sh:176-321
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] release-finish bundles OID resolution tag push release create/edit and promote in one long script. Hard to safely extend race recovery or tag logic; regressions in nested fetch/ancestor branches are easy to miss. Split OID resolution and tag idempotency into a library or functions; keep finish as thin orchestration.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: .claude/skills/release/scripts/release-set-version.sh:16-26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] semver_lt duplicated from apply-bump and ship-pr. Future fix in one copy may not propagate leading to inconsistent downgrade checks. Source scripts/lib-semver.sh with semver_lt and shared bump helpers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:170-195` — The new `--head` flag moves diff scope, `git show` reads, and `CURRENT_VERSION` sourcing onto `HEAD_COMPARE`, but the idempotency short-circuit still walks symbolic `HEAD` / `HEAD~N` and only consults subjects at that local tip. When `--head` is passed without `--base`, `SKIP_IDEMPOTENCY` stays `false`, so a local `Bump version to X.Y.Z` tip can yield `BUMP_TYPE=NONE` even though `git diff "$BASE" "$HEAD_COMPARE"` still spans unreleased public-surface changes at the explicit head ref. `/release` avoids this today because `release-prepare.sh:235` always pairs `--base` (which sets `SKIP_IDEMPOTENCY=true` at line 74), but the standalone `--head` surface is internally inconsistent and unsafe for any caller that omits `--base`. **Suggested fix:** Anchor the idempotency walk on `HEAD_COMPARE` whenever `--head` is set (or fail closed unless `--base` is also present), and add a harness case for `--head` without `--base` so the contract cannot regress silently.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:170-195` — The new `--head` flag moves diff scope, `git show` reads, and `CURRENT_VERSION` sourcing onto `HEAD_COMPARE`, but the idempotency short-circuit still walks symbolic `HEAD` / `HEAD~N` and only consults subjects at that local tip. When `--head` is passed without `--base`, `SKIP_IDEMPOTENCY` stays `false`, so a local `Bump version to X.Y.Z` tip can yield `BUMP_TYPE=NONE` even though `git diff "$BASE" "$HEAD_COMPARE"` still spans unreleased public-surface changes at the explicit head ref. `/release` avoids this today because `release-prepare.sh:235` always pairs `--base` (which sets `SKIP_IDEMPOTENCY=true` at line 74), but the standalone `--head` surface is internally inconsistent and unsafe for any caller that omits `--base`. **Suggested fix:** Anchor the idempotency walk on `HEAD_COMPARE` whenever `--head` is set (or fail closed unless `--base` is also present), and add a harness case for `--head` without `--base` so the contract cannot regress silently.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_31

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_31: **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:98-107` — The `--head` guard validates only that worktree and `HEAD_COMPARE` share the same `.version` string; it does not require `git rev-parse HEAD` to equal `HEAD_COMPARE`. Two commits can carry identical `plugin.json` versions while differing in tree/history, which lets classification proceed with a misaligned checkout ref while idempotency (when not skipped) still inspects the local tip. `release-prepare.sh:142-144` mitigates this for `/release` by enforcing `HEAD == origin/main` OIDs before invoking classify-bump, but the classifier itself does not encode that invariant, leaving a latent mis-classification surface for direct `--head` callers. **Suggested fix:** After resolving `HEAD_COMPARE`, fail closed unless `$(git rev-parse HEAD)` equals `HEAD_COMPARE` when `--head` is supplied (or document and enforce `--head` as release-only via mandatory `--base` plus OID equality).
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:98-107` — The `--head` guard validates only that worktree and `HEAD_COMPARE` share the same `.version` string; it does not require `git rev-parse HEAD` to equal `HEAD_COMPARE`. Two commits can carry identical `plugin.json` versions while differing in tree/history, which lets classification proceed with a misaligned checkout ref while idempotency (when not skipped) still inspects the local tip. `release-prepare.sh:142-144` mitigates this for `/release` by enforcing `HEAD == origin/main` OIDs before invoking classify-bump, but the classifier itself does not encode that invariant, leaving a latent mis-classification surface for direct `--head` callers. **Suggested fix:** After resolving `HEAD_COMPARE`, fail closed unless `$(git rev-parse HEAD)` equals `HEAD_COMPARE` when `--head` is supplied (or document and enforce `--head` as release-only via mandatory `--base` plus OID equality).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: .claude/skills/release/SKILL.md:127-134
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Script index highlights promote-latest-release.sh while runtime path uses promote-release.sh. Operators or agents may run the legacy promote script during recovery. Relabel legacy script under a separate Legacy section; emphasize promote-release.sh in Step 6 recovery.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: .claude/skills/release/scripts/release-prepare.sh:187-218
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sequential gh pr view per PR. Very large release windows mean slow prepare and many API calls. Optional follow-up: batch PR fetch; acceptable for current scale.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: .claude/skills/release/scripts/release-prepare.sh:104
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Baseline Latest is resolved only within gh release list --limit 100. If the true Latest release is outside the first 100 rows prepare reports ERROR=no-unique-latest-release (LATEST_COUNT=0). Paginate release list or query isLatest without a fixed low limit.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

