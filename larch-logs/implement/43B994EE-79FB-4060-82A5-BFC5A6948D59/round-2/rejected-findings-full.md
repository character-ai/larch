### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: --bump override duplicates version increment logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh`’s `--bump` override reimplements `NEW_VERSION` increment rules separately from `classify-bump.sh`. If increment rules change in one place (e.g. pre-release handling), `/release --bump` can disagree with `/bump-version` for the same `CURRENT_VERSION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: Default `classify-bump` path uses `10#` semver arithmetic beyond plan scope
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: The default classify path now uses `10#` semver arithmetic not described in the plan. Versions with leading-zero components can classify/bump differently than before. Either scope `10#` to `--base`/`--head` only or document and test the default-path change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: `--dry-run` with dirty tree vs `origin/main`-anchored diff
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `SKILL.md` allows `--dry-run` on a dirty tree while `classify-bump` reads workspace `plugin.json` for `CURRENT_VERSION`/`NEW_VERSION` but aggregate diff uses `origin/main` via `--head`. Preview versions can diverge from what a clean-tree cut would produce.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: PR list extraction requires `(#N)` at end of subject only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `release-prepare.sh` extracts PR numbers only when `(#N)` appears at the end of the squash subject. Valid merges without that suffix are silently omitted from release notes (possibly `PR_COUNT=0` with no `pr-metadata-incomplete` error). Document the convention, relax `sed` to match the last `(#digits)`, and/or warn when the log range is non-empty but `PR_COUNT=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: `test-release-prepare` does not exercise real `classify-bump` diff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Prepare tests fake `gh`/partial `git`, but `classify-bump` integration uses real `git` on synthetic OIDs. `classify-bump` can break while tests still pass with an empty diff and `BUMP_TYPE=PATCH`. Fake `git diff`/`show` for the baseline..`origin/main` range or use a full mini-repo and assert the expected bump on success paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_21: `release-already-cut` may miss per-PR bumps without Release commit
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: When `origin/main` version is ahead of the baseline tag only via per-PR bumps (no `Release v*` commit in range), `release-already-cut` may not fire, leaving confusing semver state on re-run. Optional warn when origin version is ahead of baseline tag only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: Test-only env overrides for repo and promote script
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `LARCH_RELEASE_FINISH_ORIGIN_REPO` and `LARCH_RELEASE_FINISH_PROMOTE_SCRIPT` override remote resolution and the promote helper. Malicious env could satisfy string repo checks while running an arbitrary promote script. Limit overrides to offline tests; document as non-production in `release-finish.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: PR metadata in public release notes with limited sanitization
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: PR titles/authors/URLs feed public GitHub Release notes with only mechanical `redact-secrets` coverage. Internal URLs or PII in PR titles could appear on the public release. Strengthen orchestrator sanitization beyond token families.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: `gh release create` flags misaligned with `release-tag.yaml`
- **Reviewer(s)**: dyn-tag-release-race-output.txt
- **Severity**: latent
- **Concern**: `gh release create` omits `--latest=false --prerelease` while `release-tag.yaml` creates prereleases non-latest. If `/release` wins the race, semantics differ until promote runs; prerelease flags may remain wrong briefly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-tag-release-race-output.txt: Align flags with the workflow (`--latest=false --prerelease` on create; keep edit path for races).

---


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: `semver_lt` duplicated across bump/release paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `semver_lt` in `release-set-version.sh` is a fourth copy vs `apply-bump` / `ship-pr`, increasing drift risk for leading-zero and comparison edge cases.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: Release notes redacted twice
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Release notes may pass through `redact-secrets.sh` in the orchestrator and again in `release-finish.sh`. If redaction rules diverge, the two passes could produce inconsistent output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_7

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_7: Baseline resolution uses nonexistent `is_latest` on REST release objects
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` filters `gh api /repos/.../releases` with `jq select(.is_latest == true)`. Live REST payloads use `isLatest` (via `gh release list --json`), not `is_latest`, so `LATEST_COUNT` is always 0 and live `/release` exits `ERROR=no-unique-latest-release` before PR/bump work. Offline fixtures use `is_latest`, so tests can pass while production fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: Missing `origin/main` fallback when `mergeCommit` is empty or slow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-tag-release-race-output.txt
- **Severity**: important
- **Concern**: Plan/contract expect `mergeCommit` resolution with `origin/main` fallback for `TARGET_OID`. Implementation polls `mergeCommit` ~10s then fails closed with `ERROR=merge-commit-missing` only. GitHub API lag, delayed `mergeCommit` after squash merge, or removal of prior fetch+fallback leaves valid merged releases aborting even when `origin/main` already has the bumped `plugin.json` commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-tag-release-race-output.txt: Extend backoff (e.g. 30–60s total), and/or after merge add a guarded fallback: `git fetch origin main` then require `origin/main^{commit}` equals `mergeCommit.oid` (or equals `TARGET_OID`) before proceeding—only when version at that commit matches `--version`.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

