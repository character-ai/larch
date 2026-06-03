Verifying a few high-impact claims against the codebase to normalize findings accurately.
Normalized aggregator output from 59 raw inputs (positive-only OOS attestations omitted).

### FINDING_1: Fake git stub omits HEAD rev-parse
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-shell-portability-output.txt, dyn-fixture-fidelity-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` compares `HEAD^{commit}` to `origin/main^{commit}` (lines 138–144), but `test-release-prepare.sh` fake `git` only implements `rev-parse` for `main`, `origin/main`, and the baseline tag. Paths that reach the HEAD guard hit `unexpected git: rev-parse HEAD^{commit}` (exit 9) instead of success KVs or domain errors. Harness reports ~3/11 passes; cases meant to exercise PR extraction, `--bump`, and open-PR guards do not run the subject.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Stub HEAD (and HEAD≠origin case); rerun until 11/11 pass
  - From cursor-specialist-correctness-output.txt: Stub HEAD to GIT_ORIGIN_MAIN_OID; add HEAD-mismatch stale-local-main test.
  - From cursor-specialist-testing-output.txt: Add GIT_HEAD_OID to fake git; add HEAD!=origin case; fix all 11 cases to pass.
  - From dyn-shell-portability-output.txt: Extend the fake `git` `rev-parse` branch to treat `HEAD` like `origin/main` (e.g. echo `"${GIT_HEAD_OID:-${GIT_ORIGIN_MAIN_OID}}"`).
  - From dyn-fixture-fidelity-output.txt: In the fake `rev-parse` handler, treat `HEAD` (after stripping `^{commit}`) like `main`/`origin/main` when `GIT_MAIN_OID` equals `GIT_ORIGIN_MAIN_OID`, or add an explicit `GIT_HEAD_OID` env defaulting to `GIT_ORIGIN_MAIN_OID`, and document that prepare tests must set it when simulating a detached or mismatched checkout.

### FINDING_2: test-release-set-version harness does not exercise the subject script
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: The harness builds a temp tree with its own `plugin.json`, but `release-set-version.sh` always writes `$REPO_ROOT/.claude-plugin/plugin.json` derived from the script path (the real larch checkout). Assertions read the temp file while the subject mutates the live tree; on a checkout above the test downgrade target the subject correctly refuses and the harness dies under `set -e` with a false “passes” story.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add test override or cwd-relative PLUGIN_JSON for fixtures
  - From cursor-specialist-correctness-output.txt: Test via env override or git worktree; assert the file the script actually mutates.
  - From dyn-shell-portability-output.txt: Either add a test-only `PLUGIN_JSON` override (or optional path argv) and point tests at the temp file, or stop using a temp repo and instead snapshot/restore the real `plugin.json` around each case.

### FINDING_3: Baseline Latest uses nonexistent `is_latest` on REST releases
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` (lines 104–115) selects baseline via `gh api /repos/.../releases` and `jq` filter `.is_latest == true`. REST release objects from `gh api` do not expose `is_latest` (while `gh release list --json tagName,isLatest` does). Live runs can yield `ERROR=no-unique-latest-release` with `LATEST_COUNT=0` even when exactly one Latest exists. Fixtures fake `is_latest`, masking the production bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Resolve baseline the same way as `promote-latest-release.sh` / `scripts/promote-release.sh`: `gh release list --repo "$REPO" --json tagName,isLatest` (paginate/limit as needed), require exactly one `isLatest`, and bind `BASELINE_TAG` from that; drop the nonexistent `is_latest` field from fixtures/docs too.

