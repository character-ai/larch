### OOS_1: [OUT_OF_SCOPE] `LARCH_DESIGN_REENTRY_GUARD_PPID` no longer exported before cancel render
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The old SKILL.md `cancel-reentry-guard` fence set `LARCH_DESIGN_REENTRY_GUARD_PPID="$PPID"` before `render-final-summary.sh`. The new driver's command-scoped render invocation does not forward it, and the plan does not mention preserving it. If `render-final-summary.sh` consumed that variable, reentry-guard cancels would now see an empty value. Marked out-of-scope because the plan lists no requirement to preserve it and current evidence suggests the coupling may be dormant.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Verify render-final-summary.sh does not consume LARCH_DESIGN_REENTRY_GUARD_PPID; if it does add it to the command-scoped env prefix in render_cancel_summary.

Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

