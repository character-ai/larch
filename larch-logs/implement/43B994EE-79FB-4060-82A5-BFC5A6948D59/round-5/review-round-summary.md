# Review Round 5

- Mode: `diff`
- 14 accepted, 10 rejected (10 exonerated)

## Accepted Findings

### FINDING_12: risk-integration: .claude/skills/release/scripts/test-release-prepare.sh:222-240
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Case 4 only tests main != origin/main; release-prepare also errors when HEAD != origin/main. Operator on branch main with stale/detached HEAD passes Case 4 fixtures but hits stale-local-main at runtime; CI gives false confidence. Add harness case: main == origin/main, HEAD != origin/main → exit 1, ERROR=stale-local-main.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: .claude/skills/release/scripts/test-release-prepare.sh:55-63
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] test-release-prepare stubs classify-bump; never runs real --base/--head wiring from release-prepare.sh:235. Removing --head or breaking classify invocation would not fail make test-release-prepare; only isolated test-classify-bump Test 6 would catch --base logic. Add one integration case with real classify-bump.sh and a small git fixture.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: .claude/skills/release/scripts/test-release-finish.sh
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent]  No case for git push failure with no matching remote tag (release-finish.sh:312-318). After merge, network/auth push failure leaves no remote tag; operator gets untested error path and recovery semantics. Set GIT_PUSH_RC=1 and empty GIT_LS_REMOTE_OUT; assert exit 1 and tag push failed message.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: .claude/skills/release/scripts/test-release-finish.sh:27-54
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] gh stub returns raw OID for pr view, not mergeCommit JSON from production gh invocation. Breaking --json mergeCommit -q in release-finish.sh would pass harness but fail live /release step 6. Extend stub to honor --json mergeCommit or log argv and return JSON-shaped fixture.
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/test-promote-release.sh:59-73
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] --repo case checks exit 0 only, not gh argv threading. Regression dropping REPO_ARGS from promote-release.sh would break fork/custom-repo release promote without failing tests. Log gh argv like test-create-pr.sh; assert --repo on view/list/edit.
- **Suggested revision**: Address the concern above.


