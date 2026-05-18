### FINDING_1: **Important** `correctness` — `scripts/collect-agent-results.sh:1027-1035`: when a slot was downgraded by `--structured-reviewer-validation`, the retry only runs the non-structured substantive validator before restoring `STATUS=OK`. Concrete failing scenario: a structured reviewer fails section 3.6 because it did not produce the required sidecar; its retry emits prose that passes `validate-research-output.sh`, and section 3.7 marks it OK without re-running `--structured-reviewer-mode --write-structured`, leaving downstream consumers without the structured sidecar they requested. Fix by preserving why the slot became `NOT_SUBSTANTIVE` and re-running structured validation for entries downgraded by section 3.6 before changing them back to OK.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Important** `correctness` — `scripts/collect-agent-results.sh:1027-1035`: when a slot was downgraded by `--structured-reviewer-validation`, the retry only runs the non-structured substantive validator before restoring `STATUS=OK`. Concrete failing scenario: a structured reviewer fails section 3.6 because it did not produce the required sidecar; its retry emits prose that passes `validate-research-output.sh`, and section 3.7 marks it OK without re-running `--structured-reviewer-mode --write-structured`, leaving downstream consumers without the structured sidecar they requested. Fix by preserving why the slot became `NOT_SUBSTANTIVE` and re-running structured validation for entries downgraded by section 3.6 before changing them back to OK.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Important** `correctness` — `scripts/collect-agent-results.sh:914` and `scripts/collect-agent-results.sh:959`: the NOT_SUBSTANTIVE retry looks for `${REVIEWER_FILE%.txt}.meta`, but the launcher and existing collector retry contract write/read `${OUTPUT}.meta` (`foo-output.txt.meta`). Concrete failing scenario: `cursor-specialist-structure-output.txt` is downgraded to `STATUS=NOT_SUBSTANTIVE`; `launch-review.sh` wrote `cursor-specialist-structure-output.txt.meta`, but section 3.7 checks `cursor-specialist-structure-output.meta`, silently skips the retry, and the feature’s retry-once behavior never runs. Fix by using `"${REVIEWER_FILE}.meta"` / `"${ORIG_OUTPUT}.meta"` and make `scripts/test-collect-agent-results.sh:258-290` require an actual retry artifact or successful retry result.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/collect-agent-results.sh:914` and `scripts/collect-agent-results.sh:959`: the NOT_SUBSTANTIVE retry looks for `${REVIEWER_FILE%.txt}.meta`, but the launcher and existing collector retry contract write/read `${OUTPUT}.meta` (`foo-output.txt.meta`). Concrete failing scenario: `cursor-specialist-structure-output.txt` is downgraded to `STATUS=NOT_SUBSTANTIVE`; `launch-review.sh` wrote `cursor-specialist-structure-output.txt.meta`, but section 3.7 checks `cursor-specialist-structure-output.meta`, silently skips the retry, and the feature’s retry-once behavior never runs. Fix by using `"${REVIEWER_FILE}.meta"` / `"${ORIG_OUTPUT}.meta"` and make `scripts/test-collect-agent-results.sh:258-290` require an actual retry artifact or successful retry result.
- **Suggested revision**: Address the concern above.

### FINDING_3: **Important** `risk-integration` — `skills/review/scripts/review-core.sh:327-373`: degraded NOT_SUBSTANTIVE panels are still invisible when there are zero findings, because `review-core.sh` computes `NOT_SUBSTANTIVE_SLOTS` and then exits on `FINDINGS_COUNT=0` before calling `tally-code-votes.sh`. Concrete failing scenario: one reviewer is `STATUS=NOT_SUBSTANTIVE`, six slots return `NO_ISSUES_FOUND`, threshold passes, `FINDINGS_COUNT=0`, and no `voting-tally.md` scoreboard or degraded banner is produced. Fix the zero-findings path to emit a tally/degraded artifact from `collector-results.env` and `panel-manifest.ndjson`, or move dead-slot scoreboard generation before the early return.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` — `skills/review/scripts/review-core.sh:327-373`: degraded NOT_SUBSTANTIVE panels are still invisible when there are zero findings, because `review-core.sh` computes `NOT_SUBSTANTIVE_SLOTS` and then exits on `FINDINGS_COUNT=0` before calling `tally-code-votes.sh`. Concrete failing scenario: one reviewer is `STATUS=NOT_SUBSTANTIVE`, six slots return `NO_ISSUES_FOUND`, threshold passes, `FINDINGS_COUNT=0`, and no `voting-tally.md` scoreboard or degraded banner is produced. Fix the zero-findings path to emit a tally/degraded artifact from `collector-results.env` and `panel-manifest.ndjson`, or move dead-slot scoreboard generation before the early return.
- **Suggested revision**: Address the concern above.

