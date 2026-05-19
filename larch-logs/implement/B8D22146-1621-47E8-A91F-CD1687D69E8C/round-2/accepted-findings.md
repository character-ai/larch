### FINDING_1: **Important** (`correctness`) — `skills/review/scripts/tally-code-votes.sh:219-287`: parse-rate-failed voters are subtracted from `EFFECTIVE_VOTERS`, but their files are still included in the vote-count loop. A failed voter with mostly narrative output but one parseable `FINDING_1: YES` can still tip a result: with failed cursor `YES`, healthy codex `YES`, healthy claude `NO`, the code counts `YES=2 NO=1` against `EFFECTIVE_VOTERS=2` and accepts, even though the two effective voters are split and should be neutral. Build and iterate an effective voter-file list that excludes files with parse-rate diag files, or keep the original denominator if those votes remain counted.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** (`correctness`) — `skills/review/scripts/tally-code-votes.sh:219-287`: parse-rate-failed voters are subtracted from `EFFECTIVE_VOTERS`, but their files are still included in the vote-count loop. A failed voter with mostly narrative output but one parseable `FINDING_1: YES` can still tip a result: with failed cursor `YES`, healthy codex `YES`, healthy claude `NO`, the code counts `YES=2 NO=1` against `EFFECTIVE_VOTERS=2` and accepts, even though the two effective voters are split and should be neutral. Build and iterate an effective voter-file list that excludes files with parse-rate diag files, or keep the original denominator if those votes remain counted.
- **Suggested revision**: Address the concern above.


### FINDING_10: architecture: scripts/dispatch-code-voters.sh:228-242
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Successful parse-retry leaves retry basename .launcher-stderr behind. Long sessions accumulate orphan sidecars under REVIEW_TMPDIR. rm -f "${retry_output}.launcher-stderr" after successful mv swap.
- **Suggested revision**: Address the concern above.


### FINDING_11: architecture: scripts/dispatch-code-voters.sh:232-248
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Failed or non-final retry paths may leave *-parse-retry.txt and sidecars. Humans or tools may mistake retry temp files for canonical voter outputs. rm -f retry output and sidecars on terminal failure paths.
- **Suggested revision**: Address the concern above.


### FINDING_12: architecture: skills/review/scripts/tally-code-votes.sh:287 scripts/lib-vote-tally.sh:68-70
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Shared lib documents classify_result eligible as non-failed voter files; code-review tally passes EFFECTIVE_VOTERS. Future refactors may “correct” tally toward file-count quorum or change the library under a false invariant, reintroducing wrong acceptance under narrative voters. Document at call site and extend lib-vote-tally contract text for code-review effective quorum.
- **Suggested revision**: Address the concern above.


### FINDING_14: code-quality: scripts/dispatch-code-voters.sh:153-162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] append-tool-failure --tool names launch-${voter_tool}-review.sh for parse-rate warnings even when codex/cursor retries use launch-review.sh. Misleading execution-issues attribution during triage. Use the actual launcher invoked or a neutral tool label for parse-rate warnings.
- **Suggested revision**: Address the concern above.


### FINDING_17: code-quality: skills/review/scripts/tally-code-votes.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] ELIGIBLE_VOTER_COUNT not listed in emitted-keys table. Consumers discover the key only via code or tests. Add row documenting ELIGIBLE_VOTER_COUNT and revised VOTER_COUNT semantics.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** (`risk-integration`) — `skills/review/scripts/tally-code-votes.sh:225-287`: when every voter has a parse-rate diag, `EFFECTIVE_VOTERS` becomes `0`, but the zero-judge path still checks `ELIGIBLE_VOTERS == 0`. That means tally emits `TALLY_STATUS=ok` and rejects every finding instead of triggering the existing main-agent adjudication path, even while the banner says `main-agent-required`. Base the main-agent-required branch on `EFFECTIVE_VOTERS == 0` after parse-rate degradation, and ensure `review-core.sh` receives `TALLY_STATUS=main-agent-vote-required`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** (`risk-integration`) — `skills/review/scripts/tally-code-votes.sh:225-287`: when every voter has a parse-rate diag, `EFFECTIVE_VOTERS` becomes `0`, but the zero-judge path still checks `ELIGIBLE_VOTERS == 0`. That means tally emits `TALLY_STATUS=ok` and rejects every finding instead of triggering the existing main-agent adjudication path, even while the banner says `main-agent-required`. Base the main-agent-required branch on `EFFECTIVE_VOTERS == 0` after parse-rate degradation, and ensure `review-core.sh` receives `TALLY_STATUS=main-agent-vote-required`.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/dispatch-code-voters.sh:363-368
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] VOTER_N_PARSE_RATE_STATUS defaults to OK when VOTER_N_STATUS is failed because retry/check is skipped. Downstream or logs show VOTER_1_PARSE_RATE_STATUS=OK alongside VOTER_1_STATUS=failed after empty or errored Claude output, implying parse health is OK. Set explicit status for failed slots (e.g. SKIPPED or N/A) or omit PARSE_RATE KV when status is failed.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/dispatch-code-voters.sh:370-379
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Dispatch DEGRADED_PANEL_WARNING uses non-empty outputs only; tally degrades quorum using parse-rate diags. Operators see DISPATCH_OK / DEGRADED_PANEL_WARNING that disagree with tally’s effective-judge messaging for narrative-heavy voters. Reconcile counters or document why dispatch and tally intentionally differ.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/dispatch-code-voters.sh;skills/review/scripts/tally-code-votes.sh;implementation_plan Part B
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Diag files use path-derived names (voter_parse_rate_diag_path) not plan-stated $REVIEW_TMPDIR/${voter_tool}-parse-rate-diag.txt for claude|codex|cursor. External checks or operators following the plan look for cursor-parse-rate-diag.txt etc. and miss parse-rate failure; mismatch with written plan. Align on-disk names with the plan or update the plan and all consumers to the path-derived scheme.
- **Suggested revision**: Address the concern above.


