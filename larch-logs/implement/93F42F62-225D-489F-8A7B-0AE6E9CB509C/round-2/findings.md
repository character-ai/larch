### FINDING_1: code-quality: scripts/design-pause-load.md:60-69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] MARKER_CLEARED=true|false is emitted on the success path but omitted from the documented loader output contract. A test or operator script that validates stdout against design-pause-load.md will not expect MARKER_CLEARED and may fail or ignore post-success marker-delete state. Document MARKER_CLEARED in design-pause-load.md Output Contract (and SECURITY.md if operator-facing) or remove the KV if it is test-only.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: scripts/design-pause-load.sh:235-237
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Empty ls-tree enumeration returns snapshot-not-found before artifact checks, but design-pause-load.md only describes missing-restored-artifact after extraction. A deleted or never-published snapshot subtree yields ERROR=snapshot-not-found while docs imply missing-restored-artifact, confusing runbooks and plan-aligned fixtures. Document the ! -s enum_tmp early-exit in design-pause-load.md with clear token semantics for empty vs partial snapshots.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: scripts/design-log-publish.sh:589-598
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Driver phase sentinel allowlist is duplicated from design-driver.sh with comment-only coupling. A new design-driver.sh ACTION added without updating the publisher allowlist re-breaks pause publish with unexpected file under .completed. Share one allowlist source or add a test that diffs driver actions against publisher accepted basenames.
- **Suggested revision**: Address the concern above.

### FINDING_4: code-quality: skills/design/scripts/test-design-pause-resume.sh:104-107
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ls-tree stub uses last argv token as path instead of parsing git ls-tree arguments. Future loader argv reordering makes the stub return empty output while production works, causing false-green or false-red harness results. Parse the tree path argument explicitly (after -- or by larch-logs/design/ prefix).
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: scripts/design-pause-load.sh:311
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Success path clears .pause-requested without contract documentation. Operators debugging a resumed session may not know the loader clears pause-requested state, leading to confusion about why a mid-run pause flag vanished. Mention .pause-requested removal in the success-path section of design-pause-load.md.
- **Suggested revision**: Address the concern above.

### FINDING_6: correctness: scripts/design-pause-load.sh:235-237
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Empty ls-tree enumeration exits with snapshot-not-found before artifact checks, contradicting plan/acceptance that require missing-restored-artifact for deleted/missing snapshot subtrees. After rm -rf of larch-logs/design/RUN_ID/ on the selected ref, loader emits ERROR=snapshot-not-found; operators and acceptance text expect missing-restored-artifact for this shape. Remove the ! -s enum_tmp early exit and rely on missing-restored-artifact checks, or update plan acceptance and operator docs to standardize on snapshot-not-found for empty enumeration.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/design-pause-load.md:33-54
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Contract omits the empty-enumeration error branch present in the shell implementation. Maintainer reads design-pause-load.md only and misexpects missing-restored-artifact when ls-tree returns zero paths. Document which ERROR token empty enumeration produces and how it differs from snapshot-extract-failed and missing-restored-artifact.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/scripts/test-design-pause-resume.md:33-35
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Harness doc says deleted-subtree uses missing-restored-artifact but the test asserts snapshot-not-found. Doc-driven debugging contradicts test expectations. Align the markdown coverage note with the test and chosen error token.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/design/scripts/test-design-pause-resume.sh:875-881
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] No fixture exercises GIT_STUB_SHOW_FAIL for per-path git show failures. A bug in the git show guard could ship while ls-tree-only failure remains green. Add a GIT_STUB_SHOW_FAIL=1 case expecting snapshot-extract-failed and marker retention.
- **Suggested revision**: Address the concern above.

### FINDING_10: risk-integration: skills/design/scripts/test-design-pause-resume.md:33-34
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness contract says deleted-subtree failures use missing-restored-artifact but implementation and tests now use snapshot-not-found for empty ls-tree enumeration. A maintainer reading the .md sibling could reintroduce the wrong ERROR expectation or miss a regression that restores missing-restored-artifact for empty enumeration. Update the coverage note to snapshot-not-found for empty enumeration/deleted subtree; document missing-restored-artifact only for post-extraction artifact gaps.
- **Suggested revision**: Address the concern above.

### FINDING_11: `5ccd6e3e8` — Fix design pause/resume recovery paths (core WI1–WI3)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `5ccd6e3e8` — Fix design pause/resume recovery paths (core WI1–WI3)
- **Suggested revision**: Address the concern above.