### FINDING_17: risk-integration: .claude/skills/release/scripts/release-prepare.sh:225-227
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] WARN when git log commit count exceeds PR_COUNT is untested. Operators may miss that release notes omit squash merges without (#N) while bump still reflects full diff. Add prepare fixture: two commits, one (#N); assert WARN on stderr and PR_COUNT=1.
- **Suggested revision**: Address the concern above.


### FINDING_19: security: .claude/skills/release/SKILL.md:52-54
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Step 3 trust boundary covers PR titles only but PR_LIST_FILE also includes labels author and url from gh all fed to the LLM composer A merged PR with prompt-injection text in labels or title can steer public GitHub Release notes and the release PR body; operator confirm is not a mechanical sanitizer Wrap all TSV fields in a data-not-instructions envelope; require paraphrase-only treatment for title labels and author; forbid following embedded instructions
- **Suggested revision**: Address the concern above.


### FINDING_20: architecture: .claude/skills/release/scripts/release-prepare.sh:127-175
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No check that BASELINE_TAG is an ancestor of origin/main Mis-set isLatest tag yields wrong PR list and classify range with exit 0 After tag verify run git merge-base --is-ancestor "$BASELINE_TAG" origin/main; else ERROR=baseline-not-on-main exit 1
- **Suggested revision**: Address the concern above.


### FINDING_24: **risk-integration** `.claude/skills/release/scripts/release-finish.sh:289-297` — The local-tag reconciliation branch uses `remote_oid` from the initial `ls-remote` at lines 281–282 and never re-probes before deciding whether to `git tag -f`. If the first probe sees no remote tag, a stale local `vX.Y.Z` points elsewhere, and `release-tag.yaml` pushes the correct tag to `TARGET_OID` before line 289 runs, the script exits with `ERROR=local tag … points at … not TARGET_OID` even though the remote race is already resolved. The re-probe at lines 303–309 runs only after this block, so it never runs on the failure path. **Suggested fix:** Call `remote_tag_commit_oid` again immediately before the `local_oid != TARGET_OID` branch (or move the empty-remote re-probe block above local-tag handling) so workflow wins between the first probe and local inspection follow the same recovery path as push failure (lines 313–318).
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:289-297` — The local-tag reconciliation branch uses `remote_oid` from the initial `ls-remote` at lines 281–282 and never re-probes before deciding whether to `git tag -f`. If the first probe sees no remote tag, a stale local `vX.Y.Z` points elsewhere, and `release-tag.yaml` pushes the correct tag to `TARGET_OID` before line 289 runs, the script exits with `ERROR=local tag … points at … not TARGET_OID` even though the remote race is already resolved. The re-probe at lines 303–309 runs only after this block, so it never runs on the failure path. **Suggested fix:** Call `remote_tag_commit_oid` again immediately before the `local_oid != TARGET_OID` branch (or move the empty-remote re-probe block above local-tag handling) so workflow wins between the first probe and local inspection follow the same recovery path as push failure (lines 313–318).
- **Suggested revision**: Address the concern above.


### FINDING_25: **risk-integration** `.claude/skills/release/scripts/release-finish.sh:177-186,848-850` — `mergeCommit` polling is capped at five attempts (~10s) with no `fetch origin main` inside the loop, and there is no second `gh pr view` after the post-poll fetch. If GitHub’s merge metadata lags ref updates by more than ~10s while `origin/main` already carries the bumped `plugin.json`, the script can still hit `ERROR=merge-commit-missing` and abort even though a retry would succeed; conversely, if metadata is slow but `origin/main` already matches `--version`, it silently falls back to `origin/main^{commit}` without ever binding the release PR’s `mergeCommit`. **Suggested fix:** Interleave `fetch origin main` (and optionally a short post-fetch `gh pr view`) inside the merge poll loop, or extend/document the bound with a single retry after fetch; when using the `origin/main` fallback, optionally require `gh pr view` state `MERGED` for `--pr` so finish does not tag a tip that merely matches version.
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:177-186,848-850` — `mergeCommit` polling is capped at five attempts (~10s) with no `fetch origin main` inside the loop, and there is no second `gh pr view` after the post-poll fetch. If GitHub’s merge metadata lags ref updates by more than ~10s while `origin/main` already carries the bumped `plugin.json`, the script can still hit `ERROR=merge-commit-missing` and abort even though a retry would succeed; conversely, if metadata is slow but `origin/main` already matches `--version`, it silently falls back to `origin/main^{commit}` without ever binding the release PR’s `mergeCommit`. **Suggested fix:** Interleave `fetch origin main` (and optionally a short post-fetch `gh pr view`) inside the merge poll loop, or extend/document the bound with a single retry after fetch; when using the `origin/main` fallback, optionally require `gh pr view` state `MERGED` for `--pr` so finish does not tag a tip that merely matches version.
- **Suggested revision**: Address the concern above.


### FINDING_32: **correctness** `.claude/skills/bump-version/scripts/classify-bump.sh:316-321` — Aggregate `NEW_VERSION` arithmetic uses bare `$((MAJ + 1))` / `$((MIN + 1))` / `$((PAT + 1))` without `10#`, while `release-prepare.sh:258-260` applies decimal-forced `10#` only on the `--bump` override path and `release-prepare.md:1034` documents decimal-forced arithmetic for the release flow. The primary `/release` path (no override) forwards `NEW_VERSION` straight from classify-bump output, so semver components with leading zeros can be mis-incremented or fail under bash’s octal rules, contradicting the release-side contract. **Suggested fix:** Use `10#`-prefixed arithmetic in `classify-bump.sh`’s `NEW_VERSION` computation so aggregate classification and `release-prepare.sh` override recompute share one arithmetic policy.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - **correctness** `.claude/skills/bump-version/scripts/classify-bump.sh:316-321` — Aggregate `NEW_VERSION` arithmetic uses bare `$((MAJ + 1))` / `$((MIN + 1))` / `$((PAT + 1))` without `10#`, while `release-prepare.sh:258-260` applies decimal-forced `10#` only on the `--bump` override path and `release-prepare.md:1034` documents decimal-forced arithmetic for the release flow. The primary `/release` path (no override) forwards `NEW_VERSION` straight from classify-bump output, so semver components with leading zeros can be mis-incremented or fail under bash’s octal rules, contradicting the release-side contract. **Suggested fix:** Use `10#`-prefixed arithmetic in `classify-bump.sh`’s `NEW_VERSION` computation so aggregate classification and `release-prepare.sh` override recompute share one arithmetic policy.
- **Suggested revision**: Address the concern above.


### FINDING_35: **security** `scripts/create-pr.sh:125-131` — The new two-phase redaction uses a second `mktemp` (`secrets_redacted`) that is not registered with the existing `EXIT` trap. Only `REDACTED_BODY_FILE` is removed in `cleanup()`; on the happy path `mv` renames `secrets_redacted` away, but if the process exits abnormally between `secrets_redacted=$(mktemp)` and `mv` (signal, `mv` failure under `set -e`, or any path that bypasses the explicit `rm -f` on the `redact-secrets` failure branch), a world-private but persistent `/tmp` file can remain containing PR/release body text (fully or partially secret-redacted). That is a local information-disclosure footgun for release notes or bodies that may still hold secrets in `REDACTED_BODY_FILE` until the move completes. **Suggested fix:** Track the intermediate path in the same `EXIT` trap as `REDACTED_BODY_FILE` (e.g. add `SECRETS_REDACTED_FILE` to `cleanup`, append to `NET_FAIL_FILES` until `mv` succeeds, or avoid a second file by piping `redact-secrets` into a fresh `mktemp` that immediately becomes `REDACTED_BODY_FILE` via atomic replace).
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `scripts/create-pr.sh:125-131` — The new two-phase redaction uses a second `mktemp` (`secrets_redacted`) that is not registered with the existing `EXIT` trap. Only `REDACTED_BODY_FILE` is removed in `cleanup()`; on the happy path `mv` renames `secrets_redacted` away, but if the process exits abnormally between `secrets_redacted=$(mktemp)` and `mv` (signal, `mv` failure under `set -e`, or any path that bypasses the explicit `rm -f` on the `redact-secrets` failure branch), a world-private but persistent `/tmp` file can remain containing PR/release body text (fully or partially secret-redacted). That is a local information-disclosure footgun for release notes or bodies that may still hold secrets in `REDACTED_BODY_FILE` until the move completes. **Suggested fix:** Track the intermediate path in the same `EXIT` trap as `REDACTED_BODY_FILE` (e.g. add `SECRETS_REDACTED_FILE` to `cleanup`, append to `NET_FAIL_FILES` until `mv` succeeds, or avoid a second file by piping `redact-secrets` into a fresh `mktemp` that immediately becomes `REDACTED_BODY_FILE` via atomic replace).
- **Suggested revision**: Address the concern above.


### FINDING_4: code-quality: .claude/skills/release/scripts/test-release-prepare.sh:55-64
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Prepare harness stubs classify-bump so real --base/--head wiring is untested in integration. Argv cwd or classify output parsing bugs in release-prepare could ship while unit tests stay green. Add one integration fixture using the real classify-bump.sh.
- **Suggested revision**: Address the concern above.


### FINDING_8: correctness: .claude/skills/release/scripts/release-prepare.sh:149-154
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Open-release guard uses startswith("release/v") so any branch named release/v* blocks prepare. An open PR from release/validation or release/victim-fix yields ERROR=release-cut-in-progress and aborts a legitimate cut. Restrict jq to semver release branches e.g. test("^release/v[0-9]+\\.[0-9]+\\.[0-9]+$").
- **Suggested revision**: Address the concern above.


