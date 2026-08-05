# design-step3-review.sh

## Purpose

Adapter-backed `/design` Step 3 launcher and plan-review child.

## Primary callers

- `skills/design/SKILL.md`

## Invariants

- Resolves a supplied `--session-env-path` through `scripts/larch.sh bgjob adapt --resolve-session-env` before result reads, resume state, pause handling, or tmpdir use. It never sources the file.
- Validates `--starting-round`, `--phase`, and `--findings-file` before writing resume state. `awaiting-vote` remains internal.
- Keeps `--read-result-env`, resume writes, and parent pause-save outside child mode.
- Delegates lifecycle decisions to `bgjob adapt` with explicit step `design-step3-review`, tmpdir, 21600-second budget, session path, and optional owner PID.
- Uses `--replace-completed-result` only for a validated resume invocation. Ordinary duplicate calls reattach the completed result when the input fingerprint matches. When `plan.txt` is present, the wrapper passes its sha256 as `--input-fingerprint` to `bgjob adapt`; a fingerprint mismatch (or no stored sidecar for a prior result) is treated as stale and launches fresh.
- Requests `--clear-on-fresh` for `.completed/step-3`. A completed-result reattachment preserves the marker.
- Accepts child mode only as the terminal `--bgjob-child --merge-result-env <path>` suffix. It preserves every earlier argv cell.
- Keeps scope-anchor validation, `plan-review run`, stderr capture, and status normalization in the child.
- Quarantines a prior compatibility sidecar during the child invocation. Only a fresh, complete `.step3-review-result.env` with `NEXT_ACTION` and a status row can publish atomically to the adapter merge path.
- Missing scope, panel-init failure, pause routing, and normal normalization publish a complete routing envelope and exit zero. Envelope creation or publication failure exits non-zero.
- The bgjob result env remains the prompt-side completion source. Continuation requires `BGJOB_RC=0` and route rows.

## Harness

Covered by `make test-design-structure`, `skills/design/scripts/test-design-step3-review.sh`, and `make test-step3-orchestrator-fence`.