### FINDING_12: `55c4d6a9f` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `55c4d6a9f` — Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.

### FINDING_13: `8b4235514` — chore(larch-logs) flush (run log only; not reviewed as feature code)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `8b4235514` — chore(larch-logs) flush (run log only; not reviewed as feature code)
- **Suggested revision**: Address the concern above.

### FINDING_14: `21d62ab59` — Fixes #3448 / `python/ship.py` refactor (separate from pause/resume)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `21d62ab59` — Fixes #3448 / `python/ship.py` refactor (separate from pause/resume) Security review below focuses on the pause/resume surface (`design-log-publish.sh`, `design-pause-load.sh`, contracts, tests, `SECURITY.md`). The large `python/ship.py` delta is from #3448 and is out of scope for this feature unless a critical cross-cutting issue appears; nothing critical was found in a spot check of the round-1 resume-hardening hunks.
- **Suggested revision**: Address the concern above.

### FINDING_15: **WI1** expands `.completed/` staging with a fixed four-name allowlist tied to `design-driver.sh`; publish still rejects symlinks, ancestor escapes, and arbitrary basenames.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **WI1** expands `.completed/` staging with a fixed four-name allowlist tied to `design-driver.sh`; publish still rejects symlinks, ancestor escapes, and arbitrary basenames.
- **Suggested revision**: Address the concern above.

### FINDING_16: **WI2** replaces `git archive | tar` with guarded `git ls-tree -z` + per-path `git show`. Paths come from git object enumeration under a `RUN_ID`-scoped prefix (`RUN_ID` is slug-validated); `rel` gets `..`/absolute-segment rejection; `git show` materializes blobs as regular files (git symlink objects become file *content*, not on-disk symlinks), which is at least as safe as `tar -x` for symlink escape.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **WI2** replaces `git archive | tar` with guarded `git ls-tree -z` + per-path `git show`. Paths come from git object enumeration under a `RUN_ID`-scoped prefix (`RUN_ID` is slug-validated); `rel` gets `..`/absolute-segment rejection; `git show` materializes blobs as regular files (git symlink objects become file *content*, not on-disk symlinks), which is at least as safe as `tar -x` for symlink escape.
- **Suggested revision**: Address the concern above.

### FINDING_17: **WI3** correctly keeps the marker on retryable failures and only deletes after install + `.resume-loaded`; post-success delete failure is surfaced via `WARN=marker-delete-failed` / `MARKER_CLEARED=false` without falsely reporting load failure.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **WI3** correctly keeps the marker on retryable failures and only deletes after install + `.resume-loaded`; post-success delete failure is surfaced via `WARN=marker-delete-failed` / `MARKER_CLEARED=false` without falsely reporting load failure.
- **Suggested revision**: Address the concern above.

### FINDING_18: Marker binding (`ISSUE_NUMBER`, `REPO`, `RUN_ID`, manifest/pause-state cross-checks) is unchanged and still fail-closed before install.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Marker binding (`ISSUE_NUMBER`, `REPO`, `RUN_ID`, manifest/pause-state cross-checks) is unchanged and still fail-closed before install.
- **Suggested revision**: Address the concern above.

### FINDING_19: `design-route.sh` already accumulates multiple `WARN=` lines into an array, so `body-drift` + `marker-delete-failed` coexist safely.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `design-route.sh` already accumulates multiple `WARN=` lines into an array, so `body-drift` + `marker-delete-failed` coexist safely.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 1. **security** `scripts/design-pause-load.sh:308-311` — `cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/` merges into the destination without clearing pre-existing tmpdir files first. A partial failed `cp` (or stale files already in `$DESIGN_TMPDIR`) can leave artifacts that are not part of the restored snapshot on retry. **Suggested fix:** This predates the branch; if hardening is desired, stage into a clean tmpdir or delete destination contents before install (same pattern as publish-side containment).
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] security
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 2. **security** `SECURITY.md` (pause/resume paragraph, pre-change) — Main previously documented “rejects extracted symlinks,” but `design-pause-load.sh` on `main` never implemented an explicit post-extract symlink scan; it used `git archive | tar -x`. The new `git show` path is effectively safer for symlink objects. **Suggested fix:** Optional defense-in-depth: `find "$restore_tmp" -type l` (and reject) immediately before `cp -R`, matching `design-log-publish.sh` posture — not a regression, but would align docs and code.
- **Suggested revision**: Address the concern above.

