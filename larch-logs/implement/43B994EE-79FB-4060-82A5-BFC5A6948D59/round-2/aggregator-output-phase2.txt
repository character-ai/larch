Verifying a few merge candidates against the codebase so aggregated concerns match the implementation.
Normalized aggregator output from the supplied reviewer slots. Merges follow shared behavioral risk; severity uses **important** > **latent** > **nit**.

---

### FINDING_1: --bump override duplicates version increment logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh`’s `--bump` override reimplements `NEW_VERSION` increment rules separately from `classify-bump.sh`. If increment rules change in one place (e.g. pre-release handling), `/release --bump` can disagree with `/bump-version` for the same `CURRENT_VERSION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: `--head` flag undocumented for release-prepare consumer
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `classify-bump.sh` accepts `--head` (used by `release-prepare` for `origin/main`-anchored aggregate diffs) but the flag is not documented in `classify-bump.md` or `--help`. Future refactors may remove or break `--head` without a failing default-path test, breaking release aggregate bumps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: `release-set-version.sh` does not `cd` to repo root
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Unlike sibling release scripts, `release-set-version.sh` does not `cd` to `REPO_ROOT` from `SCRIPT_DIR`. If Step 5 Bash runs outside the repo root, `plugin.json` on another tree could be updated or the script could fail opaquely.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: `test-release-prepare.md` contract out of sync with harness script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: The harness contract lists 6 cases while `test-release-prepare.sh` implements 8; cases 7–8 (fetch-fail, `pr-metadata-incomplete`) are missing from the `.md`. Contributors relying on stale docs miss regression expectations.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: `semver_lt` duplicated across bump/release paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `semver_lt` in `release-set-version.sh` is a fourth copy vs `apply-bump` / `ship-pr`, increasing drift risk for leading-zero and comparison edge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Release notes redacted twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Release notes may pass through `redact-secrets.sh` in the orchestrator and again in `release-finish.sh`. If redaction rules diverge, the two passes could produce inconsistent output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_7: Baseline resolution uses nonexistent `is_latest` on REST release objects
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` filters `gh api /repos/.../releases` with `jq select(.is_latest == true)`. Live REST payloads use `isLatest` (via `gh release list --json`), not `is_latest`, so `LATEST_COUNT` is always 0 and live `/release` exits `ERROR=no-unique-latest-release` before PR/bump work. Offline fixtures use `is_latest`, so tests can pass while production fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: No `git fetch` before `git show` / tag at `mergeCommit` OID
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-tag-release-race-output.txt
- **Severity**: important
- **Concern**: After `merge-pr.sh`, `release-finish.sh` uses `TARGET_OID` from `gh pr view … mergeCommit.oid` and immediately runs `git show "${TARGET_OID}:.claude-plugin/plugin.json"` without fetching that commit. `merge-pr.sh` only fetches `origin main` pre-merge; the squash-merge OID is often absent locally, causing spurious `ERROR=could not read plugin.json at TARGET_OID` (or tag failures) despite a successful merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-tag-release-race-output.txt: After resolving `TARGET_OID`, run `git fetch origin main` (or `git fetch origin "$TARGET_OID"` when supported) and verify `git rev-parse "origin/main^{commit}"` equals `TARGET_OID` before `git show`; fail closed on fetch/verify mismatch.

### FINDING_9: Missing `origin/main` fallback when `mergeCommit` is empty or slow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-tag-release-race-output.txt
- **Severity**: important
- **Concern**: Plan/contract expect `mergeCommit` resolution with `origin/main` fallback for `TARGET_OID`. Implementation polls `mergeCommit` ~10s then fails closed with `ERROR=merge-commit-missing` only. GitHub API lag, delayed `mergeCommit` after squash merge, or removal of prior fetch+fallback leaves valid merged releases aborting even when `origin/main` already has the bumped `plugin.json` commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-tag-release-race-output.txt: Extend backoff (e.g. 30–60s total), and/or after merge add a guarded fallback: `git fetch origin main` then require `origin/main^{commit}` equals `mergeCommit.oid` (or equals `TARGET_OID`) before proceeding—only when version at that commit matches `--version`.

### FINDING_10: Default `classify-bump` path uses `10#` semver arithmetic beyond plan scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The default classify path now uses `10#` semver arithmetic not described in the plan. Versions with leading-zero components can classify/bump differently than before. Either scope `10#` to `--base`/`--head` only or document and test the default-path change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: `--dry-run` with dirty tree vs `origin/main`-anchored diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` allows `--dry-run` on a dirty tree while `classify-bump` reads workspace `plugin.json` for `CURRENT_VERSION`/`NEW_VERSION` but aggregate diff uses `origin/main` via `--head`. Preview versions can diverge from what a clean-tree cut would produce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_12: PR list extraction requires `(#N)` at end of subject only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `release-prepare.sh` extracts PR numbers only when `(#N)` appears at the end of the squash subject. Valid merges without that suffix are silently omitted from release notes (possibly `PR_COUNT=0` with no `pr-metadata-incomplete` error). Document the convention, relax `sed` to match the last `(#digits)`, and/or warn when the log range is non-empty but `PR_COUNT=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: `test-release-prepare` does not exercise real `classify-bump` diff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Prepare tests fake `gh`/partial `git`, but `classify-bump` integration uses real `git` on synthetic OIDs. `classify-bump` can break while tests still pass with an empty diff and `BUMP_TYPE=PATCH`. Fake `git diff`/`show` for the baseline..`origin/main` range or use a full mini-repo and assert the expected bump on success paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: No harness coverage for release-cut guards
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-cut-in-progress` and `release-already-cut` guards in `release-prepare.sh` have no offline harness cases. Regressions in `gh pr list`, Release-commit detection, or live `isLatest` baseline shape can ship without CI failure. Add cases (e.g. 9–10) with `GH_FIXTURE_OPEN_PRS` and `Release v*` log subjects; align fixtures with `gh release list` field names.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_15: Case 5 bump-override assertion not enforced
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `test-release-prepare.md` case 5 documents `NEW_VERSION=2.0.0` for `--bump major`, but the harness only checks `BUMP_TYPE=MAJOR` against live `plugin.json`. On current `main`, major override yields `48.x` not `2.0.0`, so the doc misleads reviewers and the plan’s bump-override check is not enforced.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: `merge-commit-missing` exit path untested in `test-release-finish`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Slow or failed `mergeCommit` polling can regress to tagging wrong refs or aborting valid merges without offline coverage. Add a `test-release-finish` case with empty merge OID; assert exit **1** and `ERROR=merge-commit-missing`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: `create-pr.sh` body-file redaction lacks test coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `create-pr.sh` now redacts secrets on `--body-file` without a `test-create-pr` sentinel case. A redaction regression could publish secrets in release PR bodies.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: Local stale/wrong-OID tag path untested in `test-release-finish`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The local tag wrong-OID fail-closed path in `release-finish.sh` has no harness case. Production could abort on a stale local tag without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_19: Open `release/v*` guard treats `gh pr list` failure as zero PRs
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: When `gh pr list` or `jq` fails, `open_release_pr` falls back to `0`, allowing overlapping release cuts on transient `gh` errors. Fail closed on `gh`/`jq` errors; only proceed when the list succeeds and length is 0.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: Tag/release can succeed then `promote-release` fails without recovery contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `promote-release.sh` fails after tag and `gh release create`/`edit`, the tag and prerelease exist but are not Latest and success KVs may not emit. Document/retry a promote-only path and idempotent finish when tag+release already exist at `TARGET_OID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: `release-already-cut` may miss per-PR bumps without Release commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `origin/main` version is ahead of the baseline tag only via per-PR bumps (no `Release v*` commit in range), `release-already-cut` may not fire, leaving confusing semver state on re-run. Optional warn when origin version is ahead of baseline tag only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: `LARCH_RELEASE_FINISH_AT_VERSION` bypasses tree version check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_RELEASE_FINISH_AT_VERSION` skips reading `plugin.json` at `TARGET_OID`. Env pollution during `/release` could pass the version string check while tagging a merge commit whose tree lacks the expected bump.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_23: Test-only env overrides for repo and promote script
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_RELEASE_FINISH_ORIGIN_REPO` and `LARCH_RELEASE_FINISH_PROMOTE_SCRIPT` override remote resolution and the promote helper. Malicious env could satisfy string repo checks while running an arbitrary promote script. Limit overrides to offline tests; document as non-production in `release-finish.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_24: `mergeCommit.oid` not validated as a git OID before use
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `mergeCommit.oid` from `gh` is not validated as a 40-hex SHA (or via `git rev-parse --verify`) before `git show`, tag, or push. Unexpected `gh` output could resolve to an unintended ref.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_25: `BASELINE_TAG` from GitHub not format-validated
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `BASELINE_TAG` from GitHub is used in `git` revision ranges without format validation. Malformed `tag_name` could skew `git log` and `classify-bump` windows. Reject unless tag matches `^v[0-9]+\.[0-9]+\.[0-9]+$`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_26: PR metadata in public release notes with limited sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: PR titles/authors/URLs feed public GitHub Release notes with only mechanical `redact-secrets` coverage. Internal URLs or PII in PR titles could appear on the public release. Strengthen orchestrator sanitization beyond token families.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_27: `--pr` not validated as numeric
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `--pr` is not validated as numeric before `gh pr view`. A mis-parsed `PR_NUMBER` from `create-pr` output could target another PR’s merge commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_28: Tag idempotency skips remote OID re-check after race window
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: important
- **Concern**: When the first `ls-remote` finds no remote tag, a concurrent push (e.g. `release-tag.yaml`) can populate `remote_oid` before the second probe; the script then skips `git push` without re-verifying `remote_oid == TARGET_OID` (unlike the push-failure handler). A wrong-OID remote tag could still reach `gh release create` / promote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: After every `ls-remote` that yields a non-empty `remote_oid`, compare peeled commit OID to `TARGET_OID` (e.g. `git ls-remote origin "refs/tags/${TAG}^{}"` or `git rev-parse` after `git fetch origin tag`) and exit **1** on mismatch before release/promote steps.

### FINDING_29: Remote tag checks omit `^{commit}` peel for annotated tags
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: latent
- **Concern**: Remote checks use `git ls-remote origin "refs/tags/${TAG}"` without the `^{commit}` peel used locally. For annotated tags, `ls-remote` returns the tag object SHA, not the commit, causing false mismatch or false match vs `TARGET_OID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Query peeled refs consistently, e.g. `refs/tags/${TAG}^{}` (or normalize with `git rev-parse "${oid}^{commit}"` after fetch).

