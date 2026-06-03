### FINDING_1: code-quality: .claude/skills/release/scripts/release-prepare.sh:250-261
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] --bump override re-implements semver increment instead of reusing classify/apply-bump helpers. Operator override could compute a different NEW_VERSION than classify-bump for the same CURRENT_VERSION and BUMP_TYPE if arithmetic rules diverge. Extract shared bump increment helper or add classify-bump --force-bump-type and drop inline case block.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: .claude/skills/release/scripts/release-finish.sh:176-321
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] release-finish bundles OID resolution tag push release create/edit and promote in one long script. Hard to safely extend race recovery or tag logic; regressions in nested fetch/ancestor branches are easy to miss. Split OID resolution and tag idempotency into a library or functions; keep finish as thin orchestration.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: .claude/skills/release/scripts/release-set-version.sh:16-26
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] semver_lt duplicated from apply-bump and ship-pr. Future fix in one copy may not propagate leading to inconsistent downgrade checks. Source scripts/lib-semver.sh with semver_lt and shared bump helpers.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: .claude/skills/release/scripts/test-release-prepare.sh:55-64
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Prepare harness stubs classify-bump so real --base/--head wiring is untested in integration. Argv cwd or classify output parsing bugs in release-prepare could ship while unit tests stay green. Add one integration fixture using the real classify-bump.sh.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: .claude/skills/release/SKILL.md:127-134
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Script index highlights promote-latest-release.sh while runtime path uses promote-release.sh. Operators or agents may run the legacy promote script during recovery. Relabel legacy script under a separate Legacy section; emphasize promote-release.sh in Step 6 recovery.
- **Suggested revision**: Address the concern above.