### FINDING_22: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: 3. **risk-integration** `python/ship.py` (commit `21d62ab59`, #3448) — Large resume/ship refactor is unrelated to pause/resume; round-1 follow-up (`_MIN_GH_SKIPPED_MERGE_SIGNALS`, `post-merge-sentinel` gating for `manifest_done`) appears to *strengthen* merge-resume trust, not weaken it. Full audit of that surface belongs to the #3448 / Phase 7 ship review called out in `SECURITY.md`.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/design-pause-load.sh:308-313
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Success-path install spans cp, rm .pause-requested, and .resume-loaded write without a single atomic boundary. : > .resume-loaded fails after cp and .pause-requested removal: LOAD_OK=false, marker kept, tmpdir populated, no .resume-loaded; operator must retry without obvious partial-success signal. Defer .pause-requested removal until after .resume-loaded succeeds; add harness for resume-sentinel-write-failed asserting marker retention and absent sentinel.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: scripts/design-pause-load.sh:235-237
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Empty ls-tree enumeration exits early with ERROR=snapshot-not-found instead of falling through to required-artifact checks. After rm -rf of larch-logs/design/<RUN_ID>/ in the snapshot stub, load reports snapshot-not-found; the plan and fixture (a) require missing-restored-artifact so operators/automation cannot distinguish empty subtree from missing ref using the planned ERROR token. Remove the ! -s enum_tmp early exit (reserve snapshot-not-found for pre-enumeration ref/fetch failures) and restore missing-restored-artifact for empty enumeration; align deleted-subtree test and test-design-pause-resume.md.
- **Suggested revision**: Address the concern above.

### FINDING_25: architecture: python/ship.py
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] python/ship.py and python/test_ship.py were modified in round-1 review but are not in the plan file list for pause/resume WI1-WI3. The branch bundles unrelated ship-pr resume/OOS-gate logic with the pause/resume fix, breaking plan-to-diff traceability and review scope. Split ship.py changes to a separate PR or extend the plan and acceptance criteria to cover them explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/design-pause-load.sh:323-328
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] MARKER_CLEARED KV was added without updating design-pause-load.md or SECURITY.md output contracts. Downstream parsers/docs only know about WARN=marker-delete-failed per plan; MARKER_CLEARED is test-only surface with no contract doc. Document MARKER_CLEARED in design-pause-load.md and SECURITY.md, or remove it and keep WARN-only signaling per plan.
- **Suggested revision**: Address the concern above.

### FINDING_27: architecture: scripts/design-pause-load.sh:311
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Load clears restored .pause-requested after install but plan and design-pause-load.md omit this. Future readers may reintroduce immediate re-pause loops or omit harness coverage for restored pause-requested state. Add a contract bullet that successful load removes $DESIGN_TMPDIR/.pause-requested (separate from issue-body marker deletion).
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: skills/design/scripts/test-design-pause-resume.md:33-34
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Test harness doc says deleted-subtree missing-restored-artifact but test expects snapshot-not-found. Readers following the .md contract will misdiagnose failures or file wrong bug reports. Update the .md to snapshot-not-found or revert code/tests to missing-restored-artifact per plan.
- **Suggested revision**: Address the concern above.

