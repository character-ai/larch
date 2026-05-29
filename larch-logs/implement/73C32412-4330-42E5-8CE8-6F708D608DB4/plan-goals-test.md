## Goal
Implement issue #3119: [IMPLEMENTING] Breadcrumbs Deprecation Stage 4: Skill fences and public docs cleanup\n\n.

## Implementation Plan
## Plan

Stage 4 of the #3111 breadcrumb rip-out. Stages 1-3 (#3116/#3117/#3118) already removed the script + lint layer; `breadcrumb-monitor.sh` is now a Stage-3 no-op shim and `lint-foreground-markers.*` is gone. This piece finishes the rip-out at the **skill-fence**, **public-doc**, and **orphan-shim** layer: collapse every live Family-B fence to a plain foreground call, exhaustively trim the breadcrumb/Family-B prose, and delete the now-removable Stage-3 shims (which still have 8 live no-op callers).

SIMPLE bias: every edit is surgical. Touch only the Family-B / breadcrumb-monitor / `LARCH_BREADCRUMB_*` apparatus. Do not reflow or reword surrounding prose, and do not restructure scripts.

## Files to modify/create

### UPDATED: `skills/implement/SKILL.md`
Heaviest fence file (16 `breadcrumb-monitor.sh` refs). **Rebase Checkpoint Macro (L139):** drop the dead `scripts/lint-foreground-markers.sh` foreground-marker/denylist pointer (removed in Stage 3); restate checkpoint guidance as one foreground Bash invocation per Call-site registry row with argv/exit/KV authority in `scripts/rebase-checkpoint-probe.md` only. Collapse every `ship-pr.sh` / `ci-wait.sh` / `review-and-fix.sh` / `run-step5-review.sh` / `run-step2-dispatch.sh` Family-B fence to a plain foreground call: drop the `LARCH_BREADCRUMB_*` / sentinel / `LARCH_PAIRED_PID_FILE` exports, the shell `&`, PID capture, `breadcrumb-monitor.sh` invocation, `monitor_rc` branch, post-monitor `wait`, the `**⚠ Background required ...**` banners, and the `# Background pair required: see BASH_AUTHORING.md §4` comments. Rewrite the L1304 "MUST launch with `run_in_background: true` and a foreground `breadcrumb-monitor.sh` pair" warning block into a plain foreground-invocation note (keep the `ship-pr-state.sh` resume-after-timeout recovery prose — the harness auto-backgrounds an overrunning foreground call and notifies on completion). **Post-Invoke routing (FINDING_1):** after fence collapse, rewrite orchestration prose that still depends on the removed status-file / monitor pair — the Step 8+ "Post-/bump-version boundary" block (~L1378), Exit-4 "Wrapper-routing note" (~L1397), and any Step 2 / Step 5 wrapper notes that distinguish `monitor_rc` vs `writer_rc` or instruct parsing `EXIT_CODE` from `$LARCH_STATUS_FILE`. Replace with: treat the foreground Bash tool exit code from the collapsed fence as `writer_rc`; read continuation keys from `ship-pr-state.sh` (and related state files) only; drop `monitor_rc`, `$LARCH_STATUS_FILE`, and `breadcrumb-monitor.sh` routing entirely. Tombstone NEVER #16 in place following the existing NEVER #12 `(removed — see ...)` precedent (no renumbering). Trim NEVER #9: keep the ScheduleWakeup / polling-loop ban, remove the `breadcrumb-monitor.sh` pairing reference. Leave the L1399 Exit-6 `see NEVER #9` pointer valid.

### UPDATED: `skills/design/SKILL.md`
Collapse the `collect-agent-results.sh` Family-B fences (7 refs) to plain foreground calls; strip banners + per-anchor comments + breadcrumb env plumbing.

### UPDATED: `skills/design/references/brainstorm.md`
Collapse the two `collect-agent-results.sh` collector fences (the one-external and two-external examples) to plain foreground calls; remove the background-pair banners and `# Background pair required` comments (5 refs).