### FINDING_6: code-quality: .claude/skills/release/scripts/release-prepare.sh:187-218
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Sequential gh pr view per PR. Very large release windows mean slow prepare and many API calls. Optional follow-up: batch PR fetch; acceptable for current scale.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] code-quality: scripts/promote-release.sh:79-93
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] promote-release does not fail on ambiguous isLatest unlike release-prepare. Multiple Latest releases could cause unpredictable promote target. Align promote-release with prepare Latest uniqueness guard if desired later.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: .claude/skills/release/scripts/release-prepare.sh:149-154
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Open-release guard uses startswith("release/v") so any branch named release/v* blocks prepare. An open PR from release/validation or release/victim-fix yields ERROR=release-cut-in-progress and aborts a legitimate cut. Restrict jq to semver release branches e.g. test("^release/v[0-9]+\\.[0-9]+\\.[0-9]+$").
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: .claude/skills/release/scripts/release-prepare.sh:104
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Baseline Latest is resolved only within gh release list --limit 100. If the true Latest release is outside the first 100 rows prepare reports ERROR=no-unique-latest-release (LATEST_COUNT=0). Paginate release list or query isLatest without a fixed low limit.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: .claude/skills/release/scripts/release-prepare.sh:175-177
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] PR extraction requires trailing (#N) in squash subject; other merges are omitted from notes. Merged work without (#N) suffix is missing from PR_COUNT/notes while still affecting classify-bump. Document operator convention or add fallback PR discovery for notes.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: scripts/promote-release.sh:79
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Multi-line CURRENT_LATEST when multiple isLatest releases exist. Two Latest flags could break promote string compare (pre-existing). Use jq -r '.[0]' after filtering or fail on count != 1.
- **Suggested revision**: Address the concern above.

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

### FINDING_18: risk-integration: Makefile:110
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Four new harnesses added to test-harnesses-20 under 5m CI timeout. Shard 20 may approach timeout as harnesses grow; flaky CI on busy runners. Monitor CI duration; split shard or trim if needed.
- **Suggested revision**: Address the concern above.

### FINDING_19: security: .claude/skills/release/SKILL.md:52-54
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Step 3 trust boundary covers PR titles only but PR_LIST_FILE also includes labels author and url from gh all fed to the LLM composer A merged PR with prompt-injection text in labels or title can steer public GitHub Release notes and the release PR body; operator confirm is not a mechanical sanitizer Wrap all TSV fields in a data-not-instructions envelope; require paraphrase-only treatment for title labels and author; forbid following embedded instructions
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: .claude/skills/release/scripts/release-prepare.sh:127-175
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] No check that BASELINE_TAG is an ancestor of origin/main Mis-set isLatest tag yields wrong PR list and classify range with exit 0 After tag verify run git merge-base --is-ancestor "$BASELINE_TAG" origin/main; else ERROR=baseline-not-on-main exit 1
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **architecture** `scripts/promote-release.md:22-24` — Purpose text still describes promoting workflow-created pre-releases from `release-tag.yaml` only; it now also documents `--repo` and `/release` as a consumer, but not that `/release` is the primary cut path. Pre-existing tone; not introduced as a functional gap by this diff.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-prepare.sh:108` — `gh release list --limit 100` could theoretically miss a unique `isLatest` release outside the first page on repos with very large release histories. Unlikely for larch; not specified in the plan.
- **Suggested revision**: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] correctness
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: - **correctness** Plan testing strategy asked for a PR note that live `gh release create/edit` / tag push are left to manual/CI verification per verify-external-tool-invocations; that deliverable is not visible in the committed diff (may exist only in the PR description). --- **Summary:** Implementation matches the SIMPLE-tier plan and acceptance criteria in the diff. No missing planned artifacts, no wrong-language choice, no omitted harnesses from the testing strategy. Safe to treat plan fidelity as satisfied from the code side.
- **Suggested revision**: Address the concern above.

### FINDING_24: **risk-integration** `.claude/skills/release/scripts/release-finish.sh:289-297` — The local-tag reconciliation branch uses `remote_oid` from the initial `ls-remote` at lines 281–282 and never re-probes before deciding whether to `git tag -f`. If the first probe sees no remote tag, a stale local `vX.Y.Z` points elsewhere, and `release-tag.yaml` pushes the correct tag to `TARGET_OID` before line 289 runs, the script exits with `ERROR=local tag … points at … not TARGET_OID` even though the remote race is already resolved. The re-probe at lines 303–309 runs only after this block, so it never runs on the failure path. **Suggested fix:** Call `remote_tag_commit_oid` again immediately before the `local_oid != TARGET_OID` branch (or move the empty-remote re-probe block above local-tag handling) so workflow wins between the first probe and local inspection follow the same recovery path as push failure (lines 313–318).
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:289-297` — The local-tag reconciliation branch uses `remote_oid` from the initial `ls-remote` at lines 281–282 and never re-probes before deciding whether to `git tag -f`. If the first probe sees no remote tag, a stale local `vX.Y.Z` points elsewhere, and `release-tag.yaml` pushes the correct tag to `TARGET_OID` before line 289 runs, the script exits with `ERROR=local tag … points at … not TARGET_OID` even though the remote race is already resolved. The re-probe at lines 303–309 runs only after this block, so it never runs on the failure path. **Suggested fix:** Call `remote_tag_commit_oid` again immediately before the `local_oid != TARGET_OID` branch (or move the empty-remote re-probe block above local-tag handling) so workflow wins between the first probe and local inspection follow the same recovery path as push failure (lines 313–318).
- **Suggested revision**: Address the concern above.

### FINDING_25: **risk-integration** `.claude/skills/release/scripts/release-finish.sh:177-186,848-850` — `mergeCommit` polling is capped at five attempts (~10s) with no `fetch origin main` inside the loop, and there is no second `gh pr view` after the post-poll fetch. If GitHub’s merge metadata lags ref updates by more than ~10s while `origin/main` already carries the bumped `plugin.json`, the script can still hit `ERROR=merge-commit-missing` and abort even though a retry would succeed; conversely, if metadata is slow but `origin/main` already matches `--version`, it silently falls back to `origin/main^{commit}` without ever binding the release PR’s `mergeCommit`. **Suggested fix:** Interleave `fetch origin main` (and optionally a short post-fetch `gh pr view`) inside the merge poll loop, or extend/document the bound with a single retry after fetch; when using the `origin/main` fallback, optionally require `gh pr view` state `MERGED` for `--pr` so finish does not tag a tip that merely matches version.
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:177-186,848-850` — `mergeCommit` polling is capped at five attempts (~10s) with no `fetch origin main` inside the loop, and there is no second `gh pr view` after the post-poll fetch. If GitHub’s merge metadata lags ref updates by more than ~10s while `origin/main` already carries the bumped `plugin.json`, the script can still hit `ERROR=merge-commit-missing` and abort even though a retry would succeed; conversely, if metadata is slow but `origin/main` already matches `--version`, it silently falls back to `origin/main^{commit}` without ever binding the release PR’s `mergeCommit`. **Suggested fix:** Interleave `fetch origin main` (and optionally a short post-fetch `gh pr view`) inside the merge poll loop, or extend/document the bound with a single retry after fetch; when using the `origin/main` fallback, optionally require `gh pr view` state `MERGED` for `--pr` so finish does not tag a tip that merely matches version.
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/test-release-finish.sh` — Case 8 covers stale local tag when remote already matches at probe time; there is no harness case for “first `ls-remote` empty → workflow pushes correct tag → stale local tag,” which is the regression shape for the finding above. Contract text in `release-finish.md:40-41` describes push-failure TOCTOU recovery but not local-tag / first-probe ordering.
- **Suggested revision**: Address the concern above.

