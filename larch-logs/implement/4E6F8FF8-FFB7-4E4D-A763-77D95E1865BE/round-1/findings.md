Normalized aggregator output from the supplied reviewer slots. Positive attestations (FINDING_4–7, 19–21, 25–26, 29–31, 36–37) describe met requirements or correct harness behavior and are not emitted as defect findings.

### FINDING_1: [OUT_OF_SCOPE] Branch stacks multiple deliverables (#3204, #3209, #3212, larch-logs)
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `HEAD` stacks four independent deliverables (#3204 trailer harness, #3209 ship-pr/review-and-fix, #3212 cleanup, plus a `chore(larch-logs)` flush). That widens CI surface and blocks trailer-focused review on unrelated diff noise. The #3204 implement commit (`d33cdfb70`) is isolated, but the branch is not #3204-only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: For reviewability, consider splitting or clearly labeling in the PR body so trailer-harness reviewers are not blocked on ship-pr/cleanup diff noise.
  - From cursor-specialist-testing-output.txt: None for #3204; review/CI those commits on their own merits before merge.
  - From cursor-specialist-plan-fidelity-output.txt: **Why out of scope:** not named in the implementation plan and not part of the trailer-harness deliverable; review separately if this PR is meant to be #3204-only.

### FINDING_2: [OUT_OF_SCOPE] Pre-existing `test-trailer-*.sh` wrappers lack sibling `.md` docs
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The four thin wrapper harnesses (`test-trailer-dedup.sh`, `has-any`, `validate`, pre-#3204 adapters) still have no sibling `.md`; the plan explicitly kept that state. Not introduced by this diff.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_3: [OUT_OF_SCOPE] `run_has_key` duplicates `run_awk` in `test-trailer-awk.sh`
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:58-62`, `run_has_key` duplicates `run_awk` with the same `trailer_nr` + `-f` invocation; folding into `run_awk has_key` with `-v key=` would be a one-line DRY cleanup. Pre-existing pattern in sibling harnesses is similar; optional only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: folding into `run_awk has_key` with `-v key=` would be a one-line DRY cleanup.

### FINDING_4: [OUT_OF_SCOPE] Octal-rejected fixture lacks `keys`/`values` empty-output assertions
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-rebase-fixup-commit-scope-output.txt
- **Severity**: important
- **Concern**: On `skills/design/scripts/test-trailer-awk.sh` (octal-rejected fixture, ~149–161), only `parse` / `has_key` are asserted; `keys` / `values` are not. If those modes regress to emit `diff_added`/`diff_deleted` for `08`/`09` while `has_key` still rejects them, `test-trailer-helpers` can pass but trailer snapshots could corrupt. Plan’s `keys` bullet and edge-case review treat empty-output assertions as required or strongly recommended hardening.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Optional hardening — add `assert_keys` / `assert_values` for empty output on octal and `diff_added`-only on block-boundary if you want symmetric mode coverage.
  - From cursor-specialist-edge-cases-output.txt: Add assert_keys and assert_values with empty want on $TMPROOT/octal-rejected after the existing parse/has_key checks.

### FINDING_5: [OUT_OF_SCOPE] No fixture for trailing blank lines after `diff_lines:` (`trailer_nr` last-non-empty rule)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-trailer-awk.sh` has no fixture with trailing blank lines after `diff_lines:` to exercise `trailer_nr()`’s “last non-empty line” rule explicitly (behavior is implicit in existing fixtures).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add one fixture with a trailing blank line if you want a dedicated regression for `NF`-based `trailer_nr` computation.

### FINDING_6: Pre-rebase `git add -u` auto-commit stages all tracked dirty paths (`ship-pr.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-rebase-fixup-commit-scope-output.txt
- **Severity**: important
- **Concern**: In `scripts/ship-pr.sh` Step 0b (~2853–2870 / ~2856–2870), when porcelain is non-empty, `run_rebase_rebump` runs `git add -u` on every tracked dirty path and commits via `git-commit.sh` (`chore: pre-rebase working-tree fixup (#3209)`). Failures are warnings only until `drop-bump-commit.sh` Guard 1. That commit survives rebase (tests at `scripts/test-ship-pr.sh:656-660` expect it). Any unintended tracked WIP—including credentials/tokens left modified during `/implement`—can be permanently recorded on the PR branch, not merely unstaged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Restrict auto-commit to an allowlisted path set (e.g. larch-logs/ only) or fail closed when staged diff matches secret/forbidden-path policies.
  - From cursor-specialist-edge-cases-output.txt: consider scoping the add/commit to known larch-logs paths or failing closed.
  - From dyn-rebase-fixup-commit-scope-output.txt: Narrow staging to an allowlist (e.g. `larch-logs/`, known hook targets) or require a clean tracked tree except explicitly documented paths; alternatively gate the fixup on residue class (hook vs. other) before `git add -u`.

### FINDING_7: Round-mode follow-up commit lacks second submodule revert after hooks (`review-and-fix.sh`)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: At `skills/review-and-fix/scripts/review-and-fix.sh:461-465`, the follow-up round commit uses `git add -A` without re-running submodule revert after pre-commit hooks may rewrite the tree. A hook that re-modifies submodule paths after the first revert/commit can let the follow-up commit record forbidden submodule changes while the round still succeeds until later guards.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Re-run post_dispatch_submodule_revert before follow-up staging; fail closed on submodule paths in the follow-up index.

### FINDING_8: Blank-line block boundary not covered in awk unit harness
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:103-111`, the plan’s blank-line block boundary is not covered. An awk change treating blank lines as continuations could pass this harness but mis-count `block_len` until integration Case 24 fails.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add a fixture with a blank line between trailers and diff_lines:; assert parse/keys/values/has_key match in-block-only semantics.

### FINDING_9: No mixed octal-then-valid duplicate fixture for `block_len`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:94-101`, there is no fixture where rejected octal lines precede a valid trailer. A regression counting rejected octal lines toward `block_len` passes `octal-rejected` (`block_len` 0) but breaks plan-size when a valid trailer follows an `08`/`09` line.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add diff_added: 08 then diff_added: 5 before diff_lines:; assert parse block_len 1, value 5, and empty keys for the octal line alone.

### FINDING_10: `keys` mode untested on duplicate and block-boundary fixtures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: At `skills/design/scripts/test-trailer-awk.sh:149-158`, `keys` mode is not asserted on duplicate `diff_added` or block-boundary fixtures. A keys-only emission-order bug could slip past while `values`/`parse` still pass.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Assert keys on duplicate-diff-added (single diff_added) and block-boundary fixtures.

### FINDING_11: [OUT_OF_SCOPE] Cleanup retention uses top-level `find -mtime` only (#3212)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-data-loss-regression-output.txt, dyn-rebase-fixup-commit-scope-output.txt
- **Severity**: important
- **Concern**: In `skills/cleanup/scripts/cleanup.sh` (~39–86 / ~1006–1072), replacing `newest_activity_mtime` (depth-5 descendant scan) with top-level `find … -mtime +N` plus unconditional `rm -rf` can delete active `/implement` or `/design` session trees under `~/.cache/larch/sessions/` or `/tmp` when the **directory** mtime is older than `LARCH_CLEANUP_RETENTION_DAYS` (default 7) even while descendants are still written. Deep-only writes often do not refresh the session root mtime; `.larch-keepalive` is written once and is not a retention shield (harness cases `stale-dir-with-keepalive-removed` and `stale-toplevel-with-fresh-deep-child-removed` codify this). Long-lived or resumed runs on old `IMPLEMENT_TMPDIR` roots can lose `round-<N>/`, `larch-logs/implement/<RUN_ID>/`, etc., while Claude is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: document semantics or restore nested-activity checks without full-tree find hangs.
  - From dyn-data-loss-regression-output.txt: Either restore a bounded activity signal for cache session dirs (e.g. shallow `find` or touch the session root when any descendant under known prefixes is written), or add an explicit “active session” skip (e.g. refresh `.larch-keepalive` mtime on hook cadence, or skip dirs whose keepalive `SESSION_ID` matches a live token) so `/cleanup` cannot delete trees that still match `lib-resolve-implement-tmpdir.sh` / SessionStart routing.
  - From dyn-rebase-fixup-commit-scope-output.txt: If nested activity must still protect live sessions, combine top-level `find` enumeration (for performance) with a bounded newest-descendant mtime check before `rm -rf`, or touch the session directory on keepalive/heartbeat so top-level mtime tracks liveness.

### FINDING_12: [OUT_OF_SCOPE] Cleanup age-pass `find` errors swallowed
- **Reviewer(s)**: dyn-data-loss-regression-output.txt
- **Severity**: latent
- **Concern**: At `skills/cleanup/scripts/cleanup.sh:43,85`, age-pass `find` errors are swallowed (`2>/dev/null`, `|| true`), so cleanup can exit 0 with `CACHE_REMOVED=0` / `TMP_REMOVED=0` when enumeration fails; operators may believe stale data was reclaimed when nothing was deleted.
- **Suggested revisions (informational for voters; coder decides)**:

### FINDING_13: Option A backstop message misleading when follow-up fails closed at Step 5
- **Reviewer(s)**: dyn-follow-up-commit-flow-output.txt
- **Severity**: important
- **Concern**: On the round-mode follow-up path in `skills/review-and-fix/scripts/review-and-fix.sh:467-480`, a failed `git add -A` / `git-commit.sh` emits “leaving residue for the ship-pr Option A backstop”, but when tracked porcelain remains non-empty the next check returns exit **2** with `CODER_STATUS=failed` and no `CODER_COMMIT_SHA`. `review-and-fix.md` documents exit **2** as blocking for `/implement` Step 5, while Option A only runs later in `ship-pr.sh` `run_rebase_rebump`; in persistent-hook failure class the workflow stops at Step 5, so the backstop message describes a recovery path that does not run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-follow-up-commit-flow-output.txt: Reword or gate the Option A warning so it only logs when execution can actually reach `run_rebase_rebump` (e.g. findings mode / warn-and-continue), or drop it on the fail-closed branch and rely on the second `left tracked changes uncommitted after follow-up` message; align `review-and-fix.md` with whichever contract you keep.

### FINDING_14: Failed follow-up can fall through to success epilogue (`CODER_STATUS=applied`)
- **Reviewer(s)**: dyn-follow-up-commit-flow-output.txt
- **Severity**: important
- **Concern**: At `skills/review-and-fix/scripts/review-and-fix.sh:467-495`, if the follow-up `if git add -A && git-commit.sh` branch fails but `git status --porcelain --untracked-files=no` is unexpectedly empty afterward, control falls through to the success epilogue: `CODER_STATUS=applied`, exit **0**, and `CODER_COMMIT_SHA` stays at the **primary** round commit SHA even though the follow-up commit never landed. Step 5 can report success while tree state does not match `CODER_COMMIT_SHA`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-follow-up-commit-flow-output.txt: Treat follow-up `else` as failure unless you explicitly verify the residue that triggered the block is gone (e.g. return **2** or at minimum avoid emitting `applied` / refresh `commit_sha` only when follow-up succeeded).

### FINDING_15: `git add -u` (ship-pr) vs `git add -A` (review-and-fix) staging asymmetry
- **Reviewer(s)**: dyn-follow-up-commit-flow-output.txt
- **Severity**: latent
- **Concern**: Option A pre-rebase fixup (`scripts/ship-pr.sh:2856-2870`) uses `git add -u` (tracked only); round-mode primary and follow-up commits (`skills/review-and-fix/scripts/review-and-fix.sh:438-465`) use `git add -A`. Both gate on tracked-only porcelain (`--untracked-files=no`), but when tracked dirt and new untracked files coexist, Step 5 follow-up can sweep untracked into the follow-up commit while Option A may leave untracked residue and still hit `drop-bump-commit.sh` Guard 1 on a later full-tree check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-follow-up-commit-flow-output.txt: Document the intentional asymmetry and add a harness case with coexisting tracked hook residue plus untracked files, or align staging (`-A` vs `-u`) with the documented “match primary round commit” contract if full staging is required at rebase.
