### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` [skills/review/scripts/collect-findings.sh:285](</Users/zhupanov/larch2/skills/review/scripts/collect-findings.sh:285>)  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [skills/review/scripts/collect-findings.sh:285](</Users/zhupanov/larch2/skills/review/scripts/collect-findings.sh:285>)      Claude reviewer outputs that are narrative-only are now silently dropped, but they are not recorded as `STATUS=NOT_SUBSTANTIVE`. `review-core.sh` bases the reviewer failure threshold on `collector-results.env`, and `collect-findings.sh` only populates that file for `EXTERNAL_OUTPUT_FILES`; `CLAUDE_OUTPUT_FILES` go straight through `parse_output`. Concrete scenario: all hard-panel slots waterfall to Claude and return only “Gathering the diff…”-style text; `per_tmp` stays empty, `collector-results.env` stays empty, `check-reviewer-failure-threshold.sh` sees `FAILED_SLOTS=0`, and the round exits `zero-findings` instead of surfacing panel degradation. Add a Claude-path non-substantive record/log entry when a non-sentinel Claude output yields no prose or TSV findings.
- **Suggested revision**: Address the concern above.

### FINDING_2: panel [code-review/accepted]

## **Important** — **correctness** — [`scripts/dispatch-code-voters.sh:78-92`](scripts/dispatch-code-voters.sh): After `launch-claude-review.sh`, the script runs `set -e` (line 78), then the new diagnostic `{ … } > "$_voter1_diag"` block runs **without** `set +e` / `|| true` around the capture redirect. **Concrete scenario:** `${VOTER_1_PATH}.diag` is briefly non-empty and passes `[[ -s … ]]`, then `head -c 200` hits an I/O error, or the redirect to `$_voter1_diag` fails (full disk, permission). Bash exits the whole script before `dispatch-with-waterfall.sh` runs, so Voter 2/3 are never launched and KV emission (`VOTER_*`, `DISPATCH_OK`) never runs — a strictly worse failure mode than “Claude voter failed but waterfall continued.” **Suggested fix:** wrap only the capture block in `set +e` … `set -e`, or run the compound redirect as `… > "$_voter1_diag" || true`, matching the stated intent in the implementation plan that logging must not abort dispatch.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 1. **Important** — **correctness** — [`scripts/dispatch-code-voters.sh:78-92`](scripts/dispatch-code-voters.sh): After `launch-claude-review.sh`, the script runs `set -e` (line 78), then the new diagnostic `{ … } > "$_voter1_diag"` block runs **without** `set +e` / `|| true` around the capture redirect. **Concrete scenario:** `${VOTER_1_PATH}.diag` is briefly non-empty and passes `[[ -s … ]]`, then `head -c 200` hits an I/O error, or the redirect to `$_voter1_diag` fails (full disk, permission). Bash exits the whole script before `dispatch-with-waterfall.sh` runs, so Voter 2/3 are never launched and KV emission (`VOTER_*`, `DISPATCH_OK`) never runs — a strictly worse failure mode than “Claude voter failed but waterfall continued.” **Suggested fix:** wrap only the capture block in `set +e` … `set -e`, or run the compound redirect as `… > "$_voter1_diag" || true`, matching the stated intent in the implementation plan that logging must not abort dispatch.
- **Suggested revision**: Address the concern above.

### FINDING_22: panel [code-review/accepted]

## risk-integration: scripts/dispatch-code-voters.sh:101-109

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] append-tool-failure omits --status-label; default is failed Empty voter output with exit 0 logs as failed (exit 0) Pass --status-label warning when voter1_rc is 0
- **Suggested revision**: Address the concern above.

### FINDING_4: panel [code-review/accepted]

## **Nit** `code-quality` [scripts/test-dispatch-code-voters.sh:51](</Users/zhupanov/larch2/scripts/test-dispatch-code-voters.sh:51>)  

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` [scripts/test-dispatch-code-voters.sh:51](</Users/zhupanov/larch2/scripts/test-dispatch-code-voters.sh:51>)      The new Voter 1 diagnostic logging path is untested. Add a dispatch-code-voters regression case where the Claude voter exits nonzero or writes empty output, then assert `execution-issues.md` contains the `dispatch-code-voters.sh voter1` warning.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## **Nit** — **code-quality** — [`larch-logs/implement/4AC1A0C0-2CC2-49E6-B4D1-BC1960AC5D10/manifest.json:1-20`](larch-logs/implement/4AC1A0C0-2CC2-49E6-B4D1-BC1960AC5D10/manifest.json): The committed manifest shows `"status": "in-progress"`. Per [`docs/run-logs.md`](docs/run-logs.md), committed run logs are normal, but an **in-progress** snapshot can confuse anyone treating `larch-logs/` as the final run record. **Suggested fix:** ensure the implement log commit reflects a terminal manifest state, or omit this batch if it was not meant to ship with the fix.

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: 4. **Nit** — **code-quality** — [`larch-logs/implement/4AC1A0C0-2CC2-49E6-B4D1-BC1960AC5D10/manifest.json:1-20`](larch-logs/implement/4AC1A0C0-2CC2-49E6-B4D1-BC1960AC5D10/manifest.json): The committed manifest shows `"status": "in-progress"`. Per [`docs/run-logs.md`](docs/run-logs.md), committed run logs are normal, but an **in-progress** snapshot can confuse anyone treating `larch-logs/` as the final run record. **Suggested fix:** ensure the implement log commit reflects a terminal manifest state, or omit this batch if it was not meant to ship with the fix.
- **Suggested revision**: Address the concern above.

