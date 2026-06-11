# scripts/implement-admission.sh — contract

**Purpose**: mechanical **Preflight admission gate** for `/implement` before `session-setup.sh` allocates `$IMPLEMENT_TMPDIR`. Validates the positional design/tracking issue is eligible to start an implement run: not closed, not lifecycle-managed by title prefix, not an audit-report artifact, not blocked (native+prose union, fail-open), not a `[... Report]` title pattern, and carries the `[DESIGNED]` prefix. For admission, `[DESIGNED]` means Step 5c materialized the `larch:plan` block and renamed the issue; the separate design-log PR publish may still be pending or failed.

**Invocation**: `--issue <N>` (required). Decimal digit strings with leading zeros (e.g. `042`) are normalized to the same integer as `10#` arithmetic before validation. Optional `--repo OWNER/REPO`; when omitted, the script resolves `REPO` via `gh repo view --json nameWithOwner --jq '.nameWithOwner'` before calling `python3 python/cli.py blocker all-open`. Forked upstream runs MUST pass `--repo "$UPSTREAM_REPO"` from the orchestrator.

**Environment**: `gh` on `PATH`. Optional `IMPLEMENT_TMPDIR` — when set and `$IMPLEMENT_TMPDIR/parent-issue.md` exists and its `ISSUE_NUMBER=` matches `--issue`, admission may return pass with `RESUME=true` (crash-resume sentinel per `/implement` Step 0). When that file also contains `RUN_ID=`, the caller MUST export the same `RUN_ID` in the environment before invoking this script; otherwise admission falls through to the full gate (prevents a stale tmpdir whose `parent-issue.md` still lists the same issue from bypassing managed-prefix / blocker / audit checks after a different session wrote the file).

**Ordering / crash-resume vs `gh`**: The script always runs `gh issue view` (with one retry) and validates JSON before evaluating the crash-resume sentinel. A failed view yields exit **2** with `ADMISSION_ERROR=` even when `parent-issue.md` matches `--issue` and optional `RUN_ID` — operators cannot re-enter on resume alone while GitHub is unavailable; recovery requires a successful live issue read first.

**Resume vs managed-title / audit gates**: The crash-resume path still skips managed-title, the `[DESIGNED]` / `missing-designed-prefix` precondition, and audit-label checks (intentional for in-flight runs), still applies the live-title `[... Report]` pattern gate (`has_report_prefix` / exit **7**) using the successful `gh issue view` JSON, and re-runs `all_open_blockers` before emitting `RESUME=true`, so newly opened native or prose blockers are observed on resume the same as on a full pass.

**Stdout**: `KEY=value` lines (`ADMISSION_RESULT=`, `ADMISSION_ERROR=`, `BLOCKERS=`, `TITLE=`, `RESUME=`). Operators and the orchestrator parse these; keep values single-line. GitHub-controlled titles emitted in `TITLE=` are normalized to a single line (CR/LF flattened to spaces) before `emit_kv`.

**Exit 5 recovery (`managed-prefix`)**: without a surviving `$IMPLEMENT_TMPDIR` to pair with Preflight, rename the GitHub issue title in the web UI (or via `gh issue edit`) to remove the `[DESIGNING]`, `[IMPLEMENTING]`, `[DONE]`, `[STALLED]`, legacy `[IN PROGRESS]`, or legacy `[PLANNED]` prefix, then retry `/implement`. For `[DESIGNING]` titles: wait for the active `/design` session to finish and print its Step 5 footer; `[DESIGNED]` may be set before design-log publish completes, so the title is not a global "design finished" mutex.

**Exit 5 recovery (`missing-designed-prefix`)**: the issue has no `[DESIGNED]` prefix, meaning `/design` has not completed the admission-critical Step 5c plan materialization and rename. Run `/design <N>` first; Step 5c writes the `larch:plan` block, best-effort upserts the architecture diagram, renames the issue to `[DESIGNED]` (not gated on `PUBLISH_OK`), then runs design-log PR publish as a separate best-effort follow-up. Re-run `/implement` once the issue title is `[DESIGNED]` and the plan block is present, even if design-log publish is still incomplete; if same-runner serialization matters, wait for the `/design` Step 5 footer or confirm there is no active design runner before starting. Legacy `[PLANNED]` issues: re-run `/design` on the issue — it will migrate the prefix from `[PLANNED]` to `[DESIGNED]`.

**Exit codes**:
| Code | Meaning |
|------|---------|
| 0 | `ADMISSION_RESULT=pass` (optionally `RESUME=true`) |
| 2 | `gh` / resolver hard failure; `ADMISSION_ERROR=` on stdout. Closed issues are treated as failure (exit 2) per orchestrator contract. |
| 4 | `ADMISSION_RESULT=has-blockers` — non-empty blocker list in `BLOCKERS=` |
| 5 | `ADMISSION_RESULT=managed-prefix` — title starts with `[DESIGNING]`, `[IMPLEMENTING]`, `[DONE]`, `[STALLED]`, legacy `[IN PROGRESS]`, or legacy `[PLANNED]`; OR `ADMISSION_RESULT=missing-designed-prefix` — title has no `[DESIGNED]` prefix (run `/design` first) |
| 6 | `ADMISSION_RESULT=audit-report-label` — issue has `audit-report` label |
| 7 | `ADMISSION_RESULT=report-title` — title matches `[... Report]` pattern (same family as historical find-lock-issue rejection) |

**Blocker semantics (D3 fail-open)**: `python3 python/cli.py blocker all-open` inherits the fail-open posture from `python/blocker.py` — native or prose dependency reads that error out degrade to “no blockers found” rather than failing closed. On GitHub API outage this can produce a **false negative** (run proceeds when blockers might exist). `/implement` documents this under Preflight; operators accept the trade-off for availability. The same fail-open applies on the resume branch: dependency reads that error out still yield an empty blocker list.

**Native-first short-circuit**: when `native_open_blockers` returns a non-empty list, `all_open_blockers` skips the prose dependency scan entirely (see `python/blocker.py` and `skills/implement/SKILL.md` Preflight admission gate note). Trade-off: stderr / operator messaging may list only native blocker numbers until native blockers clear, even when prose dependencies would also apply.

**Related**: `python/blocker.py`, `python/test_blocker.py`, `scripts/test-implement-admission.sh`.
