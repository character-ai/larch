# design-pause-load.sh contract

## Purpose

Restores a paused `/design` tmpdir from an issue-body
`larch:design-pause` marker, then deletes the marker after a successful install.

## Interface

```text
design-pause-load.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]
```

## Behavior

On invalid `$DESIGN_TMPDIR` (outside the allowlist), the script calls `emit_load_fail "tmpdir-invalid"` and exits 0 with `LOAD_OK=false ERROR=tmpdir-invalid` so downstream KV parsers see a structured error.

The loader reads the issue body, extracts the marker payload, and validates all
git-sensitive values before any fetch:

- `ISSUE_NUMBER` must match the caller's `--issue`.
- `REPO`, when present, must match the caller repo (explicit `--repo` or
  resolved hub default).
- `RUN_ID` must pass `larch_log_slug_is_valid`.
- `STEP` must appear in `skills/design/scripts/step-name-registry.tsv`.
- `LOG_RECOVERY_BRANCH`, when present, must pass `git check-ref-format --branch`
  and exactly match either `larch-log-design-<RUN_ID>` or
  `larch-log-design-recovery-<RUN_ID>`.

`BODY_HASH` is compared against the issue body with the pause marker stripped.
Mismatch emits `WARN=body-drift` and continues; the marker remains the authority.

Snapshot restore is export-ignore-independent: the loader first captures
`git ls-tree -r -z --name-only <ref> -- larch-logs/design/<RUN_ID>/` into a
temporary NUL buffer with an explicit `if ! git ... >"$enum_tmp"` guard before
any read loop. It then iterates that buffer with `read -d ''`, recreates each
parent directory under the staging tmpdir, and copies each blob with guarded
per-file `git show <ref>:<path>` calls that route failures through
`emit_load_fail "snapshot-extract-failed"`. This guarded capture is required
under `set -euo pipefail`; process substitution alone would not reliably turn a
failed `ls-tree` into the structured failure token. If the ref resolves and
`ls-tree` succeeds but enumerates no blobs under the snapshot subtree, the
loader continues to required-artifact checks and emits
`ERROR=missing-restored-artifact`; `ERROR=snapshot-not-found` is reserved for
ref/fetch failures before enumeration. Remote recovery refs
`larch-log-design-<RUN_ID>` are fetched from `origin` first; local-only
recovery refs `larch-log-design-recovery-<RUN_ID>` are restored from the local
branch in the current clone. Otherwise the origin default branch is used.
After fetch, mutable refs such as `FETCH_HEAD` are pinned to an immutable commit
SHA with `git rev-parse --verify '<ref>^{commit}'` before any `ls-tree` or
`git show` enumeration/extraction; extraction always uses that resolved SHA,
never the mutable ref name directly.

After extraction, `manifest.json`, `run-params.json`, and `pause-state.txt`
must exist at the staging root. `plan.txt` is required only once the saved
resume step is after Step `2b`, because earlier pauses legitimately predate plan
materialization. Missing required artifacts emit `LOAD_OK=false`
`ERROR=missing-restored-artifact`. The loader keeps the marker on retryable
restore, extract, and snapshot-content failures (`snapshot-not-found`,
`snapshot-extract-failed`, `missing-restored-artifact`, install failures, and
transient `issue-body-read-failed` / `not-git-worktree`). Permanent validation
or binding failures (marker field errors, issue/repo mismatches,
restored-* mismatches, corrupt manifest) clear the marker before returning
`LOAD_OK=false`. It deletes the marker only after installing the staged restore
into the caller tmpdir and writing `.resume-loaded`; if that post-success delete
fails, the load still reports success, emits `MARKER_CLEARED=false`, and emits
`WARN=marker-delete-failed` (the route driver refuses `resume@*` until the
marker is removed manually). A successful post-load marker delete emits
`MARKER_CLEARED=true`. Successful load also removes restored
`$DESIGN_TMPDIR/.pause-requested` so the resumed run does not immediately
re-pause from stale local state. Pause snapshots may legitimately include
`.pause-requested` because publish stages the tmpdir as-is at pause-save time;
load copies that snapshot into the live tmpdir, then deletes only the restored
live `.pause-requested` sentinel before returning control. Other restored pause
metadata (`pause-state.txt`, `.resume-loaded`, staged `.completed/*`, and plan
artifacts) remains intact.

`jq` is required for `manifest.json` validation. When it is unavailable, the
loader fails closed with `LOAD_OK=false` `ERROR=jq-missing` instead of a shell
error.

## Output Contract

- Success: `LOAD_OK=true`, `STEP=<id>`, `SESSION_ID=<id>`, `RUN_ID=<id>`,
  `TIER=<value>`, `BRAINSTORM_DONE=true|false`,
  `MARKER_CLEARED=true|false`, optional `WARN=body-drift` and/or
  `WARN=marker-delete-failed`, exit 0.
- Expected failure: `LOAD_OK=false`, `ERROR=<token>`, exit 0.

The marker is deleted only after validation, artifact assertions, restore
installation, and `.resume-loaded` writes succeed. All failure paths keep it for
retry; post-success marker deletion failure is a non-fatal stale-marker warning.
