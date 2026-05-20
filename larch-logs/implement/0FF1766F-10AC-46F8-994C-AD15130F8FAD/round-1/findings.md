### FINDING_1: **architecture** `scripts/create-pr.md:63` — The existing-PR escalation paragraph still equates a non-zero `git-force-push.sh` outcome with `STATUS=diverged_retry_failed` only. After the branch change, exit 1 can also mean a dirty working tree (no `PUSHED=`/`STATUS=` on stdout), and `create-pr.sh` already suppresses helper stdout so that parenthetical was never a faithful “observed STATUS” claim; it now misstates which failure modes exist and can mislead anyone using the doc as the SSOT for stderr interpretation versus `git-force-push.md`. **Suggested fix:** Rewrite that sentence so exit 1 covers both dirty-tree aborts and post-retry diverged push failures, and point readers at `scripts/git-force-push.md` for the stdout/stderr split instead of naming a single `STATUS=` value.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **architecture** `scripts/create-pr.md:63` — The existing-PR escalation paragraph still equates a non-zero `git-force-push.sh` outcome with `STATUS=diverged_retry_failed` only. After the branch change, exit 1 can also mean a dirty working tree (no `PUSHED=`/`STATUS=` on stdout), and `create-pr.sh` already suppresses helper stdout so that parenthetical was never a faithful “observed STATUS” claim; it now misstates which failure modes exist and can mislead anyone using the doc as the SSOT for stderr interpretation versus `git-force-push.md`. **Suggested fix:** Rewrite that sentence so exit 1 covers both dirty-tree aborts and post-retry diverged push failures, and point readers at `scripts/git-force-push.md` for the stdout/stderr split instead of naming a single `STATUS=` value.
- **Suggested revision**: Address the concern above.

### FINDING_2: **architecture** `scripts/implement-finalize.sh:896-913` — `run_force_push_gate` parses `STATUS` from the captured `git-force-push.sh` output and treats anything outside `pushed|noop_same_ref` as the default case, emitting a hard-coded `warn_line` about a lease refusal. A dirty-tree failure yields an empty `STATUS` (and `rc=1`), so it follows that same branch and surfaces the wrong headline to the operator even though `larch_err` in the captured output explains the real cause; the same default branch already treats `STATUS=diverged_retry_failed` as “lease check refused,” so the new guard widens the audience for that misleading message without fixing the underlying misclassification. **Suggested fix:** Detect dirty-tree failures (e.g., non-zero `rc` with no `STATUS=` line or a stderr/grep sentinel from the merged capture) and emit a distinct warning / `append_execution_issue` string, reserving the lease wording for true `diverged_retry_failed` (and optionally other push-failure shapes).
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **architecture** `scripts/implement-finalize.sh:896-913` — `run_force_push_gate` parses `STATUS` from the captured `git-force-push.sh` output and treats anything outside `pushed|noop_same_ref` as the default case, emitting a hard-coded `warn_line` about a lease refusal. A dirty-tree failure yields an empty `STATUS` (and `rc=1`), so it follows that same branch and surfaces the wrong headline to the operator even though `larch_err` in the captured output explains the real cause; the same default branch already treats `STATUS=diverged_retry_failed` as “lease check refused,” so the new guard widens the audience for that misleading message without fixing the underlying misclassification. **Suggested fix:** Detect dirty-tree failures (e.g., non-zero `rc` with no `STATUS=` line or a stderr/grep sentinel from the merged capture) and emit a distinct warning / `append_execution_issue` string, reserving the lease wording for true `diverged_retry_failed` (and optionally other push-failure shapes).
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

### FINDING_6: **correctness** `scripts/test-create-pr.sh:312-335` — New regression coverage only exercises tracked content modification and an untracked file; it does not cover other non-empty porcelain cases called out in review notes (e.g. staged-but-uncommitted index entries, or unmerged paths), nor a controlled scenario where `git status` fails, so a future change that reintroduces `|| true` or swallows errors could pass CI while re-opening the false-negative hole. **Suggested fix:** add harness cases for “dirty index / staged only” and, if feasible in the temp-repo fixture, a stubbed or broken `git`/`GIT_DIR` path that forces `git status` to fail and asserts the script exits non-zero without pushing.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **correctness** `scripts/test-create-pr.sh:312-335` — New regression coverage only exercises tracked content modification and an untracked file; it does not cover other non-empty porcelain cases called out in review notes (e.g. staged-but-uncommitted index entries, or unmerged paths), nor a controlled scenario where `git status` fails, so a future change that reintroduces `|| true` or swallows errors could pass CI while re-opening the false-negative hole. **Suggested fix:** add harness cases for “dirty index / staged only” and, if feasible in the temp-repo fixture, a stubbed or broken `git`/`GIT_DIR` path that forces `git status` to fail and asserts the script exits non-zero without pushing.
- **Suggested revision**: Address the concern above.

