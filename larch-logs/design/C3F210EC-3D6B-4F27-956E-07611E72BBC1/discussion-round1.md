# Design Discussion — Round 1 (Step 1c + 1d resolutions)

Scope boundaries, hard constraints, and non-goals resolved before sketch phase. Architecture/mechanism choices remain open for Step 2a sketches.

## Decision 1: Coverage scope
- **Question**: Which scripts should the breadcrumb-propagation mechanism cover?
- **Resolution**: Broad — all long-running larch scripts (apply uniformly via shared wrapper / lib-quiet hook). 209 scripts source lib-quiet.sh today; 19 actually emit breadcrumbs via `emit_breadcrumb`.
- **Source**: user
- **Step**: 1c

## Decision 2: Latency target
- **Question**: What latency target is acceptable for user-visible breadcrumbs?
- **Resolution**: Either is fine — sketches decide between near real-time (per-line streaming) and periodic batch (30-60s lag).
- **Source**: user
- **Step**: 1c

## Decision 3: Display target
- **Question**: Where should propagated breadcrumbs land?
- **Resolution**: Inline in main chat transcript (visible in scrollback). NOT side-channel only.
- **Source**: user
- **Step**: 1c

## Decision 4: Foreground duplication
- **Question**: Must the solution preserve current foreground breadcrumb behavior (no double output when the script actually runs foreground)?
- **Resolution**: Yes — detect and avoid double output when foreground. The mechanism must not re-print to chat lines that the harness already shows inline.
- **Source**: user
- **Step**: 1c

## Decision 5: Foreground-marker contract for denylisted scripts (BASH_AUTHORING §4)
- **Question**: Currently 9 scripts (ship-pr.sh, ci-wait.sh, collect-agent-results.sh, dispatch-plan-voters.sh, dispatch-with-waterfall.sh, run-step5-review.sh, run-step2-dispatch.sh, step2-implement.sh, review-and-fix.sh) are lint-required to be launched foreground. Should the new mechanism preserve that, or flip them to always-background + propagate?
- **Resolution**: **Flip to always-background + propagate.** The propagation layer becomes authoritative; BASH_AUTHORING §4 foreground-marker requirements for these 9 scripts are explicitly removed by this design. lint-foreground-markers.sh and the relevant SKILL.md markers are in-scope for retirement/repurposing.
- **Source**: user
- **Step**: 1d

## Decision 6: Failure-mode UX
- **Question**: On non-zero exit, should the propagator also surface exit code + stderr tail to chat, or only progress breadcrumbs?
- **Resolution**: Yes — propagate exit code + stderr tail (last N lines) to chat on failure. The mechanism is end-to-end visible UX: progress during, status at end.
- **Source**: user
- **Step**: 1d

## Decision 7: Refactor budget
- **Question**: How much may we touch?
- **Resolution**: Allow per-script edits where useful. SKILL.md, lib-quiet.sh, and individual scripts are ALL in-scope for modification. Maximum flexibility.
- **Source**: user
- **Step**: 1d

## Decision 8: Model-actionable propagation
- **Question**: Should the breadcrumb format be designed for Claude (the assistant) to recognize and react to mid-stream, or strictly for human situational awareness?
- **Resolution**: **Deliberately model-actionable.** The breadcrumb format should let the model recognize patterns (e.g., stuck > N minutes on phase X) and potentially take adaptive action (cancel, retry, escalate). Reactive-policy surface is in-scope for sketches to consider.
- **Source**: user
- **Step**: 1d

## Decision 9: Nested-script propagation
- **Question**: Should inner-script breadcrumbs (e.g., plan-review-loop.sh → dispatch-plan-review-panel.sh → external launchers) bubble up transparently?
- **Resolution**: Transparent at any depth. Inner long-running scripts called by an outer wrapped script also have their breadcrumbs propagated. Implementation likely threads through LARCH_QUIET_BREADCRUMB_FD or a shared log.
- **Source**: user
- **Step**: 1d

## Implicit hard constraints (from codebase exploration, not asked)
- **Source**: codebase
- The `lib-quiet.sh` FD-3 machine-readable stdout contract must be preserved (callers parse `KEY=VALUE` lines, `STATUS=`, `EXIT_CODE=`, etc.).
- Existing breadcrumb emitters (`emit_breadcrumb`) and the `LARCH_QUIET_BREADCRUMBS=1` / `LARCH_QUIET_BREADCRUMB_FD` opt-in surface are pre-existing and should remain functional (additive, not replacement).
- The Claude Code harness provides `Bash` `run_in_background: true`, `Monitor`, and `ScheduleWakeup` as the three available primitives for backgrounded-script observation; AGENTS.md endorses Monitor for "logs, external polling, or event streams."
- Cross-platform: Bash 3.2 portability constraint (BASH_AUTHORING.md §3) applies to any new shell scripts.

5 Round-1d decisions resolved (plus 4 Round-1c clarifications + implicit codebase constraints).
