# scripts/implement-admission.sh — contract

**Purpose**: mechanical **Preflight admission gate** for `/implement` before `session-setup.sh` allocates `$IMPLEMENT_TMPDIR`. Validates the positional design/tracking issue is eligible to start an implement run: not closed, not lifecycle-managed by title prefix, not an audit-report artifact, not blocked (native+prose union, fail-open), and not a `[... Report]` title pattern.

**Invocation**: `--issue <N>` (required). Optional `--repo OWNER/REPO`; when omitted, the script resolves `REPO` via `gh repo view --json nameWithOwner --jq '.nameWithOwner'` and exports it before sourcing `scripts/blocker-helpers.sh`. Forked upstream runs MUST pass `--repo "$UPSTREAM_REPO"` from the orchestrator.

**Environment**: `gh` on `PATH`. Optional `IMPLEMENT_TMPDIR` — when set and `$IMPLEMENT_TMPDIR/parent-issue.md` exists and matches the requested issue number, admission returns pass with `RESUME=true` (crash-resume sentinel per `/implement` Step 0).

**Stdout**: `KEY=value` lines (`ADMISSION_RESULT=`, `ADMISSION_ERROR=`, `BLOCKERS=`, `TITLE=`, `RESUME=`). Operators and the orchestrator parse these; keep values single-line.

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | `ADMISSION_RESULT=pass` (optionally `RESUME=true`) |
| 2 | `gh` / resolver hard failure; `ADMISSION_ERROR=` on stdout. Closed issues are treated as failure (exit 2) per orchestrator contract. |
| 4 | `ADMISSION_RESULT=has-blockers` — non-empty blocker list in `BLOCKERS=` |
| 5 | `ADMISSION_RESULT=managed-prefix` — title starts with `[IN PROGRESS]`, `[DONE]`, or `[STALLED]` prefix |
| 6 | `ADMISSION_RESULT=audit-report-label` — issue has `audit-report` label |
| 7 | `ADMISSION_RESULT=report-title` — title matches `[... Report]` pattern (same family as historical find-lock-issue rejection) |

**Blocker semantics (D3 fail-open)**: `all_open_blockers` inherits the fail-open posture from `scripts/blocker-helpers.sh` — native or prose dependency reads that error out degrade to “no blockers found” rather than failing closed. On GitHub API outage this can produce a **false negative** (run proceeds when blockers might exist). `/implement` documents this under Preflight; operators accept the trade-off for availability.

**Related**: `scripts/blocker-helpers.md`, `scripts/parse-prose-blockers.md`, `scripts/test-implement-admission.sh`.
