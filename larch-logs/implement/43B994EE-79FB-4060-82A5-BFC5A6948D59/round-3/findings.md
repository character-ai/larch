Normalizing reviewer findings: reading key files to verify overlaps and merge groups.
Structured aggregator output (normalized, merged by behavioral risk; source IDs preserved in **Reviewer(s)** lines).

---

### FINDING_1: Duplicated semver increment for `--bump` override
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` reimplements MAJOR/MINOR/PATCH arithmetic for `--bump` override (lines 242–253) instead of calling the same helper used by `classify-bump.sh` / `apply-bump.sh`. Future bump-rule changes in classify/apply paths will not automatically apply to operator overrides, risking wrong `NEW_VERSION` at release cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract shared bump-from-type helper (e.g. apply-bump `_apply_bump_type`) and call it from release-prepare override path.

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

### FINDING_3: Dual secrets-redaction paths for release notes
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Notes are redacted in SKILL Step 3 and again in `release-finish.sh` (line 129+). If `redact-secrets.sh` behavior changes, both call sites must stay aligned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Single authoritative redaction site; document optional second pass only if required.

---

### FINDING_4: Script index mixes active cut flow with legacy promote helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: SKILL script index lists `promote-latest-release.sh` alongside new cut-a-release scripts without a clear active vs legacy split; operators may invoke obsolete promote-newest flow during a cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split script index into active vs legacy sections.

---

### FINDING_5: `BUMP_TYPE=NONE` not fail-fast at prepare
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: When `classify-bump.sh` emits `BUMP_TYPE=NONE` (default-path idempotency), `release-prepare.sh` still returns success KVs until `release-set-version` refuses later—operator may confirm, branch, and open a PR before hitting a no-op error. (Note: current `/release` path passes `--base`, which sets `SKIP_IDEMPOTENCY=true`; risk is strongest for direct script use or future caller changes.)
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Emit ERROR=no-bump-needed at prepare when NONE and no --bump override.

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

### FINDING_8: `classify-bump.sh` `--head` / idempotency / CLI safety
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-classify-bump-head-coordination-output.txt
- **Severity**: latent
- **Concern**: With only `--head` (no `--base`), idempotency still walks local `HEAD` (`IDEMPOTENCY_REF` at lines 159–169) and can emit `BUMP_TYPE=NONE` before the `--head`-scoped diff runs. `/release` always passes both `--base` and `--head`, but the CLI presents the flags as independent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Anchor idempotency walk to HEAD_COMPARE when --head set or reject --head without --base
  - From dyn-classify-bump-head-coordination-output.txt: Document that `--head` requires `--base` for aggregate release use, or auto-set `SKIP_IDEMPOTENCY=true` whenever `--head` is set (and add a harness case for `--head` alone vs `--base`+`--head`).

---

### FINDING_9: Contract/docs drift on `BUMP_TYPE=NONE` and default-path bump math
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `release-prepare.md` / `classify-bump.md` imply `BUMP_TYPE` may be `NONE` on paths where `--base` skips idempotency (misleading for `/release` consumers). Docs claim default path unchanged while `classify-bump.sh` default-path version math now uses `ver_*` and `10#` arithmetic (lines 304–309), risking behavior drift vs pre-PR `/implement` / `/bump-version` for unusual version strings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Note NONE is default-path only not /release consumer
  - From cursor-specialist-plan-fidelity-output.txt: Update classify-bump.md to match actual default-path semantics or revert default-path code per finding 1.

---

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

### FINDING_12: Single `gh pr view` failure aborts entire prepare
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` lines 182–220: any one unresolvable PR number in the git-log-derived list causes `emit_error pr-metadata-incomplete` and aborts the whole cut, even when most PRs and the bump range are valid.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Skip-with-warning plus operator confirm or fail only when all PR fetches fail

---

### FINDING_13: Release notes omit commits without `(#N)` in squash subject
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: PR list parsing (lines 170–173) only extracts trailing `(#N)` from commit subjects; merges without that suffix are missing from release notes while aggregate bump still reflects their code changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document or add secondary PR discovery for notes

---

### FINDING_14: `promote-release.sh` lacks unique-`isLatest` guard before promote
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `promote-release.sh` (lines 79–92) does not verify a unique Latest release before `gh release edit --latest`; metadata corruption between prepare and finish could yield ambiguous Latest promotion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Reuse unique-Latest guard before gh release edit --latest

---

### FINDING_15: Branch/main guards only in SKILL, not `release-prepare.sh`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: “Must be on `main`” is enforced in SKILL Step 1, not inside `release-prepare.sh`; direct script invocation off `main` can emit misleading version KVs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add main/HEAD==origin/main guard inside release-prepare.sh

---

### FINDING_16: No early check for existing `vNEW_VERSION` tag
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Operator can run full PR+CI before `release-finish` fails on duplicate tag; no `ls-remote` tag probe during prepare after `NEW_VERSION` is known.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: ls-remote tag check during prepare after NEW_VERSION computed

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

### FINDING_19: Reasoning log omits compare commit when `--head` is set
- **Reviewer(s)**: dyn-classify-bump-head-coordination-output.txt
- **Severity**: nit
- **Concern**: `classify-bump.sh` reasoning log records base commit only (lines 115–122), not `HEAD_COMPARE` / `--head`, so release debugging can imply classification used local `HEAD`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-classify-bump-head-coordination-output.txt: Add a “Compare commit” line using `HEAD_COMPARE` (short OID + subject) when `--head` is set.

---

### OOS_1: [OUT_OF_SCOPE] Duplicated `semver_lt` across bump scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Pre-existing `semver_lt` in `apply-bump.sh` (lines 42–52) duplicates `release-set-version` pattern; repo-wide semver comparison may drift across bump paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate semver helpers in a follow-up.

---

### OOS_2: [OUT_OF_SCOPE] Legacy `promote-latest-release.sh` vs new `/release` flow
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Legacy promote-newest script coexists with new cut-a-release flow; two promotion models in one skill directory.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Deprecate or clearly fence legacy script in docs only.

---

### OOS_3: [OUT_OF_SCOPE] `apply-bump.sh` origin race retry not mirrored on release path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `apply-bump.sh` retries on `origin/main` same-version race; release PR path has no analogous retry if concurrent merges land during CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Out of scope; optional follow-up retry in create-pr/ci-wait

---

### OOS_4: [OUT_OF_SCOPE] No offline harness for `--base` + `--head origin/main` together
- **Reviewer(s)**: dyn-classify-bump-head-coordination-output.txt
- **Severity**: nit
- **Concern**: `test-classify-bump.sh` Test 6 uses `--base` only; `test-release-prepare.sh` fakes `git` but uses host `git diff`—head/base coordination regressions may only surface in live operator runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No distinct fix bullet beyond the concern; overlaps FINDING_10 in-scope test gap.)

---

**Subsumed without separate blocks** (same risk already covered, or explicit “no defect” attestation): input FINDING_31, 32, 37, 38 (no in-scope action); FINDING_33 folded into FINDING_2 plan-fidelity strand; duplicate `release-finish` polls merged into FINDING_2; FINDING_23 merged into FINDING_8.
