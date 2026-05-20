### FINDING_1: **Important** (`correctness`) — `skills/review/scripts/tally-code-votes.sh:219-287`: parse-rate-failed voters are subtracted from `EFFECTIVE_VOTERS`, but their files are still included in the vote-count loop. A failed voter with mostly narrative output but one parseable `FINDING_1: YES` can still tip a result: with failed cursor `YES`, healthy codex `YES`, healthy claude `NO`, the code counts `YES=2 NO=1` against `EFFECTIVE_VOTERS=2` and accepts, even though the two effective voters are split and should be neutral. Build and iterate an effective voter-file list that excludes files with parse-rate diag files, or keep the original denominator if those votes remain counted.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** (`correctness`) — `skills/review/scripts/tally-code-votes.sh:219-287`: parse-rate-failed voters are subtracted from `EFFECTIVE_VOTERS`, but their files are still included in the vote-count loop. A failed voter with mostly narrative output but one parseable `FINDING_1: YES` can still tip a result: with failed cursor `YES`, healthy codex `YES`, healthy claude `NO`, the code counts `YES=2 NO=1` against `EFFECTIVE_VOTERS=2` and accepts, even though the two effective voters are split and should be neutral. Build and iterate an effective voter-file list that excludes files with parse-rate diag files, or keep the original denominator if those votes remain counted.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** (`risk-integration`) — `skills/review/scripts/tally-code-votes.sh:225-287`: when every voter has a parse-rate diag, `EFFECTIVE_VOTERS` becomes `0`, but the zero-judge path still checks `ELIGIBLE_VOTERS == 0`. That means tally emits `TALLY_STATUS=ok` and rejects every finding instead of triggering the existing main-agent adjudication path, even while the banner says `main-agent-required`. Base the main-agent-required branch on `EFFECTIVE_VOTERS == 0` after parse-rate degradation, and ensure `review-core.sh` receives `TALLY_STATUS=main-agent-vote-required`.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** (`risk-integration`) — `skills/review/scripts/tally-code-votes.sh:225-287`: when every voter has a parse-rate diag, `EFFECTIVE_VOTERS` becomes `0`, but the zero-judge path still checks `ELIGIBLE_VOTERS == 0`. That means tally emits `TALLY_STATUS=ok` and rejects every finding instead of triggering the existing main-agent adjudication path, even while the banner says `main-agent-required`. Base the main-agent-required branch on `EFFECTIVE_VOTERS == 0` after parse-rate degradation, and ensure `review-core.sh` receives `TALLY_STATUS=main-agent-vote-required`.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Nit** (`risk-integration`) — `skills/review/scripts/tally-code-votes.md:58`: the stdout contract still says `VOTER_COUNT` is the raw voter-file count, but the code now emits effective voter count and adds undocumented `ELIGIBLE_VOTER_COUNT`. Update the docs so downstream consumers know which count is raw vs degraded.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Nit** (`risk-integration`) — `skills/review/scripts/tally-code-votes.md:58`: the stdout contract still says `VOTER_COUNT` is the raw voter-file count, but the code now emits effective voter count and adds undocumented `ELIGIBLE_VOTER_COUNT`. Update the docs so downstream consumers know which count is raw vs degraded.
- **Suggested revision**: Address the concern above.

