## Goal
Implement issue #4779: [IMPLEMENTING] [port-drift] [BUG] design_pause.py dropped pause/resume marker-binding guards in the #3681 sh-to-py port.

## Implementation Plan
## Summary

The #3681 bash-to-Python port of the `/design` pause/resume flow (`design-pause-save.sh` / `design-pause-load.sh` to `python/design_pause.py`) silently dropped a cluster of marker-binding and validation guards that `SECURITY.md` still documents as live. This is the same drop-class as the design-log filter regression fixed in #4766, found by the follow-up migration-wave audit. Severity: high (security hardening). Exploit detail is kept minimal here per the maintainer's request; the trust model is the collaborator-editable pause marker in a public issue body.

## Root cause

`pause_load_main` / `pause_save_main` reimplemented the bash flow but omitted the guards the bash versions enforced. `SECURITY.md` section "/design pause/resume marker binding" describes these guards as the active mitigation, so doc and code now disagree.

## Evidence

Verified against `python/design_pause.py` (load path L224-339, save path L125-224):

- **Mutable-ref extraction.** SECURITY.md: the loader "pins FETCH_HEAD to an immutable commit SHA via git rev-parse --verify '<ref>^{commit}' ... never passes mutable FETCH_HEAD directly into extraction." Code sets `snapshot_ref="FETCH_HEAD"` (L268) and uses it directly in `git ls-tree` (L285) and `git show` (L302). No rev-parse pin.
- **Recovery-branch validation.** Bash restricted the branch to `larch-log-design[-recovery]-<RUN_ID>` and ran `git check-ref-format`. Code fetches `payload["LOG_RECOVERY_BRANCH"]` unvalidated (L262-264), so an unvalidated value flows into `git fetch origin <value>` as a positional token.
- **Repo / manifest binding.** SECURITY.md: loader "fails closed unless those bindings match the caller issue/repo." Code checks only `ISSUE_NUMBER==issue` (L251); no repo-binding and no `manifest.json` issue_number/run_id cross-check.
- **Restored-path rejection.** SECURITY.md: loader "rejects paths outside the snapshot subtree." Code writes `dest = restore_tmp / rel` (L299) with no `..` guard. (Real-world exploitability is low because git tree paths cannot contain `..` and the final copy at L320 is basename-scoped, but the documented defense-in-depth guard is gone.)
- **Marker lifecycle.** SECURITY.md documents clear-on-permanent-failure and delete-on-success with a `MARKER_CLEARED` contract; code never deletes the marker. `design-route.sh` refuses `resume@*` on a stale marker, so resume can wedge.
- **pause-save tmpdir allowlist.** Bash ran `larch_design_tmpdir_validate` (canonical $TMPDIR//tmp/~/.cache/larch/sessions allowlist, control-char and `..` rejection). `pause_save_main` checks only `.is_dir()` (L133). The session-env allowlist validator (`python/cli.py session validate-design-tmpdir`) exists but is not invoked here.
- **pause-save local state redaction.** Bash wrote the `redact secrets`-passed payload to `pause-state.txt` (published into committed `larch-logs/`); code writes raw `state_lines`. Low-density fields, low severity. The outbound marker body IS redacted via `named_block_write_main`.

## Affected files

- `python/design_pause.py` (load + save) — the dropped guards.
- `SECURITY.md` "/design pause/resume marker binding" — the spec to restore against (and to reconcile if any guard is intentionally retired).
- `python/test_design_pause.py` — needs assertions for each restored guard.

## Suggested fix

Restore each guard to match the SECURITY.md contract: rev-parse-pin the snapshot SHA before extraction; validate `LOG_RECOVERY_BRANCH` against the documented prefixes + `check-ref-format`; bind repo and cross-check the restored `manifest.json`; reject `..`/out-of-subtree restored paths; implement the marker clear/delete lifecycle; route pause-save through the design-tmpdir allowlist validator; redact `pause-state.txt`. Add a regression test per guard. If any guard was intentionally dropped, update SECURITY.md instead.

## Test plan
(no test plan section in plan-file)
