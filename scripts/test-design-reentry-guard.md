# test-design-reentry-guard.sh contract

`scripts/test-design-reentry-guard.sh` is the offline harness for `scripts/lib-design-reentry-guard.sh`.

## Coverage

- F1: absent marker returns rc 1 with `MARKER_HIT=false REASON=absent`.
- F2: fresh marker for the same issue and PPID returns rc 0 with `MARKER_HIT=true`.
- F3: stale marker returns a stale miss and is removed.
- F4: marker for a different PPID does not block the current PPID.
- F5: marker for a different issue does not block the current issue.
- F6: write path creates `$HOME/.cache/larch/sessions` in a fresh HOME.
- F7: future-dated marker returns `REASON=invalid-mtime` and is removed.
- F8: invalid issue or PPID inputs return rc 2; invalid writes also return rc 2.

Each fixture runs with a temporary HOME so the harness never touches the operator's real session cache.
