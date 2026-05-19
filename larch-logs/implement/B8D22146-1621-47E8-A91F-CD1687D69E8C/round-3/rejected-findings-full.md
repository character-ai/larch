### [rejected] FINDING_10

### FINDING_10: correctness: skills/review/scripts/tally-code-votes.sh:275-276
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Voter parse-rate degraded banner text does not match the implementation plan’s quoted user-facing string. Operators or issue #2351 acceptance criteria expecting the exact “inflated NEUT counts; treat results with caution” wording will see different text. Align banner copy with the plan/issue or record an explicit spec change.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_11

### FINDING_11: correctness: skills/review/scripts/tally-code-votes.sh:276
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Voter parse-rate degraded banner prose does not match the plan’s verbatim string (mentions quorum removal instead of inflated NEUT / caution). Issue #2356-style copy parity, reviewer sign-off on banner text, or grep-based tests expecting the plan string will fail or drift from the approved wording. Match the plan’s exact printf text or formally change the plan and any dependent tests/docs.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_12

### FINDING_12: risk-integration: scripts/dispatch-code-voters.sh:209-217
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Voter 2/3 retries use launch-review.sh --tool instead of the plan-named launch-cursor-review.sh / dispatch-with-waterfall single-slot. If launch-review.sh is not fully equivalent to the first-pass waterfall wiring, retries could diverge subtly from the initial dispatch. Verify parity with first attempt; align docs or switch launchers to match audited behavior.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_13

### FINDING_13: risk-integration: scripts/dispatch-code-voters.sh:384-385
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Slot-indexed prompt files (codex_prompt/cursor_prompt) are passed into retry even when the waterfall’s final tool for that slot is not the primary tool. If make_voter_prompt_file ever diverges by label, a Claude fallback on slot 2 could be retried with codex-labeled file content that is no longer equivalent. Bind retry `src_prompt_file` to the manifest-resolved prompt path for that slot/tool, or document and test the same-body invariant.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_16

### FINDING_16: risk-integration: skills/review/scripts/tally-code-votes.sh:582-583
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] VOTER_COUNT KV now means effective quorum; ELIGIBLE_VOTER_COUNT holds the raw count. External automation (outside this repo) that parsed VOTER_COUNT as raw panel size will misinterpret healthy 3-file panels after parse-rate exclusion. Document the breaking KV semantics or add a backward-compatible alias.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_17

### FINDING_17: risk-integration: skills/review/scripts/tally-code-votes.sh:582-583
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] VOTER_COUNT KV semantics changed; ELIGIBLE_VOTER_COUNT added. External consumers expecting VOTER_COUNT to equal raw voter file count could mis-handle quorum or reporting. Document breaking change or emit a transitional alias for one release if needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_19

### FINDING_19: security: scripts/dispatch-code-voters.sh voter_parse_rate_diag_path (voter_tool branch)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] voter_tool is concatenated into a path without normalization or whitelist. Current waterfall output is constrained to claude codex cursor; future caller changes could pass ../ segments and break the intended REVIEW_TMPDIR jail. Whitelist voter_tool to claude codex cursor before path construction.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_20

### FINDING_20: security: skills/review/scripts/tally-code-votes.sh (effective voter selection via parse-rate diag presence)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Effective quorum now gates on existence of parse-rate diag files under REVIEW_TMPDIR. A stale or forged claude-parse-rate-diag.txt (or per-output *-parse-rate-diag.txt for non-prefixed basenames) can remove a judge from EFFECTIVE_VOTERS and change acceptance thresholds without that voter file being narrative-only. Document single-writer trust; clear diags at tally entry unless produced in the same run; or bind diag to voter-output checksum written only by dispatch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_3

### FINDING_3: architecture: scripts/dispatch-code-voters.sh:195-217
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Voter 2/3 retry uses launch-review.sh --tool instead of the plan’s named launch-cursor-review.sh / dispatch-with-waterfall.sh paths. None unless a future change bypasses launch-review.sh assumptions; mainly spec drift vs written plan. Update plan or add a short comment referencing the supported launcher entrypoint.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_4

### FINDING_4: architecture: scripts/dispatch-code-voters.sh:195-220
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Voter-2/3 parse-rate retry uses launch-review.sh for codex/cursor instead of the plan’s launch-cursor-review.sh and single-slot dispatch-with-waterfall.sh. A reader or follow-up change following the plan literally may wire different env/flags or miss waterfall-only behavior; parity with the agreed design doc is broken until reconciled. Re-invoke retries through the launchers named in the plan, or amend the plan if launch-review.sh is the sole supported path and document why.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_5

### FINDING_5: architecture: scripts/dispatch-code-voters.sh:245-260 skills/review/scripts/tally-code-votes.sh:198-208
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Duplicate voter_parse_rate_diag_path implementations. Future diag path drift could misalign dispatch writes and tally reads. Centralize helper or document single canonical naming contract.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 NEUTRAL=1

### [rejected] FINDING_6

### FINDING_6: code-quality: scripts/dispatch-code-voters.sh:191-193
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] parse_rate_status_from_output can emit multiple lines if stdout ever gains extra PARSE_RATE_STATUS lines. Future helper edits could break [[ "$status" == "NOT_SUBSTANTIVE" ]] and downstream emit_kv assignment. Constrain to a single emitted status line (grep -m1 or awk END-only print).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

### [rejected] FINDING_8

### FINDING_8: correctness: skills/review/scripts/tally-code-votes.sh:1137-1140
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Scoreboard live-row label normalization adds an extra trailing .txt strip beyond the plan’s only -output.txt strip. Unlikely today; only matters if a reviewer key ever ends in .txt without the -output suffix pattern. Limit normalization to the plan’s single sub unless a real key requires the second strip.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 NEUTRAL=1