### FINDING_4: Duplicated `--bump` NEW_VERSION math vs classify-bump
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` (247–258) recomputes `NEW_VERSION` for `--bump` override separately from `classify-bump.sh` / `apply-bump.sh`. Future bump-rule changes in one path only can break the operator override path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extend classify-bump with forced bump type or shared lib-semver helper

### FINDING_5: `--bump` override can emit non-canonical versions (leading zeros)
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `--bump` override (253–257) uses `10#` arithmetic for increments but concatenates raw `ver_maj` / `ver_min` from `IFS='.' read` without normalizing components. Versions matching `[0-9]+\.[0-9]+\.[0-9]+$` with leading-zero segments (e.g. `01.2.3`) can produce non-canonical `NEW_VERSION` (e.g. `01.3.0`) or octal pitfalls where `10#` is not applied on output components.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: After `read`, normalize with `10#` for all three components when building `NEW_VERSION`, matching the semver compare block at lines 162–166.

### FINDING_6: Duplicate semver_lt in release scripts
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `release-set-version.sh` defines a third copy of semver comparison logic already duplicated elsewhere in the repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract scripts/lib-semver.sh

### FINDING_7: Repetitive per-PR jq blocks in release-prepare
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `release-prepare.sh` (187–220) repeats similar jq extraction per PR field, increasing maintenance cost for PR metadata columns.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Single jq-to-TSV pass or small helper

### FINDING_8: TARGET_OID resolution fragile (inline logic, shallow-clone fetch skip)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-release-idempotency-output.txt
- **Severity**: important
- **Concern**: `release-finish.sh` embeds heavy TARGET_OID resolution (161–231) that is easy to regress vs `release-finish.md`. After the poll exhausts, fallback (206–224) may skip `git fetch origin "$TARGET_OID"` when non-`--verify` `rev-parse` outputs match `origin/main^{commit}` even though `git rev-parse --verify "${TARGET_OID}^{commit}"` still fails (shallow/partial clone, object not in local ODB), yielding `ERROR=fetch-failed: could not resolve TARGET_OID after fetch` despite a known-good OID on the remote.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Extract tested resolve_release_target_oid helper
  - From dyn-release-idempotency-output.txt: In the `target_oid_resolved != true` block, gate the fetch skip on successful `--verify` for both sides (or always run `git fetch origin "$TARGET_OID"` / deepen `origin/main` when `--verify` fails), and only then re-check ancestor/`origin/main` equality.

### FINDING_9: Redundant notes redaction in release-finish
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `release-finish.sh` (129–133) runs `redact-secrets.sh` again after SKILL Step 3 and `create-pr.sh` may already have redacted notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Skip when pre-redacted or document-only

### FINDING_10: Public release text missing redact-tmpdir-paths
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Release notes and PR bodies only pass through `redact-secrets.sh` (SKILL Step 3; `release-finish.sh`). Session tmpdir paths or operator repo paths in LLM-composed notes can reach public GitHub Release and PR body without `redact-tmpdir-paths.sh`, unlike `create-pr.sh` alignment.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pipe notes through redact-tmpdir-paths.sh then redact-secrets.sh in SKILL Step 3 and release-finish.sh; align with create-pr.sh.

### FINDING_11: mergeCommit.oid not validated before git fetch/tag
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `release-finish.sh` assigns `TARGET_OID` from `gh pr view` `mergeCommit.oid` without validating it as a hex commit SHA before `git fetch`/tag operations. Unexpected `gh` output could drive git with a non-SHA ref token.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Require ^[0-9a-fA-F]{7,40}$ or fail after gh pr view before TARGET_OID assignment.

