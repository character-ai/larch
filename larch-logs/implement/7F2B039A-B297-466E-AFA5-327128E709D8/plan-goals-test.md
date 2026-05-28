## Goal
Implement issue #3041: [IMPLEMENTING] Add --emergency flag to /implement that bypasses plan validation in the GitHub…\n\nAdd --emergency flag to /implement that bypasses plan validation in the GitHub issue (Preflight plan-presence/adequacy gating) and proceeds through the implementation flow as though no plan validation step existed. The flag is optional with default off (current behavior preserved). Update relevant documentation (skills/implement/SKILL.md, references, AGENTS.md if applicable, README/docs that describe /implement Preflight) to describe the new flag and when to use it..

## Implementation Plan
## Plan

# Implementation Plan — `--emergency` flag for `/implement`

## Approach

Add an opt-in boolean `--emergency` flag to `/implement` that downgrades three Preflight gates (plan-block presence, plan-adequacy audit, clarify-state pending) from hard refusals to "warn and proceed". Each time a bypass actually fires, emit a loud bold chat warning AND append a structured entry to a Preflight-tmpdir bypass log. Bootstrap consumes that log via the existing `--preflight-tmpdir` channel once `IMPLEMENT_TMPDIR` exists. The flag is threaded through `scripts/implement-bootstrap.sh` into the existing `persist-implement-run-flags.sh` call, and `post-tracking-issue.sh` / `write-final-report.sh` / `render-run-summary.sh` emit `Emergency: true` in `larch:metadata` and `larch:final-summary` when set. Default off; current behavior is byte-preserved when `--emergency` is absent.

`--emergency` is **mutually exclusive with `--draft`** only; compatible with `--forked` and `--merge`. Semantic materiality / stale-plan notice (Preflight item 6) is **not** bypassed and still fires on both AUDIT=pass and emergency audit-refuse paths.

## Files to modify/create

### UPDATED: `skills/implement/SKILL.md`
- Add `--emergency` row to the `Flags` argv table (default `false`; "Bypass plan-block presence, plan-adequacy audit, and clarify-state pending Preflight gates; warn loudly on each triggered bypass").
- Add mutual-exclusion check in the `Mutual exclusion` block: `--emergency` + `--draft` together → print `**⚠ --emergency and --draft are mutually exclusive. Aborting.**` and exit before Preflight.
- Add a short `Emergency mode (--emergency)` subsection inside `Preflight — issue-anchored plan` (before item 1) explaining the bypass semantics, the three gates it covers, the warning contract, and what it does **not** bypass (admission gate, semantic materiality).
- Modify Preflight **item 3** (`BLOCK_PRESENT=false` / `MALFORMED=...` branches): when `emergency_requested=true`, instead of exit 2, (a) write the raw issue body (from the `gh issue view` JSON captured in item 2) to `$PREFLIGHT_TMPDIR/plan-from-issue.txt`, (b) print the bold warning, (c) append a structured entry to `$PREFLIGHT_TMPDIR/emergency-bypass.log`, and continue to item 4.
- Modify Preflight **item 4** (`AUDIT=refuse` branch): when `emergency_requested=true`, (a) print the bold warning, (b) append a structured entry to `$PREFLIGHT_TMPDIR/emergency-bypass.log`, (c) **continue to item 6 (semantic materiality)** — do NOT skip item 6 just because audit was refused. Item 6 fires after both AUDIT=pass and emergency-bypassed AUDIT=refuse.
- Modify Preflight **item 5** (the `clarify-state.sh` / clarify-post path): item 5 currently runs only on `AUDIT=refuse`. When `emergency_requested=true`, item 5 is fully bypassed — no clarify request is posted, no `needs-design-clarification` label is added; the bold warning + bypass-log entry already emitted by item 4 covers the operator audit trail.
- Preserve **item 6** (semantic materiality) unchanged in behavior, but **reach it from both AUDIT=pass AND emergency-audit-refuse paths** — under `--emergency`, the stale-plan notice still fires and may still exit 2.
- Thread `--emergency-requested "$emergency_requested"` into the `${CLAUDE_PLUGIN_ROOT}/scripts/implement-bootstrap.sh --up-to-phase plan` invocation in Step 0 (both initial and resume-shape calls). Add a `_ib_emergency=()` builder beside `_ib_fork=()` mirroring the existing pattern.
- Remove any prompt-side post-bootstrap persist or post-bootstrap log-copy language — bootstrap now owns both the run-flags persistence (via the existing `persist-implement-run-flags.sh` call) and the `emergency-bypass.log` consumption.