### FINDING_29: **correctness** `scripts/design-pause-load.sh:235-236` — After a successful `git ls-tree` (exit 0, ref already resolved at lines 206–228), an empty `enum_tmp` short-circuits to `ERROR=snapshot-not-found` instead of continuing to the required-artifact checks that emit `ERROR=missing-restored-artifact` (lines 262–266). That reuses the same token as genuine ref-resolution failures (`fetch` / `show-ref` at lines 209–226), so operators and automation cannot tell “git ref missing” from “ref OK but `larch-logs/design/<RUN_ID>/` has no blobs” (deleted subtree, wrong `RUN_ID`, never-published snapshot). The plan’s edge cases and `design-pause-load.md` describe empty-subtree / missing-content as `missing-restored-artifact`; round 1 added this early exit and the harness at `skills/design/scripts/test-design-pause-resume.sh:870` now expects `snapshot-not-found`, but `skills/design/scripts/test-design-pause-resume.md:33-34` still documents deleted-subtree coverage as `missing-restored-artifact`. **Suggested fix:** Drop the `if [[ ! -s "$enum_tmp" ]]` block and let an empty enumeration fall through to the existing `manifest.json` / `run-params.json` / `pause-state.txt` checks (emitting `missing-restored-artifact`), reserving `snapshot-not-found` for fetch/show-ref failures only; align the test and `.md` sibling with that contract.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - **correctness** `scripts/design-pause-load.sh:235-236` — After a successful `git ls-tree` (exit 0, ref already resolved at lines 206–228), an empty `enum_tmp` short-circuits to `ERROR=snapshot-not-found` instead of continuing to the required-artifact checks that emit `ERROR=missing-restored-artifact` (lines 262–266). That reuses the same token as genuine ref-resolution failures (`fetch` / `show-ref` at lines 209–226), so operators and automation cannot tell “git ref missing” from “ref OK but `larch-logs/design/<RUN_ID>/` has no blobs” (deleted subtree, wrong `RUN_ID`, never-published snapshot). The plan’s edge cases and `design-pause-load.md` describe empty-subtree / missing-content as `missing-restored-artifact`; round 1 added this early exit and the harness at `skills/design/scripts/test-design-pause-resume.sh:870` now expects `snapshot-not-found`, but `skills/design/scripts/test-design-pause-resume.md:33-34` still documents deleted-subtree coverage as `missing-restored-artifact`. **Suggested fix:** Drop the `if [[ ! -s "$enum_tmp" ]]` block and let an empty enumeration fall through to the existing `manifest.json` / `run-params.json` / `pause-state.txt` checks (emitting `missing-restored-artifact`), reserving `snapshot-not-found` for fetch/show-ref failures only; align the test and `.md` sibling with that contract.
- **Suggested revision**: Address the concern above.

### FINDING_30: **correctness** `scripts/design-pause-load.sh:308-311` — On the success path, `cp -R` can fully install the snapshot and then `rm -f "$DESIGN_TMPDIR/.pause-requested"` can fail (permissions, immutable flag, unexpected directory), triggering `emit_load_fail "restore-install-failed"` while the issue-body pause marker is still present. That is structured KV output (not a bare `set -e` exit), but the restored tmpdir already contains a copied `.pause-requested` from the snapshot (see harness setup at `skills/design/scripts/test-design-pause-resume.sh:206-212`), so the next `/design` Bash prelude will immediately re-exec `design-pause-save.sh` even though load reported failure and the marker was intentionally kept for retry. **Suggested fix:** Treat failure to clear the live `.pause-requested` sentinel separately from install failure—e.g. attempt `rm -f` before emitting success, or on `rm` failure emit `LOAD_OK=true` with a distinct `WARN=pause-sentinel-clear-failed` (mirroring the marker-delete pattern) after verifying required artifacts, so a resumable load does not leave a live pause-request trigger in `$DESIGN_TMPDIR`.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - **correctness** `scripts/design-pause-load.sh:308-311` — On the success path, `cp -R` can fully install the snapshot and then `rm -f "$DESIGN_TMPDIR/.pause-requested"` can fail (permissions, immutable flag, unexpected directory), triggering `emit_load_fail "restore-install-failed"` while the issue-body pause marker is still present. That is structured KV output (not a bare `set -e` exit), but the restored tmpdir already contains a copied `.pause-requested` from the snapshot (see harness setup at `skills/design/scripts/test-design-pause-resume.sh:206-212`), so the next `/design` Bash prelude will immediately re-exec `design-pause-save.sh` even though load reported failure and the marker was intentionally kept for retry. **Suggested fix:** Treat failure to clear the live `.pause-requested` sentinel separately from install failure—e.g. attempt `rm -f` before emitting success, or on `rm` failure emit `LOAD_OK=true` with a distinct `WARN=pause-sentinel-clear-failed` (mirroring the marker-delete pattern) after verifying required artifacts, so a resumable load does not leave a live pause-request trigger in `$DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.

### FINDING_31: [OUT_OF_SCOPE] The new `ls-tree` capture (`if ! git … ls-tree … >"$enum_tmp"`) and per-path `if ! git show` guards in `scripts/design-pause-load.sh:232-250` correctly follow the `scripts/scrub-log-secrets.sh:176-185` pattern and avoid the `set -euo pipefail` pitfall where a failed `ls-tree` inside process substitution would masquerade as `missing-restored-artifact`.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - The new `ls-tree` capture (`if ! git … ls-tree … >"$enum_tmp"`) and per-path `if ! git show` guards in `scripts/design-pause-load.sh:232-250` correctly follow the `scripts/scrub-log-secrets.sh:176-185` pattern and avoid the `set -euo pipefail` pitfall where a failed `ls-tree` inside process substitution would masquerade as `missing-restored-artifact`.
- **Suggested revision**: Address the concern above.

