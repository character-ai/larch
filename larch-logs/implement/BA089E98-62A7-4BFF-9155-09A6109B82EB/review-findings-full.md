### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` — `scripts/collect-agent-results.sh:1027-1035`: when a slot was downgraded by `--structured-reviewer-validation`, the retry only runs the non-structured substantive validator before restoring `STATUS=OK`. Concrete failing scenario: a structured reviewer fails section 3.6 because it did not produce the required sidecar; its retry emits prose that passes `validate-research-output.sh`, and section 3.7 marks it OK without re-running `--structured-reviewer-mode --write-structured`, leaving downstream consumers without the structured sidecar they requested. Fix by preserving why the slot became `NOT_SUBSTANTIVE` and re-running structured validation for entries downgraded by section 3.6 before changing them back to OK.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 4. **Important** `correctness` — `scripts/collect-agent-results.sh:1027-1035`: when a slot was downgraded by `--structured-reviewer-validation`, the retry only runs the non-structured substantive validator before restoring `STATUS=OK`. Concrete failing scenario: a structured reviewer fails section 3.6 because it did not produce the required sidecar; its retry emits prose that passes `validate-research-output.sh`, and section 3.7 marks it OK without re-running `--structured-reviewer-mode --write-structured`, leaving downstream consumers without the structured sidecar they requested. Fix by preserving why the slot became `NOT_SUBSTANTIVE` and re-running structured validation for entries downgraded by section 3.6 before changing them back to OK.
- **Suggested revision**: Address the concern above.

### FINDING_10: panel [code-review/accepted]

