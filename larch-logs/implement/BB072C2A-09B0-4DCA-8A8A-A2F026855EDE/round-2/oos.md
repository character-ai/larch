### FINDING_3: Filtered collector rows are mapped to the wrong slot order
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-edge-cases, dyn-dyn-bgjob-contract
- **Severity**: major
- **Concern**: Once failed lanes are filtered out of `COLLECT_ARGS`, the collector-side sidecar/status loop still indexes against the full fixed slot list, so later lanes can be attributed to the wrong slot.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Ingest per fixed slot path instead of COLLECT_ARGS row index.
  - From codex-specialist-edge-cases: Keep (slot, output_path) pairs for passed lanes, or derive the slot from each collected output path. Never map filtered collector rows against the full fixed slot list.
  - From dyn-dyn-bgjob-contract: Keep passing all four slot paths to `collect-results` in fixed `arch`→`sec` order (collector already reports per-path `STATUS`), or rewrite the sidecar loop to key off each path’s slot suffix (`codex-research-<slot>-output.txt`) instead of collector row index.


Vote tally: YES=1 NO=2 JUDGE_ERROR=0 Result=neutral (neutral-rescued)

### OOS_1: [OUT_OF_SCOPE] Literal-string collision check still misses runtime mapping
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases
- **Severity**: minor
- **Concern**: Out-of-scope follow-up: the collision test only checks literal strings, not the runtime slug registry or computed result-env paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Bad slug reuse could pass CI. Out of scope for this chunk; enhance in a follow-up if desired.
  - From cursor-specialist-edge-cases: Extend harness to assert slug registry mapping or computed result-env paths


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_2: [OUT_OF_SCOPE] Stale background-launch and auto-background wording remains
- **Reviewer(s)**: cursor-specialist-correctness, cursor-specialist-edge-cases, dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The prose still describes the old run_in_background / auto-background behavior after the bgjob migration, which is operator-confusing but not a runtime regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: Update prose to foreground bgjob start.
  - From cursor-specialist-edge-cases: Rename to foreground bgjob start
  - From dyn-dyn-bgjob-contract: Reword to state that `collect-results` remains a long-timeout foreground Bash call while external lanes use bgjob.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_3: [OUT_OF_SCOPE] Merge-env truncation pins remain out of scope
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The merge-env truncation safeguard is still only documented, so a later edit could drop it without CI noticing; this chunk treats that as follow-up work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: Add contains pins for `: > "$RESEARCH_TMPDIR/.research-<slot>-merge.env"` (and the validation equivalents) so stale merge envs cannot regress silently.


Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

### OOS_4: [OUT_OF_SCOPE] Research Codex bgjob start still lacks env exports
- **Reviewer(s)**: dyn-dyn-bgjob-contract
- **Severity**: minor
- **Concern**: The research Codex launcher still omits the child-runtime exports that the validation path already uses, which is a parity/future-proofing concern rather than a current bug.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-dyn-bgjob-contract: Add `export RESEARCH_TMPDIR CLAUDE_PLUGIN_ROOT` before research Codex `bgjob start` for parity and future-proofing if `launch-codex-exec` ever reads those vars at runtime.
Vote tally: YES=0 NO=3 JUDGE_ERROR=0 Result=rejected Fileable=false

