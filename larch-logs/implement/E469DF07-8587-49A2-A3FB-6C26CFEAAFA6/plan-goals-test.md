## Goal
Apply lib-quiet.sh FD-3 mechanism to 21 /review machinery scripts

## Implementation Plan
# Implementation Plan: Quiet-by-default Phase 2 — /review machinery

## Objective
Apply the FD-3 + lib-quiet.sh mechanism to 21 review-machinery scripts (7 in skills/review/scripts/, 14 in scripts/). Audit 4 sourced libs. Update .md contract siblings.

## Conversion pattern per script
1. Source lib-quiet.sh near top (after other lib-*.sh sources):
   - For scripts/: `source "$SCRIPT_DIR/lib-quiet.sh"`
   - For skills/review/scripts/: `source "$PLUGIN_ROOT/scripts/lib-quiet.sh"` (needs PLUGIN_ROOT)
2. Call larch_quiet_init immediately after source
3. Convert contract output `echo "KEY=VAL"` / `printf 'KEY=%s\n' "$x"` → `emit_kv KEY "$x"`
4. Decorative progress lines → `emit_breadcrumb "..."`
5. Leave all other stdout/stderr untouched (larch_quiet_init handles redirection)
6. Special case: render-specialist-prompt.sh + render-reviewer-prompt.sh write CONTENT not KV.
   Add larch_quiet_init then `[ "${LARCH_QUIET_PID:-}" = "$$" ] && exec 1>&3` to restore stdout
   to original (pipe/terminal) while keeping stderr in quiet log.

## Files to modify

### skills/review/scripts/ (7 scripts)
- collect-findings.sh: PLUGIN_ROOT exists; convert 5 printf contract lines at end
- detect-wholesale-rejection.sh: NO SCRIPT_DIR/PLUGIN_ROOT — add both; convert 2 printf lines
- dispatch-panel.sh: PLUGIN_ROOT exists; convert printf output block at end
- emit-tally.sh: SCRIPT_DIR exists but NO PLUGIN_ROOT — add PLUGIN_ROOT; convert 3 printf lines + %q→plain
- gather-context.sh: PLUGIN_ROOT exists; convert scattered printf lines
- log-phase.sh: PLUGIN_ROOT exists; no contract output; just add source+init
- tally-votes.sh: SCRIPT_DIR exists but NO PLUGIN_ROOT — add PLUGIN_ROOT; convert 5 printf lines + %q→plain

### skills/review/scripts/ .md contract siblings (7 files)
- Each: add "On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout."

### scripts/ (14 scripts)
- check-reviewers.sh: convert echo "KEY=val" → emit_kv for all contract lines
- collect-agent-results.sh: large script; no contract output (all written to file); add source+init
- compose-review-findings.sh: convert 4 echo contract lines
- compose-tally-record.sh: no stdout contract; add source+init
- dispatch-plan-voters.sh: convert echo early-exit lines + 5 printf terminal lines
- generate-code-reviewer-agent.sh: "echo Wrote..." is progress → emit_breadcrumb
- generate-pre-rendered-reviewer-prompts.sh: "echo Wrote..." → emit_breadcrumb
- launch-claude-subprocess.sh: convert 4 printf contract lines
- launch-review.sh: very large; no contract KV output (passes to cursor/codex); add source+init
- render-lane-status.sh: convert 7 printf contract lines
- render-reviewer-prompt.sh: content generator → add larch_quiet_init + exec 1>&3 restore
- render-specialist-prompt.sh: content generator → add larch_quiet_init + exec 1>&3 restore
- run-negotiation-round.sh: convert 1 echo contract line
- wait-for-reviewers.sh: convert STATUS/OUTPUT_FILE/ELAPSED printf lines

### scripts/ .md contract siblings (14 files)
- Each: add "On non-zero exit, `FAILURE_LOG=<path>` may appear on stdout."

## Sourced libraries (4 files — audit only)
- lib-codex-launcher-common.sh: no stray stdout → no action
- lib-cursor-launcher-common.sh: no stray stdout → no action
- lib-external-launcher-common.sh: no stray stdout → no action
- lib-gemini-launcher-review.sh: one `printf '%s'... > file` (file write, not stdout) → no action


## Test plan
- skills/review/scripts/test-*.sh: already have assert_stdout_cap (expect quiet behavior) → no LARCH_QUIET_DISABLE needed
- scripts/test-launch-review.sh, test-collect-agent-results.sh, test-check-reviewers.sh, test-render-lane-status.sh, test-wait-for-reviewers.sh, test-dispatch-plan-voters.sh: use $() capture or file redirect → work with emit_kv via FD3 → no changes needed
- test-render-specialist-prompt.sh, test-render-reviewer-prompt.sh: use $() + exec 1>&3 pattern works
