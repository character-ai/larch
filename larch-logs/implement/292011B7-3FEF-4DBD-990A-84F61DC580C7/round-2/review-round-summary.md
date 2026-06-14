# Review Round 2

- Mode: `diff`
- 4 accepted, 0 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Missing test for idempotent Step 5c success with empty PR stdout
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: On idempotent Step 5c re-entry after a prior successful publish, `design-log-publish.sh` can return `PUBLISH_OK=true` with empty `PR_NUMBER`/`PR_URL` (late no-delta idempotency). The wrapper reloads prior PR metadata in memory at `design-publish.sh:706-711`, but CI has no harness asserting `.design-publish-result.env` still contains the prior PR after that success path, and no case covering the RC-1 no-delta path end-to-end (failed-reentry and new-PR-reentry exist; idempotent success with empty PR stdout does not). A regression removing or misordering the reload/persist logic could ship while still rendering `approved`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a test mirroring `D_SHORT` but with `PUBLISH_OK_VALUE=true` and empty PR stdout, asserting `PR_NUMBER`/`PR_URL` remain in `.design-publish-result.env`.
  - From cursor-specialist-testing-output.txt: Add a case seeding prior PUBLISH_OK=true and PR 77, stub publish to emit only PUBLISH_OK=true, assert design-log-publish is invoked and PR 77 is preserved in result env and render output.


### FINDING_10: Retired-script lint prefilter skips retired `.py` paths
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: At `python/migration_lint.py:280-288`, the new retired-script prefilter skips every line that lacks `.sh` or `.md`, but `python/migrated-scripts.tsv` already contains retired `.py` paths such as `python/ci_cli.py`. A tracked doc or script can reintroduce the literal `python/ci_cli.py`; this line contains neither `.sh` nor `.md`, so `lint retired-scripts` never checks it and incorrectly reports clean.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Build candidate retired paths from every retired basename, not only `.sh`/`.md` lines. For example, remove the `.sh`/`.md` gate and rely on the `retired_by_basename` lookup.


### FINDING_11: Final idempotency porcelain check omits untracked files
- **Reviewer(s)**: dyn-shell-rebuild-output.txt
- **Severity**: important
- **Concern**: At `scripts/design-log-publish.sh:618-624`, final-mode late idempotency calls `git status --porcelain -- "$rel"` without `-uall` (or an equivalent post-`git add -A` cached diff). If a consumer clone sets `status.showUntrackedFiles=no`, new snapshot files under the run directory are omitted from porcelain while tracked edits/deletions still appear. That can yield an empty porcelain result and an early `PUBLISH_OK=true` exit even when the desired snapshot adds files not on `origin/<default>`. The new rebuild path depends on this check more than the removed early shortcut, so the failure mode is newly reachable on re-publish.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-rebuild-output.txt: Use `git -C "$WT_DIR" status --porcelain -uall -- "$rel"` for rebuild delta detection, or stage with `git add -A -- "$rel"` and gate idempotency on `git diff --cached --quiet HEAD -- "$rel"` (then keep the manifest-only churn branch on the staged diff). Mirror the same rule anywhere final idempotency still reads porcelain (including the manifest-only path at `627-630`).


### FINDING_8: DESIGN_LOG_PR_* exports before prior PR metadata reload on idempotent re-entry
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: On idempotent Step 5c re-entry at `skills/design/scripts/design-publish.sh:697-717`, `DESIGN_LOG_PR_NUMBER`/`DESIGN_LOG_PR_URL` exports happen before the prior PR metadata reload block. A prior successful publish stored `PR_NUMBER=77`; a re-entry publish returns `PUBLISH_OK=true` with empty PR fields because `design-log-publish.sh` found no delta; `render-final-summary` runs with empty `DESIGN_LOG_PR_NUMBER` and the operator loses the log PR link in the final summary even though publish succeeded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Move DESIGN_LOG_PR_NUMBER/DESIGN_LOG_PR_URL exports after the result_env_load_success_metadata reload block, or re-export after reload.


