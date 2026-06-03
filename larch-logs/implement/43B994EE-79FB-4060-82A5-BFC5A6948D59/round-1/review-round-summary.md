# Review Round 1

- Mode: `diff`
- 25 accepted, 5 rejected (5 exonerated)

## Accepted Findings

### FINDING_1: SKILL.md Step 2 never runs release-prepare.sh
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-bash-compatibility-output.txt, dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: Step 2’s bash block assigns the script path to `PREPARE_OUT` and line-continues `--repo`, `--bump`, and `--out-dir` as separate commands (uses undefined `BUMP_FLAG`). An orchestrator following the skill verbatim does not execute `release-prepare.sh`, produces no KV/PR list, and cannot continue Steps 3–4.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Use explicit `"$PWD/.../release-prepare.sh"` invocation with `${BUMP_OVERRIDE:+--bump "$BUMP_OVERRIDE"}` and `--out-dir`; parse stdout KV lines directly.
  - From cursor-specialist-plan-fidelity-output.txt: Invoke script and capture stdout: `prepare_out=$(.../release-prepare.sh ...)`; parse KV from `prepare_out`.
  - From dyn-bash-compatibility-output.txt: Use command substitution, e.g. `PREPARE_OUT=$("$PWD/.claude/skills/release/scripts/release-prepare.sh" --repo "$REPO" ${BUMP_FLAG:+--bump "$BUMP_OVERRIDE"} --out-dir "$(mktemp -d)")`, and parse KV lines from that capture.
  - From dyn-contract-to-implementation-output.txt: Invoke the helper directly (or capture stdout), e.g. `PREPARE_DIR="$(mktemp -d)"` plus `"$PWD/.claude/skills/release/scripts/release-prepare.sh" --repo "$REPO" ${BUMP_FLAG:+--bump "$BUMP_OVERRIDE"} --out-dir "$PREPARE_DIR"`, then parse that command’s stdout; reserve `PREPARE_OUT` for output if you still want the name.


### FINDING_10: TSV PR metadata not sanitized (newline/control chars)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `pr-list.tsv` only normalizes tabs in `title`; `labels`, `author`, and `url` are emitted raw. Embedded newlines or control characters break TSV parsing in Step 3 and weaken the prompt-injection envelope for orchestrator-composed notes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Normalize all TSV fields (strip/replace whitespace control chars).
  - From cursor-specialist-security-output.txt: Sanitize every TSV field (strip/replace `\n`, `\r`, `\t`, and other C0 controls) before `printf`, or emit PR rows as JSON Lines and parse structurally in the orchestrator.


### FINDING_11: jq failure on bad gh JSON aborts prepare mid-loop
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Under `set -e`, a `jq` failure on malformed `pr_json` aborts the entire prepare mid-loop after partial TSV write, without a structured `ERROR=`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Per-PR validation with explicit error handling or bounded failure reporting.


### FINDING_12: mergeCommit missing falls back to origin/main tip
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, dyn-release-race-conditions-output.txt
- **Severity**: important
- **Concern**: When `mergeCommit.oid` is empty, `TARGET_OID` falls back to `origin/main^{commit}` without proving it is the release PR squash merge. A later commit on `main` can pass the version gate while the tag/release points at the wrong OID (or wrong tree).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Retry mergeCommit or fail closed; avoid origin/main fallback without proving it is the release merge.
  - From cursor-specialist-security-output.txt: Treat missing `mergeCommit` as a hard error after merge, or resolve OID via `gh pr view` merge ref / compare API and verify the commit is an ancestor of `origin/main` and contains the release PR’s single-file `plugin.json` change.
  - From dyn-release-race-conditions-output.txt: Poll `mergeCommit.oid` with bounded backoff before falling back; or resolve the squash merge via `git log origin/main --grep` / merge-base against the release PR branch; or require `TARGET_OID` to equal `mergeCommit.oid` when the PR is `MERGED` before tagging.