### FINDING_4: **Important** `security` — `scripts/collect-agent-results.sh:936-1000`: the new NOT_SUBSTANTIVE retry executes `OUTER_LAUNCHER` from the sidecar after only basic file checks, bypassing the canonical `launch-review.sh` and expected prompt-sidecar validation already used by the empty-output retry path. Concrete scenario: a crafted retry sidecar for a narrative-only output sets `OUTER_LAUNCHER=/tmp/runner`, `OUTER_LAUNCHER_PROMPT_FILE=/tmp/prompt`, `OUTER_LAUNCHER_WORKDIR=/tmp`, `TOOL=cursor`, and `TIMEOUT=1`; the collector reaches line 995 and runs that executable. Reuse the existing section-3 outer-launcher validation before spawning: canonical `launch-review.sh`, expected `${ORIG_OUTPUT}.prompt`, no `..`, regular non-symlink files, valid risk.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` — `scripts/collect-agent-results.sh:936-1000`: the new NOT_SUBSTANTIVE retry executes `OUTER_LAUNCHER` from the sidecar after only basic file checks, bypassing the canonical `launch-review.sh` and expected prompt-sidecar validation already used by the empty-output retry path. Concrete scenario: a crafted retry sidecar for a narrative-only output sets `OUTER_LAUNCHER=/tmp/runner`, `OUTER_LAUNCHER_PROMPT_FILE=/tmp/prompt`, `OUTER_LAUNCHER_WORKDIR=/tmp`, `TOOL=cursor`, and `TIMEOUT=1`; the collector reaches line 995 and runs that executable. Reuse the existing section-3 outer-launcher validation before spawning: canonical `launch-review.sh`, expected `${ORIG_OUTPUT}.prompt`, no `..`, regular non-symlink files, valid risk.
- **Suggested revision**: Address the concern above.

### FINDING_5: [OUT_OF_SCOPE] architecture: Branch diff composition
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] larch-logs plus agnix/github-remote changes intermixed with #2323 panel fixes PR story and bisect span multiple unrelated themes Accept per policy or split PRs for clarity
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-collect-agent-results.sh:237-246
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] C_IT1 fixture is nonsensical prose on main Pre-existing on merge-base; not introduced by this branch. Fix in a separate hygiene PR on main.
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] risk-integration: .claude-plugin/plugin.json;CHANGELOG.md;.agnix.toml;scripts/github-remote-repo.sh;larch-logs/implement/B4EC9C2D-9849-4DE1-BC6C-B52A4D731F70/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Branch mixes #2323 behavior with unrelated agnix/regex/version/log artifacts Harder review and rollback attribution Split unrelated changes into separate commits/PRs when feasible
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] risk-integration: scripts/github-remote-repo.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Unrelated regex tweak in same branch Not part of #2323 plan surface. Relegate to separate commit/PR or revert if accidental.
- **Suggested revision**: Address the concern above.

### FINDING_9: architecture: scripts/collect-agent-results.sh:892-1041
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] NOT_SUBSTANTIVE retry omits CMD_JSON/run-external-agent path promised in Fix A Reviewer is NOT_SUBSTANTIVE with valid CMD_JSON but no OUTER_LAUNCHER in .meta; no retry runs while plan/spec expect one Implement the plan’s CMD_JSON branch or narrow docs/callers so the contract matches shipped behavior
- **Suggested revision**: Address the concern above.

### FINDING_10: architecture: skills/review/scripts/review-core.md (missing)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan listed review-core.md update; file unchanged vs merge-base Orchestrator docs omit new threshold/tally wiring. Update review-core.md for collector-results file, threshold KV, and tally flags.
- **Suggested revision**: Address the concern above.

### FINDING_11: code-quality: implementation_plan:Fix-A vs scripts/collect-agent-results.sh:892-1041
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] CMD_JSON/run-external-agent NOT_SUBSTANTIVE retry path omitted vs plan NOT_SUBSTANTIVE slots launched only with CMD_JSON metadata never receive the promised stronger-prompt retry Add inner retry branch mirroring section 3 or update plan and callers if outer-launcher-only is intentional
- **Suggested revision**: Address the concern above.