### FINDING_4: [OUT_OF_SCOPE] architecture: larch-logs/implement/B8D22146-1621-47E8-A91F-CD1687D69E8C/*
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Committed implement session metadata under larch-logs. Intentional per repo run-log policy. No action.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: scripts/dispatch-with-waterfall.sh:163-167
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Waterfall Claude prompt launches omit --role voter. File unchanged by this branch; ROLE may be inert for prompt-file path. Consider --role voter for clarity if subprocess ever keys off role.
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: larch-logs/implement/B8D22146-1621-47E8-A91F-CD1687D69E8C/manifest.json:16
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Implement run manifest status remains in-progress in committed log. Minor metadata inconsistency in shipped run log only. Accept as run-log policy or refresh manifest when flushing logs if desired.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: larch-logs/implement/B8D22146-1621-47E8-A91F-CD1687D69E8C/
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Committed implement run metadata ships with the branch. Intentional per repo run-log policy; not a functional regression in voter/tally logic. N/A (policy-driven).
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] security: scripts/dispatch-code-voters.sh:52-53,71-72
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] User-controlled ballot path is embedded in voter prompts and concatenated into retry prompts; same class of trust as before the change. Pre-existing prompt injection / path-leak surface relative to caller-supplied --ballot-file. No change required for this branch scope; harden separately if threat model demands.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/dispatch-code-voters.sh launch_voter_retry;implementation_plan Part A voter-2/3
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Retries use launch-review.sh --tool instead of launch-cursor-review.sh and single-slot dispatch-with-waterfall.sh as specified. Waterfall or direct-launcher behavior may differ from what #2336 parity assumed; plan traceability fails. Use the planned launchers or amend the plan with evidence of equivalence to reviewer path.
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

### FINDING_13: code-quality: scripts/dispatch-code-voters.sh (retry path vs plan text)
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan named fixed diag basename and specific relaunchers; implementation uses output-adjacent diag paths and launch-review.sh for externals. None if dispatch and tally agree; confusion only for plan-as-spec readers. Reconcile plan or add a short comment in dispatch tying behavior to #2336 parity intent.
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/dispatch-code-voters.sh:153-162
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] append-tool-failure --tool names launch-${voter_tool}-review.sh for parse-rate warnings even when codex/cursor retries use launch-review.sh. Misleading execution-issues attribution during triage. Use the actual launcher invoked or a neutral tool label for parse-rate warnings.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/dispatch-code-voters.sh:226-241
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Retry success path leaves *-parse-retry.txt.launcher-stderr orphan. Extra clutter under REVIEW_TMPDIR. rm retry sidecars (e.g. *.launcher-stderr) after successful mv.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/dispatch-code-voters.sh:99-105 skills/review/scripts/tally-code-votes.sh:198-204
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicate voter_parse_rate_diag_path helper in dispatch and tally. Future edits to diag naming risk updating one site and not the other. Source a single shared helper or small sourced library function.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/review/scripts/tally-code-votes.md
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] ELIGIBLE_VOTER_COUNT not listed in emitted-keys table. Consumers discover the key only via code or tests. Add row documenting ELIGIBLE_VOTER_COUNT and revised VOTER_COUNT semantics.
- **Suggested revision**: Address the concern above.

### FINDING_18: correctness: scripts/dispatch-code-voters.sh (check_and_retry_voter_parse_rate / launch_voter_retry)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Successful voter parse-rate retry can leave orphan *-parse-retry.txt.launcher-stderr sidecars. REVIEW_TMPDIR clutter across repeated reviews. rm -f retry-specific sidecars after successful promotion.
- **Suggested revision**: Address the concern above.

### FINDING_19: correctness: scripts/dispatch-code-voters.sh:213-248
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Failed or rejected parse-rate retries can leave *-parse-retry.txt (and launcher stderr sidecars) in REVIEW_TMPDIR. Stale retry artifacts accumulate and can be mistaken for real voter outputs or pollute review tmp hygiene. Always rm -f retry_output and its sidecars when the retry is not promoted to the canonical voter_path.
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

### FINDING_23: correctness: skills/review/scripts/tally-code-votes.sh (live scoreboard awk per diff)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Second sub(/\.txt$/, "", label) after stripping -output.txt can over-normalize unusual live basenames. Rare label mismatch between live and dead scoreboard rows. Restrict normalization to the planned -output.txt strip only.
- **Suggested revision**: Address the concern above.