### FINDING_27: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:177-180` — `merge_oid` newline stripping and `${merge_oid%% *}` plus the `^[0-9a-fA-F]{7,40}$` gate are adequate for normal `gh -q` output; a multi-token or non-hex first token would be dropped or rejected rather than producing a silent partial hash.
- **Suggested revision**: Address the concern above.

### FINDING_28: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:209-256,394-418` — When `TARGET_OID` is an ancestor of a later `origin/main` tip (case 10 / harness), tagging the squash-merge OID rather than tip is intentional; version is verified at `TARGET_OID` only, which matches the plan’s fail-closed stance vs `release-tag.yaml` on the same OID.
- **Suggested revision**: Address the concern above.

### FINDING_29: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-toctou-race-output.txt
- **Concern**: - **risk-integration** `.claude/skills/release/scripts/release-finish.sh:303-318` — Post-push failure re-probe and same-OID continuation correctly close the tag-push TOCTOU against `release-tag.yaml`; the gap is asymmetric with the pre-push local-tag path. **Branch commits (vs `main`):** `6576ec069` Add operator-run /release skill … through `9f8c36634` Address code review feedback (round 4).
- **Suggested revision**: Address the concern above.

### FINDING_30: **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:170-195` — The new `--head` flag moves diff scope, `git show` reads, and `CURRENT_VERSION` sourcing onto `HEAD_COMPARE`, but the idempotency short-circuit still walks symbolic `HEAD` / `HEAD~N` and only consults subjects at that local tip. When `--head` is passed without `--base`, `SKIP_IDEMPOTENCY` stays `false`, so a local `Bump version to X.Y.Z` tip can yield `BUMP_TYPE=NONE` even though `git diff "$BASE" "$HEAD_COMPARE"` still spans unreleased public-surface changes at the explicit head ref. `/release` avoids this today because `release-prepare.sh:235` always pairs `--base` (which sets `SKIP_IDEMPOTENCY=true` at line 74), but the standalone `--head` surface is internally inconsistent and unsafe for any caller that omits `--base`. **Suggested fix:** Anchor the idempotency walk on `HEAD_COMPARE` whenever `--head` is set (or fail closed unless `--base` is also present), and add a harness case for `--head` without `--base` so the contract cannot regress silently.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:170-195` — The new `--head` flag moves diff scope, `git show` reads, and `CURRENT_VERSION` sourcing onto `HEAD_COMPARE`, but the idempotency short-circuit still walks symbolic `HEAD` / `HEAD~N` and only consults subjects at that local tip. When `--head` is passed without `--base`, `SKIP_IDEMPOTENCY` stays `false`, so a local `Bump version to X.Y.Z` tip can yield `BUMP_TYPE=NONE` even though `git diff "$BASE" "$HEAD_COMPARE"` still spans unreleased public-surface changes at the explicit head ref. `/release` avoids this today because `release-prepare.sh:235` always pairs `--base` (which sets `SKIP_IDEMPOTENCY=true` at line 74), but the standalone `--head` surface is internally inconsistent and unsafe for any caller that omits `--base`. **Suggested fix:** Anchor the idempotency walk on `HEAD_COMPARE` whenever `--head` is set (or fail closed unless `--base` is also present), and add a harness case for `--head` without `--base` so the contract cannot regress silently.
- **Suggested revision**: Address the concern above.