### FINDING_12: code-quality: scripts/collect-agent-results.sh:902-978
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated META parsing loops Extra complexity and drift risk when keys change Extract a single meta reader helper
- **Suggested revision**: Address the concern above.

### FINDING_13: code-quality: scripts/test-collect-agent-results.sh:2067-2080
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] C_NSR comment contradicts chmod +x on fake launcher Misleading test documentation Fix comment to describe executable stub launcher
- **Suggested revision**: Address the concern above.

### FINDING_14: code-quality: scripts/test-collect-agent-results.sh:237-39
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] C_IT1 fixture contains unrelated LLM conversational lines. Confuses maintainers about what the test proves. Use minimal neutral prose around the fenced TSV.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/test-collect-agent-results.sh:266-271
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment says non-executable fake launcher but chmod +x is applied Confuses future maintainers about why retry is skipped Update comment to describe the real skip mechanism
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/test-collect-agent-results.sh:266-271
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Comment says non-executable fake launcher but chmod +x applied Misleading maintenance story for future edits Fix comment or use a genuinely non-executable path to match intent
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: scripts/test-collect-agent-results.sh:266-271
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Comment says non-executable fake launcher but chmod +x makes it executable Confuses future maintainers about test intent Fix comment or chmod to match stated intent
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: scripts/test-collect-agent-results.sh:283-290
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] C_NSR always records ok whether retry sentinel exists Harness cannot detect broken NS retry dispatch Stub launcher that deterministically writes sentinels and assert expectations
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: skills/review/scripts/review-core.md
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Plan called for review-core.md tally wiring docs; file not updated Operators reading review-core.md miss new collector-results and banner inputs Update review-core.md to describe collector-results and NOT_SUBSTANTIVE banner flags
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: skills/review/scripts/tally-code-votes.sh:16-17
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] usage omits new CLI flags. Operators rely on --help for wiring hints. Add --collector-results-file and --not-substantive-count to usage text.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: skills/review/scripts/tally-code-votes.sh:16-17
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] usage() omits --collector-results-file and --not-substantive-count Operators see incomplete --help on unknown flags Update usage string to include new optional flags
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: skills/review/scripts/tally-code-votes.sh:16-18
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] usage() omits new tally flags Operators see incomplete --help-style text Update usage() to list --collector-results-file and --not-substantive-count
- **Suggested revision**: Address the concern above.

### FINDING_23: code-quality: skills/review/scripts/tally-code-votes.sh:16-18
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] usage() omits new CLI flags --help output incomplete vs tally-code-votes.md Extend usage string with --collector-results-file and --not-substantive-count
- **Suggested revision**: Address the concern above.

### FINDING_24: code-quality: skills/review/scripts/tally-code-votes.sh:16-18
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] usage() omits new CLI flags --help and misuse paths omit --collector-results-file and --not-substantive-count Extend usage string with the new optional flags
- **Suggested revision**: Address the concern above.

### FINDING_25: code-quality: skills/review/scripts/tally-code-votes.sh:2403
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] usage() omits new CLI flags --help does not list --collector-results-file or --not-substantive-count. Extend usage string to match implemented options.
- **Suggested revision**: Address the concern above.

### FINDING_26: correctness: scripts/collect-agent-results.md scripts/collect-agent-results.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Retry documented as section 3.7 vs plan section 3.6 Numbering mismatch only; structured pass is 3.6. Rename sections in docs/comments to match plan or add explicit cross-reference.
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/collect-agent-results.sh:1790-1941
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Missing CMD_JSON-only NOT_SUBSTANTIVE retry branch planned in Fix A steps 4-5 NOT_SUBSTANTIVE slots with only CMD_JSON meta never get the one-shot stronger-prompt relaunch; behavior diverges from plan. Implement run-external-agent.sh retry path for NOT_SUBSTANTIVE when OUTER_LAUNCHER absent but CMD_JSON valid, mirroring section 3.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/collect-agent-results.sh:857-1035
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] NS retry runs after structured validation and only re-validates substantively With both --substantive-validation and --structured-reviewer-validation a structured-failure NOT_SUBSTANTIVE can become OK after retry without passing structured validation again Reorder passes (retry before 3.6) or re-run structured validator on successful NS retry before marking OK
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/collect-agent-results.sh:857-1041
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] No structured re-validation after NS retry success when structured validation was enabled Plan-review style runs can end OK without required STRUCTURED_SIDECAR for the retried file Re-run section 3.6 on successful retry output or merge structured fields into the updated RESULTS row
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: scripts/collect-agent-results.sh:857-890,1026-1035
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] NS retry promotes to OK using substantive validator only after structured NOT_SUBSTANTIVE Plan-review style collect with --structured-reviewer-validation can leave OK rows without required .tsv/.jsonl sidecar after a “successful” NS retry After OK promotion re-run structured validation (or rerun section 3.6 for that index) before finalizing RESULTS
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: scripts/collect-agent-results.sh:892-1043
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] NOT_SUBSTANTIVE retry implements only OUTER_LAUNCHER relaunch; no CMD_JSON path from plan A CMD_JSON-only .meta after NOT_SUBSTANTIVE never receives the one-shot stronger-prompt retry Add run-external-agent.sh retry branch when OUTER_LAUNCHER missing but CMD_JSON valid (mirror section 3)
- **Suggested revision**: Address the concern above.