### FINDING_7: **risk-integration** `scripts/test-create-pr.sh:17-30` — **Important:** `setup_repo` leaves `body.md` untracked after the initial commit, so the new `create-pr.sh` guard sees every harness repo as dirty before it ever reaches `git push`. Concrete failure: the first create-path test at `scripts/test-create-pr.sh:82-84` invokes `create-pr.sh --body-file body.md`; `git status --porcelain` reports `?? body.md`, `create-pr.sh` exits 1, and `make test-create-pr` fails instead of proving the clean-tree path. **Suggested fix:** Make the fixture repos clean by committing `body.md` in `setup_repo` or placing the PR body file outside the worktree, then keep the dirty tracked/untracked cases adding their extra files after setup.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: - **risk-integration** `scripts/test-create-pr.sh:17-30` — **Important:** `setup_repo` leaves `body.md` untracked after the initial commit, so the new `create-pr.sh` guard sees every harness repo as dirty before it ever reaches `git push`. Concrete failure: the first create-path test at `scripts/test-create-pr.sh:82-84` invokes `create-pr.sh --body-file body.md`; `git status --porcelain` reports `?? body.md`, `create-pr.sh` exits 1, and `make test-create-pr` fails instead of proving the clean-tree path. **Suggested fix:** Make the fixture repos clean by committing `body.md` in `setup_repo` or placing the PR body file outside the worktree, then keep the dirty tracked/untracked cases adding their extra files after setup.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] **Acceptance vs diff:** The precomputed diff does not add `scripts/test-ship-pr.sh` coverage or touch `scripts/ship-pr.sh` directly; enforcement is delegated to `create-pr.sh` / `git-force-push.sh`. If issue #2434 explicitly required a `ship-pr.sh`-level hook or ship-pr harness tests, that gap is outside this diff’s surface (no `ship-pr.sh` changes in `diff.txt`).
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Acceptance vs diff:** The precomputed diff does not add `scripts/test-ship-pr.sh` coverage or touch `scripts/ship-pr.sh` directly; enforcement is delegated to `create-pr.sh` / `git-force-push.sh`. If issue #2434 explicitly required a `ship-pr.sh`-level hook or ship-pr harness tests, that gap is outside this diff’s surface (no `ship-pr.sh` changes in `diff.txt`).
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] **Caller tolerance:** `scripts/create-pr.sh:138-140` appends helper stderr via `2>>"$PUSH_STDERR"` while discarding stdout; with `larch_quiet_init`, `larch_err` writes to the saved original stderr FD (`scripts/lib-quiet.sh:80-86`), so dirty-tree diagnostics still land in `PUSH_STDERR` and get surfaced by the parent’s `ERROR: Failed to push branch on existing-PR fast-path: …` path. `scripts/ship-pr.sh:1444-1448` keys off `rc` and logs combined output to `fail_file`, which is sufficient for the new exit 1. `scripts/merge-pr.sh:193-200` uses `PUSHED`/`STATUS` awk extraction with `|| true`; an empty `PUSHED` on dirty-tree failure still routes to `MERGE_RESULT=error` without merging, which is safe even though the prose says “force-push failed” generically.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Caller tolerance:** `scripts/create-pr.sh:138-140` appends helper stderr via `2>>"$PUSH_STDERR"` while discarding stdout; with `larch_quiet_init`, `larch_err` writes to the saved original stderr FD (`scripts/lib-quiet.sh:80-86`), so dirty-tree diagnostics still land in `PUSH_STDERR` and get surfaced by the parent’s `ERROR: Failed to push branch on existing-PR fast-path: …` path. `scripts/ship-pr.sh:1444-1448` keys off `rc` and logs combined output to `fail_file`, which is sufficient for the new exit 1. `scripts/merge-pr.sh:193-200` uses `PUSHED`/`STATUS` awk extraction with `|| true`; an empty `PUSHED` on dirty-tree failure still routes to `MERGE_RESULT=error` without merging, which is safe even though the prose says “force-push failed” generically.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] **Double guard / exit-code parity:** `create-pr.sh` runs the porcelain guard before any push (`scripts/create-pr.sh:96-103`), so a dirty tree at script entry never reaches `git-force-push.sh`; the helper guard is defense-in-depth for direct callers (`merge-pr.sh`, `implement-finalize.sh` Step 8b, `ship-pr.sh` rebase-rebump). Both failure modes use exit 1, consistent with the updated `scripts/create-pr.md` exit table; stderr text differs (`ERROR: Uncommitted…` vs `git-force-push.sh: uncommitted…`), so operators are not forced to rely on exit-code subtyping alone.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **Double guard / exit-code parity:** `create-pr.sh` runs the porcelain guard before any push (`scripts/create-pr.sh:96-103`), so a dirty tree at script entry never reaches `git-force-push.sh`; the helper guard is defense-in-depth for direct callers (`merge-pr.sh`, `implement-finalize.sh` Step 8b, `ship-pr.sh` rebase-rebump). Both failure modes use exit 1, consistent with the updated `scripts/create-pr.md` exit table; stderr text differs (`ERROR: Uncommitted…` vs `git-force-push.sh: uncommitted…`), so operators are not forced to rely on exit-code subtyping alone.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] **Pre-existing / not introduced by this diff:** `scripts/ship-pr.sh` is unchanged; pushes still flow through `scripts/create-pr.sh` and `scripts/git-force-push.sh`, so behavior is covered indirectly even though the feature text mentioned `ship-pr.sh` by name.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **Pre-existing / not introduced by this diff:** `scripts/ship-pr.sh` is unchanged; pushes still flow through `scripts/create-pr.sh` and `scripts/git-force-push.sh`, so behavior is covered indirectly even though the feature text mentioned `ship-pr.sh` by name.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] **TOCTOU:** Any point-in-time `git status` check can pass and the working tree can still change before `git push`; that race is inherent and not introduced solely by this branch (the guard still removes the dominant “forgot to commit” failure mode).
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **TOCTOU:** Any point-in-time `git status` check can pass and the working tree can still change before `git push`; that race is inherent and not introduced solely by this branch (the guard still removes the dominant “forgot to commit” failure mode).
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] **`scripts/create-pr.sh:40-43`:** `trap cleanup EXIT` already removes `REDACTED_BODY_FILE` on the new `exit 1` path, so the dirty-tree abort does not leave the redaction tempfile behind (the scout note about cleanup is not a defect here).
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **`scripts/create-pr.sh:40-43`:** `trap cleanup EXIT` already removes `REDACTED_BODY_FILE` on the new `exit 1` path, so the dirty-tree abort does not leave the redaction tempfile behind (the scout note about cleanup is not a defect here).
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] **`scripts/merge-pr.sh:193-196`:** `git-force-push.sh` output is merged stdout/stderr with `PUSHED` parsed from lines; a dirty-tree exit leaves `PUSHED` non-`true`, so the existing failure branch still trips without requiring a new parser shape.
- **Reviewer**: dyn-git-state-coverage-output.txt
- **Concern**: - **`scripts/merge-pr.sh:193-196`:** `git-force-push.sh` output is merged stdout/stderr with `PUSHED` parsed from lines; a dirty-tree exit leaves `PUSHED` non-`true`, so the existing failure branch still trips without requiring a new parser shape.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] code-quality: scripts/test-ship-pr.sh:404-414
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Rebump harness stubs git-force-push.sh with exit 0. New real-script guard is not exercised in ship-pr tests. Pre-existing stub pattern; only note if end-to-end ship-pr coverage of the guard is desired later.
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] risk-integration: feature_description vs branch
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Feature text names ship-pr and test-ship-pr; branch targets leaf scripts and test-create-pr. Documentation of intent vs file-level plan wording mismatch. No code change required if issue #2434 accepts leaf-script enforcement.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/create-pr.sh:148-155
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Guard runs after mktemp and PR body redaction work. Dirty repos pay for redaction and temp file setup before failing fast. Move porcelain check earlier after prerequisite validation and before mktemp/redact.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/git-force-push.sh:61-64 vs scripts/create-pr.sh:151-154
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent operator guidance between the two dirty-tree messages. Operators get discard guidance on one path but not the other. Align error text with create-pr.sh including discard wording.
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: scripts/test-create-pr.sh:312-315
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Clean-tree test discards stderr via 2>/dev/null. Regression or unexpected errors hide in /dev/null; failure shows only as missing PR_STATUS line. Capture stderr to a temp file and assert empty or expected content like other cases.
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: scripts/test-create-pr.sh:320-335
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Dirty tests accept any non-zero exit. Exit 2 from unrelated failures could satisfy the test without proving the guard. Assert exit code 1 explicitly for dirty-tree scenarios.
- **Suggested revision**: Address the concern above.