### FINDING_31: **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:98-107` — The `--head` guard validates only that worktree and `HEAD_COMPARE` share the same `.version` string; it does not require `git rev-parse HEAD` to equal `HEAD_COMPARE`. Two commits can carry identical `plugin.json` versions while differing in tree/history, which lets classification proceed with a misaligned checkout ref while idempotency (when not skipped) still inspects the local tip. `release-prepare.sh:142-144` mitigates this for `/release` by enforcing `HEAD == origin/main` OIDs before invoking classify-bump, but the classifier itself does not encode that invariant, leaving a latent mis-classification surface for direct `--head` callers. **Suggested fix:** After resolving `HEAD_COMPARE`, fail closed unless `$(git rev-parse HEAD)` equals `HEAD_COMPARE` when `--head` is supplied (or document and enforce `--head` as release-only via mandatory `--base` plus OID equality).
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - **architecture** `.claude/skills/bump-version/scripts/classify-bump.sh:98-107` — The `--head` guard validates only that worktree and `HEAD_COMPARE` share the same `.version` string; it does not require `git rev-parse HEAD` to equal `HEAD_COMPARE`. Two commits can carry identical `plugin.json` versions while differing in tree/history, which lets classification proceed with a misaligned checkout ref while idempotency (when not skipped) still inspects the local tip. `release-prepare.sh:142-144` mitigates this for `/release` by enforcing `HEAD == origin/main` OIDs before invoking classify-bump, but the classifier itself does not encode that invariant, leaving a latent mis-classification surface for direct `--head` callers. **Suggested fix:** After resolving `HEAD_COMPARE`, fail closed unless `$(git rev-parse HEAD)` equals `HEAD_COMPARE` when `--head` is supplied (or document and enforce `--head` as release-only via mandatory `--base` plus OID equality).
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `.claude/skills/bump-version/scripts/classify-bump.sh:316-321` — Aggregate `NEW_VERSION` arithmetic uses bare `$((MAJ + 1))` / `$((MIN + 1))` / `$((PAT + 1))` without `10#`, while `release-prepare.sh:258-260` applies decimal-forced `10#` only on the `--bump` override path and `release-prepare.md:1034` documents decimal-forced arithmetic for the release flow. The primary `/release` path (no override) forwards `NEW_VERSION` straight from classify-bump output, so semver components with leading zeros can be mis-incremented or fail under bash’s octal rules, contradicting the release-side contract. **Suggested fix:** Use `10#`-prefixed arithmetic in `classify-bump.sh`’s `NEW_VERSION` computation so aggregate classification and `release-prepare.sh` override recompute share one arithmetic policy.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - **correctness** `.claude/skills/bump-version/scripts/classify-bump.sh:316-321` — Aggregate `NEW_VERSION` arithmetic uses bare `$((MAJ + 1))` / `$((MIN + 1))` / `$((PAT + 1))` without `10#`, while `release-prepare.sh:258-260` applies decimal-forced `10#` only on the `--bump` override path and `release-prepare.md:1034` documents decimal-forced arithmetic for the release flow. The primary `/release` path (no override) forwards `NEW_VERSION` straight from classify-bump output, so semver components with leading zeros can be mis-incremented or fail under bash’s octal rules, contradicting the release-side contract. **Suggested fix:** Use `10#`-prefixed arithmetic in `classify-bump.sh`’s `NEW_VERSION` computation so aggregate classification and `release-prepare.sh` override recompute share one arithmetic policy.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `.claude/skills/release/scripts/test-release-prepare.sh` PATH-shims a fake `classify-bump.sh` instead of exercising the real `--base "$BASELINE_TAG" --head origin/main` integration, so regressions in the cross-script contract above would not be caught by the offline prepare harness alone.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - `.claude/skills/release/scripts/test-release-prepare.sh` PATH-shims a fake `classify-bump.sh` instead of exercising the real `--base "$BASELINE_TAG" --head origin/main` integration, so regressions in the cross-script contract above would not be caught by the offline prepare harness alone.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] For the wired `/release` path specifically (`release-prepare.sh:235` with paired flags plus `HEAD`/`main`/`origin/main` OID guards at lines 136-144): `CURRENT_VERSION` is correctly read from `git show "${HEAD_COMPARE}:.claude-plugin/plugin.json"`, idempotency is skipped via `--base`, and `NAME_STATUS` / modified-file `git show` calls consistently use `$HEAD_COMPARE` rather than bare `HEAD`.
- **Reviewer**: dyn-script-interface-output.txt
- **Concern**: - For the wired `/release` path specifically (`release-prepare.sh:235` with paired flags plus `HEAD`/`main`/`origin/main` OID guards at lines 136-144): `CURRENT_VERSION` is correctly read from `git show "${HEAD_COMPARE}:.claude-plugin/plugin.json"`, idempotency is skipped via `--base`, and `NAME_STATUS` / modified-file `git show` calls consistently use `$HEAD_COMPARE` rather than bare `HEAD`.
- **Suggested revision**: Address the concern above.