### UPDATED: `scripts/implement-bootstrap.sh`
- Add `--emergency-requested true|false` argv flag parsing; default `false`; validate value.
- Forward the value into the existing `persist-implement-run-flags.sh` invocation as `--emergency-requested "$EMERGENCY_REQUESTED"`.
- Forward the value into the existing `post-tracking-issue.sh` invocation so `larch:metadata` composition has the boolean before it runs (FINDING_2).
- Inside `phase_plan_materialize`, alongside the existing `plan-from-issue.txt` copy from `$PREFLIGHT_TMPDIR`, when `$PREFLIGHT_TMPDIR/emergency-bypass.log` exists and is non-empty, append its contents to `$IMPLEMENT_TMPDIR/execution-issues.md` using the existing `append-tool-failure.sh` pattern with category `Warnings` (FINDING_5). Use a stable site label such as `implement-bootstrap emergency-bypass-log`.
- Add `EMERGENCY_REQUESTED=<value>` to the stdout KV stream so the SKILL.md token-aware scan can parse it (parity with `RUN_ID`, `BRANCH_NAME`, etc., though the orchestrator may not need it after this change).

### UPDATED: `scripts/implement-bootstrap.md`
- Document the new `--emergency-requested` argv flag, the `EMERGENCY_REQUESTED=` stdout KV line, and the `emergency-bypass.log` consumption inside `phase_plan_materialize`.

### UPDATED: `scripts/persist-implement-run-flags.sh`
- Add `--emergency-requested true|false` flag parsing (same shape as `--no-issues`).
- Default to `false` when the flag is omitted.
- Validate value is `true` or `false`; fail with `exit 2` otherwise.
- Add `printf 'EMERGENCY_REQUESTED=%s\n' "$EMERGENCY_REQUESTED"` to the writer block before the `mv "$tmp" "$out"` atomic move.

### UPDATED: `scripts/persist-implement-run-flags.md`
- Document the new `--emergency-requested` flag and the `EMERGENCY_REQUESTED=` KV line. Note default `false`.

### UPDATED: `scripts/post-tracking-issue.sh` (or its sibling implementation file; verify path before editing)
- Accept the emergency boolean (either as a new argv flag or via reading `EMERGENCY_REQUESTED` from the persisted `run-flags.sh` inside `$IMPLEMENT_TMPDIR`).
- When composing `summary-metadata.md` (or the body that becomes the `larch:metadata` comment), include a line `Emergency: true` when set; omit the line entirely when false (so non-emergency runs do not gain a noisy `Emergency: false` line).

### UPDATED: `scripts/post-tracking-issue.md`
- Document the emergency boolean input and the `Emergency: true` line in the composed `larch:metadata` body.

### UPDATED: `scripts/write-final-report.sh` (or `skills/implement/scripts/write-final-report.sh` — verify the canonical path)
- Read `EMERGENCY_REQUESTED` from `$IMPLEMENT_TMPDIR/run-flags.sh` (the file already written by `persist-implement-run-flags.sh`).
- Pass the value to `render-run-summary.sh` via a new `--emergency-requested` argv flag (or environment variable, whichever matches the existing convention).

### UPDATED: `scripts/write-final-report.md` (or `skills/implement/scripts/write-final-report.md`)
- Document the new read/pass behavior.

### UPDATED: `scripts/render-run-summary.sh` (or `skills/implement/scripts/render-run-summary.sh`)
- Accept the new `--emergency-requested true|false` argv flag (default `false`).
- When true, emit a `- Emergency: true` line inside the rendered `larch:final-summary` body; when false, omit.