### FINDING_21: correctness: scripts/create-pr.sh:22-25
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] File-header exit-code comments omit dirty-tree exit 1 and misstate exit 2 scope after the new guard. Operators reading only the script banner misdiagnose a dirty-tree failure as a generic push failure or miss the new exit-1 meaning. Align header with create-pr.md exit-code table.
- **Suggested revision**: Address the concern above.

### FINDING_22: correctness: scripts/create-pr.sh:98 scripts/git-force-push.sh:59
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] git status errors are swallowed as empty DIRTY_FILES via 2>/dev/null and || true. git status fails (corrupt metadata edge) but push proceeds without the intended safety gate. Fail closed when git status is non-zero instead of treating errors as clean.
- **Suggested revision**: Address the concern above.

### FINDING_23: correctness: scripts/git-push.sh:39-45
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Ship-pr still calls git-push.sh after CI fixes without a clean-tree guard; only create-pr and git-force-push were hardened. Uncommitted OOS or stray edits remain local while git-push.sh pushes the new Fix CI commit; remote advances without those files; same silent data-loss pattern as issue #2434. Add porcelain abort to git-push.sh before push; extend test-git-push.sh or ship-pr tests; update workflow-lifecycle invariant text to list all push wrappers.
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: docs/workflow-lifecycle.md:26-28
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Prose attributes the guard to /implement rather than the shell entrypoints. Readers may search SKILL.md for enforcement that lives in scripts. Name create-pr.sh and git-force-push.sh (or ship-pr call chain) explicitly.
- **Suggested revision**: Address the concern above.

