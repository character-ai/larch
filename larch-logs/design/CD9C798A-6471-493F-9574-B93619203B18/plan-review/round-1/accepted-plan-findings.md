### FINDING_1: Stale 0444 relocated snapshots block rewrite and carryover
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Cursor-Innovation, Codex-Innovation, Codex-Pragmatic, Cursor-dyn-artifact-lifecycle, Codex-dyn-artifact-lifecycle
- **Severity**: important
- **Concern**: Planned 0444 hardening on deterministic relocated snapshot paths under `${TMPDIR}/larch-pre-coder-snapshots/<hash>/round-N` does not clear or replace existing read-only artifacts before the next write. Those paths are outside `cleanup-tmpdir.sh` reap, so a later same-repo/same-round run can hit leftover 0444 `pre-coder-head.txt`, `pre-coder-tracked-paths.txt`, and patch files. Bash redirection to existing 0444 files fails; the existing `|| rm -f` path on `pre-coder-head.txt` removes the head without retrying, so `snapshot_pre_coder_tracked_state` may be skipped while stale tracked-path and patch files remain—carryover classification can silently degrade or diverge from current git state. The same no-cleanup pattern can also leave `post-coder-head.txt` stale when a `round_dir` is reused.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Before each snapshot/head redirect, unlink the specific existing artifact or write temp+mv, then chmod after successful writes; keep directories writable as planned
  - From Codex-Edge: Before the first snapshot redirect at both normal and MAV write sites, remove stale snapshot contents for that snap_dir and recreate it, or remove and retry every hardened artifact write. Add a stale-0444 same-path regression so the relocation branch still writes fresh snapshots.
  - From Cursor-Innovation: Before any write to snap_dir in both main and MAV paths, remove or reset the per-round snapshot contents, for example rm -rf "$snap_dir" then mkdir -p "$snap_dir", or targeted rm/chmod before redirects, so each round starts from an empty writable snapshot dir before chmod 0444 is applied.
  - From Codex-Innovation: Before any write to snap_dir in both main and MAV paths, remove or reset the per-round snapshot contents, for example rm -rf "$snap_dir" then mkdir -p "$snap_dir", or targeted rm/chmod before redirects, so each round starts from an empty writable snapshot dir before chmod 0444 is applied.
  - From Codex-Pragmatic: Before writing a round snapshot, rm -f the known snapshot files/globs in snap_dir, then write and harden them; apply the same stale-file cleanup to the MAV pre-coder-head write path if it can reuse the same snap_dir
  - From Cursor-dyn-artifact-lifecycle: When the $PWD relocation branch leaves a prior round's snapshots under ${TMPDIR}/larch-pre-coder-snapshots/<hash>/ (not removed by cleanup-tmpdir.sh), a later run reuses the same snap_dir. Redirect to an existing 0444 pre-coder-head.txt fails; the existing || rm -f drops the head and skips snapshot_pre_coder_tracked_state while stale 0444 tracked-paths and patch files remain — carryover classification can silently diverge from current git state. Unconditionally remove pre-coder snapshot files (or the whole snap_dir) immediately before the pre-coder-head write in both the main round path (~1321) and run_implement_mav_apply (~401), then write, snapshot, and chmod; do not rely on redirect failure to clear a prior 0444 head.
  - From Codex-dyn-artifact-lifecycle: Before each planned hardened write, remove only the exact prior artifacts that may be 0444, then write and harden. For main snapshots, clear pre-coder-head.txt, pre-coder-tracked-paths.txt, and pre-coder-path-diffs/*.patch before regeneration. For MAV and post-coder-head, rm -f the target before redirecting. Do not add broad relocated-dir cleanup.


### FINDING_3: Relocation test TMPDIR prefix does not match production normalization
- **Reviewer(s)**: Cursor-Requirements, Codex-dyn-harness-coupling
- **Severity**: important
- **Concern**: Planned in-repo relocation assertions can fail to match the real relocated path even when relocation is correct: the plan uses invalid `${TMPDIR:-/tmp%/}` syntax (literal `%`), and a literal `TMPDIR`-based prefix without trailing-slash stripping can expect a double-slash on macOS where `TMPDIR` commonly ends with `/`, while the production helper strips it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Fix the plan (and test) to assert under `"${t}/larch-pre-coder-snapshots/"` where `t` is `${TMPDIR:-/tmp}` with a trailing slash stripped (same as production helper)
  - From Codex-dyn-harness-coupling: In the test, compute expected_tmp="${TMPDIR:-/tmp}"; expected_tmp="${expected_tmp%/}" and assert snap_dir starts with "$expected_tmp/larch-pre-coder-snapshots/"


### FINDING_4: Tests do not assert `post-coder-head.txt` is chmod 0444
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: Acceptance requires `post-coder-head.txt` to be chmod 0444 and cleanup-safe, but the planned 0444 coverage only exercises pre-coder snapshot artifacts via `harden_pre_coder_snapshot_perms`. A missed chmod at either post-coder-head write site would still pass the proposed tests.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add minimal mode assertions for post-coder-head.txt in existing fix-applied and mav-apply test coverage, and remove the round dir afterward or assert rm -rf succeeds to cover cleanup.


### FINDING_5: Carryover harness fixture uses wrong cwd for `snap_dir`
- **Reviewer(s)**: Codex-dyn-harness-coupling
- **Severity**: important
- **Concern**: Existing carryover fixtures compute `snap_dir` before `cd`, but the proposed helper branches on the current PWD. The fixture writes pre-coder-head and patch files to the old sibling path; then `round_tracked_dirty_outside_manifest` runs after `cd` into the work repo and recomputes a relocated TMPDIR path, so it cannot find the fixture and carryover assertions fail.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-coupling: Compute snap_dir and create the fixture from the same work-repo cwd used by the guard call, or cd before both setup and assertions so every pre_coder_snapshot_dir call sees the same PWD