### FINDING_32: [OUT_OF_SCOPE] `design-route.sh` appends every `WARN=` line into `WARN_LINES[]` (`skills/design/scripts/design-route.sh:310`), so combined `WARN=body-drift` + `WARN=marker-delete-failed` output is not dropped by the primary resume consumer.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - `design-route.sh` appends every `WARN=` line into `WARN_LINES[]` (`skills/design/scripts/design-route.sh:310`), so combined `WARN=body-drift` + `WARN=marker-delete-failed` output is not dropped by the primary resume consumer.
- **Suggested revision**: Address the concern above.

### FINDING_33: [OUT_OF_SCOPE] `scripts/design-log-publish.sh:589-598` driver-phase allowlist (WI1) is narrow and consistent with `skills/design/scripts/design-driver.sh` flat `.completed/$step_name` writes; negative coverage for `.completed/bogus` exists in `scripts/test-design-log-publish.sh`.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - `scripts/design-log-publish.sh:589-598` driver-phase allowlist (WI1) is narrow and consistent with `skills/design/scripts/design-driver.sh` flat `.completed/$step_name` writes; negative coverage for `.completed/bogus` exists in `scripts/test-design-log-publish.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_34: [OUT_OF_SCOPE] Pre-existing: `scripts/design-log-publish.sh:615` still stages `.completed` via `done < <(find …)` without an explicit `find` failure guard; not introduced by this branch.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - Pre-existing: `scripts/design-log-publish.sh:615` still stages `.completed` via `done < <(find …)` without an explicit `find` failure guard; not introduced by this branch.
- **Suggested revision**: Address the concern above.

### FINDING_35: **risk-integration** `scripts/design-pause-load.sh:235-237` — After a ref resolves successfully, an empty `ls-tree` enumeration now emits `ERROR=snapshot-not-found`, collapsing three previously distinct failure shapes into one token: fetch/show-ref failure, wrong/missing ref, and “ref OK but snapshot subtree empty/corrupt.” Before this branch, an empty `git archive | tar` install fell through to `missing-restored-artifact`, so operators and harnesses could tell “remote resolved, content missing” apart from “could not find snapshot ref.” The regression harness at `skills/design/scripts/test-design-pause-resume.sh:862-871` was updated to expect `snapshot-not-found`, but the plan acceptance still called for `missing-restored-artifact` on the deleted-subtree fixture. **Suggested fix:** Reserve `snapshot-not-found` for fetch/show-ref failures only; when `ls-tree` succeeds but the buffer is empty (or required root artifacts are absent after extraction), emit `missing-restored-artifact` so retryable content gaps stay distinguishable from ref-resolution failures.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:235-237` — After a ref resolves successfully, an empty `ls-tree` enumeration now emits `ERROR=snapshot-not-found`, collapsing three previously distinct failure shapes into one token: fetch/show-ref failure, wrong/missing ref, and “ref OK but snapshot subtree empty/corrupt.” Before this branch, an empty `git archive | tar` install fell through to `missing-restored-artifact`, so operators and harnesses could tell “remote resolved, content missing” apart from “could not find snapshot ref.” The regression harness at `skills/design/scripts/test-design-pause-resume.sh:862-871` was updated to expect `snapshot-not-found`, but the plan acceptance still called for `missing-restored-artifact` on the deleted-subtree fixture. **Suggested fix:** Reserve `snapshot-not-found` for fetch/show-ref failures only; when `ls-tree` succeeds but the buffer is empty (or required root artifacts are absent after extraction), emit `missing-restored-artifact` so retryable content gaps stay distinguishable from ref-resolution failures.
- **Suggested revision**: Address the concern above.

