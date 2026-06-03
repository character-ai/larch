# Review Round 2

- Mode: `diff`
- 17 accepted, 13 rejected (12 exonerated)

## Accepted Findings

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


### FINDING_2: `--head` flag undocumented for release-prepare consumer
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `classify-bump.sh` accepts `--head` (used by `release-prepare` for `origin/main`-anchored aggregate diffs) but the flag is not documented in `classify-bump.md` or `--help`. Future refactors may remove or break `--head` without a failing default-path test, breaking release aggregate bumps.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_20: Tag/release can succeed then `promote-release` fails without recovery contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If `promote-release.sh` fails after tag and `gh release create`/`edit`, the tag and prerelease exist but are not Latest and success KVs may not emit. Document/retry a promote-only path and idempotent finish when tag+release already exist at `TARGET_OID`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_22: `LARCH_RELEASE_FINISH_AT_VERSION` bypasses tree version check
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_RELEASE_FINISH_AT_VERSION` skips reading `plugin.json` at `TARGET_OID`. Env pollution during `/release` could pass the version string check while tagging a merge commit whose tree lacks the expected bump.
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


### FINDING_8: No `git fetch` before `git show` / tag at `mergeCommit` OID
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-tag-release-race-output.txt
- **Severity**: important
- **Concern**: After `merge-pr.sh`, `release-finish.sh` uses `TARGET_OID` from `gh pr view … mergeCommit.oid` and immediately runs `git show "${TARGET_OID}:.claude-plugin/plugin.json"` without fetching that commit. `merge-pr.sh` only fetches `origin main` pre-merge; the squash-merge OID is often absent locally, causing spurious `ERROR=could not read plugin.json at TARGET_OID` (or tag failures) despite a successful merge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-tag-release-race-output.txt: After resolving `TARGET_OID`, run `git fetch origin main` (or `git fetch origin "$TARGET_OID"` when supported) and verify `git rev-parse "origin/main^{commit}"` equals `TARGET_OID` before `git show`; fail closed on fetch/verify mismatch.