### UPDATED: `scripts/render-run-summary.md` (or `skills/implement/scripts/render-run-summary.md`)
- Document the new flag and the rendered Emergency line.

### UPDATED: `skills/implement/references/summary-comment-template.md`
- Document the optional `Emergency: true|false` (omit-when-false) line in both `larch:metadata` and `larch:final-summary` template bodies.

### NEW or UPDATED: `scripts/test-persist-implement-run-flags.sh` (if not present, create as a sibling alongside the existing `.md`)
- Cover three cases: (a) `--emergency-requested true` → `EMERGENCY_REQUESTED=true` in output; (b) `--emergency-requested false` → `EMERGENCY_REQUESTED=false`; (c) flag omitted → `EMERGENCY_REQUESTED=false` (default).
- Validation: invalid value (e.g., `--emergency-requested maybe`) → exit 2.

### UPDATED: `skills/implement/scripts/test-implement-bootstrap.sh` (verify path)
- Add at least one harness case that drives `implement-bootstrap.sh --emergency-requested true` and asserts (a) `EMERGENCY_REQUESTED=true` in the stdout KV stream, (b) `persist-implement-run-flags.sh` is invoked with `--emergency-requested true`, (c) `emergency-bypass.log` is appended into `execution-issues.md` when the file exists in `$PREFLIGHT_TMPDIR`, and (d) `post-tracking-issue.sh` receives or reads the boolean.

### UPDATED: `scripts/test-write-final-report.sh` (or wherever the final-report harness lives; verify path)
- Add a harness case for `EMERGENCY_REQUESTED=true` in `run-flags.sh` → rendered `larch:final-summary` includes `Emergency: true`. Add a case for `false` → the line is omitted.

### UPDATED: `README.md`
- Update the `/implement` skill blurb row to add a short clause: "Use `--emergency` to bypass plan-block presence / plan-adequacy audit / clarify-state pending gates (default off)."

### UPDATED: `AGENTS.md`
- Update the `docs/issue-anchored-plan.md` reference line to acknowledge the new bypass: append a parenthetical "(`--emergency` may bypass these gates with loud warnings; semantic materiality still fires)" to the sentence describing Preflight enforcement.

### UPDATED: `docs/issue-anchored-plan.md`
- Add a brief note in the Preflight section: `--emergency` may downgrade BLOCK_PRESENT=false, AUDIT=refuse, and clarify-state pending from hard refusals to warn-and-proceed; semantic materiality still fires under emergency.

### UPDATED: `docs/installation-and-setup.md` and/or `docs/skills.md` (only when the file currently documents the `/implement` flag surface or Preflight behavior in detail — verify before editing; do not create new doc sections speculatively)
- Add a brief reference to `--emergency` matching the README change.

## Approach details (ordered)

1. Parse `--emergency` in `/implement` Step 1; default `false`; mental flag `emergency_requested`.
2. Add mutual-exclusion check against `--draft` immediately after existing `--forked`/`--merge` and `--draft`/`--merge` checks. Reject before Preflight.
3. In Preflight item 3, branch on `emergency_requested` for the `BLOCK_PRESENT=false` (and `MALFORMED=*`) exit paths. Under emergency, materialize the raw issue body into `$PREFLIGHT_TMPDIR/plan-from-issue.txt` and continue. Emit the bold chat warning + append a structured line to `$PREFLIGHT_TMPDIR/emergency-bypass.log`.
4. In Preflight item 4, branch on `emergency_requested` for the `AUDIT=refuse` path. Under emergency: warn loudly, log the bypass, and **continue to item 6** (skip item 5; do NOT skip item 6).
5. Item 6 (semantic materiality) is now reachable from BOTH `AUDIT=pass` AND `emergency-audit-refuse` paths. Its behavior is unchanged: if the issue is clearly stale, post the stale-notice comment and exit 2.
6. Thread `--emergency-requested "$emergency_requested"` into the `implement-bootstrap.sh --up-to-phase plan` invocation (both initial and resume shape).
7. In `implement-bootstrap.sh`: parse `--emergency-requested`, default false; forward to `persist-implement-run-flags.sh`; forward to `post-tracking-issue.sh`; consume `$PREFLIGHT_TMPDIR/emergency-bypass.log` inside `phase_plan_materialize` (append to `execution-issues.md` via `append-tool-failure.sh` category Warnings); emit `EMERGENCY_REQUESTED=` on stdout.
8. In `persist-implement-run-flags.sh`: parse the new flag, validate, write `EMERGENCY_REQUESTED=` line to `run-flags.sh`.
9. In `post-tracking-issue.sh`: when emergency boolean is true, include `Emergency: true` in the composed `summary-metadata.md`.
10. In `write-final-report.sh` + `render-run-summary.sh`: read `EMERGENCY_REQUESTED` from `run-flags.sh`; pass through; render `Emergency: true` line in `larch:final-summary` only when true.
11. Update `summary-comment-template.md` to document the optional line.
12. Update documentation (`README.md`, `AGENTS.md`, `docs/issue-anchored-plan.md`, plus any `docs/skills.md` / `docs/installation-and-setup.md` content that materially covers Preflight).
13. Add test coverage: writer harness for `EMERGENCY_REQUESTED=`; bootstrap harness case for argv threading + log consumption; final-report harness case for the rendered line.

