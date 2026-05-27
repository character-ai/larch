# lib-design-reentry-guard.sh contract

`scripts/lib-design-reentry-guard.sh` is a sourced-only Bash 3.2 library for the `/design` same-session re-entry guard.

## Marker grammar

Marker path:

```text
$HOME/.cache/larch/sessions/design-completed-<issue_number>-<ppid>
```

Both `<issue_number>` and `<ppid>` must be unsigned decimal integers. The key is intentionally repo-agnostic: the `/design` single-runner invariant plus per-PPID scoping keeps same-session cross-repo collisions outside the supported workflow, while avoiding an early Step 0b dependency on repo resolution.

## Functions

- `design_reentry_marker_path <issue_number> <ppid>` — prints the marker path. Returns 2 on invalid input.
- `design_reentry_marker_write <issue_number> <ppid>` — creates the parent directory with `mkdir -p`, then `touch`es the marker. Returns 0 on success, 1 on filesystem failure, 2 on invalid input. Failures print `MARKER_WRITE_FAILED=true REASON=<reason>` to stderr.
- `design_reentry_marker_hit <issue_number> <ppid> [ttl_seconds]` — returns 0 when a marker exists and `0 <= age < ttl`; returns 1 for a miss; returns 2 on invalid input. Default TTL is 300 seconds.

## Output grammar

`design_reentry_marker_hit` prints one KV line:

- Hit: `MARKER_HIT=true MARKER_AGE=<seconds> MARKER_TTL=<seconds>`
- Absent/stat miss: `MARKER_HIT=false REASON=absent`
- Stale: `MARKER_HIT=false REASON=stale MARKER_AGE=<seconds>` and best-effort removes the marker
- Future-dated marker: `MARKER_HIT=false REASON=invalid-mtime` and best-effort removes the marker
- Invalid input: `MARKER_HIT=false REASON=invalid-input`

## Stat portability

The library tries GNU `stat -c %Y "$path"` first, then BSD/macOS `stat -f %m "$path"`. Both outputs must match `^[0-9]+$` and be non-zero before use. All `stat` stderr is suppressed; a race where the marker disappears between the file check and `stat` is treated as `REASON=absent`.

## Test harness

`scripts/test-design-reentry-guard.sh` covers absent, hit, stale cleanup, per-PPID and per-issue isolation, fresh HOME writes, future mtime cleanup, and invalid-input return codes.