### FINDING_36: **risk-integration** `scripts/design-pause-load.sh:203-248` — Snapshot restore still binds `REPO_TOP` from the caller’s CWD (`git rev-parse --show-toplevel`) while `--repo` scopes only `gh` issue reads and marker delete; all `ls-tree`/`show`/`fetch` operations use that CWD-derived worktree. The new export-ignore reproduction in `skills/design/scripts/test-design-pause-resume.sh:237-240` works only because it `cd`s into the init repo first—without that, a pause marker bound to `owner/repo` can validate while restore reads `larch-logs/design/<RUN_ID>/` from a different clone (plugin cache vs consumer repo), yielding `snapshot-not-found` or silently wrong bytes. **Suggested fix:** Fail closed when `CURRENT_REPO` is set and the CWD top-level’s `origin` remote does not match it, or thread an explicit git worktree root derived from `--repo` into every `git -C` call (document the CWD requirement prominently in `design-pause-load.md` if binding cannot be automated).
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:203-248` — Snapshot restore still binds `REPO_TOP` from the caller’s CWD (`git rev-parse --show-toplevel`) while `--repo` scopes only `gh` issue reads and marker delete; all `ls-tree`/`show`/`fetch` operations use that CWD-derived worktree. The new export-ignore reproduction in `skills/design/scripts/test-design-pause-resume.sh:237-240` works only because it `cd`s into the init repo first—without that, a pause marker bound to `owner/repo` can validate while restore reads `larch-logs/design/<RUN_ID>/` from a different clone (plugin cache vs consumer repo), yielding `snapshot-not-found` or silently wrong bytes. **Suggested fix:** Fail closed when `CURRENT_REPO` is set and the CWD top-level’s `origin` remote does not match it, or thread an explicit git worktree root derived from `--repo` into every `git -C` call (document the CWD requirement prominently in `design-pause-load.md` if binding cannot be automated).
- **Suggested revision**: Address the concern above.

### FINDING_37: **risk-integration** `scripts/design-pause-load.sh:214-248` — Remote recovery still sets `snapshot_ref=FETCH_HEAD` immediately after `git fetch origin "$LOG_RECOVERY_BRANCH"`, then performs separate `ls-tree` and per-file `show` calls. Any concurrent `git fetch` in the same worktree can repoint `FETCH_HEAD` between those steps; the old single `git archive` pipeline had a smaller exposure window, and the new multi-invocation path amplifies it. **Suggested fix:** After a successful fetch, pin an immutable ref (`origin/$LOG_RECOVERY_BRANCH` or a captured SHA via `git rev-parse FETCH_HEAD`) and use only that pinned value for both enumeration and extraction.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:214-248` — Remote recovery still sets `snapshot_ref=FETCH_HEAD` immediately after `git fetch origin "$LOG_RECOVERY_BRANCH"`, then performs separate `ls-tree` and per-file `show` calls. Any concurrent `git fetch` in the same worktree can repoint `FETCH_HEAD` between those steps; the old single `git archive` pipeline had a smaller exposure window, and the new multi-invocation path amplifies it. **Suggested fix:** After a successful fetch, pin an immutable ref (`origin/$LOG_RECOVERY_BRANCH` or a captured SHA via `git rev-parse FETCH_HEAD`) and use only that pinned value for both enumeration and extraction.
- **Suggested revision**: Address the concern above.

### FINDING_38: **risk-integration** `scripts/design-pause-load.sh:308-311` — Restore installs with `cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/ and treats a subsequent `.pause-requested` removal failure as `restore-install-failed` while keeping the pause marker. A failed `cp` or `rm` can therefore leave a partially populated `$DESIGN_TMPDIR` with the marker still present, so a retry overlays another restore onto inconsistent state instead of a clean staging boundary. **Suggested fix:** On `restore-install-failed`, remove or quarantine the partial install under `$DESIGN_TMPDIR` before exiting, or swap/replace the tmpdir atomically only after `.resume-loaded` is written so retries always start from a known-empty target.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:308-311` — Restore installs with `cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/ and treats a subsequent `.pause-requested` removal failure as `restore-install-failed` while keeping the pause marker. A failed `cp` or `rm` can therefore leave a partially populated `$DESIGN_TMPDIR` with the marker still present, so a retry overlays another restore onto inconsistent state instead of a clean staging boundary. **Suggested fix:** On `restore-install-failed`, remove or quarantine the partial install under `$DESIGN_TMPDIR` before exiting, or swap/replace the tmpdir atomically only after `.resume-loaded` is written so retries always start from a known-empty target.
- **Suggested revision**: Address the concern above.