### FINDING_12: PR list inferred from commit subject (#N) suffixes only
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `release-prepare.sh` (175–178, broader 175–220) builds the PR list from `git log` subjects with trailing `(#N)` only. Squash/merge commits without that suffix are omitted from release notes while still affecting `classify-bump` diff scope—incomplete Added/Changed/Fixed sections and possible `PR_COUNT=0` with non-empty aggregate diff. A merge-capable actor could also mis-attribute PRs in public notes if subjects are crafted; maintainer trust boundary is undocumented.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document or broaden subject parsing.
  - From cursor-specialist-security-output.txt: Document maintainer trust boundary; optionally verify PR mergeCommit matches log commit.
  - From cursor-specialist-edge-cases-output.txt: Widen (#N) parsing or warn when log commit count exceeds PR_COUNT.

### FINDING_13: jq -e on .author.login fails for null author
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `release-prepare.sh` (206–208) uses `jq -e -r '.author.login'`. One PR with deleted/null author aborts the entire release with `pr-metadata-incomplete`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Use .author.login // "unknown" or tolerate missing author.

### FINDING_14: release-already-cut guard too narrow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `release-already-cut` (167–168) matches only exact `Release vX.Y.Z` commit subjects. Non-standard squash titles can skip the guard while `origin/main` `plugin.json` is already ahead, allowing duplicate cut proposals; should also consider version on `origin/main` vs proposed `NEW_VERSION`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add version-based or PR-metadata guard.
  - From cursor-specialist-edge-cases-output.txt: Also fail when origin/main plugin.json version is already >= proposed NEW_VERSION.

### FINDING_15: LLM release-note composition prompt-only
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: SKILL Step 3 treats untrusted PR titles in prose but lacks mechanical enforcement beyond operator discipline; malicious PR titles can manipulate preview or confirmed public notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Enforce injection envelope; show raw titles in Step 4 preview; optional length caps.

### FINDING_16: Test env vars can override production paths in release-finish
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `release-finish.sh` test env vars can override origin repo and promote script in any shell; poisoned env in shared CI/operator shell could weaken repo coupling or run an arbitrary promote helper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict overrides to test mode or document never export in production shells.

### FINDING_17: release-tag workflow vs finish TARGET_OID race
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Concurrent `release-tag.yaml` may tag `origin/main` tip while `release-finish.sh` targets `mergeCommit.oid`. Another commit on main after the release PR merges can place remote `vX.Y.Z` at tip B while finish targets merge A with the same `plugin.json` version, failing with remote tag on a different commit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document recovery in SKILL Step 6; optionally accept origin/main tip when version matches and remote tag already exists there.

### FINDING_18: Full /release retry blocked after merged release PR when finish fails
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: If Step 6 `release-finish` fails after Step 5 merge, re-running `/release` hits `release-already-cut` in prepare before Step 6; operator cannot resume promote/tag without manual `release-finish.sh` / `promote-release.sh`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add Step 6 failure instructions to re-run release-finish.sh or promote-release.sh directly.

### FINDING_19: Stale local tag blocks idempotent finish when remote tag is correct
- **Reviewer(s)**: dyn-release-idempotency-output.txt
- **Severity**: important
- **Concern**: Tag idempotency checks remote peeled OIDs but a stale local tag on a different commit aborts at 266–268 before `gh release` edit/create or promote, even when `remote_oid` equals `TARGET_OID` (e.g. workflow already pushed tag). Re-run cannot self-heal without manual local tag deletion.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-idempotency-output.txt: When `remote_oid` is non-empty and equals `TARGET_OID`, treat the remote as authoritative: skip the hard error (or `git tag -f "$TAG" "$TARGET_OID"` to realign the local ref), then continue to `gh release` and `promote-release.sh` as today.

### FINDING_20: Tag push stderr discarded
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `release-finish.sh` (283–291) discards push stderr; auth/network failures surface only as generic tag push failed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Surface push stderr in the ERROR line.

### FINDING_21: No handling for existing release/v* branch on retry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Partial Step 5 can leave `release/v*`. A second `/release` run fails at `git checkout -b` with no documented cleanup/reuse.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Document branch cleanup or reuse existing release branch.

### FINDING_22: classify-bump default path changed vs plan byte-for-byte requirement
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `classify-bump.sh` default path was refactored (argv parsing, reordered version read, `HEAD_COMPARE`) and now rejects unknown args. Plan acceptance required unchanged default behavior for `/implement` and `/bump-version`; subtle output/ordering changes or formerly ignored argv could break Step 8 without golden default-path harness signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Restore verbatim default-path code behind no-flag entry, or amend the plan to behavioral equivalence and add golden default-path harness assertions.

### FINDING_23: Success-path prepare tests may flap on real classify-bump diff
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: After HEAD stub is fixed, success-path prepare tests still delegate `classify-bump` diff to real git with synthetic OIDs; `BUMP_TYPE`/`NEW_VERSION` can vary with checkout state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Shim classify-bump or fake diff-tree output deterministically.

### FINDING_24: No harness for promote-release-failed retry contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-release-idempotency-output.txt
- **Severity**: latent
- **Concern**: `test-release-finish.sh` lacks a two-invocation case: first run `PROMOTE_RC=1` (tag + `gh release` succeed), second run with release existing expects `RELEASE_ACTION=edit` and promote success per `release-finish.md` (43–45).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add PROMOTE_RC=1 case asserting ERROR=promote-release-failed.
  - From dyn-release-idempotency-output.txt: Add an offline two-invocation case: first run with `PROMOTE_RC=1` (expect exit 1, no success KV); second with `GH_FIXTURE_RELEASE_EXISTS=1` and `PROMOTE_RC=0` (expect exit 0 and `RELEASE_ACTION=edit`).

### FINDING_25: No harness for baseline-tag-unresolvable after successful fetch
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: No fixture where fetch succeeds but baseline tag `rev-parse` fails; operator typo/missing tag error path untested offline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture with successful fetch and failed baseline rev-parse --verify.
  - From cursor-specialist-plan-fidelity-output.txt: Add harness case: fetch ok, rev-parse fails, expect ERROR=baseline-tag-unresolvable.

### FINDING_26: Plan-required atomicity coverage missing for release-set-version
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan/testing strategy calls for atomic write coverage; harness has no partial-failure / byte-identical-on-error assertion. Failed `jq` or interrupted `mv` could corrupt `plugin.json` without offline detection (distinct from FINDING_2 path mismatch).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add atomicity test or document as manual-only in harness contract.
  - From cursor-specialist-plan-fidelity-output.txt: Add a harness case with a failing jq stub or pre-mv failure and assert plugin.json is byte-identical on non-zero exit; document in test-release-set-version.md.

### FINDING_27: Live tag push and gh release only partially fixture-tested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Per plan, live `git push` tag and `gh release create/edit` are only partially covered; `gh` flag/API drift could break release cut without automated signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: PR test-plan checklist or future gated integration smoke.

### FINDING_28: Fake git in test-release-finish lacks merge-base semantics
- **Reviewer(s)**: dyn-fixture-fidelity-output.txt
- **Severity**: latent
- **Concern**: Fake `git` has no `merge-base` case; `release-finish.sh` ancestor checks fall through to exit 9 but are masked by OID-equality shortcuts. All harness cases use identical `GIT_TARGET_OID` and `GIT_ORIGIN_MAIN_OID`, so ancestor semantics (squash behind tip but on history) are never validated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-fidelity-output.txt: Add a `merge-base)` branch that returns **0** when `GIT_MERGE_BASE_IS_ANCESTOR=1` (or when `GIT_TARGET_OID` equals `GIT_ORIGIN_MAIN_OID`), returns **1** when `GIT_MERGE_BASE_IS_ANCESTOR=0`, and add at least one case where `TARGET_OID` ≠ `origin/main` tip but should still be accepted only via `--is-ancestor`.

### FINDING_29: Fake git log silently delegates to real git on mismatch
- **Reviewer(s)**: dyn-fixture-fidelity-output.txt
- **Severity**: latent
- **Concern**: In `test-release-prepare.sh`, the `log` handler only matches exact `"${GIT_BASELINE_TAG}..origin/main"` + `--format=%s`; any mismatch `exec`s `$REAL_GIT`, making PR count / `release-already-cut` machine-dependent on the host repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fixture-fidelity-output.txt: On mismatch, `exit 1` with a clear “unexpected git log” message (or require an explicit `GIT_LOG_FORCE_REAL=1`) instead of delegating to `$REAL_GIT` inside offline tests.

### FINDING_30: Baseline docs/API mismatch (gh api vs gh release list)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Implementation uses `gh api /releases` + `is_latest` instead of plan-specified `gh release list --json tagName,isLatest`; future CLI/API differences could diverge from documented operator expectations (related to FINDING_3).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Align implementation with gh release list or update plan and release-prepare.md to name the REST API as canonical.

---

### OOS_1: [OUT_OF_SCOPE] Pre-existing semver_lt duplication in ship-pr.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `scripts/ship-pr.sh:845+` duplicates semver compare logic; not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Consolidate in a follow-up

### OOS_2: [OUT_OF_SCOPE] promote-release.sh lacks unique isLatest guard
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-release-idempotency-output.txt
- **Severity**: latent
- **Concern**: `scripts/promote-release.sh` (~79) does not fail closed when multiple `isLatest=true` releases exist; ambiguous `CURRENT_LATEST` string compare if GitHub metadata is corrupt. `/release` depends on promote more heavily but ambiguity predates this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add fail-closed Latest count in promote-release.sh later
  - From cursor-specialist-correctness-output.txt: Use jq -r '.[0]' or fail on count != 1.
  - From cursor-specialist-edge-cases-output.txt: Count isLatest rows and exit 1 if count != 1.
  - From dyn-release-idempotency-output.txt: (same concern as above; no additional distinct proposal beyond count enforcement)

### OOS_3: [OUT_OF_SCOPE] Pre-existing classify-bump leading-zero math
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: latent
- **Concern**: `classify-bump.sh:316-320` uses `$((MAJ + 1))` without `10#`; same leading-zero/octal class if versions ever carry leading zeros; not introduced by this branch’s diff hunk.
- **Suggested revisions (informational for voters; coder decides)**:
  - (No slot provided a distinct fix beyond noting pre-existing scope; dyn-shell-portability listed it as follow-up class only.)

### OOS_4: [OUT_OF_SCOPE] No automated test for release-tag.yaml vs release-finish race
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `.github/workflows/release-tag.yaml` ordering/race with orchestrator finish is manual-only; pre-existing gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Future workflow fixture or fork smoke (pre-existing gap).

### OOS_5: [OUT_OF_SCOPE] create-pr.sh redaction supporting change
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `scripts/create-pr.sh:2424-2434` now redacts secrets in PR bodies; not in plan file list but supports release notes safety. No action required for Phase 3 unless scope control matters.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: N/A (supporting change). No action required for Phase 3 unless scope control matters.

### OOS_6: [OUT_OF_SCOPE] test-promote-release.sh does not assert gh --repo threading
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-promote-release.sh:2757-2787` promote-release `--repo` harness does not assert `gh` argv threading; regression could drop `--repo` on one call without failing tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Extend fake gh to require --repo when fixture expects it.

---

**Merge notes (for voters):** Raw inputs 50–52 and 56–59 were positive traces or non-actionable attestations and were omitted. Inputs 1/10/16/42/53 → FINDING_1; 2/11/43 → FINDING_2; 18/48 → FINDING_24; 19/38 → FINDING_25; 20/36 → FINDING_26; 6/46 → FINDING_8; 9/15/34/49 → OOS_2; 13/25/30 → FINDING_12; 14/33 → FINDING_14; 41 stands alone as FINDING_3 (also overlaps FINDING_30 doc drift). Highest-priority in-scope cluster for release cut viability: **FINDING_3** (live baseline), **FINDING_1** + **FINDING_2** (harness green), then **FINDING_10**, **FINDING_11**, **FINDING_17**–**FINDING_19** (operator/security/idempotency).
