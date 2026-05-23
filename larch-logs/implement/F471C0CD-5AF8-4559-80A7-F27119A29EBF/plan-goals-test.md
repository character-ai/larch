## Goal
Switch tracking-issue title-prefix state machine from [IN PROGRESS]/[PLANNED] to [DESIGNING]/[DESIGNED]/[IMPLEMENTING]/[DONE]/[STALLED] and add [DESIGNED] precondition at /implement admission.

## Implementation Plan
## Plan

### Goal

Switch the tracking-issue title-prefix state machine from the current 5-state set (`[IN PROGRESS]`, `[DONE]`, `[STALLED]`, `[PLANNED]`) to a 5-state set (`[DESIGNING]`, `[DESIGNED]`, `[IMPLEMENTING]`, `[DONE]`, `[STALLED]`). Add a `[DESIGNED]` precondition check at `/implement` Preflight admission so issues without a completed `/design` run hard-fail before allocating session state. Audit and update every `[IN PROGRESS]` / `[PLANNED]` reference in the active runtime surface (skills/, scripts/, agents/, .claude/, SECURITY.md, docs/, tests). Leave historical artifacts (CHANGELOG.md, larch-logs/**) unchanged.

### State machine summary

| Stage | Old prefix | New prefix | Writer |
|---|---|---|---|
| /design start | (none) | `[DESIGNING]` | scripts/tracking-issue-write.sh rename --state designing (new) |
| /design complete | `[PLANNED]` | `[DESIGNED]` | scripts/tracking-issue-write.sh rename --state designed (renamed) |
| /implement start | `[IN PROGRESS]` | `[IMPLEMENTING]` | scripts/tracking-issue-write.sh rename --state implementing (renamed) |
| /implement success | `[DONE]` | `[DONE]` | unchanged |
| /implement failure | `[STALLED]` | `[STALLED]` | unchanged |

Legacy `[IN PROGRESS]` and `[PLANNED]` prefixes are stripped by `strip_lifecycle_prefix` (so rename remains idempotent for in-flight issues), but neither is accepted as a `--state` argv value and `[PLANNED]` no longer satisfies the `/implement` admission precondition.

### Files to modify

**Core helpers**: `scripts/tracking-issue-write.sh` (state_to_prefix accepted set: drop `in-progress` / `planned`, add `designing` / `designed` / `implementing`; expand `strip_lifecycle_prefix` to cover both legacy and new prefixes; mirror in `CUR_CANON_PREFIXES`; update usage/error strings + the anchored-regex docstring), `scripts/tracking-issue-write.md`, `scripts/lib-title-markers.sh` (rewrite the prefix case-block in `insert_signal_marker`), `scripts/implement-admission.sh` (extend `has_managed_prefix` to include `[DESIGNING]` / `[IMPLEMENTING]` / legacy `[PLANNED]` / legacy `[IN PROGRESS]`; add a new `has_designed_prefix` check + a new `missing-designed-prefix` admission result at exit 5; preserve resume-sentinel and forked-mode carve-outs), `scripts/implement-admission.md`.

**Skills**: `skills/design/SKILL.md` — insert a new Step 0b sub-step that calls `tracking-issue-write.sh rename --state designing` AFTER the clarify-loop / already-planned / tier-gate routers have committed to proceeding (placement avoids the cancel-leaves-misleading-state edge case); switch Step 0b sub-step 3.5 and Step 5b sub-step 7 callsites from `--state planned` to `--state designed` and rewrite the surrounding `[PLANNED]` prose. `skills/implement/SKILL.md` — switch Branch 1 and Branch 2 rename callsites from `--state in-progress` to `--state implementing`; update narrative paragraphs at lines 646, 668, 715, 731; add a one-line note in the Step 0 admission section pointing at the new `[DESIGNED]` precondition.

**Skill peripherals**: `.claude/skills/audit-runs/SKILL.md` + `scripts/test-audit-runs.sh` (replace `[IN PROGRESS]` literals with `[IMPLEMENTING]` at 4 SKILL.md sites + 4 test fixtures, update assertion labels); `.claude/skills/combine-issues/SKILL.md` + `scripts/fetch-combinable-issues.sh` (rewrite the jq exclusion regex to `^\[(DESIGNING|IMPLEMENTING|STALLED|DONE)\]`; add a justifying comment that `[DESIGNED]` is intentionally NOT excluded because designed-but-unimplemented issues remain valid combine candidates).

**Docs/SECURITY**: `SECURITY.md` (line 106 managed-lifecycle list + trailing tracking-adoption sentence); `docs/issue-anchored-plan.md` (line 177 `IN PROGRESS` → `IMPLEMENTING`); `agent-lint.toml` (line 877 comment hint).

**Tests**: `scripts/test-tracking-issue-write.sh` — rewrite legacy-prefix fixtures (lines 50, 98, 108, 125, 132); update `--state` argv (`in-progress` → `implementing`, `planned` → `designed`); add fixtures for `--state designing` from no-prefix and `--state designed` from legacy `[PLANNED]` (verifies migration strip + new prepend in one shot). `scripts/test-implement-admission.sh` — rewrite `[IN PROGRESS]` fixture literals (lines 216, 273, 300, 326, 352); add new admission cases: (a) `[DESIGNED]` → exit 0 / pass, (b) `[DESIGNING]` → exit 5 / managed-prefix, (c) no-prefix → exit 5 / missing-designed-prefix, (d) legacy `[PLANNED]` → exit 5 / managed-prefix. `scripts/test-lib-title-markers.sh` — rewrite the `[PLANNED]` fixture as `[DESIGNED]`; add a `[DESIGNING]` fixture to confirm marker insertion preserves the new prefix.

**Changelog**: add a single new Unreleased entry in `CHANGELOG.md` summarizing the prefix-set switch, the new `/implement` precondition, the legacy migration posture, and the active-runtime-only audit scope. Do not modify historical entries.

### Approach

- **Single-PR strategy**: ship every change together because the rename helper, admission gate, callers, and test fixtures cross-cut.
- **Migration posture**: legacy `[IN PROGRESS]` and `[PLANNED]` titles are tolerated by `strip_lifecycle_prefix` (so re-running `/design` on a `[PLANNED]` issue cleanly migrates), but rejected by admission and not accepted as `--state` argv values.
- **Admission precondition placement**: new `missing-designed-prefix` check fires AFTER managed-prefix / report-prefix / audit-label / blockers — the precondition is the last gate before PASS; exit code reuses 5; `ADMISSION_RESULT` differentiates via the new value.
- **Forked-mode and resume carve-outs**: preserved (resume sentinel exits 0 before reaching the new check).
- **/design Step 0 rename placement**: insert AFTER routers (clarify-loop, already-planned) commit to proceeding, not at start of Step 0a — prevents cancel-leaves-misleading-state.

### Edge cases

- Issue already in `[PLANNED]` mid-migration → /implement admission rejects; operator re-runs `/design` (auto-migrates to `[DESIGNED]`).
- Issue already in `[IN PROGRESS]` with no surviving `$IMPLEMENT_TMPDIR` → /implement admission rejects (managed-prefix); operator manually renames or accepts the abandoned run.
- Concurrent /design and /implement on same issue → /implement admission sees `[DESIGNING]` and rejects (expected behavior).
- Round-trip marker preservation → unchanged (strip-then-prepend mechanic unchanged).
- Title 256-char limit → prefix lengths differ slightly (longest new prefix `[IMPLEMENTING] ` = 16 chars); slicing logic is prefix-length-aware, no behavioral change beyond a recommended new long-title fixture.

### Failure modes

1. **Stale prefix literal**: a missed `[IN PROGRESS]` / `[PLANNED]` reference. Earliest warning: `bash scripts/relevant-checks.sh` or a CI test harness assertion. Mitigation: explicit `git grep -nE '\[(IN PROGRESS|PLANNED)\]' -- ':!CHANGELOG.md' ':!larch-logs/'` pass after edits with documented allow-list verification.
2. **Admission precondition rejecting valid resumed runs**: ordering bug puts the new check before resume sentinel. Earliest warning: existing resume test fixtures fail. Mitigation: insert the new check AFTER the resume branch.
3. **combine-issues jq regex typo**: silently wrong exclusion set. Earliest warning: a hermetic fixture pipeline test. Mitigation: extend or add fixture coverage for the filter.

### Testing strategy

- Run `make test-tracking-issue-write`, `make test-implement-admission`, `make test-lib-title-markers`, and the audit-runs test suite — all must pass with updated fixtures.
- Add new harness coverage: (a) admission PASS on `[DESIGNED]`, (b) admission REJECT on missing prefix and on `[PLANNED]`, (c) admission REJECT on `[DESIGNING]`, (d) rename migration round-trip from `[PLANNED]` to `[DESIGNED]` via a single `tracking-issue-write.sh` call, (e) FALSE-POSITIVE marker insertion against a `[DESIGNING]` title.
- Run `bash scripts/relevant-checks.sh` after all edits.

## Acceptance

- Every `--state planned` / `--state in-progress` call site in `skills/design/SKILL.md` and `skills/implement/SKILL.md` is rewritten to the new state names.
- `scripts/tracking-issue-write.sh state_to_prefix` accepts exactly `{designing, designed, implementing, done, stalled}` and rejects `{in-progress, planned}` with a clear error message.
- `scripts/implement-admission.sh` admits `[DESIGNED]` prefixed titles, rejects no-prefix titles with `ADMISSION_RESULT=missing-designed-prefix` at exit 5, rejects `[DESIGNING]` / `[IMPLEMENTING]` / `[DONE]` / `[STALLED]` / legacy `[PLANNED]` / legacy `[IN PROGRESS]` with `ADMISSION_RESULT=managed-prefix` at exit 5, and preserves the resume-sentinel bypass.
- `/design` Step 0 renames the issue to `[DESIGNING]` after the clarify-loop / already-planned / tier-gate routers commit; the rename is idempotent and best-effort.
- `/design` Step 5b renames the issue to `[DESIGNED]` (was `[PLANNED]`) on successful publish.
- `/implement` Step 0 renames the issue to `[IMPLEMENTING]` (was `[IN PROGRESS]`); Step 18 retains `[DONE]` / `[STALLED]` unchanged.
- A `git grep -nE '\[(IN PROGRESS|PLANNED)\]' -- ':!CHANGELOG.md' ':!larch-logs/'` audit pass returns zero hits in the live runtime surface (skills/, scripts/, agents/, .claude/, SECURITY.md, AGENTS.md, docs/, agent-lint.toml).
- All updated test harnesses (`make test-tracking-issue-write`, `make test-implement-admission`, `make test-lib-title-markers`, the audit-runs test suite) pass green.
- `bash scripts/relevant-checks.sh` succeeds.
- A new Unreleased `CHANGELOG.md` entry describes the prefix-set switch, the new `/implement` precondition, the legacy migration posture, and the audit scope.

diff_lines: 380

## Test plan
(no test plan section in plan-file)