### FINDING_39: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:322-326` — When both body drift and marker-delete fail, two `WARN=` lines are emitted; `design-route.sh` accumulates all `WARN` values, but any downstream consumer that keeps only the last `WARN` will drop `body-drift`. Consider comma-joining or a second keyed warning if that surfaces in practice.
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] The branch also carries unrelated `python/` ship/CI-monitor changes from commit `21d62ab59` (#3448); they are outside the pause/resume snapshot-restore surface reviewed here.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - The branch also carries unrelated `python/` ship/CI-monitor changes from commit `21d62ab59` (#3448); they are outside the pause/resume snapshot-restore surface reviewed here.
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] WI1 (`design-log-publish.sh` driver phase-sentinel allowlist) and WI2 (`ls-tree`+`show` bypassing `export-ignore`) match the stated plan; path-prefix guards at `scripts/design-pause-load.sh:239-245` and the real-git export-ignore fixture are appropriate mitigations for the restore primitive change.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - WI1 (`design-log-publish.sh` driver phase-sentinel allowlist) and WI2 (`ls-tree`+`show` bypassing `export-ignore`) match the stated plan; path-prefix guards at `scripts/design-pause-load.sh:239-245` and the real-git export-ignore fixture are appropriate mitigations for the restore primitive change.
- **Suggested revision**: Address the concern above.

### FINDING_42: **architecture** `skills/design/scripts/design-route.sh:292-375` — WI3 keeps the pause marker on loader failures so operators can retry, but `design-route.sh` still treats `LOAD_OK=false` as fallthrough into title/re-entry/plan routing (`design-route.md` line 31) instead of emitting `ROUTE=cancel-pause-load`. On the normal paused issue (`[DESIGNING]` from `design-init-runparams.sh`), a retryable failure such as `ERROR=snapshot-not-found` or `ERROR=missing-restored-artifact` therefore ends in `ROUTE=cancel-title-filter` with the lifecycle rename banner, while the structured loader `ERROR=` is secondary. That recreates the #3506 failure mode the branch set out to fix: the marker survives, but `/design` aborts with misleading “rename the title” guidance until the snapshot is fixed. **Suggested fix:** When `pause_marker_present` and `LOAD_OK=false` (or loader exit ≠ 0), set `ROUTE=cancel-pause-load`, forward the loader `ERROR=` into `ERROR_LINES`, and exit before title-eligibility; reserve fallthrough only for `no-pause-marker` paths.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - **architecture** `skills/design/scripts/design-route.sh:292-375` — WI3 keeps the pause marker on loader failures so operators can retry, but `design-route.sh` still treats `LOAD_OK=false` as fallthrough into title/re-entry/plan routing (`design-route.md` line 31) instead of emitting `ROUTE=cancel-pause-load`. On the normal paused issue (`[DESIGNING]` from `design-init-runparams.sh`), a retryable failure such as `ERROR=snapshot-not-found` or `ERROR=missing-restored-artifact` therefore ends in `ROUTE=cancel-title-filter` with the lifecycle rename banner, while the structured loader `ERROR=` is secondary. That recreates the #3506 failure mode the branch set out to fix: the marker survives, but `/design` aborts with misleading “rename the title” guidance until the snapshot is fixed. **Suggested fix:** When `pause_marker_present` and `LOAD_OK=false` (or loader exit ≠ 0), set `ROUTE=cancel-pause-load`, forward the loader `ERROR=` into `ERROR_LINES`, and exit before title-eligibility; reserve fallthrough only for `no-pause-marker` paths.
- **Suggested revision**: Address the concern above.