### FINDING_32: correctness: scripts/collect-agent-results.sh:914-915,958-959
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Wrong .meta path uses REVIEWER_FILE%.txt.meta instead of OUTPUT_FILE.meta. NOT_SUBSTANTIVE retry never sees run-external-agent sidecars named foo.txt.meta so retries silently no-op for standard .txt reviewer outputs. Use META="${REVIEWER_FILE}.meta" consistent with run-external-agent.sh and section 3 line 500.
- **Suggested revision**: Address the concern above.

### FINDING_33: correctness: scripts/test-collect-agent-results.sh:258-290
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] C_NSR asserts neither success nor failure of retry; comment contradicts chmod +x Test always passes even if retry never runs; weak regression vs plan. Use deterministic stub launcher and assert sentinel or STATUS transition; fix comment.
- **Suggested revision**: Address the concern above.

### FINDING_34: correctness: skills/review/scripts/check-reviewer-failure-threshold.sh:2249 skills/review/scripts/review-core.sh:2277
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan C1 asked for NOT_SUBSTANTIVE_COUNT KV; implementation emits NOT_SUBSTANTIVE_SLOTS External consumers following the plan grep the wrong key name and see no count. Emit NOT_SUBSTANTIVE_COUNT as specified (alias NOT_SUBSTANTIVE_SLOTS if desired).
- **Suggested revision**: Address the concern above.

### FINDING_35: correctness: skills/review/scripts/tally-code-votes.sh:2567
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Dead-slot awk skips dyn- manifest basenames Dynamic manifest slots with no score_rows never appear as dead rows. Include dyn rows or document intentional exclusion vs feature text.
- **Suggested revision**: Address the concern above.

### FINDING_36: correctness: skills/review/scripts/tally-code-votes.sh:427-434
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fragile NDJSON output extraction via awk gsub Manifest formatting changes could mis-parse output paths and mis-label dead vs live slots Parse manifest with jq or a dedicated NDJSON reader consistent with other tooling
- **Suggested revision**: Address the concern above.

### FINDING_37: correctness: skills/review/scripts/tally-code-votes.sh:434-437
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Dead-slot rows default STATUS=NOT_SUBSTANTIVE when collector has no basename entry Manifest slot with no collector row mislabeled as narrative-only NOT_SUBSTANTIVE Use a distinct default (e.g. UNKNOWN) unless STATUS is parsed from collector results
- **Suggested revision**: Address the concern above.

### FINDING_38: correctness: skills/review/scripts/tally-code-votes.sh:434-437
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Dead-slot rows default STATUS=NOT_SUBSTANTIVE without collector evidence Non-narrative absences mis-labeled as narrative-only in voting-tally.md Use UNKNOWN or require collector_status hit before emitting NOT_SUBSTANTIVE
- **Suggested revision**: Address the concern above.

### FINDING_39: correctness: skills/review/scripts/tally-code-votes.sh:434-437
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dead-slot default STATUS=NOT_SUBSTANTIVE when collector lacks that basename Missing or partial collector file mis-labels never-launched or unknown slots as narrative-only Use explicit unknown status or require collector row before emitting dead slot
- **Suggested revision**: Address the concern above.

### FINDING_40: risk-integration: .agnix.toml:26
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Global AS-014 disable removes that agnix rule repo-wide. Future true positives AS-014 would catch outside the bash regex case pass agent-lint until found elsewhere. Drop global disable if github[.]com rewrites alone satisfy agnix or scope disable if agnix supports it.
- **Suggested revision**: Address the concern above.