### FINDING_24: correctness: skills/review/scripts/tally-code-votes.sh live scoreboard awk;implementation_plan Part C
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Extra sub(/\.txt$/, "", label) beyond stripping -output.txt only. Unusual reviewer keys ending in .txt could render shorter labels than dead-slot normalization. Match renderer normalization exactly to the plan’s single sub or document the broader rule.
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: scripts/dispatch-code-voters.sh:178-200
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Codex/Cursor parse retries use launch-review.sh instead of dispatch-with-waterfall.sh. If waterfall and launch-review diverge in the future, retries may not mirror first-pass behavior. Comment invariant or share one launcher path for waterfall and retry.
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: scripts/dispatch-code-voters.sh:370-380
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] DEGRADED_PANEL_WARNING uses non-empty output count only; ignores parse-rate NOT_SUBSTANTIVE that tally treats as reduced quorum. Three slots can all be non-empty narrative while tally downgrades to 2-judge (or 1-judge) rules; dispatch emits no degraded warning, so upstream automation relying on dispatch KVs disagrees with tally banners and vote outcomes. Align dispatch effective-judge accounting with tally (parse-rate diag or PARSE_RATE_STATUS) or emit a separate KV that matches EFFECTIVE_VOTERS semantics.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: scripts/dispatch-code-voters.sh:370-380 vs skills/review/scripts/tally-code-votes.sh:219-287
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Dispatch DEGRADED_PANEL_WARNING uses non-empty outputs only; tally uses EFFECTIVE_VOTERS including parse-rate diag slots. Dispatch KV says full panel while tally degrades tier for the same run. Align effective-judge counting with parse-rate status or document intentional divergence.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/review/scripts/tally-code-votes.md:37-69
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] tally-code-votes.md still defines VOTER_COUNT as voter file count and describes quorum as ELIGIBLE file count without parse-rate exceptions. Consumers of the doc or of VOTER_COUNT alone believe the panel is still a 3-file quorum while classify_result uses EFFECTIVE_VOTERS; acceptance tier and NEUT semantics diverge from documentation. Update markdown: document VOTER_COUNT vs ELIGIBLE_VOTER_COUNT; revise threshold section for parse-rate-degraded quorum.
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/review/scripts/tally-code-votes.md:58-69
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Documentation still describes VOTER_COUNT as raw voter file count and quorum based only on eligible files; code uses EFFECTIVE_VOTERS for classify_result and banners and emits ELIGIBLE_VOTER_COUNT. Operator follows docs and misconfigures automation or misreads quorum vs parse-rate degradation. Update tally-code-votes.md table and Threshold section for effective vs eligible and new key.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: skills/review/scripts/tally-code-votes.md:58-69 and skills/review/scripts/tally-code-votes.sh:287,572-573
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] VOTER_COUNT and quorum documentation still describe raw eligible voter files while classify_result and VOTER_COUNT KV use EFFECTIVE_VOTERS. External scripts or humans following tally-code-votes.md may treat VOTER_COUNT as file count and mis-rank panel strength or compare inconsistent numbers to other pipeline stages. Update tally-code-votes.md to document EFFECTIVE vs ELIGIBLE semantics and new ELIGIBLE_VOTER_COUNT; align threshold prose with classify_result’s actual quorum input.
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/review/scripts/tally-code-votes.md:58-70
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] tally-code-votes.md still documents VOTER_COUNT as raw voter file count and describes quorum without parse-rate effective voters. Readers apply wrong acceptance rules after parse-rate degradation. Update stdout table (ELIGIBLE_VOTER_COUNT + VOTER_COUNT semantics) and threshold narrative for EFFECTIVE_VOTERS / parse-rate diag.
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

### FINDING_35: risk-integration: skills/review/scripts/test-tally-code-votes.md; skills/review/scripts/tally-code-votes.md:77
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Harness docs not updated for new tally test cases. Future contributors miss documented coverage expectations. Extend harness documentation bullets.
- **Suggested revision**: Address the concern above.

### FINDING_36: security: skills/review/scripts/tally-code-votes.sh:219-224
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Parse-rate failure is inferred solely from existence of a sibling *-parse-rate-diag.txt next to each voter file path. A writer with the same filesystem access as vote outputs can force EFFECTIVE_VOTERS down without plausible structured votes, biasing outcomes toward neutral tiers. Document trust boundary for REVIEW_TMPDIR or bind diag detection to verified dispatch output (manifest/KV) before counting a slot as parse-failed.
- **Suggested revision**: Address the concern above.

