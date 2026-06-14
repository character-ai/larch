# Review Round 1

- Mode: `diff`
- 8 accepted, 4 rejected (1 neutral)

## Accepted Findings

### FINDING_1: correctness: design-publish.sh stale PR metadata reload on successful re-publish
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-shell-rebuild-output.txt
- **Severity**: important
- **Concern**: After prior `PUBLISH_OK=true`, the wrapper always reloads old PR metadata via `result_env_load_success_metadata` (lines 700-703/704) even when the current `design-log-publish` succeeded with a new PR. On Step 5c re-entry (e.g., first publish records PR #50, second creates incremental PR #51), freshly parsed publish metadata is overwritten before rendering and emitting results, so stdout KVs and summary can disagree with the PR just created.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Load prior PR metadata only when current publish returned empty PR fields or failed; on successful publish with non-empty PR_NUMBER/PR_URL, write updated metadata (narrow write-once to failure-only clobber).
  - From codex-specialist-edge-cases-output.txt: Only reload prior success metadata for current failures or no-delta successes with empty PR fields, and preserve current non-empty PR metadata on successful publishes.
  - From cursor-specialist-testing-output.txt: Apply write-once only on failure paths; on current success keep parsed PR fields and write result env.
  - From dyn-shell-rebuild-output.txt: Only call `result_env_load_success_metadata` at `700-703` when the current attempt did not succeed (`PUBLISH_OK` is not `true` after parsing `_publish_out`); when the current attempt returns `PUBLISH_OK=true`, keep the parsed `PR_NUMBER` / `PR_URL` / `RECOVERY_BRANCH` and allow `write_result_env_and_emit` to update the result env instead of hitting the write-once skip path.


### FINDING_11: risk-integration: missing regression test for mandatory pre-push fetch failure
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Mandatory pre-push fetch failure path has no regression test. `git fetch` of `origin/default` fails during final rebuild; script should emit `PUBLISH_OK=false` and skip push/PR, but regressions would be undetected.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add test-design-log-publish.sh git-wrapper case that fails the pre-rebuild default fetch; assert PUBLISH_OK=false and no pr create/push.


### FINDING_14: risk-integration: missing in-scope manifest-only timestamp churn regression test
- **Reviewer(s)**: codex-specialist-testing-output.txt, dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The plan-required manifest-only timestamp-churn regression is missing. The new idempotency branch in `scripts/design-log-publish.sh:617-620` can regress and reopen duplicate PRs when only manifest timestamps differ. The harness only has the RUNNOOP rerun with a frozen `date` stub, which mostly exercises byte-identical reruns, not differing `started_at`/`updated_at` with otherwise identical trees.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-testing-output.txt: Add a stale-origin final-publish test that asserts PUBLISH_OK=true and no PR creation for manifest-only churn.
  - From dyn-harness-realism-output.txt: Add a case that seeds `main` with the same run files, changes only manifest timestamps in the desired snapshot (or uses distinct frozen times across runs), and asserts `PUBLISH_OK=true` with no `pr create`.


### FINDING_15: correctness: write-once gate skips updating result env on successful incremental re-flush
- **Reviewer(s)**: dyn-shell-rebuild-output.txt
- **Severity**: important
- **Concern**: `write_result_env_and_emit` skips `phase_driver_write_result_env` whenever the existing result file already has `PUBLISH_OK=true`, without checking whether the current publish attempt produced newer metadata (`skills/design/scripts/design-publish.sh:447-448`). Combined with the always-invoke publish change, a successful incremental re-flush after an earlier successful flush will not persist the new PR fields to `.design-publish-result.env`, leaving downstream Step 5c / resume consumers on stale recovery metadata.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-rebuild-output.txt: Narrow write-once to failure paths only (preserve prior success when the current attempt returns `PUBLISH_OK=false` or a non-zero `_publish_rc`); when the current attempt returns `PUBLISH_OK=true`, always write the parsed metadata even if a prior success record exists.


### FINDING_20: risk-integration: wrapper re-entry test does not prove delta forwarding or failure preservation
- **Reviewer(s)**: dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The re-entry case (`skills/design/scripts/test-design-publish.sh:1274-1307`) seeds prior `PUBLISH_OK=true` and checks that `design-log-publish` is invoked, but it does not add a final-only snapshot artifact as the plan specifies, and the publish stub still returns success. It therefore does not prove that wrapper re-entry forwards a real delta to `design-log-publish.sh` or that write-once preservation holds when the second publish attempt fails after a delta exists.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-harness-realism-output.txt: Add a final-only file under `$D_SHORT`, set `PUBLISH_OK_VALUE=false` (and/or non-zero `PUBLISH_STUB_RC`) on the second call, assert `design-log-publish` ran with the updated tree, and assert prior `PR_NUMBER`/`PR_URL` remain when write-once applies.


### FINDING_4: correctness: missing test for prior success plus second successful publish with new PR
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: No test covers prior `PUBLISH_OK=true` plus a second successful publish with a new PR. The wrapper PR-metadata regression above would not be caught by CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add re-entry test: seed prior success, stub publish returning new PR_NUMBER, assert result env and exports match new PR.


### FINDING_5: risk-integration: misleading test name and weak assertions at empty-porcelain case
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-harness-realism-output.txt
- **Severity**: important
- **Concern**: The case at `scripts/test-design-log-publish.sh:905-937` still says "fails closed when main lacks run id" but expects `PUBLISH_OK=true`. The git wrapper forces empty `git status --porcelain` regardless of worktree content while the design tmpdir contains `missing.txt`. The test exercises "porcelain is empty", not "main lacks run id", and never checks that `missing.txt` stayed off `main`, so a rebuild bug that short-circuits on empty porcelain could pass without publishing anything.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Rename test to describe stubbed empty-porcelain idempotent success.
  - From dyn-harness-realism-output.txt: Rename the scenario to match late idempotency, drop the status-forcing stub (or scope it only to the rebuild porcelain call), seed `main` with a byte-identical run tree, and assert both `PUBLISH_OK=true` and no `pr create` plus unchanged `main` content.


### FINDING_8: correctness: stale remote branch detection drives wrong final-mode push strategy
- **Reviewer(s)**: codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, dyn-shell-rebuild-output.txt
- **Severity**: important
- **Concern**: `REMOTE_BRANCH_EXISTS` and the lease baseline for `--force-with-lease` are decided from a single best-effort fetch at script start (`scripts/design-log-publish.sh:250-254`), while the pushed commit is built much later after staging, redaction, and the final rebuild fetch of `origin/$ORIGIN_DEFAULT`. After squash-merge with delete-branch, a stale local `origin/larch-log-design-$RUN_ID` ref can remain while the remote branch is gone; re-flush uses `--force-with-lease` and push fails even though a plain `-u` push could recreate the branch. A concurrent or recovery publish that advanced the remote log branch during the window can also make `--force-with-lease` fail unexpectedly or succeed against a stale lease if the tracking ref was never updated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Use fresh remote existence detection such as git ls-remote --heads, or prune/delete stale tracking refs on fetch failure, and only force-with-lease when the remote branch actually exists.
  - From cursor-specialist-edge-cases-output.txt: Re-check remote branch existence (or git fetch -p) immediately before push; use normal git push -u when the remote branch is absent.
  - From codex-specialist-edge-cases-output.txt: Verify actual remote branch existence with ls-remote or prune/delete stale tracking refs on fetch failure, and use --force-with-lease only for real remote branches.
  - From dyn-shell-rebuild-output.txt: Re-fetch `origin/$WT_BRANCH` immediately before the final push (mirroring `design_publish_refresh_default_ref`) and pass an explicit lease ref (`--force-with-lease=refs/heads/$WT_BRANCH:<sha>`) derived from that fresh fetch.


