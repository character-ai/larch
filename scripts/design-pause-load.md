# design-pause-load.sh contract

## Purpose

Restores a paused `/design` tmpdir from an issue-body
`larch:design-pause` marker, then deletes the marker.

## Interface

```text
design-pause-load.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]
```

## Behavior

The loader reads the issue body, extracts the marker payload, and validates all
git-sensitive values before any fetch:

- `ISSUE_NUMBER` must match the caller's `--issue`.
- `REPO`, when present, must match the caller repo (explicit `--repo` or
  resolved hub default).
- `RUN_ID` must pass `larch_log_slug_is_valid`.
- `STEP` must appear in `skills/design/scripts/step-name-registry.tsv`.
- `LOG_RECOVERY_BRANCH`, when present, must pass `git check-ref-format --branch`
  and start with `larch-log-design-`.

`BODY_HASH` is compared against the issue body with the pause marker stripped.
Mismatch emits `WARN=body-drift` and continues; the marker remains the authority.

Snapshot fetch uses `git fetch origin <ref>` followed by local
`git archive <ref> larch-logs/design/<RUN_ID>/ | tar -x --strip-components=3 -C
<staging-tmpdir>`. `LOG_RECOVERY_BRANCH` is fetched first when present, and the
loader archives the resolved fetched commit rather than the mutable
`FETCH_HEAD` ref. Otherwise the origin default branch is used.

After extraction, `plan.txt`, `run-params.json`, and `pause-state.txt` must
exist at the staging root. Missing artifacts emit `LOAD_OK=false`
`ERROR=missing-restored-artifact`. The loader rejects staged symlinks, rejects a
staged `.git` path, verifies enumerated restored files stay under the staging
root, deletes the marker, and only then installs the staged restore into the
caller tmpdir.

For unrecoverable snapshot failures (`snapshot-not-found`,
`snapshot-extract-failed`, `snapshot-contains-symlink`,
`snapshot-path-escape`, `restore-forbidden-path`, or
`missing-restored-artifact`), the loader best-effort clears the pause marker
before returning `LOAD_OK=false` so later `/design` runs do not keep retrying
the same broken snapshot.

## Output Contract

- Success: `LOAD_OK=true`, `STEP=<id>`, `SESSION_ID=<id>`, `RUN_ID=<id>`,
  `TIER=<value>`, `BRAINSTORM_DONE=true|false`, optional `WARN=body-drift`,
  exit 0.
- Expected failure: `LOAD_OK=false`, `ERROR=<token>`, exit 0.

The marker is deleted only after validation and artifact assertions pass and
before the staged restore is installed into the caller tmpdir.