## Edge cases

- **`--emergency` + `--draft`**: rejected before Preflight with the new mutual-exclusion message.
- **`--emergency` + `--forked`**: allowed. Bypass applies on the upstream design issue; `--repo "$UPSTREAM_REPO"` paths are unchanged.
- **`--emergency` + `--merge`**: allowed. Merge loop unchanged.
- **`--emergency` set but `larch:plan` block is present AND `AUDIT=pass`**: no bypass actually triggers; no warning is printed (no bypass occurred); `$PREFLIGHT_TMPDIR/emergency-bypass.log` is absent or empty, so bootstrap's log-consumption step is a no-op; `EMERGENCY_REQUESTED=true` is still persisted to `run-flags.sh` and surfaced in metadata/final-summary for audit-trail honesty.
- **`--emergency` set but issue body is empty (no `larch:plan` block and the raw body is empty/whitespace-only)**: item 3 fallback would write an empty plan file. Add a fail-closed branch in item 3 emergency-fallback: when the raw body is empty/whitespace-only, print `**❌ /implement --emergency: issue #<N> has no larch:plan block AND the issue body is empty — nothing to implement. Aborting.**` and exit 2. (Plan must come from somewhere.)
- **`--emergency` with malformed `larch:plan`** (`plan-block-read.sh` exit 1, `MALFORMED=...`): same fallback as `BLOCK_PRESENT=false` — discard the malformed plan, use the raw issue body, warn loudly, log the bypass.
- **Semantic materiality refuses (item 6 stale-plan)** under `--emergency`: still exits 2 with the stale-notice posted. Emergency does not override staleness; this is the documented non-goal.
- **Admission gate refuses (item 1 exit 4/5/6/7)** under `--emergency`: still exits. Admission is **not** bypassed.
- **Resume-shape bootstrap call (`/implement` re-entry after a prior failure)**: the resume call MUST also receive `--emergency-requested` so the persisted run-flags stay consistent across attempts on the same issue.

## Failure modes

- **Wrong-issue-body fallback**: an operator might run `--emergency` on an issue whose body is conversational rather than a plan. Bootstrap will see prose with no `## Plan` / `## Acceptance` headers. The implementer waterfall will receive that text as the plan. Mitigation: the bold warning explicitly names that the raw issue body is being used; operators are expected to read it. (We do not block — `--emergency` is opt-in for fast paths.)
- **Audit trail truncation on bootstrap bail**: if `implement-bootstrap.sh` fails before `phase_plan_materialize` (e.g., `STEP_FAILED=session-setup`), the `emergency-bypass.log` consumption never runs; the log lives only in `$PREFLIGHT_TMPDIR` and may be cleaned up by the preflight tmpdir cleanup. Mitigation: the bold chat warning at Preflight is the immediate operator-visible record; the persistent log is best-effort.
- **Stale persisted flag from a prior run**: `run-flags.sh` is recreated each run by `persist-implement-run-flags.sh` (atomic mktemp + mv), so there is no stale-flag risk between runs.
- **Generator divergence**: `larch:metadata` is composed inside bootstrap by `post-tracking-issue.sh`; `larch:final-summary` is composed at the end of the run by `write-final-report.sh` / `render-run-summary.sh`. Both producers must independently read or accept `EMERGENCY_REQUESTED`. The plan threads the value into both producer chains to avoid drift.