### FINDING_43: **architecture** `scripts/design-pause-load.sh:235-237` vs `scripts/design-pause-load.sh:262-267` — Empty `ls-tree` enumeration (deleted `larch-logs/design/<RUN_ID>/` subtree) now short-circuits to `ERROR=snapshot-not-found`, while a non-empty enumeration that lacks `manifest.json` / `run-params.json` / `pause-state.txt` still yields `ERROR=missing-restored-artifact`. The plan and edge-case prose treated an empty subtree as `missing-restored-artifact`; the harness at `skills/design/scripts/test-design-pause-resume.sh:862-870` codifies `snapshot-not-found` instead. Marker retention is the same, but operators and automation lose a distinct “snapshot published but incomplete/corrupt” signal. **Suggested fix:** Drop the `! -s "$enum_tmp"` early exit and let the existing required-artifact loop emit `missing-restored-artifact` for empty enumeration; or document `snapshot-not-found` as the canonical empty-subtree token everywhere (contract + tests + SECURITY.md).
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - **architecture** `scripts/design-pause-load.sh:235-237` vs `scripts/design-pause-load.sh:262-267` — Empty `ls-tree` enumeration (deleted `larch-logs/design/<RUN_ID>/` subtree) now short-circuits to `ERROR=snapshot-not-found`, while a non-empty enumeration that lacks `manifest.json` / `run-params.json` / `pause-state.txt` still yields `ERROR=missing-restored-artifact`. The plan and edge-case prose treated an empty subtree as `missing-restored-artifact`; the harness at `skills/design/scripts/test-design-pause-resume.sh:862-870` codifies `snapshot-not-found` instead. Marker retention is the same, but operators and automation lose a distinct “snapshot published but incomplete/corrupt” signal. **Suggested fix:** Drop the `! -s "$enum_tmp"` early exit and let the existing required-artifact loop emit `missing-restored-artifact` for empty enumeration; or document `snapshot-not-found` as the canonical empty-subtree token everywhere (contract + tests + SECURITY.md).
- **Suggested revision**: Address the concern above.

### FINDING_44: **architecture** `scripts/design-pause-load.sh:323-328` and `scripts/design-pause-load.md:60-64` — Round 1 added `MARKER_CLEARED=true|false` on the success path, but the contract doc still lists only `WARN=body-drift` / `WARN=marker-delete-failed`. `design-route.sh:300-312` also does not parse or relay `MARKER_CLEARED`, so integrated `/design` runs only see `WARN=marker-delete-failed` while direct loader callers can see both. That splits the lifecycle contract across call paths. **Suggested fix:** Either document `MARKER_CLEARED` in `design-pause-load.md` (and parse/relay it in `design-route.sh`’s pause-load KV loop), or drop `MARKER_CLEARED` and rely solely on `WARN=marker-delete-failed` for a single cross-boundary signal.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - **architecture** `scripts/design-pause-load.sh:323-328` and `scripts/design-pause-load.md:60-64` — Round 1 added `MARKER_CLEARED=true|false` on the success path, but the contract doc still lists only `WARN=body-drift` / `WARN=marker-delete-failed`. `design-route.sh:300-312` also does not parse or relay `MARKER_CLEARED`, so integrated `/design` runs only see `WARN=marker-delete-failed` while direct loader callers can see both. That splits the lifecycle contract across call paths. **Suggested fix:** Either document `MARKER_CLEARED` in `design-pause-load.md` (and parse/relay it in `design-route.sh`’s pause-load KV loop), or drop `MARKER_CLEARED` and rely solely on `WARN=marker-delete-failed` for a single cross-boundary signal.
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] The precomputed diff at `round-2/diff.txt` also includes large `python/ship.py` / `python/test_ship.py` changes and an implement run-log commit (`8b4235514`) that are unrelated to pause/resume; review those separately if the PR scope is meant to be pause-only.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - The precomputed diff at `round-2/diff.txt` also includes large `python/ship.py` / `python/test_ship.py` changes and an implement run-log commit (`8b4235514`) that are unrelated to pause/resume; review those separately if the PR scope is meant to be pause-only.
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] `design-pause-load.sh:203-204` binds `REPO_TOP` from the caller’s cwd (`git rev-parse --show-toplevel`) while `gh` uses `--repo`; the new real-git export-ignore test documents this cwd requirement. Cross-worktree resume without `cd` into the consumer clone remains a pre-existing footgun, not introduced here.
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - `design-pause-load.sh:203-204` binds `REPO_TOP` from the caller’s cwd (`git rev-parse --show-toplevel`) while `gh` uses `--repo`; the new real-git export-ignore test documents this cwd requirement. Cross-worktree resume without `cd` into the consumer clone remains a pre-existing footgun, not introduced here.
- **Suggested revision**: Address the concern above.

### FINDING_47: [OUT_OF_SCOPE] WI1’s four-name allowlist in `scripts/design-log-publish.sh:589-598` matches `skills/design/scripts/design-driver.sh:61-63,112` today; future driver actions still require dual-side updates (plan failure mode 1).
- **Reviewer**: dyn-resume-state-output.txt
- **Concern**: - WI1’s four-name allowlist in `scripts/design-log-publish.sh:589-598` matches `skills/design/scripts/design-driver.sh:61-63,112` today; future driver actions still require dual-side updates (plan failure mode 1).
- **Suggested revision**: Address the concern above.