## architecture: skills/review/scripts/review-core.md (missing)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan listed review-core.md update; file unchanged vs merge-base Orchestrator docs omit new threshold/tally wiring. Update review-core.md for collector-results file, threshold KV, and tally flags.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## code-quality: scripts/test-collect-agent-results.sh:2067-2080

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] C_NSR comment contradicts chmod +x on fake launcher Misleading test documentation Fix comment to describe executable stub launcher
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## code-quality: scripts/test-collect-agent-results.sh:266-271

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Comment says non-executable fake launcher but chmod +x is applied Confuses future maintainers about why retry is skipped Update comment to describe the real skip mechanism
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## code-quality: scripts/test-collect-agent-results.sh:283-290

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] C_NSR always records ok whether retry sentinel exists Harness cannot detect broken NS retry dispatch Stub launcher that deterministically writes sentinels and assert expectations
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** `correctness` — `scripts/collect-agent-results.sh:914` and `scripts/collect-agent-results.sh:959`: the NOT_SUBSTANTIVE retry looks for `${REVIEWER_FILE%.txt}.meta`, but the launcher and existing collector retry contract write/read `${OUTPUT}.meta` (`foo-output.txt.meta`). Concrete failing scenario: `cursor-specialist-structure-output.txt` is downgraded to `STATUS=NOT_SUBSTANTIVE`; `launch-review.sh` wrote `cursor-specialist-structure-output.txt.meta`, but section 3.7 checks `cursor-specialist-structure-output.meta`, silently skips the retry, and the feature’s retry-once behavior never runs. Fix by using `"${REVIEWER_FILE}.meta"` / `"${ORIG_OUTPUT}.meta"` and make `scripts/test-collect-agent-results.sh:258-290` require an actual retry artifact or successful retry result.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` — `scripts/collect-agent-results.sh:914` and `scripts/collect-agent-results.sh:959`: the NOT_SUBSTANTIVE retry looks for `${REVIEWER_FILE%.txt}.meta`, but the launcher and existing collector retry contract write/read `${OUTPUT}.meta` (`foo-output.txt.meta`). Concrete failing scenario: `cursor-specialist-structure-output.txt` is downgraded to `STATUS=NOT_SUBSTANTIVE`; `launch-review.sh` wrote `cursor-specialist-structure-output.txt.meta`, but section 3.7 checks `cursor-specialist-structure-output.meta`, silently skips the retry, and the feature’s retry-once behavior never runs. Fix by using `"${REVIEWER_FILE}.meta"` / `"${ORIG_OUTPUT}.meta"` and make `scripts/test-collect-agent-results.sh:258-290` require an actual retry artifact or successful retry result.
- **Suggested revision**: Address the concern above.

### FINDING_20: panel [code-review/accepted]

## code-quality: skills/review/scripts/tally-code-votes.sh:16-17

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] usage omits new CLI flags. Operators rely on --help for wiring hints. Add --collector-results-file and --not-substantive-count to usage text.
- **Suggested revision**: Address the concern above.

### FINDING_3: panel [code-review/accepted]

## **Important** `risk-integration` — `skills/review/scripts/review-core.sh:327-373`: degraded NOT_SUBSTANTIVE panels are still invisible when there are zero findings, because `review-core.sh` computes `NOT_SUBSTANTIVE_SLOTS` and then exits on `FINDINGS_COUNT=0` before calling `tally-code-votes.sh`. Concrete failing scenario: one reviewer is `STATUS=NOT_SUBSTANTIVE`, six slots return `NO_ISSUES_FOUND`, threshold passes, `FINDINGS_COUNT=0`, and no `voting-tally.md` scoreboard or degraded banner is produced. Fix the zero-findings path to emit a tally/degraded artifact from `collector-results.env` and `panel-manifest.ndjson`, or move dead-slot scoreboard generation before the early return.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 3. **Important** `risk-integration` — `skills/review/scripts/review-core.sh:327-373`: degraded NOT_SUBSTANTIVE panels are still invisible when there are zero findings, because `review-core.sh` computes `NOT_SUBSTANTIVE_SLOTS` and then exits on `FINDINGS_COUNT=0` before calling `tally-code-votes.sh`. Concrete failing scenario: one reviewer is `STATUS=NOT_SUBSTANTIVE`, six slots return `NO_ISSUES_FOUND`, threshold passes, `FINDINGS_COUNT=0`, and no `voting-tally.md` scoreboard or degraded banner is produced. Fix the zero-findings path to emit a tally/degraded artifact from `collector-results.env` and `panel-manifest.ndjson`, or move dead-slot scoreboard generation before the early return.
- **Suggested revision**: Address the concern above.

### FINDING_37: panel [code-review/accepted]

## correctness: skills/review/scripts/tally-code-votes.sh:434-437

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Dead-slot rows default STATUS=NOT_SUBSTANTIVE when collector has no basename entry Manifest slot with no collector row mislabeled as narrative-only NOT_SUBSTANTIVE Use a distinct default (e.g. UNKNOWN) unless STATUS is parsed from collector results
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Important** `security` — `scripts/collect-agent-results.sh:936-1000`: the new NOT_SUBSTANTIVE retry executes `OUTER_LAUNCHER` from the sidecar after only basic file checks, bypassing the canonical `launch-review.sh` and expected prompt-sidecar validation already used by the empty-output retry path. Concrete scenario: a crafted retry sidecar for a narrative-only output sets `OUTER_LAUNCHER=/tmp/runner`, `OUTER_LAUNCHER_PROMPT_FILE=/tmp/prompt`, `OUTER_LAUNCHER_WORKDIR=/tmp`, `TOOL=cursor`, and `TIMEOUT=1`; the collector reaches line 995 and runs that executable. Reuse the existing section-3 outer-launcher validation before spawning: canonical `launch-review.sh`, expected `${ORIG_OUTPUT}.prompt`, no `..`, regular non-symlink files, valid risk.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `security` — `scripts/collect-agent-results.sh:936-1000`: the new NOT_SUBSTANTIVE retry executes `OUTER_LAUNCHER` from the sidecar after only basic file checks, bypassing the canonical `launch-review.sh` and expected prompt-sidecar validation already used by the empty-output retry path. Concrete scenario: a crafted retry sidecar for a narrative-only output sets `OUTER_LAUNCHER=/tmp/runner`, `OUTER_LAUNCHER_PROMPT_FILE=/tmp/prompt`, `OUTER_LAUNCHER_WORKDIR=/tmp`, `TOOL=cursor`, and `TIMEOUT=1`; the collector reaches line 995 and runs that executable. Reuse the existing section-3 outer-launcher validation before spawning: canonical `launch-review.sh`, expected `${ORIG_OUTPUT}.prompt`, no `..`, regular non-symlink files, valid risk.
- **Suggested revision**: Address the concern above.

### FINDING_45: panel [code-review/accepted]

## risk-integration: scripts/test-collect-agent-results.sh:258-290,scripts/collect-agent-results.sh:1009-1011

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] C_NS_RETRY waits full outer timeout and does not assert retry outcomes Fake launcher yields up to ~120s wait per run; no assertion on retry output, validator, or RESULTS line Stub launcher that writes sentinel quickly; assert RESULTS / paths; keep WAIT_FOR_REVIEWERS_POLL_INTERVAL low with a small TIMEOUT meta
- **Suggested revision**: Address the concern above.

### FINDING_48: panel [code-review/accepted]

## risk-integration: skills/review/scripts/tally-code-votes.sh:351-377 vs 382-437

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Dead-slot rows replace numeric Score with STATUS=… string Downstream parsers expecting numeric last column break or mis-tally Add Status column or keep Score numeric and move annotation elsewhere
- **Suggested revision**: Address the concern above.

### FINDING_9: panel [code-review/accepted]

## architecture: scripts/collect-agent-results.sh:892-1041

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] NOT_SUBSTANTIVE retry omits CMD_JSON/run-external-agent path promised in Fix A Reviewer is NOT_SUBSTANTIVE with valid CMD_JSON but no OUTER_LAUNCHER in .meta; no retry runs while plan/spec expect one Implement the plan’s CMD_JSON branch or narrow docs/callers so the contract matches shipped behavior
- **Suggested revision**: Address the concern above.