### FINDING_35: **security** `scripts/create-pr.sh:125-131` — The new two-phase redaction uses a second `mktemp` (`secrets_redacted`) that is not registered with the existing `EXIT` trap. Only `REDACTED_BODY_FILE` is removed in `cleanup()`; on the happy path `mv` renames `secrets_redacted` away, but if the process exits abnormally between `secrets_redacted=$(mktemp)` and `mv` (signal, `mv` failure under `set -e`, or any path that bypasses the explicit `rm -f` on the `redact-secrets` failure branch), a world-private but persistent `/tmp` file can remain containing PR/release body text (fully or partially secret-redacted). That is a local information-disclosure footgun for release notes or bodies that may still hold secrets in `REDACTED_BODY_FILE` until the move completes. **Suggested fix:** Track the intermediate path in the same `EXIT` trap as `REDACTED_BODY_FILE` (e.g. add `SECRETS_REDACTED_FILE` to `cleanup`, append to `NET_FAIL_FILES` until `mv` succeeds, or avoid a second file by piping `redact-secrets` into a fresh `mktemp` that immediately becomes `REDACTED_BODY_FILE` via atomic replace).
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `scripts/create-pr.sh:125-131` — The new two-phase redaction uses a second `mktemp` (`secrets_redacted`) that is not registered with the existing `EXIT` trap. Only `REDACTED_BODY_FILE` is removed in `cleanup()`; on the happy path `mv` renames `secrets_redacted` away, but if the process exits abnormally between `secrets_redacted=$(mktemp)` and `mv` (signal, `mv` failure under `set -e`, or any path that bypasses the explicit `rm -f` on the `redact-secrets` failure branch), a world-private but persistent `/tmp` file can remain containing PR/release body text (fully or partially secret-redacted). That is a local information-disclosure footgun for release notes or bodies that may still hold secrets in `REDACTED_BODY_FILE` until the move completes. **Suggested fix:** Track the intermediate path in the same `EXIT` trap as `REDACTED_BODY_FILE` (e.g. add `SECRETS_REDACTED_FILE` to `cleanup`, append to `NET_FAIL_FILES` until `mv` succeeds, or avoid a second file by piping `redact-secrets` into a fresh `mktemp` that immediately becomes `REDACTED_BODY_FILE` via atomic replace).
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `release-finish.sh:26-30,137-148` — The `_tmp_notes` / `REDACTED_NOTES_FILE` pipeline matches the intended pattern: both paths are covered by the `EXIT` trap; after success `rm` + `unset _tmp_notes` makes the trap’s `[[ -n "${_tmp_notes:-}" ]]` guard avoid double-remove; `REDACTED_NOTES_FILE` is still removed on all `exit` paths (including `gh release` / `promote-release` failures). No defect found in the trap logic the scout asked about.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `release-finish.sh:155-245` — `fetch_err` temporaries are explicitly `rm -f`’d on every branch; no leak introduced there.
- **Suggested revision**: Address the concern above.

### FINDING_38: [OUT_OF_SCOPE] security
- **Reviewer**: dyn-redaction-tmpfiles-output.txt
- **Concern**: - **security** `release-prepare.sh:234-240` — `classify_err_file` is always `rm -f`’d on success and failure; pre-existing style, not part of the new redaction surface.
- **Suggested revision**: Address the concern above.

