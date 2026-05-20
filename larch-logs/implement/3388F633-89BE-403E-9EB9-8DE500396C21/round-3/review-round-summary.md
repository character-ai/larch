# Review Round 3

- Mode: `diff`
- Accepted findings: 10
- Rejected findings: 3
- Exonerated findings: 4
- Neutral findings: 1

## Accepted Findings

### FINDING_1: **(correctness)** [`scripts/capture-session-transcript.md:39-40`](scripts/capture-session-transcript.md): The contract states that for every status, including `captured`, the wrapper appends a `Warnings` entry, but [`scripts/capture-session-transcript.sh:84-86`](scripts/capture-session-transcript.sh) contradicts that whenever `REFRESH_MODE=true` and the status is `captured` (the successful `refresh-run-logs.sh` path).
- **Reviewer**: dyn-step-ordering-output.txt
- **Concern**: - **(correctness)** [`scripts/capture-session-transcript.md:39-40`](scripts/capture-session-transcript.md): The contract states that for every status, including `captured`, the wrapper appends a `Warnings` entry, but [`scripts/capture-session-transcript.sh:84-86`](scripts/capture-session-transcript.sh) contradicts that whenever `REFRESH_MODE=true` and the status is `captured` (the successful `refresh-run-logs.sh` path).   **Suggested fix:** Align the contract with the implementation (or vice versa) using the same behavior change or documentation update as above.
- **Suggested revision**: Address the concern above.


### FINDING_15: correctness: scripts/capture-session-transcript.md:33-39
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Contract says `captured` means write+commit succeeded and every status appends Warnings, but `--defer-commit` emits `captured` before commit and refresh mode skips `captured` warnings. Operator or future caller trusts the doc or un-redirected stdout and mis-reads whether `larch-log.sh commit` has run, or expects a Warnings append on refresh success and mis-debugs. Update status definitions and the "every status" paragraph to match defer/refresh behavior (or add a distinct deferred-write status).
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/verify-run-log-completeness.sh:16-19 plus scripts/verify-run-log-completeness.md:221-224
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] manifest_pr_number uses GNU-only awk match(..., m); trailing || true hides parse failure so MANIFEST_PR_NUMBER is always empty on stock awk. Documented pr_number-based later-phase reachability never activates on default awk; inconsistent trees that only signal via manifest pr_number can be misclassified vs the written contract. Replace with portable JSON extraction (e.g. python3) or explicit gawk; add a harness case proving pr_number-only detection once fixed.
- **Suggested revision**: Address the concern above.


### FINDING_2: **(correctness)** [`scripts/capture-session-transcript.sh:84-86`](scripts/capture-session-transcript.sh), [`scripts/refresh-run-logs.sh:89-107`](scripts/refresh-run-logs.sh): With `--refresh-mode true` and `--defer-commit true` (the path `refresh-run-logs.sh` uses after token/timing writes), `append_warning` returns early when the terminal status is `captured`, so no `SESSION_TRANSCRIPT_STATUS=captured` line is appended to `execution-issues.md`. The post-transcript `flush-execution-issues.sh` call therefore cannot persist that success outcome into `execution-issues.ndjson` for the same refresh commit, even though the transcript batch was written and will be picked up by the final `larch-log.sh commit`. This breaks the sequencing expectation from the review brief (warning must reach the committed NDJSON batch alongside the transcript write) and conflicts with the updated narrative in [`docs/run-logs.md:189`](docs/run-logs.md) (“every capture outcome”).
- **Reviewer**: dyn-step-ordering-output.txt
- **Concern**: - **(correctness)** [`scripts/capture-session-transcript.sh:84-86`](scripts/capture-session-transcript.sh), [`scripts/refresh-run-logs.sh:89-107`](scripts/refresh-run-logs.sh): With `--refresh-mode true` and `--defer-commit true` (the path `refresh-run-logs.sh` uses after token/timing writes), `append_warning` returns early when the terminal status is `captured`, so no `SESSION_TRANSCRIPT_STATUS=captured` line is appended to `execution-issues.md`. The post-transcript `flush-execution-issues.sh` call therefore cannot persist that success outcome into `execution-issues.ndjson` for the same refresh commit, even though the transcript batch was written and will be picked up by the final `larch-log.sh commit`. This breaks the sequencing expectation from the review brief (warning must reach the committed NDJSON batch alongside the transcript write) and conflicts with the updated narrative in [`docs/run-logs.md:189`](docs/run-logs.md) (“every capture outcome”).   **Suggested fix:** Drop the `REFRESH_MODE && status=captured` short-circuit, narrow it (for example only skip when `DEFER_COMMIT` is `false`), or explicitly document and test an intentional exception for refresh success and adjust [`docs/run-logs.md:189`](docs/run-logs.md) / callers so the contract matches behavior.
- **Suggested revision**: Address the concern above.


