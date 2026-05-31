# design-route.sh

**Consumer**: `/design` Step 0b — pre-gate phase driver (resume detection, title-eligibility, re-entry guard, single `ROUTE=` verdict).

**Caller**: `skills/design/SKILL.md` Step 0b (after issue fetch and `REPO` resolve; before clarify / already-planned `AskUserQuestion` gates).

## Argv

| Flag | Required | Notes |
|------|----------|-------|
| `--design-tmpdir PATH` | yes | `cd … && pwd -P` |
| `--issue N` | yes | Positive integer |
| `--issue-title STR` | yes | No embedded newline/CR |
| `--issue-body-file PATH` | yes | Readable regular file; not a symlink |
| `--has-clarify-label true\|false` | yes | Orchestrator parses issue labels |
| `--claude-pid N` | yes | Positive integer |
| `--repo OWNER/REPO` | no | Forwarded from orchestrator; validated when present |

The driver does not fetch the issue body or resolve `REPO` itself.

## Derived / session inputs

- `$PLUGIN_ROOT/scripts/design-pause-load.sh` when body contains `<!-- larch:design-pause:start -->` (optional `${REPO:+--repo}`).
- `scripts/lib-title-eligibility.sh`, `scripts/lib-design-reentry-guard.sh`.
- Plan markers `MARK_START` / `MARK_END` copied verbatim from `scripts/plan-block-read.sh` lines 20–21.

## Responsibilities

1. Resume: `LOAD_OK=true` → `ROUTE=resume@<STEP>` + resume KVs; `LOAD_OK=false` → emit `WARN`/`ERROR`, fall through to steps 2–4 (no early `ROUTE=proceed`).
2. Title-eligibility: lifecycle → `cancel-title-filter` + `TITLE_FILTER_REASON=lifecycle` + marker; archival → `cancel-title-filter` + `archival`; brainstorm prefix → `BRAINSTORM_PREFIX=true` only.
3. Re-entry guard: `MARKER_HIT=true` → `cancel-reentry-guard` + age/TTL/path KVs; miss or helper rc 2 → continue.
4. Verdict: clarify label → `clarify`; well-formed plan block → `already-planned`; else `proceed`. Malformed plan markers → absent.

## Result env (`.design-route-result.env`)

Allowlist: `ROUTE`, `BRAINSTORM_PREFIX`, `TITLE_FILTER_REASON`, `TITLE_FILTER_MARKER`, `MARKER_AGE`, `MARKER_TTL`, `DESIGN_REENTRY_MARKER_PATH`, `RESUME_STEP`, `SESSION_ID`, `RUN_ID`, `TIER`, `BRAINSTORM_DONE`, `WARN`, `ERROR`.

## Exit codes

| Code | When |
|------|------|
| `0` | Any routing verdict (including cancel routes) |
| `1` | `phase_driver_write_result_env` refusal |
| `2` | Argv / body-file / repo config error |

## LLM boundary

Stops before clarify loop, already-planned `AskUserQuestion`, verbal `/larch:issue`, and user-facing cancel banners (orchestrator-owned).

## Idempotency

Safe to re-run on the same inputs; no user prompts.

## Harness

`scripts/test-design-structure.sh` (Step 0b extracted-shape greps; no dedicated offline harness per #3245).

Orchestrator handoff: Step 3–shaped `set +e` capture (`_route_out`), file-first allowlisted read of `.design-route-result.env` (symlink refusal), `case` loop — routing keys via `printf -v`, `WARN`/`ERROR` printed immediately; stdout merge fills missing routing keys only; abort on exit `2` or unexpected non-zero before `ROUTE` branches. Does **not** call `phase_driver_read_result_env`.
