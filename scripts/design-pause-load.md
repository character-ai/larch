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

- `RUN_ID` must pass `larch_log_slug_is_valid`.
- `STEP` must appear in `skills/design/scripts/step-name-registry.tsv`.
- `LOG_RECOVERY_BRANCH`, when present, must pass `git check-ref-format --branch`
  and start with `larch-log-design-`.

`BODY_HASH` is compared against the issue body with the pause marker stripped.
Mismatch emits `WARN=body-drift` and continues; the marker remains the authority.

Snapshot fetch uses `git fetch origin <ref>` followed by local
`git archive <ref> larch-logs/design/<RUN_ID>/ | tar -x --strip-components=3 -C
<tmpdir>`. `LOG_RECOVERY_BRANCH` is fetched first when present; otherwise the
origin default branch is used.

After extraction, `plan.txt`, `run-params.json`, and `pause-state.txt` must exist
at the tmpdir root. Missing artifacts emit `LOAD_OK=false`
`ERROR=missing-restored-artifact`.

## Output Contract

- Success: `LOAD_OK=true`, `STEP=<id>`, `SESSION_ID=<id>`, `RUN_ID=<id>`,
  `TIER=<value>`, `BRAINSTORM_DONE=true|false`, optional `WARN=body-drift`,
  exit 0.
- Expected failure: `LOAD_OK=false`, `ERROR=<token>`, exit 0.

The marker is deleted only after validation and artifact assertions pass.