### FINDING_26: risk-integration: scripts/dispatch-code-voters.sh:370-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] DEGRADED_PANEL_WARNING uses non-empty output count only; ignores parse-rate NOT_SUBSTANTIVE that tally treats as reduced quorum. Three slots can all be non-empty narrative while tally downgrades to 2-judge (or 1-judge) rules; dispatch emits no degraded warning, so upstream automation relying on dispatch KVs disagrees with tally banners and vote outcomes. Align dispatch effective-judge accounting with tally (parse-rate diag or PARSE_RATE_STATUS) or emit a separate KV that matches EFFECTIVE_VOTERS semantics.
- **Suggested revision**: Address the concern above.


### FINDING_27: risk-integration: scripts/dispatch-code-voters.sh:370-380 vs skills/review/scripts/tally-code-votes.sh:219-287
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Dispatch DEGRADED_PANEL_WARNING uses non-empty outputs only; tally uses EFFECTIVE_VOTERS including parse-rate diag slots. Dispatch KV says full panel while tally degrades tier for the same run. Align effective-judge counting with parse-rate status or document intentional divergence.
- **Suggested revision**: Address the concern above.


### FINDING_30: risk-integration: skills/review/scripts/tally-code-votes.md:58-69 and skills/review/scripts/tally-code-votes.sh:287,572-573
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] VOTER_COUNT and quorum documentation still describe raw eligible voter files while classify_result and VOTER_COUNT KV use EFFECTIVE_VOTERS. External scripts or humans following tally-code-votes.md may treat VOTER_COUNT as file count and mis-rank panel strength or compare inconsistent numbers to other pipeline stages. Update tally-code-votes.md to document EFFECTIVE vs ELIGIBLE semantics and new ELIGIBLE_VOTER_COUNT; align threshold prose with classify_result’s actual quorum input.
- **Suggested revision**: Address the concern above.


### FINDING_32: risk-integration: skills/review/scripts/tally-code-votes.sh emit_kv;implementation_plan Part B
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] VOTER_COUNT now reflects EFFECTIVE_VOTERS; ELIGIBLE_VOTER_COUNT added; plan did not define this KV change. Downstream automation expecting VOTER_COUNT equals number of --voter-files may mis-rank quorum or logging. Update consumers and tally-code-votes.md or preserve prior VOTER_COUNT meaning with a new key for effective count.
- **Suggested revision**: Address the concern above.


### FINDING_33: risk-integration: skills/review/scripts/tally-code-votes.sh:228-249 vs 572-573
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] ELIGIBLE_VOTER_COUNT is not emitted on the ELIGIBLE_VOTERS==0 early exit. Strict KV consumers expecting stable keys fail on main-agent-required runs. Emit ELIGIBLE_VOTER_COUNT (0) alongside VOTER_COUNT on early exit.
- **Suggested revision**: Address the concern above.


### FINDING_34: risk-integration: skills/review/scripts/tally-code-votes.sh:572-573 skills/review/scripts/tally-code-votes.md:58-69
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] VOTER_COUNT semantics changed to effective quorum; sibling markdown still documents old contract and quorum story. Readers of tally-code-votes.md or parsers assuming VOTER_COUNT equals number of voter files misinterpret degraded runs after parse-rate failures. Update tally-code-votes.md stdout table and threshold section for VOTER_COUNT ELIGIBLE_VOTER_COUNT and parse-rate-adjusted quorum.
- **Suggested revision**: Address the concern above.