### FINDING_13: gh release list --limit 200 may miss Latest baseline
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `gh release list --limit 200` may omit the true Latest release on large histories, causing false `no-unique-latest-release`, wrong `BASELINE_TAG`, or blocking a valid cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Paginate or query Latest explicitly.
  - From cursor-specialist-edge-cases-output.txt: Paginate or query Latest without a low fixed limit.


### FINDING_14: test-release-prepare omits baseline-tag-unresolvable case
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The prepare harness does not cover fetch failure plus `rev-parse` failure → `ERROR=baseline-tag-unresolvable` exit 1, so fetch/verify regressions may not fail CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add harness case: fetch fails and rev-parse fails → ERROR=baseline-tag-unresolvable exit 1.


### FINDING_15: promote-release argv / --repo paths untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Refactored `promote-release.sh` argv and `--repo` forwarding lack offline tests; default vs `--repo` paths could promote the wrong hub in fork/multi-remote workflows.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fake-gh `test-promote-release.sh` for default and `--repo` paths.


### FINDING_16: test-classify-bump Test 6 asserts too weakly
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Test 6 only asserts `BUMP_TYPE != NONE`; mis-classification as PATCH could pass while an idempotency bug returns the wrong bump level.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Assert `BUMP_TYPE=MINOR` for the fixture with new skill + post-bump tweak.


### FINDING_18: No script-level redact-secrets on public release/PR publish
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `release-finish.sh` passes `--notes-file` straight to `gh release create/edit` without `redact-secrets.sh`; `create-pr.sh` redacts tmpdir paths but not secrets. Orchestrator-composed notes become durable public PR body and GitHub Release surfaces; a missed Step 3 redaction can leak tokens from PR titles.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Pipe notes through `redact-secrets.sh` inside `release-finish.sh` (and chain secret redaction in `create-pr.sh` for defense in depth), matching the `/issue` outbound model.