## Testing strategy

- **Unit (writer)**: `scripts/test-persist-implement-run-flags.sh` — covers `EMERGENCY_REQUESTED=true|false`, default-false, and invalid-value rejection.
- **Bootstrap harness**: `skills/implement/scripts/test-implement-bootstrap.sh` (verify exact path) — add a case driving `--emergency-requested true` end-to-end through `phase_plan_materialize` and asserting the persist call, log consumption, and post-tracking-issue.sh handoff.
- **Final-report harness**: a regression test asserting that with `EMERGENCY_REQUESTED=true` in `run-flags.sh`, the rendered `larch:final-summary` includes `Emergency: true`; with false, the line is omitted.
- **Documentation lint**: existing markdown lint will catch any new prose issues.
- **Manual end-to-end (operator)**:
  1. Create a test issue with no `larch:plan` block; run `/implement --emergency <N>` and verify the bold warning, the bootstrap consumes `emergency-bypass.log` into `execution-issues.md`, the issue title's tracking-summary refresh shows `Emergency: true`, and `/implement` proceeds.
  2. Run `/implement --emergency --draft <N>` and verify the mutual-exclusion error.
  3. Run `/implement <N>` (without `--emergency`) on an issue with no `larch:plan` and verify it still exits 2 as today (regression).
  4. Run `/implement --emergency <N>` on an issue WITH a valid `larch:plan` and `AUDIT=pass`: verify `EMERGENCY_REQUESTED=true` is persisted and surfaced in metadata/final-summary even though no bypass actually triggered.

## Acceptance

- `/implement --emergency <N>` on an issue WITHOUT a `larch:plan` block prints a loud bold chat warning, writes a structured entry to `$IMPLEMENT_TMPDIR/execution-issues.md` (via bootstrap's `emergency-bypass.log` consumption), uses the raw issue body as the plan, and proceeds (does not exit 2 from item 3).
- `/implement --emergency <N>` on an issue with `AUDIT=refuse` prints the bold warning, logs the bypass, skips item 5 (clarify-state), and still runs item 6 (semantic materiality) — which may still exit 2 if the issue is stale.
- `/implement --emergency --draft <N>` exits before Preflight with `**⚠ --emergency and --draft are mutually exclusive. Aborting.**`.
- `/implement <N>` (without `--emergency`) on an issue with no `larch:plan` block still exits 2 with the existing message — current behavior is byte-preserved.
- `run-flags.sh` contains `EMERGENCY_REQUESTED=true|false` matching the argv. Invalid values to `--emergency-requested` are rejected with exit 2 in `persist-implement-run-flags.sh`.
- `larch:metadata` (composed by `post-tracking-issue.sh` inside bootstrap) emits an `Emergency: true` line only when `EMERGENCY_REQUESTED=true`.
- `larch:final-summary` (composed by `write-final-report.sh` / `render-run-summary.sh`) emits an `Emergency: true` line only when `EMERGENCY_REQUESTED=true`.
- Tests pass: `scripts/test-persist-implement-run-flags.sh`, the relevant `test-implement-bootstrap.sh` case, and the final-report harness case for the rendered Emergency line.
- Documentation updates land in `skills/implement/SKILL.md`, `scripts/implement-bootstrap.md`, `scripts/persist-implement-run-flags.md`, `scripts/post-tracking-issue.md`, `scripts/write-final-report.md`, `scripts/render-run-summary.md`, `skills/implement/references/summary-comment-template.md`, `README.md`, `AGENTS.md`, and `docs/issue-anchored-plan.md`.

diff_lines: 180

## Test plan
(no test plan section in plan-file)
