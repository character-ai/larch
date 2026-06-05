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
failed `ls-tree` into the structured failure token. Remote recovery refs
`larch-log-design-<RUN_ID>` are fetched from `origin` first; local-only
recovery refs `larch-log-design-recovery-<RUN_ID>` are restored from the local
branch in the current clone. Otherwise the origin default branch is used.

After extraction, `manifest.json`, `run-params.json`, and `pause-state.txt`
must exist at the staging root. `plan.txt` is required only once the saved
resume step is after Step `2b`, because earlier pauses legitimately predate plan
materialization. Missing required artifacts emit `LOAD_OK=false`
`ERROR=missing-restored-artifact`. The loader keeps the marker on every
restore, extract, validation, and snapshot-content failure so the same marker is
retryable. It deletes the marker only after installing the staged restore into
the caller tmpdir and writing `.resume-loaded`; if that post-success delete
fails, the load still reports success and emits `WARN=marker-delete-failed`.

`jq` is required for `manifest.json` validation. When it is unavailable, the
loader fails closed with `LOAD_OK=false` `ERROR=jq-missing` instead of a shell
error.

## Output Contract

- Success: `LOAD_OK=true`, `STEP=<id>`, `SESSION_ID=<id>`, `RUN_ID=<id>`,
  `TIER=<value>`, `BRAINSTORM_DONE=true|false`, optional `WARN=body-drift`
  and/or `WARN=marker-delete-failed`, exit 0.
- Expected failure: `LOAD_OK=false`, `ERROR=<token>`, exit 0.

The marker is deleted only after validation, artifact assertions, restore
installation, and `.resume-loaded` writes succeed. All failure paths keep it for
retry; post-success marker deletion failure is a non-fatal stale-marker warning.
