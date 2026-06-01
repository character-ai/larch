### FINDING_1:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:373-384,1321-1326,1531-1533; skills/review-and-fix/scripts/review-implement-step5-loop.sh:401-413
- **Concern**: Proposed 0444 hardening leaves deterministic relocated snapshot paths non-reusable because old read-only files are not removed before later redirects. Scenario: If an in-$PWD run repeats the same round before OS TMPDIR cleanup, existing 0444 pre-coder-head/tracked/diff files cannot be truncated; the pre-head write can fall into the rm branch without retry or diff writes can fail, disabling or corrupting carryover classification
- **Proposed resolution**: Before each snapshot/head redirect, unlink the specific existing artifact or write temp+mv, then chmod after successful writes; keep directories writable as planned

### FINDING_2:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1321-1326; skills/review-and-fix/scripts/review-implement-step5-loop.sh:401-403
- **Concern**: Deterministic relocated snapshot paths are hardened to 0444 but not cleared before the next write. Scenario: The relocation branch stores snapshots under ${TMPDIR}/larch-pre-coder-snapshots/<hash>/round-N and cleanup-tmpdir.sh does not reap them. A later same-repo same-round run can hit leftover 0444 files: pre-coder-head.txt redirect fails and the planned failure branch removes it without retrying, so carryover snapshots silently disappear; stale tracked-path or patch files would also block redirects under set -e if only the head write is retried.
- **Proposed resolution**: Before the first snapshot redirect at both normal and MAV write sites, remove stale snapshot contents for that snap_dir and recreate it, or remove and retry every hardened artifact write. Add a stale-0444 same-path regression so the relocation branch still writes fresh snapshots.

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:14
- **Concern**: Plan says pre-coder-path-diffs/*.patch already covers *.cached.patch. Scenario: Bash *.patch does not match names ending in .cached.patch; harden_pre_coder_snapshot_perms would skip indexed carryover snapshots, leaving them writable if a grant ever reached the dir
- **Proposed resolution**: In harden_pre_coder_snapshot_perms, chmod both pre-coder-path-diffs/*.patch and pre-coder-path-diffs/*.cached.patch (or one loop over all files in that dir); extend the 0444 harness fixture to assert mode 444 on a .cached.patch file

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1321-1326; skills/review-and-fix/scripts/review-implement-step5-loop.sh:401-403
- **Concern**: Read-only relocated snapshots are reused without clearing stale files. Scenario: The plan relocates the $PWD branch under ${TMPDIR}/larch-pre-coder-snapshots/<hash>/<round> and documents that cleanup-tmpdir.sh will not reap it, then chmods files 0444. A later run with the same repo parent and round basename hits existing read-only pre-coder-head.txt/pre-coder-tracked-paths.txt/patch files; redirection fails or stale diffs survive, so carryover classification degrades and MAV may accidentally see old tracked snapshots despite the head-only contract.
- **Proposed resolution**: Before any write to snap_dir in both main and MAV paths, remove or reset the per-round snapshot contents, for example rm -rf "$snap_dir" then mkdir -p "$snap_dir", or targeted rm/chmod before redirects, so each round starts from an empty writable snapshot dir before chmod 0444 is applied.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1321-1326
- **Concern**: Plan hardens snapshot files to 0444 but does not clear stale snapshot artifacts before the next write. Scenario: After an interrupted or repeated run reuses the same round snapshot path, redirects to pre-existing 0444 files fail; the current pre-coder-head branch removes the file after the failed redirect but does not retry, so the round runs without carryover snapshots
- **Proposed resolution**: Before writing a round snapshot, rm -f the known snapshot files/globs in snap_dir, then write and harden them; apply the same stale-file cleanup to the MAV pre-coder-head write path if it can reuse the same snap_dir

### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:38 (plan)
- **Concern**: In-repo relocation test asserts path under `${TMPDIR:-/tmp%/}/larch-pre-coder-snapshots/`. Scenario: The `%` is not valid TMPDIR syntax; implementer may copy literally and the assertion never matches the real relocated path
- **Proposed resolution**: Fix the plan (and test) to assert under `"${t}/larch-pre-coder-snapshots/"` where `t` is `${TMPDIR:-/tmp}` with a trailing slash stripped (same as production helper)

### FINDING_7:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:348-383,3051-3089
- **Concern**: Plan does not validate post-coder-head.txt chmod. Scenario: The acceptance requires post-coder-head.txt to be chmod 0444 and cleanup-safe, but the planned 0444 test only covers pre-coder snapshot artifacts via harden_pre_coder_snapshot_perms; a missed chmod at either post-coder-head write site would still pass the proposed tests.
- **Proposed resolution**: Add minimal mode assertions for post-coder-head.txt in existing fix-applied and mav-apply test coverage, and remove the round dir afterward or assert rm -rf succeeds to cover cleanup.

### FINDING_8:
- **Reviewer(s)**: Cursor-dyn-artifact-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1323-1326
- **Concern**: skills/review-and-fix/scripts/review-implement-step5-loop.sh:403. Scenario: 0444 hardening without pre-write cleanup interacts with existing redirect-failure rm -f on pre-coder-head.txt
- **Proposed resolution**: When the $PWD relocation branch leaves a prior round's snapshots under ${TMPDIR}/larch-pre-coder-snapshots/<hash>/ (not removed by cleanup-tmpdir.sh), a later run reuses the same snap_dir. Redirect to an existing 0444 pre-coder-head.txt fails; the existing || rm -f drops the head and skips snapshot_pre_coder_tracked_state while stale 0444 tracked-paths and patch files remain — carryover classification can silently diverge from current git state. Unconditionally remove pre-coder snapshot files (or the whole snap_dir) immediately before the pre-coder-head write in both the main round path (~1321) and run_implement_mav_apply (~401), then write, snapshot, and chmod; do not rely on redirect failure to clear a prior 0444 head.

### FINDING_9:
- **Reviewer(s)**: Codex-dyn-artifact-lifecycle
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/review-and-fix.sh:1321-1326,1531-1533; skills/review-and-fix/scripts/review-implement-step5-loop.sh:401-413; scripts/cleanup-tmpdir.sh:63-70
- **Concern**: Planned 0444 hardening has no same-path rewrite preparation. Scenario: Relocated snapshots are outside cleanup-tmpdir's rm -rf target, so rerunning the same in-repo round can hit existing 0444 pre-coder files. Bash redirection then fails before git rev-parse runs; the existing || rm -f branch deletes the file but does not retry. The round can proceed without a fresh pre-coder snapshot, and existing 0444 patch files can also block regeneration. The same pattern can remove-but-not-refresh post-coder-head.txt when a round_dir is reused.
- **Proposed resolution**: Before each planned hardened write, remove only the exact prior artifacts that may be 0444, then write and harden. For main snapshots, clear pre-coder-head.txt, pre-coder-tracked-paths.txt, and pre-coder-path-diffs/*.patch before regeneration. For MAV and post-coder-head, rm -f the target before redirecting. Do not add broad relocated-dir cleanup.

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-harness-coupling
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:512-528,558-577
- **Concern**: Existing carryover fixtures compute snap_dir before cd, but the proposed helper branches on the current PWD. Scenario: The fixture writes pre-coder-head and patch files to the old sibling path; then round_tracked_dirty_outside_manifest runs after cd into the work repo and recomputes a relocated TMPDIR path, so it cannot find the fixture and the carryover assertions fail
- **Proposed resolution**: Compute snap_dir and create the fixture from the same work-repo cwd used by the guard call, or cd before both setup and assertions so every pre_coder_snapshot_dir call sees the same PWD

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-harness-coupling
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/review-and-fix/scripts/test-review-and-fix.sh:22-23
- **Concern**: The planned in-repo relocation assertion describes the expected TMPDIR prefix without the same trailing-slash normalization as the helper. Scenario: On macOS TMPDIR commonly ends with slash; the helper strips it, but a literal TMPDIR-based prefix assertion can expect a double-slash path and fail even when relocation is correct
- **Proposed resolution**: In the test, compute expected_tmp="${TMPDIR:-/tmp}"; expected_tmp="${expected_tmp%/}" and assert snap_dir starts with "$expected_tmp/larch-pre-coder-snapshots/"
