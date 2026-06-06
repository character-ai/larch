### [rejected] FINDING_11

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_11: `5ccd6e3e8` — Fix design pause/resume recovery paths (core WI1–WI3)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `5ccd6e3e8` — Fix design pause/resume recovery paths (core WI1–WI3)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_12: `55c4d6a9f` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `55c4d6a9f` — Address code review feedback (round 1)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_13: `8b4235514` — chore(larch-logs) flush (run log only; not reviewed as feature code)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `8b4235514` — chore(larch-logs) flush (run log only; not reviewed as feature code)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: `21d62ab59` — Fixes #3448 / `python/ship.py` refactor (separate from pause/resume)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `21d62ab59` — Fixes #3448 / `python/ship.py` refactor (separate from pause/resume) Security review below focuses on the pause/resume surface (`design-log-publish.sh`, `design-pause-load.sh`, contracts, tests, `SECURITY.md`). The large `python/ship.py` delta is from #3448 and is out of scope for this feature unless a critical cross-cutting issue appears; nothing critical was found in a spot check of the round-1 resume-hardening hunks.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **WI1** expands `.completed/` staging with a fixed four-name allowlist tied to `design-driver.sh`; publish still rejects symlinks, ancestor escapes, and arbitrary basenames.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **WI1** expands `.completed/` staging with a fixed four-name allowlist tied to `design-driver.sh`; publish still rejects symlinks, ancestor escapes, and arbitrary basenames.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **WI2** replaces `git archive | tar` with guarded `git ls-tree -z` + per-path `git show`. Paths come from git object enumeration under a `RUN_ID`-scoped prefix (`RUN_ID` is slug-validated); `rel` gets `..`/absolute-segment rejection; `git show` materializes blobs as regular files (git symlink objects become file *content*, not on-disk symlinks), which is at least as safe as `tar -x` for symlink escape.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **WI2** replaces `git archive | tar` with guarded `git ls-tree -z` + per-path `git show`. Paths come from git object enumeration under a `RUN_ID`-scoped prefix (`RUN_ID` is slug-validated); `rel` gets `..`/absolute-segment rejection; `git show` materializes blobs as regular files (git symlink objects become file *content*, not on-disk symlinks), which is at least as safe as `tar -x` for symlink escape.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **WI3** correctly keeps the marker on retryable failures and only deletes after install + `.resume-loaded`; post-success delete failure is surfaced via `WARN=marker-delete-failed` / `MARKER_CLEARED=false` without falsely reporting load failure.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **WI3** correctly keeps the marker on retryable failures and only deletes after install + `.resume-loaded`; post-success delete failure is surfaced via `WARN=marker-delete-failed` / `MARKER_CLEARED=false` without falsely reporting load failure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: Marker binding (`ISSUE_NUMBER`, `REPO`, `RUN_ID`, manifest/pause-state cross-checks) is unchanged and still fail-closed before install.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Marker binding (`ISSUE_NUMBER`, `REPO`, `RUN_ID`, manifest/pause-state cross-checks) is unchanged and still fail-closed before install.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: `design-route.sh` already accumulates multiple `WARN=` lines into an array, so `body-drift` + `marker-delete-failed` coexist safely.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `design-route.sh` already accumulates multiple `WARN=` lines into an array, so `body-drift` + `marker-delete-failed` coexist safely.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: risk-integration: scripts/design-pause-load.sh:308-313
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Success-path install spans cp, rm .pause-requested, and .resume-loaded write without a single atomic boundary. : > .resume-loaded fails after cp and .pause-requested removal: LOAD_OK=false, marker kept, tmpdir populated, no .resume-loaded; operator must retry without obvious partial-success signal. Defer .pause-requested removal until after .resume-loaded succeeds; add harness for resume-sentinel-write-failed asserting marker retention and absent sentinel.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/design-log-publish.sh:589-598
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Driver phase sentinel allowlist is duplicated from design-driver.sh with comment-only coupling. A new design-driver.sh ACTION added without updating the publisher allowlist re-breaks pause publish with unexpected file under .completed. Share one allowlist source or add a test that diffs driver actions against publisher accepted basenames.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: **correctness** `scripts/design-pause-load.sh:308-311` — On the success path, `cp -R` can fully install the snapshot and then `rm -f "$DESIGN_TMPDIR/.pause-requested"` can fail (permissions, immutable flag, unexpected directory), triggering `emit_load_fail "restore-install-failed"` while the issue-body pause marker is still present. That is structured KV output (not a bare `set -e` exit), but the restored tmpdir already contains a copied `.pause-requested` from the snapshot (see harness setup at `skills/design/scripts/test-design-pause-resume.sh:206-212`), so the next `/design` Bash prelude will immediately re-exec `design-pause-save.sh` even though load reported failure and the marker was intentionally kept for retry. **Suggested fix:** Treat failure to clear the live `.pause-requested` sentinel separately from install failure—e.g. attempt `rm -f` before emitting success, or on `rm` failure emit `LOAD_OK=true` with a distinct `WARN=pause-sentinel-clear-failed` (mirroring the marker-delete pattern) after verifying required artifacts, so a resumable load does not leave a live pause-request trigger in `$DESIGN_TMPDIR`.
- **Reviewer**: dyn-shell-failure-output.txt
- **Concern**: - **correctness** `scripts/design-pause-load.sh:308-311` — On the success path, `cp -R` can fully install the snapshot and then `rm -f "$DESIGN_TMPDIR/.pause-requested"` can fail (permissions, immutable flag, unexpected directory), triggering `emit_load_fail "restore-install-failed"` while the issue-body pause marker is still present. That is structured KV output (not a bare `set -e` exit), but the restored tmpdir already contains a copied `.pause-requested` from the snapshot (see harness setup at `skills/design/scripts/test-design-pause-resume.sh:206-212`), so the next `/design` Bash prelude will immediately re-exec `design-pause-save.sh` even though load reported failure and the marker was intentionally kept for retry. **Suggested fix:** Treat failure to clear the live `.pause-requested` sentinel separately from install failure—e.g. attempt `rm -f` before emitting success, or on `rm` failure emit `LOAD_OK=true` with a distinct `WARN=pause-sentinel-clear-failed` (mirroring the marker-delete pattern) after verifying required artifacts, so a resumable load does not leave a live pause-request trigger in `$DESIGN_TMPDIR`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: **risk-integration** `scripts/design-pause-load.sh:203-248` — Snapshot restore still binds `REPO_TOP` from the caller’s CWD (`git rev-parse --show-toplevel`) while `--repo` scopes only `gh` issue reads and marker delete; all `ls-tree`/`show`/`fetch` operations use that CWD-derived worktree. The new export-ignore reproduction in `skills/design/scripts/test-design-pause-resume.sh:237-240` works only because it `cd`s into the init repo first—without that, a pause marker bound to `owner/repo` can validate while restore reads `larch-logs/design/<RUN_ID>/` from a different clone (plugin cache vs consumer repo), yielding `snapshot-not-found` or silently wrong bytes. **Suggested fix:** Fail closed when `CURRENT_REPO` is set and the CWD top-level’s `origin` remote does not match it, or thread an explicit git worktree root derived from `--repo` into every `git -C` call (document the CWD requirement prominently in `design-pause-load.md` if binding cannot be automated).
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:203-248` — Snapshot restore still binds `REPO_TOP` from the caller’s CWD (`git rev-parse --show-toplevel`) while `--repo` scopes only `gh` issue reads and marker delete; all `ls-tree`/`show`/`fetch` operations use that CWD-derived worktree. The new export-ignore reproduction in `skills/design/scripts/test-design-pause-resume.sh:237-240` works only because it `cd`s into the init repo first—without that, a pause marker bound to `owner/repo` can validate while restore reads `larch-logs/design/<RUN_ID>/` from a different clone (plugin cache vs consumer repo), yielding `snapshot-not-found` or silently wrong bytes. **Suggested fix:** Fail closed when `CURRENT_REPO` is set and the CWD top-level’s `origin` remote does not match it, or thread an explicit git worktree root derived from `--repo` into every `git -C` call (document the CWD requirement prominently in `design-pause-load.md` if binding cannot be automated).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_37: **risk-integration** `scripts/design-pause-load.sh:214-248` — Remote recovery still sets `snapshot_ref=FETCH_HEAD` immediately after `git fetch origin "$LOG_RECOVERY_BRANCH"`, then performs separate `ls-tree` and per-file `show` calls. Any concurrent `git fetch` in the same worktree can repoint `FETCH_HEAD` between those steps; the old single `git archive` pipeline had a smaller exposure window, and the new multi-invocation path amplifies it. **Suggested fix:** After a successful fetch, pin an immutable ref (`origin/$LOG_RECOVERY_BRANCH` or a captured SHA via `git rev-parse FETCH_HEAD`) and use only that pinned value for both enumeration and extraction.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:214-248` — Remote recovery still sets `snapshot_ref=FETCH_HEAD` immediately after `git fetch origin "$LOG_RECOVERY_BRANCH"`, then performs separate `ls-tree` and per-file `show` calls. Any concurrent `git fetch` in the same worktree can repoint `FETCH_HEAD` between those steps; the old single `git archive` pipeline had a smaller exposure window, and the new multi-invocation path amplifies it. **Suggested fix:** After a successful fetch, pin an immutable ref (`origin/$LOG_RECOVERY_BRANCH` or a captured SHA via `git rev-parse FETCH_HEAD`) and use only that pinned value for both enumeration and extraction.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_38: **risk-integration** `scripts/design-pause-load.sh:308-311` — Restore installs with `cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/ and treats a subsequent `.pause-requested` removal failure as `restore-install-failed` while keeping the pause marker. A failed `cp` or `rm` can therefore leave a partially populated `$DESIGN_TMPDIR` with the marker still present, so a retry overlays another restore onto inconsistent state instead of a clean staging boundary. **Suggested fix:** On `restore-install-failed`, remove or quarantine the partial install under `$DESIGN_TMPDIR` before exiting, or swap/replace the tmpdir atomically only after `.resume-loaded` is written so retries always start from a known-empty target.
- **Reviewer**: dyn-git-snapshot-output.txt
- **Concern**: - **risk-integration** `scripts/design-pause-load.sh:308-311` — Restore installs with `cp -R "$restore_tmp"/. "$DESIGN_TMPDIR"/ and treats a subsequent `.pause-requested` removal failure as `restore-install-failed` while keeping the pause marker. A failed `cp` or `rm` can therefore leave a partially populated `$DESIGN_TMPDIR` with the marker still present, so a retry overlays another restore onto inconsistent state instead of a clean staging boundary. **Suggested fix:** On `restore-install-failed`, remove or quarantine the partial install under `$DESIGN_TMPDIR` before exiting, or swap/replace the tmpdir atomically only after `.resume-loaded` is written so retries always start from a known-empty target.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: code-quality: skills/design/scripts/test-design-pause-resume.sh:104-107
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] ls-tree stub uses last argv token as path instead of parsing git ls-tree arguments. Future loader argv reordering makes the stub return empty output while production works, causing false-green or false-red harness results. Parse the tree path argument explicitly (after -- or by larch-logs/design/ prefix).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