### FINDING_41: risk-integration: scripts/collect-agent-results.sh:1009-1011
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] NS-retry wait uses || true masking wait fatals Silent loss of wait errors can strand NOT_SUBSTANTIVE despite retriable work Align with documented initial-wait stderr contract or document the divergence
- **Suggested revision**: Address the concern above.

### FINDING_42: risk-integration: scripts/collect-agent-results.sh:892-1035
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] NOT_SUBSTANTIVE retry implements only OUTER_LAUNCHER .meta path; no CMD_JSON / run-external-agent fallback from plan CMD_JSON-only slots stay NOT_SUBSTANTIVE with no retry despite plan promising inner-path retry Add CMD_JSON retry mirroring empty-output retry plus a harness case
- **Suggested revision**: Address the concern above.

### FINDING_43: risk-integration: scripts/collect-agent-results.sh:892-1043
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] No CMD_JSON fallback for NOT_SUBSTANTIVE retry per plan. CMD_JSON-only external slots stay NOT_SUBSTANTIVE without the promised second launch. Mirror section 3 inner CMD_JSON retry for eligible NOT_SUBSTANTIVE rows.
- **Suggested revision**: Address the concern above.

### FINDING_44: risk-integration: scripts/github-remote-repo.sh:1988-1995
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Unrelated regex tweak bundled with #2323 Noise for reviewers bisecting functional changes Revert or split to a separate PR
- **Suggested revision**: Address the concern above.

### FINDING_45: risk-integration: scripts/test-collect-agent-results.sh:258-290,scripts/collect-agent-results.sh:1009-1011
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] C_NS_RETRY waits full outer timeout and does not assert retry outcomes Fake launcher yields up to ~120s wait per run; no assertion on retry output, validator, or RESULTS line Stub launcher that writes sentinel quickly; assert RESULTS / paths; keep WAIT_FOR_REVIEWERS_POLL_INTERVAL low with a small TIMEOUT meta
- **Suggested revision**: Address the concern above.

### FINDING_46: risk-integration: scripts/test-collect-agent-results.sh:266-290
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] C_NSR allows success whether or not -ns-retry.txt.done exists; does not assert validator or OK promotion Retry regressions in wait/launch/validate can slip past CI because the test never fails Stub launcher writing valid retry output and assert STATUS=OK and REVIEWER_FILE=*-ns-retry.txt; add failing-validation case
- **Suggested revision**: Address the concern above.

### FINDING_47: risk-integration: skills/review/scripts/review-core.md (missing)
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Plan listed review-core.md update; file not changed Undocumented threshold-to-tally wiring for NOT_SUBSTANTIVE banner and collector handoff Update review-core.md per plan
- **Suggested revision**: Address the concern above.

### FINDING_48: risk-integration: skills/review/scripts/tally-code-votes.sh:351-377 vs 382-437
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dead-slot rows replace numeric Score with STATUS=… string Downstream parsers expecting numeric last column break or mis-tally Add Status column or keep Score numeric and move annotation elsewhere
- **Suggested revision**: Address the concern above.

### FINDING_49: risk-integration: skills/review/scripts/tally-code-votes.sh:351-377,382-437
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Dead-slot scoreboard rows use non-numeric final column Automated parsers assume column 11 is numeric Score and mis-handle appended STATUS rows Use a separate STATUS column or keep Score numeric and move status into an extra column
- **Suggested revision**: Address the concern above.

### FINDING_50: risk-integration: skills/review/scripts/tally-code-votes.sh:382-437
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Dead-slot STATUS defaults to NOT_SUBSTANTIVE when collector map misses Slot never launched or FAILED without a mapped basename shows as narrative-only; operators chase the wrong failure mode Require explicit STATUS from collector or emit UNKNOWN/NEVER_LAUNCHED; align basename normalization with collector keys
- **Suggested revision**: Address the concern above.

### FINDING_51: security: scripts/collect-agent-results.sh:936-1001
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] NOT_SUBSTANTIVE retry exec trusts .meta OUTER_LAUNCHER paths without section-3 canonical checks. A non-canonical or hostile .meta can cause exec of an arbitrary executable under the collector UID while empty-output retry would reject the same metadata. Reuse section 3 outer-launcher validation (.. guards canonical launch-review.sh path expected .prompt sidecar non-symlink rules) before spawning 3.7.
- **Suggested revision**: Address the concern above.