### FINDING_20: risk-integration: scripts/test-capture-session-transcript.sh:887-916
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Default-branch regression no longer asserts repo stays free of copied run logs after failed commit. Partial-copy+broken-commit regression would not be caught by this harness. Re-add a `test ! -e` (or equivalent) check on `larch-logs/implement/<run-id>` in the repo.
- **Suggested revision**: Address the concern above.


### FINDING_3: **Important** `correctness` [docs/run-logs-required-files.tsv:8](<OPERATOR_REPO_PATH>/docs/run-logs-required-files.tsv:8) marks `code-review-tally.json` and `review-findings-full.jsonl` as `always`, but `--design-only` runs stop before Step 5 and can still commit partial logs per the updated docs. Concrete scenario: a valid `--design-only` run with `manifest.json`, `plan-goals-test.md`, and `plan-review-tally.json` will be reported as `MISSING=code-review-tally.json,review-findings-full.jsonl`. Add a Step 5 condition/reachability signal for these rows, and update [scripts/test-verify-run-log-completeness.sh:112](<OPERATOR_REPO_PATH>/scripts/test-verify-run-log-completeness.sh:112) so the pre-Step-7a partial test does not include Step 5 files.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` [docs/run-logs-required-files.tsv:8](<OPERATOR_REPO_PATH>/docs/run-logs-required-files.tsv:8) marks `code-review-tally.json` and `review-findings-full.jsonl` as `always`, but `--design-only` runs stop before Step 5 and can still commit partial logs per the updated docs. Concrete scenario: a valid `--design-only` run with `manifest.json`, `plan-goals-test.md`, and `plan-review-tally.json` will be reported as `MISSING=code-review-tally.json,review-findings-full.jsonl`. Add a Step 5 condition/reachability signal for these rows, and update [scripts/test-verify-run-log-completeness.sh:112](<OPERATOR_REPO_PATH>/scripts/test-verify-run-log-completeness.sh:112) so the pre-Step-7a partial test does not include Step 5 files.
- **Suggested revision**: Address the concern above.


### FINDING_4: **Important** `correctness` [scripts/verify-run-log-completeness.sh:18](<OPERATOR_REPO_PATH>/scripts/verify-run-log-completeness.sh:18) uses `awk match(..., ..., m)`, which is not supported by the BSD `awk` version used on macOS. Concrete scenario: a run dir whose only later-phase signal is `manifest.json` containing `"pr_number": 123` will leave `MANIFEST_PR_NUMBER` empty, so the verifier can emit `OK` instead of requiring Step 8/9 files. Use a portable parser here, for example `sed -nE` for this single numeric field or `jq` with a documented fallback.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` [scripts/verify-run-log-completeness.sh:18](<OPERATOR_REPO_PATH>/scripts/verify-run-log-completeness.sh:18) uses `awk match(..., ..., m)`, which is not supported by the BSD `awk` version used on macOS. Concrete scenario: a run dir whose only later-phase signal is `manifest.json` containing `"pr_number": 123` will leave `MANIFEST_PR_NUMBER` empty, so the verifier can emit `OK` instead of requiring Step 8/9 files. Use a portable parser here, for example `sed -nE` for this single numeric field or `jq` with a documented fallback.
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** [`scripts/test-verify-run-log-completeness.sh:84-99`](scripts/test-verify-run-log-completeness.sh:84-99) — Tests cover “full Step-7a set minus transcript” and “pre-Step-7a with only `always` files,” but not the scout’s intermediate tree (“Step-7a inferred from one artifact, other Step-7a manifest rows still absent”). That boundary is where `condition_reached` and the TSV interact most; adding a fixture with e.g. only `token-report.json` plus the `always` set and asserting the expected `MISSING=` list would lock the intended behavior. Suggested fix: add that fixture and assertions.
- **Reviewer**: dyn-condition-inference-output.txt
- **Concern**: - **correctness** [`scripts/test-verify-run-log-completeness.sh:84-99`](scripts/test-verify-run-log-completeness.sh:84-99) — Tests cover “full Step-7a set minus transcript” and “pre-Step-7a with only `always` files,” but not the scout’s intermediate tree (“Step-7a inferred from one artifact, other Step-7a manifest rows still absent”). That boundary is where `condition_reached` and the TSV interact most; adding a fixture with e.g. only `token-report.json` plus the `always` set and asserting the expected `MISSING=` list would lock the intended behavior. Suggested fix: add that fixture and assertions.
- **Suggested revision**: Address the concern above.