### FINDING_30: `gh release create` flags misaligned with `release-tag.yaml`
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: latent
- **Concern**: `gh release create` omits `--latest=false --prerelease` while `release-tag.yaml` creates prereleases non-latest. If `/release` wins the race, semantics differ until promote runs; prerelease flags may remain wrong briefly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Align flags with the workflow (`--latest=false --prerelease` on create; keep edit path for races).

---

### OOS_1: [OUT_OF_SCOPE] `apply-bump.sh` `semver_lt` lacks `10#` coercion
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `apply-bump` `semver_lt` lacks `10#` coercion used in new release scripts. Inconsistent octal-edge behavior across bump paths (pre-existing). Align when consolidating semver helpers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_2: [OUT_OF_SCOPE] Legacy `promote-latest-release.sh` retained
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Legacy `promote-latest-release.sh` remains alongside the new cut-a-release flow. Operators might invoke the old promote-only path by habit. Remove after migration if unused.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### OOS_3: [OUT_OF_SCOPE] `merge-pr.sh` never fetches after successful merge
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `merge-pr.sh` never fetches after a successful merge. Downstream scripts expecting fresh `origin/main` or merge-OID objects may fail until manual fetch. Add optional post-merge `git fetch origin main`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### OOS_4: [OUT_OF_SCOPE] Harness fixtures use wrong `is_latest` API shape
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Offline `test-release-prepare` fixtures use `is_latest` on `gh api` shape while production lacks that field, so CI cannot catch FINDING_7. Add cases with `gh release list` JSON field names or integration smoke against real `gh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### OOS_5: [OUT_OF_SCOPE] `release-tag.yaml` still builds notes from `CHANGELOG.md`
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: nit
- **Concern**: When the workflow wins the release-creation race, notes come from `CHANGELOG.md` until `/release` overwrites via `gh release edit`. Pre-existing overlap, not introduced by core helpers on this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Address the concern above.

### OOS_6: [OUT_OF_SCOPE] Plan vs `release-finish.md` documentation drift on fallback
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: nit
- **Concern**: Implementation plan still describes `mergeCommit` with `origin/main` fallback; branch dropped fallback in round 1. Documentation drift only; behavior is defined by script and contract file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Address the concern above.

---

**Merge summary (for voters):** 49 raw inputs → **30 in-scope** findings + **6 out-of-scope**. Highest-impact clusters: **FINDING_7** (baseline API field), **FINDING_8–9** (post-merge git handoff), **FINDING_14–16** (harness gaps), **FINDING_19–20** (fail-open guards / partial promote). Code read confirms `is_latest` at ```108:108:.claude/skills/release/scripts/release-prepare.sh``` and `git show` without prior fetch at ```153:156:.claude/skills/release/scripts/release-finish.sh```.
