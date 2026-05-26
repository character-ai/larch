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
| `LOG_FLUSH_STATUS` | `ok`, `degraded`, `skipped-no-logs-commit`, or `skipped-rebase-checkpoint` |
| `STEP_7A_BAIL_REASON` | Empty on non-argv paths; `argv` on usage errors |

The helper re-emits the `rebase-checkpoint-probe.sh` KV envelope onto the caller-visible contract stream before its final KV tail.

## Exit Codes

| Code | Meaning |
| --- | --- |
| `0` | Step completed or degraded non-fatally |
| `1` | Rebase checkpoint reported a conflict and Step 7a preserved that exit |
| `3` | Rebase checkpoint reported a non-conflict failure and Step 7a preserved that exit |
| `2` | Argument validation failed |

## Bail Reasons

`argv` is the only current bail reason. Diagram generation, comment upsert, rebase probe, and log flush degradation do not set a bail reason; they append warnings or tool failures and continue.

## Invariants

- Phases stay in the same order as the previous Step 7a `SKILL.md` body: rehydrate, token/timing marks, classifier, diagram generation, comment composition/upsert, 7a.r rebase probe, pre-bump flush, final KV tail.
- `summary-diagrams.md` preserves the existing `larch:diagrams` content shape: Architecture Diagram content or placeholder, blank line, then Code Flow content or placeholder.
- Empty `ISSUE_NUMBER` still gates the tracking-issue upsert.
- `generate-code-flow-diagram.sh` currently emits `STATUS=skipped` only for sanitizer rejection; Step 7a suppresses the `larch:diagrams` upsert on that status and still writes the placeholder body to `summary-diagrams.md`.
- `LARCH_QUIET_BREADCRUMBS=1` is exported for the 7a.r rebase checkpoint probe.
- The helper does not write a `diagrams` larch-log batch.

## Edit-in-sync

Keep this file aligned with:

- `skills/implement/SKILL.md` Step 7a
- `skills/implement/scripts/test-step-7a.sh`