### UPDATED: `skills/design/references/dialectic-execution.md`
Collapse the `collect-agent-results.sh` collector fences (6 refs).

### UPDATED: `skills/design/references/plan-review.md`
Collapse the `dispatch-plan-voters.sh` / `collect-agent-results.sh` / `dispatch-with-waterfall.sh` fences (4 refs).

### UPDATED: `skills/implement/references/rebase-rebump-subprocedure.md`
Collapse the `ci-wait.sh` / `ship-pr.sh` fence (1 ref); keep the long-wait policy prose, reframed as plain-foreground + auto-background-on-overrun.

### UPDATED: `skills/implement/references/stall-recovery.md`
No `breadcrumb-monitor.sh` fence — procedural contract only. Rewrite dispatch + safety prose that still mandates Family B background+monitor pairs: Contract intro (L5), Procedure step 5 `step5-review` / `step8-shippr` bullets (L23-24), and Safety Constraints (L53). Replace with plain foreground `${CLAUDE_PLUGIN_ROOT}/scripts/run-step5-review.sh` and `ship-pr.sh` invocations (same argv as today); drop six-path `LARCH_*` breadcrumb exports and monitor-failure vs writer-stall routing. Align with FINDING_1: treat the Bash tool exit code as `writer_rc`; read continuation/classification evidence from `ship-pr-state.sh` / `BAIL_FAILURE_DETAIL_LOG` only — no `breadcrumb-monitor.sh`, `monitor_rc`, or `$LARCH_STATUS_FILE` branches.

### UPDATED: `skills/research/references/research-phase.md`
Collapse the `collect-agent-results.sh` collector fences (3 refs).

### UPDATED: `skills/research/references/validation-phase.md`
Collapse the `collect-agent-results.sh` collector fences (3 refs).

### UPDATED: `skills/review/references/heavy-worker.md`
Collapse the Family-B fence (1 ref).

### UPDATED: `skills/shared/dialectic-protocol.md`
Collapse the `collect-agent-results.sh` fences (3 refs).

### UPDATED: `skills/shared/external-reviewers.md`
Collapse the `collect-agent-results.sh` fences (3 refs).

### UPDATED: `skills/shared/voting-protocol.md`
Collapse the `dispatch-plan-voters.sh` fence (1 ref).

### UPDATED: `BASH_AUTHORING.md`
Delete §4 ("Background+propagate markers for blocking Family B script calls", lines 79-149 / EOF) in full. Keep §1-3 unchanged. The `CLAUDE.md` `@BASH_AUTHORING.md` import stays (§1-3 remain load-bearing).

### UPDATED: `AGENTS.md`
Trim the two breadcrumb bullets (L57-58). Keep the polling-loop / `ScheduleWakeup` ban prose. Remove the "Family B denylisted scripts ... pair with foreground `breadcrumb-monitor.sh`" exception clause, the `BASH_AUTHORING.md §4` / `lint-foreground` references, and the whole "Top-level Family B background+monitor pairs must capture the writer PID and `wait`" bullet. Restate the long-script guidance as: rely on Bash `<task-notification>` for one-shot completion (the harness auto-backgrounds an overrunning foreground call).