### FINDING_6: **correctness** [`scripts/verify-run-log-completeness.sh:16-20`](scripts/verify-run-log-completeness.sh:16-20) — `manifest_pr_number()` uses gawk’s three-argument `match(..., m)` capture form. Default `awk` on macOS (and other BSD-derived builds) rejects this at parse time; stderr is discarded (`2>/dev/null`), and the `|| true` on the `awk` invocation swallows the failure, so `MANIFEST_PR_NUMBER` is always empty and the `pr_number` bridge in `condition_reached step9a1` / `step8` / `step7a` never actually activates on those platforms. Suggested fix: replace with portable extraction (e.g. `python3 -c` + `json.load`, or `grep`/`sed` without gawk extensions) and avoid silencing parse errors for the extractor.
- **Reviewer**: dyn-condition-inference-output.txt
- **Concern**: - **correctness** [`scripts/verify-run-log-completeness.sh:16-20`](scripts/verify-run-log-completeness.sh:16-20) — `manifest_pr_number()` uses gawk’s three-argument `match(..., m)` capture form. Default `awk` on macOS (and other BSD-derived builds) rejects this at parse time; stderr is discarded (`2>/dev/null`), and the `|| true` on the `awk` invocation swallows the failure, so `MANIFEST_PR_NUMBER` is always empty and the `pr_number` bridge in `condition_reached step9a1` / `step8` / `step7a` never actually activates on those platforms. Suggested fix: replace with portable extraction (e.g. `python3 -c` + `json.load`, or `grep`/`sed` without gawk extensions) and avoid silencing parse errors for the extractor.
- **Suggested revision**: Address the concern above.


### FINDING_7: **correctness** [`scripts/verify-run-log-completeness.sh:26-37`](scripts/verify-run-log-completeness.sh:26-37) + [`docs/run-logs-required-files.tsv:11-15`](docs/run-logs-required-files.tsv:11-15) + [`skills/implement/SKILL.md:1675-1702`](skills/implement/SKILL.md:1675-1702) — `condition_reached step7a` becomes true if any single Step-7a marker file exists (including `token-report.json` alone). The manifest then treats `session-transcript.jsonl` as mandatory whenever Step 7a is “reached.” Step 7a prose documents `capture-session-transcript.sh` as always exiting 0 and not gating the flush on `$?`, so a run can persist earlier Step-7a batches yet never produce a committed `session-transcript.jsonl`. In that situation the verifier reports `MISSING=session-transcript.jsonl` while `/implement` is defined to continue — a strictness mismatch between the new completeness gate and the orchestration contract. Suggested fix: pick one contract (e.g. fail the Step 7a commit path when status is not `captured`, or relax manifest reachability / required set so the checker matches allowed partial success).
- **Reviewer**: dyn-condition-inference-output.txt
- **Concern**: - **correctness** [`scripts/verify-run-log-completeness.sh:26-37`](scripts/verify-run-log-completeness.sh:26-37) + [`docs/run-logs-required-files.tsv:11-15`](docs/run-logs-required-files.tsv:11-15) + [`skills/implement/SKILL.md:1675-1702`](skills/implement/SKILL.md:1675-1702) — `condition_reached step7a` becomes true if any single Step-7a marker file exists (including `token-report.json` alone). The manifest then treats `session-transcript.jsonl` as mandatory whenever Step 7a is “reached.” Step 7a prose documents `capture-session-transcript.sh` as always exiting 0 and not gating the flush on `$?`, so a run can persist earlier Step-7a batches yet never produce a committed `session-transcript.jsonl`. In that situation the verifier reports `MISSING=session-transcript.jsonl` while `/implement` is defined to continue — a strictness mismatch between the new completeness gate and the orchestration contract. Suggested fix: pick one contract (e.g. fail the Step 7a commit path when status is not `captured`, or relax manifest reachability / required set so the checker matches allowed partial success).
- **Suggested revision**: Address the concern above.