### FINDING_19: promote-release.sh --repo lacks OWNER/REPO format validation
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--repo` accepts any string with only a length check, unlike `release-prepare.sh` / `release-finish.sh`. A typo can target an unintended repository the token can write to.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse the same `^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$` guard as the release scripts.


### FINDING_2: gh pr view failures silently dropped from PR list
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: `gh pr view` failures are skipped with `|| continue`, so `PR_COUNT` and release notes can under-report versus `(#N)` tokens in `git log` while the script still exits 0. Operators may confirm a release with incomplete PR metadata and no structured signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Fail closed or emit per-PR warnings when `gh pr view` fails instead of silent continue.
  - From cursor-specialist-correctness-output.txt: Fail closed or emit ERROR/WARN with missing PR numbers; do not exit success with silent drops.
  - From cursor-specialist-testing-output.txt: Fail closed or warn+count failures; add harness for missing pr fixture.
  - From cursor-specialist-security-output.txt: Fail closed when any parsed PR number cannot be fetched, or emit a loud `WARN` KV with the missing set and require explicit operator acknowledgment before Step 4.
  - From cursor-specialist-edge-cases-output.txt: Fail closed on any missing PR metadata or emit loud WARN and abort confirm path.
  - From dyn-contract-to-implementation-output.txt: Fail closed, or emit `WARN_PR_SKIPPED=<n>` / log skipped numbers to stderr and document partial metadata in `release-prepare.md`; at minimum warn in `SKILL.md` Step 2 when `PR_COUNT` is less than the number of `(#N)` tokens seen in the log.


### FINDING_22: classify-bump --base diffs to HEAD not origin/main
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `classify-bump --base` diffs `"$BASE" HEAD` not `origin/main`; future callers without main==origin/main guard can classify the wrong aggregate diff.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Pass `--head origin/main` from release-prepare or document hard dependency on guards.


### FINDING_23: Bash 3.2 leading-zero semver arithmetic in --bump override
- **Reviewer(s)**: dyn-bash-compatibility-output.txt
- **Severity**: important
- **Concern**: The `--bump` override path uses bare `$((maj + 1))` etc. after `IFS='.' read`; on macOS Bash 3.2, components with leading zeros (e.g. `1.08.0`) can trigger invalid octal arithmetic and abort under `set -e`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-compatibility-output.txt: After `read`, increment with `10#`-prefixed arithmetic, e.g. `NEW_VERSION="$((10#maj + 1)).0.0"`, or reuse the same helper pattern as `classify-bump.sh` after adding `10#` there too.


### FINDING_24: Bash 3.2 leading-zero hazard in release-set-version semver_lt
- **Reviewer(s)**: dyn-bash-compatibility-output.txt
- **Severity**: important
- **Concern**: `semver_lt` compares components with `[[ $a_min -lt $b_min ]]` after `IFS='.' read`, with the same Bash 3.2 leading-zero / octal parsing hazard as the prepare override block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-compatibility-output.txt: Compare with decimal-forced arithmetic, e.g. `(( 10#a_min < 10#b_min ))`, for all three components in both operands.


### FINDING_25: Tag push TOCTOU vs release-tag.yaml breaks first-run idempotency
- **Reviewer(s)**: dyn-release-race-conditions-output.txt
- **Severity**: important
- **Concern**: Between initial `git ls-remote` and `git push`, `release-tag.yaml` may create `refs/tags/v<VERSION>` at `TARGET_OID`. Push then fails with “tag already exists” and the script exits before `gh release` edit/create and `promote-release.sh`, even though the remote tag is correct—only a full re-run succeeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-race-conditions-output.txt: Re-run `git ls-remote` immediately before push, or on push failure re-check whether the remote tag exists at `TARGET_OID` and continue to release edit/promote when it matches; only fail closed when the remote OID differs.


### FINDING_26: Re-running release-prepare after release PR merge can advance NEW_VERSION again
- **Reviewer(s)**: dyn-release-race-conditions-output.txt
- **Severity**: important
- **Concern**: After a successful release PR merge (e.g. `release-finish.sh` failed post-merge), re-running prepare with `SKIP_IDEMPOTENCY=true` re-classifies over a bumped `plugin.json` on `main` and can emit another patch bump (e.g. 47.0.57 → 47.0.58), misleading Step 4 or opening a second bump PR. `SKIP_IDEMPOTENCY` also blocks surfacing “already prepared” via `BUMP_TYPE=NONE` in some legacy states.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-release-race-conditions-output.txt: In `release-prepare.sh`, detect an in-flight or completed cut (open `release/v*` PR, `Release v*` on `origin/main`, or `CURRENT_VERSION` vs Latest tag); emit a distinct `ERROR=` or freeze `NEW_VERSION` when `plugin.json` on `origin/main` already reflects the target cut. Optionally narrow `--base` idempotency to ignore only bump-shaped commits, not all release states.


### FINDING_27: release-prepare.sh never cd's to REPO_ROOT
- **Reviewer(s)**: dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: The script resolves `REPO_ROOT` for `classify-bump.sh` but never `cd`s there; all `git` calls and classify (via `$PWD/.claude-plugin/plugin.json`) use the caller’s cwd. Running off repo root mis-anchors the PR window and bump despite the contract saying classify runs on repo root.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-to-implementation-output.txt: `cd "$REPO_ROOT"` immediately after computing `REPO_ROOT` (and document “always run from any cwd” in `release-prepare.md`), or pass an explicit repo-root flag through to `classify-bump.sh`.


### FINDING_28: release-finish.md partial KV stream if promote fails after RELEASE_ACTION
- **Reviewer(s)**: dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: Contract lists success KVs but implementation prints `RELEASE_ACTION` after create/edit, then runs `promote-release.sh`; promote failure exits 1 without emitting `TARGET_OID`/`TAG`/`VERSION`, leaving a partial KV stream for orchestrators.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-to-implementation-output.txt: Document “all listed keys only on exit 0 after promote succeeds,” or reorder so tail KVs are printed only after promote, or print a failure `ERROR=` and exit before any success keys on promote failure.


### FINDING_29: release-finish.md omits exit code 2 for usage/validation
- **Reviewer(s)**: dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: Contract documents exit 1 for tag/OID conflicts but not exit 2 for usage/validation errors used by the implementation, so harnesses cannot distinguish operator misuse from operational failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-to-implementation-output.txt: Add an “Exit codes” table mirroring `release-set-version.md` (0 success, 1 operational/`gh`/git/promote, 2 usage/validation).


### FINDING_3: git `origin` vs `gh --repo` can diverge (split-brain release)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: Git fetch/push/ls-remote use `origin` while `gh` honors `--repo`. On a fork or misconfigured clone, tags can be pushed to one remote while Releases/releases are created on another hub repo.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document origin must match `--repo` or resolve git remote from REPO for all git steps.
  - From cursor-specialist-security-output.txt: Resolve the git remote URL for the requested `OWNER/REPO` (or require `origin` URL to match `--repo` via `gh repo view` / `git remote get-url`) before tag push.
  - From cursor-specialist-edge-cases-output.txt: Verify origin remote matches `--repo` before fetch/tag push.
  - From dyn-contract-to-implementation-output.txt: Resolve the git remote that matches `$REPO` (e.g. via `gh repo view --json url` / existing remote helpers) and use that remote for fetch/ls-remote/push; document the coupling in `release-finish.md`.


### FINDING_30: release-prepare ERROR= split across stdout and stderr
- **Reviewer(s)**: dyn-contract-to-implementation-output.txt
- **Severity**: important
- **Concern**: Some exit-1 paths emit `ERROR=` on stdout (baseline/stale-main) while dependency/`gh release list` failures go only to stderr. `SKILL.md` says parse `ERROR=` on exit 1 without specifying stdout, so some failures are not machine-parseable.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-contract-to-implementation-output.txt: Emit a single `ERROR=<token>` line on stdout for every exit 1 path (keep human detail on stderr), and document the contract in `release-prepare.md`.

---


### FINDING_4: Missing offline test-release-finish harness (in-scope plan gap)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-release-race-conditions-output.txt
- **Severity**: important
- **Concern**: The testing strategy calls for offline `test-release-finish.sh` coverage (OID/version/tag idempotency, wrong-OID remote tag, create-vs-edit paths), but the branch lacks that harness and Makefile target. Regressions in `release-finish.sh` fail-closed and tagging behavior can ship undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add `test-release-finish.sh` with shims for mergeCommit origin/main version gate and tag conflict paths.
  - From cursor-specialist-correctness-output.txt: Add shim harness for version mismatch and wrong-OID remote tag paths.
  - From cursor-specialist-testing-output.txt: Add PATH-shimmed `test-release-finish.sh` with version-mismatch, wrong remote tag, and create-or-edit decision fixtures; register in Makefile.
  - From cursor-specialist-edge-cases-output.txt: Add `test-release-finish.sh` and Makefile target per plan.
  - From dyn-release-race-conditions-output.txt: (merged concern only; no distinct fix beyond plan harness—see testing slot bullets above.)


### FINDING_6: classify-bump stderr suppressed on failure
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `classify-bump` stderr is discarded on failure; operators only see a generic `classify-bump failed` without plugin.json, ref, or classifier detail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Preserve and surface classifier stderr on failure.
  - From cursor-specialist-correctness-output.txt: Propagate stderr tail into prepare ERROR output.
  - From cursor-specialist-edge-cases-output.txt: Surface classifier stderr in prepare error output.


### FINDING_7: dry-run skips main guard but prepare uses HEAD vs origin/main
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `--dry-run` skips the main-branch guard while prepare mixes `HEAD` and `origin/main` ranges, so dry-run off-main can show inconsistent bump vs PR list compared to a real cut.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Require main for prepare or align classify diff with origin/main for `--base`.
  - From cursor-specialist-edge-cases-output.txt: Apply same guards for dry-run or pin prepare to origin/main explicitly.


### FINDING_9: Tag-only fetch fallback can leave stale origin/main
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After failed `main`+tags fetch, tag-only fetch fallback can pass `stale-local-main` while `origin/main` is outdated. PR list and `classify-bump` then use a stale range, yielding wrong `PR_COUNT`, notes, and semver.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Require successful origin/main refresh or exit with explicit ERROR; do not treat tag-only fetch as sufficient.
  - From cursor-specialist-edge-cases-output.txt: Require successful origin/main refresh or compare origin/main to ls-remote before prepare succeeds.


