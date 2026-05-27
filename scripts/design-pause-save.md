# design-pause-save.sh contract

## Purpose

Publishes the current `/design` tmpdir as a pause snapshot, then writes a
`larch:design-pause` marker block into the issue body. Publishing happens first;
the issue marker is the atomic pointer that makes the snapshot resumable.

## Interface

```text
design-pause-save.sh --design-tmpdir PATH --issue N [--repo OWNER/REPO]
```

The script sources `PATH/source-env.sh` when present and uses `SESSION_ID` as
the run id. It computes `STEP` by walking
`skills/design/scripts/step-name-registry.tsv` in file order and selecting the
first step whose `.completed/step-<id>` sentinel is absent.

## Output Contract

- Success: `PAUSE_OK=true`, `STEP=<id>`, `RUN_ID=<id>`, exit 0.
- Expected failure: `PAUSE_OK=false`, `ERROR=<token>`, exit 0.

Failures are appended to `$DESIGN_TMPDIR/execution-issues.md` under `Tool
Failures` when enough tmpdir context exists.

If `design-log-publish.sh --reason pause` emits `PUBLISH_OK=false` with a
non-empty `RECOVERY_BRANCH`, that branch is recorded as `LOG_RECOVERY_BRANCH`
inside `pause-state.txt` before the marker is written. If publish fails without
a recovery branch, no marker is written.

Normal invocation is synchronous from `/larch:pause`. The `/design` Bash prelude
may also invoke it defensively when `.pause-requested` exists.
