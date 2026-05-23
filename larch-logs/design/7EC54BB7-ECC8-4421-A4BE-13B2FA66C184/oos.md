### OOS_1: DISPATCH_OK semantics divergence between /design and /review
- **Description**: `skills/design/SKILL.md:594` vs `skills/review/scripts/review-core.sh:370-378` — `/design` plan-review prose says "proceed when `DISPATCH_OK=false`" while `review-core.sh` treats static dispatch failure as `THRESHOLD_REASON=dispatch-failed` / exit 2. Operators reusing mental model across `/design` Step 3 and `/review` may mis-handle severity of waterfall failure. Documentation alignment issue separate from the paths-file change.
- **Reviewer**: Cursor-arch
- **Focus area**: risk-integration (documentation alignment)
- **Suggested resolution**: File a follow-up doc/workflow alignment issue covering `DISPATCH_OK` semantics across `/design` and `/review`.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_2: Other dispatchers still parse ALL_OUTPUT_FILES with read -r -a
- **Description**: Multiple non-design dispatchers still parse `ALL_OUTPUT_FILES` with `read -r -a outputs_arr <<< "$all_outputs"`:
  - `scripts/dispatch-plan-voters.sh:119-123` (inside script subshell, same-shell safe but multi-word-path hazard if a path contains spaces)
  - `scripts/dispatch-code-voters.sh:405-406` (same)
  - `skills/review/scripts/dispatch-panel.sh:404-426` (same hazard class in `/review`)
  - Affected repo-relative file paths: `scripts/dispatch-plan-voters.sh`, `scripts/dispatch-code-voters.sh`, `skills/review/scripts/dispatch-panel.sh`
  Adopting `ALL_OUTPUT_FILES_PATH` internally in these scripts would close the residual paths-with-spaces hazard. Plan explicitly limits scope to the cross-subshell hazard; this is a follow-up.
- **Reviewers**: Cursor-edge, Codex-edge, Cursor-innovation, Cursor-pragmatic
- **Focus area**: risk-integration
- **Suggested resolution**: File a follow-up issue: "Consume `ALL_OUTPUT_FILES_PATH` / paths-file internally in voter dispatchers and review panel dispatcher for paths-with-spaces robustness."


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_3: eval "$_plan_voter_dispatch" pre-existing shell-injection surface
- **Description**: `skills/design/references/plan-review.md:105-112` — Voter dispatch output is consumed via `eval "$_plan_voter_dispatch"`. A degraded-panel WARN value or any emitted KV containing shell metacharacters could misparse or execute as shell. Adding `VOTER_PATHS_FILE` widens the eval surface (one more emitted value). Pre-existing security concern that the paths-file change makes slightly more relevant.
  - Affected repo-relative file paths: `skills/design/references/plan-review.md`
- **Reviewers**: Codex-edge (classified as OOS), Codex-innovation (classified as in-scope but defers naturally as follow-up)
- **Focus area**: security
- **Suggested resolution**: File a follow-up: "Replace `eval "$_plan_voter_dispatch"` with a `while IFS= read -r line; do case "$key" in ...` whitelist parser matching the Step 3 dispatcher parsing pattern."

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

