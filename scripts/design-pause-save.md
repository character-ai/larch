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
first step whose `.completed/step-<id>` sentinel is absent. The marker payload
also binds the snapshot to `ISSUE_NUMBER=<argv --issue>` and, when repository
identity can be resolved through `scripts/resolve-repo.sh`, `REPO=<owner/repo>`.

## Output Contract

- Success: `PAUSE_OK=true`, `STEP=<id>`, `RUN_ID=<id>`, exit 0.
- Expected failure: `PAUSE_OK=false`, `ERROR=<token>`, exit 0.

Failures are appended to `$DESIGN_TMPDIR/execution-issues.md` under `Tool
Failures` when enough tmpdir context exists.

If `design-log-publish.sh --reason pause` emits `PUBLISH_OK=false` with a
non-empty `RECOVERY_BRANCH`, that branch is recorded as `LOG_RECOVERY_BRANCH`
inside `pause-state.txt`, written into the marker payload, and surfaced on
stdout as `WARN=recovery-branch-only` plus `LOG_RECOVERY_BRANCH=<branch>`
before the marker is written. If publish fails without a recovery branch, no
marker is written. A pause publish that produces no new committed snapshot
delta now fails closed the same way, so `/larch:pause` does not leave behind a
marker that points at a non-materialized run snapshot.

Normal invocation is synchronous from `/larch:pause`. The `/design` Bash
prelude may also invoke it defensively when `.pause-requested` exists, and
`/larch:pause` itself now arms that sentinel before invoking the helper so the
next Bash boundary can honor a deferred pause request.