### UPDATED: `SECURITY.md`
Surgical. Remove the "**Breadcrumb monitor (Stage 3)**" block (L211-221) and the "Live monitor streaming removed (Stage 3)" / live-stream transitional language (L28-34, L274-295) that describe the now-deleted shim and removed live machinery. PRESERVE the committed `larch-logs/<run-id>/breadcrumbs/` forensics-directory publication contract, the `larch_log_publish_breadcrumbs_shared` reference, and the redaction contracts. Do NOT touch the render-cache hardening language — that is Stage 5 (#3120).

### UPDATED: `docs/run-logs.md`
Remove live-stream / monitor machinery references. PRESERVE the committed `larch-logs/<run-id>/breadcrumbs/` forensics-directory documentation (the parent issue explicitly preserves this directory; "breadcrumb" here means the forensics dir, not the removed monitor).

### UPDATED: `docs/linting.md`
Update the Family-B-fence-lint row (L22) to reflect that Stage 4 has removed the remaining skill-fence prose (past tense; `lint-foreground-markers` already gone since Stage 3). KEEP the generic script "breadcrumb count" harness rows (rebase-checkpoint-probe, phantom-probe, apply-bump, ship-pr) — those are script progress breadcrumbs, not the Family-B monitor.

### UPDATED: `docs/configuration-and-permissions.md`
Remove the single `LARCH_BREADCRUMB_*` env-var reference if it documents the removed live-stream plumbing (verify it is Family-B before trimming).

### UPDATED: `scripts/lib-quiet.sh`
Remove the two no-op compatibility shim definitions `larch_quiet_append_done_trap` and `larch_quiet_write_paired_pid_file`. Keep `emit` / `emit_kv` / `larch_quiet_init` / `sanitize_diagnostic_line` and the redaction path untouched (the `sanitize_diagnostic_line` audit is Stage 5).

### UPDATED: `scripts/lib-quiet.md`
Drop the documentation for the two removed no-op shims.

### UPDATED: `scripts/breadcrumb-monitor.sh`
DELETE this file (the Stage-3 no-op shim is unreferenced once the fences collapse).

### UPDATED: `scripts/breadcrumb-monitor.md`
DELETE this sibling doc.

### UPDATED: `scripts/ci-wait.sh`
Remove the dead `larch_quiet_append_done_trap` call (L68). Remove the `lib-quiet` source line only if no other `lib-quiet` symbol is used.

### UPDATED: `scripts/collect-agent-results.sh`
Remove the dead `larch_quiet_append_done_trap` call (L308).

### UPDATED: `scripts/dispatch-plan-voters.sh`
Remove the dead `larch_quiet_append_done_trap` call (L11).

### UPDATED: `scripts/dispatch-with-waterfall.sh`
Remove the dead `larch_quiet_append_done_trap` call (L10).

### UPDATED: `scripts/ship-pr.sh`
Remove the dead `larch_quiet_append_done_trap` call (L3281). Verify the removal does not orphan a now-empty conditional branch.

### UPDATED: `skills/implement/scripts/run-step2-dispatch.sh`
Remove the dead `larch_quiet_append_done_trap` call (L86) and the "Source lib-quiet only for `larch_quiet_append_done_trap`; do NOT call" comment + the conditional `lib-quiet` source it guards (L80) if `lib-quiet` is no longer needed.

### UPDATED: `skills/implement/scripts/run-step2-dispatch.md`
Drop the "Stage 3 no-op `larch_quiet_append_done_trap` shim" documentation (L11).

### UPDATED: `skills/implement/scripts/step2-implement.sh`
Remove the dead `larch_quiet_append_done_trap` call (L77).

### UPDATED: `skills/review-and-fix/scripts/review-and-fix.sh`
Remove the dead `larch_quiet_append_done_trap` call (L15).

### UPDATED: `scripts/test-lib-quiet.sh`
Delete case 11 (Stage 3 compatibility shim no-op exercise that calls `larch_quiet_append_done_trap` / `larch_quiet_write_paired_pid_file`); renumber cases 12–17 → 11–16. Trim `scripts/test-lib-quiet.md` to drop the shim-no-op bullet so it stays aligned with the harness.

### UPDATED: `scripts/test-collect-agent-results.sh`
Rewrite C_DONE (~L211–222): remove `COLLECTOR_DONE_SENTINEL` / `COLLECTOR_STATUS_FILE` setup and the `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` env exports (collector no longer consumes them); invoke the collector plainly and keep the `STATUS=OK` assertion. Update the case header comment accordingly so the final grep gate stays clean.

### UPDATED: `scripts/test-design-structure.sh`
Remove (or invert to assert-absence) the background-pair banner + `# Background pair required` in-fence assertions (L398-402) and the `breadcrumb-monitor` reference. Ensure `assert_bash_fences_have_pause_check` still passes for the remaining `/design` fences (the pause-check prelude is orthogonal to Family-B and must survive).


### UPDATED: `scripts/test-ship-pr.sh`
Strip top-level `unset` lines for removed Family-B env vars (`LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, etc.); keep only isolation for symbols still used post-rip-out.

### UPDATED: `skills/implement/scripts/test-run-step2-dispatch.sh`
Remove `env -u LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` / `LARCH_PAIRED_PID_FILE` / `LARCH_BREADCRUMB_STREAM` (and related) from dispatch harness invocations.

### UPDATED: `skills/review/scripts/test-dispatch-panel.sh`
Narrow the preamble `unset` list to drop removed sentinel/stream/paired-PID names.

### UPDATED: `skills/review-and-fix/scripts/test-review-and-fix.sh`
Same: drop removed Family-B names from harness `unset` hygiene.

### UPDATED: `skills/design/scripts/test-dispatch-plan-assessors.sh`
Drop removed sentinel/stream/paired-PID names from harness `unset` hygiene.

### UPDATED: `skills/design/scripts/test-tally-plan-assessor.sh`
Same.

### UPDATED: `skills/design/scripts/test-assess-plan-round.sh`
Remove the `LARCH_BREADCRUMB_MONITOR_SH` save/restore + `mock-monitor.sh` stub (L282-354); keep dispatch/tally/snapshot stub overrides only.

## Approach

1. Pre-flight grep to enumerate exact fence boundaries and confirm the caller set is unchanged from this plan.
2. Collapse the 13 skill `.md` fences first (mechanical, per-fence). Replace each background+monitor block with the plain foreground invocation, preserving the pre-existing source-env / pause-check prelude where present. In `skills/implement/SKILL.md`, apply the FINDING_1 post-Invoke routing rewrite in the same pass as fence collapse (do not leave status-file / `monitor_rc` prose behind).
3. Trim root + public docs (`BASH_AUTHORING.md` §4, `AGENTS.md`, `SECURITY.md`, `docs/run-logs.md`, `docs/linting.md`, `docs/configuration-and-permissions.md`), distinguishing removed live machinery from preserved forensics/redaction/progress-breadcrumb content.
4. Remove the 8 dead `larch_quiet_append_done_trap` call sites, then delete the two shim definitions from `lib-quiet.sh`, then delete `breadcrumb-monitor.sh` + `.md` — in that order so no script ever references a missing function.
5. Update `test-design-structure.sh`, `test-lib-quiet.sh` (drop case 11), and `test-collect-agent-results.sh` (C_DONE sentinel strip) in lockstep with shim removal.
6. **Grep-gate harness sweep:** strip or narrow removed-symbol `unset` / `env -u` hygiene in the test harnesses listed above (and any sibling harness that still names `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_PAIRED_PID_FILE`, `LARCH_BREADCRUMB_STREAM`, or `LARCH_BREADCRUMB_MONITOR_SH`); do not add grep exclusions for test-only isolation lines.
7. Run the full grep gate (Testing strategy) + `make lint` until green.

## Edge cases

- **"breadcrumb" is overloaded.** Remove only the Family-B live-stream / monitor / `LARCH_BREADCRUMB_*` apparatus. PRESERVE: the committed `larch-logs/<run-id>/breadcrumbs/` forensics directory + its docs; the `larch_log_publish_breadcrumbs_shared` path; generic script progress-breadcrumb terminology and "breadcrumb count" harness rows; the `> 🔶` step-marker breadcrumbs.
- **NEVER renumbering.** Tombstone NEVER #16 in place (NEVER #12 precedent); do not renumber, so cross-references to higher NEVER numbers stay valid. NEVER #9 is trimmed in place, not removed (its ScheduleWakeup/polling ban is preserved and still referenced by `test-anti-improvised-wakeup.sh`, `step2-implement.md`, AGENTS.md L61).
- **Post-Invoke routing after fence collapse.** Step 8+ / Exit-4 prose that still parses `$LARCH_STATUS_FILE` or branches on `monitor_rc` will mis-route stalls and bail paths once fences are plain foreground. Mitigation: apply the FINDING_1 `skills/implement/SKILL.md` edits in the same change, not fence-only.
- **Shim-deletion ordering.** `larch_quiet_append_done_trap` has 8 live `.sh` callers and scripts run `set -euo pipefail`; deleting the shim before removing every call site causes `command not found` aborts in `ship-pr.sh` / `ci-wait.sh`. Remove callers first, grep to zero, then delete the shim.
- **`larch_quiet_write_paired_pid_file`** already has zero `.sh` callers (only prose in `BASH_AUTHORING.md` / `SECURITY.md`); safe to delete with the doc trims.
- **`SECURITY.md` Stage 4/5 boundary.** Stage 4 removes the breadcrumb-monitor/live-stream language only; Stage 5 (#3120) owns render-cache hardening language. Do not edit render-cache prose here.
- **`orchestrator-never.md` is a no-op.** It contains only the ScheduleWakeup ban; it has no Family-B content. Audit only — do not invent edits.
- **`#2919` is already closed.** No code change; an optional back-reference comment is the only possible action.
- **Verify no residual caller** in `run-step5-review.sh` and any dynamic caller before deleting the shims.
- **Harness-only grep hits.** Unit tests can pass while the pre-close grep gate still matches `unset`/`env -u` lines or `LARCH_BREADCRUMB_MONITOR_SH` mock stubs in test harnesses. Mitigation: apply the grep-gate harness sweep (Approach step 6) in the same PR — no narrow test-only grep exclusions.

## Failure modes

1. **Stale fence-shape assertions break CI.** Earliest signal: `make lint` / `test-design-structure.sh` fails on a banner/comment assertion. Mitigation: update `test-design-structure.sh` in the same change; run structure tests after the sweep.
2. **Over-removal of preserved content.** Earliest signal: `docs/run-logs.md` forensics section missing, polling-loop-ban harness fails, or script progress-breadcrumb tests fail. Mitigation: scope every deletion to the Family-B apparatus; run `test-implement-anti-polling-rule.sh` and the affected script harnesses.
3. **Shim deleted with a caller remaining.** Earliest signal: `ship-pr.sh` / `ci-wait.sh` abort at runtime with `larch_quiet_append_done_trap: command not found`. Mitigation: enforce the remove-callers-then-delete-shim ordering; final grep must show zero callers before shim deletion.
4. **Shim harness still exercises deleted symbols.** Earliest signal: `make test-lib-quiet` fails in case 11 with `command not found` under `set -euo pipefail`, or C_DONE leaves `LARCH_DONE_SENTINEL` / `LARCH_STATUS_FILE` in `test-collect-agent-results.sh` and trips the final grep gate. Mitigation: update `scripts/test-lib-quiet.sh` and rewrite C_DONE in `scripts/test-collect-agent-results.sh` in the same PR as shim deletion.
5. **Pre-close grep fails on harness hygiene only.** Earliest signal: skill/doc edits and unit tests are green but the final grep gate hits `unset`/`env -u` lines in `test-ship-pr.sh`, `test-run-step2-dispatch.sh`, design/review harnesses, or `LARCH_BREADCRUMB_MONITOR_SH` in `test-assess-plan-round.sh`. Mitigation: complete Approach step 6 before declaring the PR grep-clean.

## Testing strategy

- `make lint` (runs the pre-commit hooks repo-wide) must pass.
- Structure harnesses: `scripts/test-design-structure.sh`, `scripts/test-implement-structure.sh`, `scripts/test-research-structure.sh`, `scripts/test-review-structure.sh`.
- Affected-script harnesses: `scripts/test-ship-pr.sh`, `scripts/test-collect-agent-results.sh`, `scripts/test-dispatch-plan-voters.sh`, `scripts/test-lib-quiet.sh`, `skills/implement/scripts/test-step2-implement.sh`, `skills/implement/scripts/test-run-step2-dispatch.sh`, `scripts/test-implement-anti-polling-rule.sh`, plus any `ci-wait` / `dispatch-with-waterfall` / `review-and-fix` harness present.
- Grep-gate harness sweep (same PR): `skills/implement/scripts/test-run-step2-dispatch.sh`, `skills/review/scripts/test-dispatch-panel.sh`, `skills/review-and-fix/scripts/test-review-and-fix.sh`, `skills/design/scripts/test-dispatch-plan-assessors.sh`, `skills/design/scripts/test-assess-plan-round.sh`, `skills/design/scripts/test-tally-plan-assessor.sh`; re-grep repo for any remaining harness `unset`/`env -u` of removed symbols before close.
- `bash scripts/relevant-checks.sh` on the changed set.
- Final grep gate (must return zero outside `larch-logs/**`, `CHANGELOG.md`, and preserved `breadcrumbs/` forensics-dir references): `breadcrumb-monitor`, `LARCH_BREADCRUMB_MONITOR_SH`, `LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_PAIRED_PID_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, `larch_quiet_append_done_trap`, `larch_quiet_write_paired_pid_file`, `Background pair required`, `must be paired with breadcrumb-monitor`, `BASH_AUTHORING.md §4`.


## Acceptance

- All live Family-B fences across the 13 skill `.md` files collapse to plain foreground calls. No `breadcrumb-monitor.sh`, `monitor_rc`, `LARCH_BREADCRUMB_*`, `LARCH_DONE_SENTINEL`, `LARCH_PAIRED_PID_FILE`, sentinel exports, `**⚠ Background required**` banners, or `# Background pair required` comments remain in orchestrator-facing markdown.
- `BASH_AUTHORING.md` §4 is removed; §1-3 and the `CLAUDE.md` `@BASH_AUTHORING.md` import stay intact.
- `AGENTS.md` keeps the polling-loop / ScheduleWakeup ban; the breadcrumb-monitor / Family-B exception clauses and the background+monitor PID-wait bullet are gone.
- `SECURITY.md` drops the breadcrumb-monitor / live-stream language; the forensics-dir publication contract, `larch_log_publish_breadcrumbs_shared`, and redaction contracts are preserved; render-cache language is untouched (Stage 5).
- `scripts/breadcrumb-monitor.{sh,md}` are deleted; both `larch_quiet` no-op shims are removed from `lib-quiet.{sh,md}` only after all 8 `larch_quiet_append_done_trap` call sites are removed (scripts must not abort with `command not found`).
- Preserved: the committed `larch-logs/<run-id>/breadcrumbs/` forensics directory and its docs, generic script progress-breadcrumb terminology, and the redaction toolchain.
- Structure tests (`test-design-structure.sh` and peers) assert ABSENCE of the fence shape; `make lint` and the affected script harnesses pass.
- Final grep gate returns zero hits (outside `larch-logs/`, `CHANGELOG.md`, and preserved `breadcrumbs/` forensics references) for `breadcrumb-monitor`, `LARCH_BREADCRUMB_STREAM`, `LARCH_DONE_SENTINEL`, `LARCH_STATUS_FILE`, `LARCH_PAIRED_PID_FILE`, `LARCH_BREADCRUMBS_SURFACED_FILE`, `larch_quiet_append_done_trap`, `larch_quiet_write_paired_pid_file`, `Background pair required`, `BASH_AUTHORING.md §4`.

diff_lines: 1548

## Test plan
(no test plan section in plan-file)
