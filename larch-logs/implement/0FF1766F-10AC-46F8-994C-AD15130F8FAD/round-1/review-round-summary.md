# Review Round 1

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 6
- Exonerated findings: 0
- Neutral findings: 0

## Accepted Findings

### FINDING_1: **architecture** `scripts/create-pr.md:63` — The existing-PR escalation paragraph still equates a non-zero `git-force-push.sh` outcome with `STATUS=diverged_retry_failed` only. After the branch change, exit 1 can also mean a dirty working tree (no `PUSHED=`/`STATUS=` on stdout), and `create-pr.sh` already suppresses helper stdout so that parenthetical was never a faithful “observed STATUS” claim; it now misstates which failure modes exist and can mislead anyone using the doc as the SSOT for stderr interpretation versus `git-force-push.md`. **Suggested fix:** Rewrite that sentence so exit 1 covers both dirty-tree aborts and post-retry diverged push failures, and point readers at `scripts/git-force-push.md` for the stdout/stderr split instead of naming a single `STATUS=` value.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **architecture** `scripts/create-pr.md:63` — The existing-PR escalation paragraph still equates a non-zero `git-force-push.sh` outcome with `STATUS=diverged_retry_failed` only. After the branch change, exit 1 can also mean a dirty working tree (no `PUSHED=`/`STATUS=` on stdout), and `create-pr.sh` already suppresses helper stdout so that parenthetical was never a faithful “observed STATUS” claim; it now misstates which failure modes exist and can mislead anyone using the doc as the SSOT for stderr interpretation versus `git-force-push.md`. **Suggested fix:** Rewrite that sentence so exit 1 covers both dirty-tree aborts and post-retry diverged push failures, and point readers at `scripts/git-force-push.md` for the stdout/stderr split instead of naming a single `STATUS=` value.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/create-pr.sh:22-25
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] File-header exit-code comments omit dirty-tree exit 1 and misstate exit 2 scope after the new guard. Operators reading only the script banner misdiagnose a dirty-tree failure as a generic push failure or miss the new exit-1 meaning. Align header with create-pr.md exit-code table.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/create-pr.sh:98 scripts/git-force-push.sh:59
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] git status errors are swallowed as empty DIRTY_FILES via 2>/dev/null and || true. git status fails (corrupt metadata edge) but push proceeds without the intended safety gate. Fail closed when git status is non-zero instead of treating errors as clean.
- **Suggested revision**: Address the concern above.


### FINDING_3: **code-quality** `scripts/git-force-push.sh:24-27` — The script header’s “Exit codes” comment still says exit 1 is only `PUSHED=false` with `STATUS=diverged_retry_failed`, with no mention of the new dirty-tree exit 1 or partial stdout (`BRANCH=` only). That contradicts the updated sibling contract in `scripts/git-force-push.md` from the same diff and violates the repo’s “keep script headers aligned with behavior” expectation. **Suggested fix:** Update the header block so exit 1 documents both dirty-tree (no `PUSHED`/`STATUS`) and `diverged_retry_failed`, matching `scripts/git-force-push.md`.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **code-quality** `scripts/git-force-push.sh:24-27` — The script header’s “Exit codes” comment still says exit 1 is only `PUSHED=false` with `STATUS=diverged_retry_failed`, with no mention of the new dirty-tree exit 1 or partial stdout (`BRANCH=` only). That contradicts the updated sibling contract in `scripts/git-force-push.md` from the same diff and violates the repo’s “keep script headers aligned with behavior” expectation. **Suggested fix:** Update the header block so exit 1 documents both dirty-tree (no `PUSHED`/`STATUS`) and `diverged_retry_failed`, matching `scripts/git-force-push.md`.
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** `scripts/create-pr.sh:98-102` — `DIRTY_FILES=$(git status --porcelain 2>/dev/null || true)` discards stderr and forces success on non-zero exit, so a failing or mis-invoked `git status` (broken repo, wrong `GIT_DIR`, I/O error) yields an empty `DIRTY_FILES` and the script can treat the tree as clean and continue toward push, which is the opposite of fail-closed for the new guard’s purpose. **Suggested fix:** run `git status --porcelain` without `|| true`, do not send stderr to `/dev/null`, and on non-zero exit emit `larch_err` with stderr (or re-run with explicit error) and exit non-zero (e.g. `2` for “guard could not run”) instead of inferring cleanliness from empty output.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **correctness** `scripts/create-pr.sh:98-102` — `DIRTY_FILES=$(git status --porcelain 2>/dev/null || true)` discards stderr and forces success on non-zero exit, so a failing or mis-invoked `git status` (broken repo, wrong `GIT_DIR`, I/O error) yields an empty `DIRTY_FILES` and the script can treat the tree as clean and continue toward push, which is the opposite of fail-closed for the new guard’s purpose. **Suggested fix:** run `git status --porcelain` without `|| true`, do not send stderr to `/dev/null`, and on non-zero exit emit `larch_err` with stderr (or re-run with explicit error) and exit non-zero (e.g. `2` for “guard could not run”) instead of inferring cleanliness from empty output.
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** `scripts/git-force-push.sh:59-63` — Same pattern as `create-pr.sh`: `2>/dev/null || true` can turn a hard `git status` failure into a false “clean” result and allow `push_with_lease` to run, undermining defense-in-depth for direct callers (`scripts/merge-pr.sh`, `scripts/ship-pr.sh`). **Suggested fix:** mirror the fail-closed handling above: propagate `git status` failure as a distinct abort (and surface stderr) rather than collapsing all failures to an empty porcelain snapshot.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **correctness** `scripts/git-force-push.sh:59-63` — Same pattern as `create-pr.sh`: `2>/dev/null || true` can turn a hard `git status` failure into a false “clean” result and allow `push_with_lease` to run, undermining defense-in-depth for direct callers (`scripts/merge-pr.sh`, `scripts/ship-pr.sh`). **Suggested fix:** mirror the fail-closed handling above: propagate `git status` failure as a distinct abort (and surface stderr) rather than collapsing all failures to an empty porcelain snapshot.
- **Suggested revision**: Address the concern above.


### FINDING_7: **risk-integration** `scripts/test-create-pr.sh:17-30` — **Important:** `setup_repo` leaves `body.md` untracked after the initial commit, so the new `create-pr.sh` guard sees every harness repo as dirty before it ever reaches `git push`. Concrete failure: the first create-path test at `scripts/test-create-pr.sh:82-84` invokes `create-pr.sh --body-file body.md`; `git status --porcelain` reports `?? body.md`, `create-pr.sh` exits 1, and `make test-create-pr` fails instead of proving the clean-tree path. **Suggested fix:** Make the fixture repos clean by committing `body.md` in `setup_repo` or placing the PR body file outside the worktree, then keep the dirty tracked/untracked cases adding their extra files after setup.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `scripts/test-create-pr.sh:17-30` — **Important:** `setup_repo` leaves `body.md` untracked after the initial commit, so the new `create-pr.sh` guard sees every harness repo as dirty before it ever reaches `git push`. Concrete failure: the first create-path test at `scripts/test-create-pr.sh:82-84` invokes `create-pr.sh --body-file body.md`; `git status --porcelain` reports `?? body.md`, `create-pr.sh` exits 1, and `make test-create-pr` fails instead of proving the clean-tree path. **Suggested fix:** Make the fixture repos clean by committing `body.md` in `setup_repo` or placing the PR body file outside the worktree, then keep the dirty tracked/untracked cases adding their extra files after setup.
- **Suggested revision**: Address the concern above.


