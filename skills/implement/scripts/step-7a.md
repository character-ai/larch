# step-7a.sh

`step-7a.sh` is the foreground `/implement` Step 7a orchestration helper. It rehydrates session context, handles code-flow diagram generation and `larch:diagrams` comment upsert, runs the 7a.r rebase checkpoint, and performs the pre-bump run-log flush before Step 8.

## Interface

```bash
skills/implement/scripts/step-7a.sh \
  --implement-tmpdir PATH \
  [--issue-number N] \
  [--run-id ID] \
  [--no-logs-commit BOOL] \
  [--forked-target BOOL]
```

`--implement-tmpdir` is required and must be absolute. Optional values fall back to `$IMPLEMENT_TMPDIR/session-env.sh` keys when omitted.

## Stdout contract

| Key | Values |
| --- | --- |
| `DIAGRAM_STATUS` | `ok`, `skipped`, `failed`, or `skip` (`skip` means the small/non-runtime classifier skipped generation) |
| `DIAGRAM_PATH` | Absolute path to `code-flow-diagram.md`, or empty |
| `COMMENT_URL` | Tracking issue comment URL, or empty when upsert is gated, skipped, or failed |
| `SESSION_TRANSCRIPT_STATUS` | Relayed `capture-session-transcript.sh` status lines, when emitted |
| `LOG_FLUSH_STATUS` | `ok`, `degraded`, `skipped-no-logs-commit`, or `skipped-rebase-checkpoint` |
| `STEP_7A_BAIL_REASON` | Empty on non-argv paths; `argv` on usage errors |

The helper re-emits the `rebase-checkpoint-probe.sh` and `capture-session-transcript.sh` KV envelopes onto the caller-visible contract stream before its final KV tail.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Step completed or degraded non-fatally |
| `1` | Rebase checkpoint reported a conflict and Step 7a preserved that exit |
| `3` | Rebase checkpoint reported a non-conflict failure and Step 7a preserved that exit |
| Other non-zero | Step 7a preserved the probe exit; the orchestrator uses the macro's `unexpected-rc-<n>` / other-non-zero routing |
| `2` | Argument validation failed |

## Bail Reasons

`argv` is the only current bail reason. Diagram generation, comment upsert, rebase probe, and log flush degradation do not set a bail reason; they append warnings or tool failures and continue.

## Invariants

- Phases stay in the same order as the previous Step 7a `SKILL.md` body: rehydrate, token/timing marks, classifier, Code Flow generation, shared diagrams-comment upsert, 7a.r rebase probe, pre-bump flush, final KV tail.
- The classifier, diagram generator, and 7a.r rebase probe use module-level `base_remote` / `base_ref`, defaulting to `origin/main` and switching to `upstream/main` when `--forked-target true` is on argv or when `LARCH_FORKED_TARGET=true` is rehydrated from `$IMPLEMENT_TMPDIR/session-env.sh` during session-key lookup.
- `LARCH_FORKED_TARGET` has no direct shell-environment fallback; only argv and the session-env file are honored.
- When `REPO` or `UPSTREAM_REPO` is present in `$IMPLEMENT_TMPDIR/session-env.sh`, Step 7a threads the resolved owner/repo to `scripts/upsert-diagrams-comment.sh` via `--repo`.
- Step 7a writes `$IMPLEMENT_TMPDIR/code-flow-section.md` only when `generate-code-flow-diagram.sh` reports `STATUS=ok`. The file contains the `## Code Flow Diagram` section passed to `scripts/upsert-diagrams-comment.sh`.
- When generation is skipped or failed, Step 7a removes any stale local `code-flow-diagram.md` / `code-flow-section.md`, omits the upsert, and preserves any prior valid Code Flow section on the issue instead of replacing it with a placeholder.
- Empty `ISSUE_NUMBER` still gates the tracking-issue upsert.
- `larch:diagrams` uses the shared stable marker `<!-- larch:diagrams v1 -->`; Step 7a does not call `tracking-issue-summary.sh` directly and does not use a `runid=` marker for diagrams.
- `LARCH_QUIET_BREADCRUMBS=1` is exported for the 7a.r rebase checkpoint probe.
- Only `REBASE_OUTCOME=ok|skipped` reaches the pre-bump flush phase.
- The helper does not write a `diagrams` larch-log batch.

## Regression checklist

- Green generation writes `code-flow-section.md` and invokes `scripts/upsert-diagrams-comment.sh`.
- Prior Architecture content is preserved by the shared helper while Code Flow is replaced.
- No prior diagrams comment produces a Code Flow-only body.
- `STATUS=skipped` and `STATUS=failed` omit `code-flow-section.md` and skip the upsert.
- Legacy `<!-- larch:diagrams v1 runid=... -->` comments do not collide with the stable marker.
- `ARCHITECTURE_DIAGRAM_FILE` has no effect on Step 7a.

## Edit-in-sync

Keep this file aligned with:

- `skills/implement/SKILL.md` Step 7a
- `skills/implement/scripts/test-step-7a.sh`
