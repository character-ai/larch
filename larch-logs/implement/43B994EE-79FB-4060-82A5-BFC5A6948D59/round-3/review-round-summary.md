# Review Round 3

- Mode: `diff`
- 8 accepted, 11 rejected (11 exonerated)

## Accepted Findings

### FINDING_10: Missing harness for `classify-bump --head origin/main`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` invokes `classify-bump.sh --base "$BASELINE_TAG" --head origin/main` but `test-classify-bump.sh` has no case where `--head origin/main` must exclude commits not on `origin/main`. Regression could mis-classify aggregate bump when local `HEAD` and `origin/main` diverge.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add Test 7: fixture repo where --head origin/main must exclude commits not on origin/main; assert expected BUMP_TYPE.

---


### FINDING_11: `create-pr.sh` may skip secrets redaction silently
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: After mandatory tmpdir redaction, secrets redaction runs only when `redact-secrets.sh` is executable (`if [[ -x "$REDACT_SECRETS_HELPER" ]]` at lines 121–129). A `/release` run with unredacted `notes.md` and a non-executable helper can publish raw tokens in the public release PR body before `release-finish` redacts again.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require redact-secrets.sh to exist and be executable; abort on redaction failure; never skip silently.

---


### FINDING_17: Default-path semver increment changed vs compatibility plan
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Default-path bump block (lines 304–309) was altered to `ver_*` / `10#` arithmetic despite plan requiring byte-for-byte unchanged default behavior without `--base`. Branches with leading-zero version components could get a different `NEW_VERSION` than before this PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Restore the original default-path bump block verbatim, or gate 10#/ver_* changes behind the --base/--head branch only.

---


### FINDING_18: SKILL gaps vs plan for operator confirm and CI wait
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Plan called for `PR_COUNT=0` confirm to default to Cancel; SKILL only warns. Plan Step 5 specified `ci-wait` timeout `1860000`; SKILL Step 5 omits it, risking orchestrator Bash timeout on long release CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Add explicit Step 4 guidance to default to Cancel when PR_COUNT=0 unless the operator explicitly overrides.
  - From cursor-specialist-plan-fidelity-output.txt: Document timeout: 1860000 (or equivalent) on the Step 5 ci-wait Bash block.

---


### FINDING_2: `release-finish.sh` TARGET_OID resolution fragile after squash merge
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-release-finish-oid-resolution-output.txt
- **Severity**: important
- **Concern**: Step 6 depends on `gh pr view` `mergeCommit.oid` with ~10s polling, then `git rev-parse --verify` on that OID **before** `git fetch origin main` (lines 137–172). If `mergeCommit` stays empty after poll, the script exits `ERROR=merge-commit-missing` with no `origin/main` fallback even when main already has the release commit and matching `plugin.json` (plan-required behavior). If `mergeCommit` is returned but the squash OID is not yet local, `ERROR=invalid mergeCommit.oid` can fire before fetch populates the object. When `origin/main^{commit}` ≠ `TARGET_OID`, bare `git fetch origin "$TARGET_OID"` (stderr discarded) may fail on reachability/timing and surface generic `ERROR=could not resolve TARGET_OID after fetch`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: After poll timeout fetch origin/main and use as TARGET_OID with same plugin.json version check per original plan
  - From cursor-specialist-plan-fidelity-output.txt: After mergeCommit polling fails, fetch origin/main and use its OID when plugin.json .version matches --version; retain fail-closed checks for wrong remote/local tags.
  - From dyn-release-finish-oid-resolution-output.txt: Move `git fetch origin main` (and tag fetch if needed) immediately after resolving `merge_oid`, then `git rev-parse --verify` / `git show` for `plugin.json`; only use the SHA-specific fetch when `origin/main^{commit}` ≠ `TARGET_OID` after a successful main fetch, with bounded retries aligned with the `mergeCommit` poll loop.
  - From dyn-release-finish-oid-resolution-output.txt: After reordering fetches (above), prefer repeated `git fetch origin main` (with the same backoff used for `mergeCommit`) until `git merge-base --is-ancestor "$TARGET_OID" origin/main` or `origin/main^{commit}` equals `TARGET_OID`; treat SHA-only fetch as a last resort; surface `git fetch` stderr on failure and distinguish errors (e.g. `ERROR=target-oid-not-on-origin-main` vs `ERROR=fetch-failed`).

---


### FINDING_6: Bump preview uses worktree `plugin.json` while diff uses `--head`
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, dyn-classify-bump-head-coordination-output.txt
- **Severity**: important
- **Concern**: `classify-bump.sh` reads `CURRENT_VERSION` from working-tree `.claude-plugin/plugin.json` (lines 68–69) while `git diff` uses `HEAD_COMPARE` when `--head` is set (e.g. `origin/main`). SKILL allows `--dry-run` on a dirty tree; prepare/classify can then show wrong `CURRENT_VERSION`/`NEW_VERSION`. `release-prepare.sh` checks `main` vs `origin/main` but not `HEAD^{commit}` vs `origin/main^{commit}`, so direct prepare calls off `release/v*` or with uncommitted `plugin.json` edits can diverge from the classified commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require clean tree for prepare or warn that bump preview is invalid when dirty.
  - From cursor-specialist-edge-cases-output.txt: Anchor CURRENT_VERSION to origin/main (or --head) in release-prepare or classify-bump when --head is set
  - From dyn-classify-bump-head-coordination-output.txt: When `--head` is set, read `.version` from `git show "$HEAD_COMPARE:.claude-plugin/plugin.json"` (fail closed on mismatch with the worktree file), and have `release-prepare.sh` also require `HEAD^{commit}` == `origin/main^{commit}` (or run prepare only from a documented `git checkout main` wrapper).

---


### FINDING_7: `release-already-cut` misses squash-merge commit subjects
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` line 163 uses anchored `^Release vX.Y.Z$` but squash merges produce subjects like `Release v1.2.3 (#456)`. When `origin/main` plugin version is ahead of baseline but Latest tag is stale, prepare may not emit `ERROR=release-already-cut`, allowing a duplicate release PR.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use grep or regex allowing optional trailing ( #N ) consistent with PR extraction; add harness case Release v1.1.0 (#1)

---


### FINDING_9: Contract/docs drift on `BUMP_TYPE=NONE` and default-path bump math
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `release-prepare.md` / `classify-bump.md` imply `BUMP_TYPE` may be `NONE` on paths where `--base` skips idempotency (misleading for `/release` consumers). Docs claim default path unchanged while `classify-bump.sh` default-path version math now uses `ver_*` and `10#` arithmetic (lines 304–309), risking behavior drift vs pre-PR `/implement` / `/bump-version` for unusual version strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Note NONE is default-path only not /release consumer
  - From cursor-specialist-plan-fidelity-output.txt: Update classify-bump.md to match actual default-path semantics or revert default-path code per finding 1.

---


