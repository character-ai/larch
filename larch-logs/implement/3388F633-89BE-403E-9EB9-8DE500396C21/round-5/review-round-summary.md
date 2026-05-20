# Review Round 5

- Mode: `diff`
- Accepted findings: 15
- Rejected findings: 3
- Exonerated findings: 3
- Neutral findings: 0

## Accepted Findings

### FINDING_10: **correctness**, [`scripts/verify-run-log-completeness.sh:80`](scripts/verify-run-log-completeness.sh): `MANIFEST_STATUS` is derived with `awk -F'"' '/"status"[[:space:]]*:/ { print $4; exit }'`, which breaks on pretty-printed JSON, reordered keys where `"status"` is not on the first matching line the way `awk` expects, escaped quotes inside the value, or non-standard quoting. **`[ "$MANIFEST_STATUS" = "done" ]`** in [`scripts/verify-run-log-completeness.sh:64-65`](scripts/verify-run-log-completeness.sh) then mis-infers `step9a1`. **Suggested fix:** parse with `python3 -c` / `jq` like `manifest_pr_number`, or reuse the same JSON reader for both fields; extend tests with a real multi-line `manifest.json` fixture.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`scripts/verify-run-log-completeness.sh:80`](scripts/verify-run-log-completeness.sh): `MANIFEST_STATUS` is derived with `awk -F'"' '/"status"[[:space:]]*:/ { print $4; exit }'`, which breaks on pretty-printed JSON, reordered keys where `"status"` is not on the first matching line the way `awk` expects, escaped quotes inside the value, or non-standard quoting. **`[ "$MANIFEST_STATUS" = "done" ]`** in [`scripts/verify-run-log-completeness.sh:64-65`](scripts/verify-run-log-completeness.sh) then mis-infers `step9a1`. **Suggested fix:** parse with `python3 -c` / `jq` like `manifest_pr_number`, or reuse the same JSON reader for both fields; extend tests with a real multi-line `manifest.json` fixture.
- **Suggested revision**: Address the concern above.


### FINDING_2: **[correctness]** [scripts/ship-pr.md:101-102](scripts/ship-pr.md): The “Log Refresh” paragraph still says `scripts/refresh-run-logs.sh` re-renders and commits only `token-report` and `timing-report` before each push. The branch’s [scripts/refresh-run-logs.sh:84-98](scripts/refresh-run-logs.sh) also re-captures `session-transcript` (with `--defer-commit true`) before the same `larch-log.sh commit`. **Suggested fix:** Extend that sentence (and any downstream bullets that enumerate batches) to include `session-transcript` so ship-pr docs match runtime behavior.
- **Reviewer**: dyn-commit-handoff-output.txt
- **Concern**: - **[correctness]** [scripts/ship-pr.md:101-102](scripts/ship-pr.md): The “Log Refresh” paragraph still says `scripts/refresh-run-logs.sh` re-renders and commits only `token-report` and `timing-report` before each push. The branch’s [scripts/refresh-run-logs.sh:84-98](scripts/refresh-run-logs.sh) also re-captures `session-transcript` (with `--defer-commit true`) before the same `larch-log.sh commit`. **Suggested fix:** Extend that sentence (and any downstream bullets that enumerate batches) to include `session-transcript` so ship-pr docs match runtime behavior.
- **Suggested revision**: Address the concern above.


### FINDING_20: architecture: skills/implement/SKILL.md:1703 vs skills/implement/SKILL.md:1658-1666
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 7a prose mandates append-tool-failure capture for token/timing/write/commit failures and forbids bare `\|\| true`, but the adjacent Bash still uses bare `\|\| true` on token-report/timing-report and token/timing larch-log writes. This PR tightens the documented contract (adds flush-execution-issues explicitly) without changing those lines, widening the doc↔script gap; failed token/timing renders can still vanish silently aside from optional tmp logs. Either add the documented capture/append pattern for those commands or narrow the prose to match the intentional best-effort behavior.
- **Suggested revision**: Address the concern above.


### FINDING_21: code-quality: docs/run-logs-required-files.tsv:1-15 + scripts/verify-run-log-completeness.sh:28-63
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Manifest omits oos-issues (and only gates step9a1 on run-statistics) while SKILL Step 9a.1 lists oos-issues as a batch. A committed run dir could lack oos-issues.ndjson yet still print OK once step9a1 is considered reached. Add oos-issues.ndjson (and align token/timing refresh rows if required) to the TSV and tests, or document that oos-issues is intentionally optional and adjust SKILL wording.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/verify-run-log-completeness.sh:71-72
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] manifest status parsed with fragile awk. Reformatted manifest.json can mis-detect status=done and skew step9a1 reachability. Parse manifest.json with python3 for status (and pr_number) or constrain supported manifest shapes in docs.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/verify-run-log-completeness.sh:80
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] `MANIFEST_STATUS` is derived via fragile awk field splitting on manifest.json. JSON formatting changes break the awk extraction so step9a1 reachability mis-fires and the verifier reports false MISSING or skips required rows. Parse status with jq or Python like manifest_pr_number().
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/verify-run-log-completeness.sh:80
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] awk-based manifest status parse manifest.json format changes could mis-infer phase reachability Parse status with python3 json like manifest_pr_number
- **Suggested revision**: Address the concern above.


### FINDING_28: risk-integration: scripts/test-verify-run-log-completeness.sh:71
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] `assert_manifest_matches_batch_table \|\| true` swallows non-zero exit from the manifest↔batch-table alignment guard. Slug/extension drift between docs/run-logs-required-files.tsv and scripts/larch-log-batches.sh ships green while the verifier’s assumptions are wrong; regressions hide until runtime consumers break. Remove `\|\| true` and fail the harness when alignment fails; or structure the function to exit the script directly on mismatch.
- **Suggested revision**: Address the concern above.


### FINDING_29: security: scripts/capture-session-transcript.sh:177-212
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Unredacted subprocess stderr is embedded into execution-issue warning text that can be committed in larch-logs. Git or helper stderr may include credential-bearing URLs or token-shaped material; truncating to 300 chars still leaks partial secrets into pushed run logs. Pipe stderr snippets through redact-secrets.sh (and/or omit detail from committed warnings).
- **Suggested revision**: Address the concern above.


### FINDING_4: **[correctness]** [skills/implement/SKILL.md:1703](skills/implement/SKILL.md): The Step 7a prose says `capture-session-transcript.sh` “emits the machine status on stdout” and that callers must use “the status line plus the post-transcript `flush-execution-issues.sh` refresh” as the contract. [scripts/refresh-run-logs.sh:87-98](scripts/refresh-run-logs.sh) intentionally redirects capture stdout to `/dev/null`, so for that caller there is no observable status line—only the execution-issues append (and flush when the checkpoint gate passes) remains. **Suggested fix:** Qualify the contract: stdout is for prompt-side Step 7a; refresh mode relies on execution-issues (and must keep the post-transcript flush + commit ordering).
- **Reviewer**: dyn-commit-handoff-output.txt
- **Concern**: - **[correctness]** [skills/implement/SKILL.md:1703](skills/implement/SKILL.md): The Step 7a prose says `capture-session-transcript.sh` “emits the machine status on stdout” and that callers must use “the status line plus the post-transcript `flush-execution-issues.sh` refresh” as the contract. [scripts/refresh-run-logs.sh:87-98](scripts/refresh-run-logs.sh) intentionally redirects capture stdout to `/dev/null`, so for that caller there is no observable status line—only the execution-issues append (and flush when the checkpoint gate passes) remains. **Suggested fix:** Qualify the contract: stdout is for prompt-side Step 7a; refresh mode relies on execution-issues (and must keep the post-transcript flush + commit ordering).
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness**, [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) / editor discipline: rows must be **tab-separated**; the reader uses `IFS=' '` in [`scripts/verify-run-log-completeness.sh:85`](scripts/verify-run-log-completeness.sh). Space-aligned TSV edits would mis-bind `relative_path` / `condition` and can **skip** requirements silently. **Suggested fix:** document in [`scripts/verify-run-log-completeness.md`](scripts/verify-run-log-completeness.md) or add a CI lint that rejects non-tab TSV data lines.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) / editor discipline: rows must be **tab-separated**; the reader uses `IFS='	'` in [`scripts/verify-run-log-completeness.sh:85`](scripts/verify-run-log-completeness.sh). Space-aligned TSV edits would mis-bind `relative_path` / `condition` and can **skip** requirements silently. **Suggested fix:** document in [`scripts/verify-run-log-completeness.md`](scripts/verify-run-log-completeness.md) or add a CI lint that rejects non-tab TSV data lines.
- **Suggested revision**: Address the concern above.


### FINDING_6: **correctness**, [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) vs [`scripts/verify-run-log-completeness.sh:55-58`](scripts/verify-run-log-completeness.sh): reachability for `step8` treats **`final-summary.md`** as proof the step was reached, but the TSV has **no** `final-summary.md` row, so the checker can never report that file as **MISSING** even when other logic implies a complete post–Step-8 tree should have it. **Suggested fix:** add a `final-summary.md` row with an appropriate `condition` / batch metadata aligned with [`docs/run-logs.md`](docs/run-logs.md), or drop `final-summary` from reachability if it is intentionally optional.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`docs/run-logs-required-files.tsv`](docs/run-logs-required-files.tsv) vs [`scripts/verify-run-log-completeness.sh:55-58`](scripts/verify-run-log-completeness.sh): reachability for `step8` treats **`final-summary.md`** as proof the step was reached, but the TSV has **no** `final-summary.md` row, so the checker can never report that file as **MISSING** even when other logic implies a complete post–Step-8 tree should have it. **Suggested fix:** add a `final-summary.md` row with an appropriate `condition` / batch metadata aligned with [`docs/run-logs.md`](docs/run-logs.md), or drop `final-summary` from reachability if it is intentionally optional.
- **Suggested revision**: Address the concern above.


### FINDING_7: **correctness**, [`scripts/test-verify-run-log-completeness.sh:146-158`](scripts/test-verify-run-log-completeness.sh): Test 9’s tree omits **`session-transcript.jsonl`** (among other Step-7a files) while asserting only **`version-bump-reasoning.md`** and **`run-statistics.md`** appear under `MISSING=`. That does not fully pin the cascading reachability the scout described (a regression that dropped `session-transcript.jsonl` from `MISSING` could still satisfy the two substring asserts if other strings accidentally matched). **Suggested fix:** add `assert_contains` for `session-transcript.jsonl` (and any other mandatory omissions for that fixture).
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`scripts/test-verify-run-log-completeness.sh:146-158`](scripts/test-verify-run-log-completeness.sh): Test 9’s tree omits **`session-transcript.jsonl`** (among other Step-7a files) while asserting only **`version-bump-reasoning.md`** and **`run-statistics.md`** appear under `MISSING=`. That does not fully pin the cascading reachability the scout described (a regression that dropped `session-transcript.jsonl` from `MISSING` could still satisfy the two substring asserts if other strings accidentally matched). **Suggested fix:** add `assert_contains` for `session-transcript.jsonl` (and any other mandatory omissions for that fixture).
- **Suggested revision**: Address the concern above.


### FINDING_8: **correctness**, [`scripts/verify-run-log-completeness.sh:16-31`](scripts/verify-run-log-completeness.sh): `manifest_pr_number()` only prints when `pr_number` is a JSON **int** (`if isinstance(value, int): print(value)`). A string value (e.g. `"pr_number":"123"`) prints nothing, so `MANIFEST_PR_NUMBER` stays empty, `[ -n "$MANIFEST_PR_NUMBER" ]` in `step8` / `step9a1` never fires from the manifest alone, and later-phase requirements keyed off PR can be skipped while still emitting **OK**. **Suggested fix:** treat non-null `str` (and optionally `bool`) the same as `int` for display/truth tests, or use `json.load` + explicit `value not in (None, "", 0)` semantics; add a harness case with string `pr_number`.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`scripts/verify-run-log-completeness.sh:16-31`](scripts/verify-run-log-completeness.sh): `manifest_pr_number()` only prints when `pr_number` is a JSON **int** (`if isinstance(value, int): print(value)`). A string value (e.g. `"pr_number":"123"`) prints nothing, so `MANIFEST_PR_NUMBER` stays empty, `[ -n "$MANIFEST_PR_NUMBER" ]` in `step8` / `step9a1` never fires from the manifest alone, and later-phase requirements keyed off PR can be skipped while still emitting **OK**. **Suggested fix:** treat non-null `str` (and optionally `bool`) the same as `int` for display/truth tests, or use `json.load` + explicit `value not in (None, "", 0)` semantics; add a harness case with string `pr_number`.
- **Suggested revision**: Address the concern above.


### FINDING_9: **correctness**, [`scripts/verify-run-log-completeness.sh:61-65`](scripts/verify-run-log-completeness.sh) vs [`docs/run-logs-required-files.tsv:15`](docs/run-logs-required-files.tsv): `step9a1` includes `has_file oos-issues.ndjson`, but the manifest lists no `oos-issues.ndjson` path, so that branch only affects reachability inference and **never** drives a missing-file report for OOS logs. **Suggested fix:** add an `oos-issues.ndjson` row if that artifact is part of the committed contract, or remove the dead `has_file` arm.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`scripts/verify-run-log-completeness.sh:61-65`](scripts/verify-run-log-completeness.sh) vs [`docs/run-logs-required-files.tsv:15`](docs/run-logs-required-files.tsv): `step9a1` includes `has_file oos-issues.ndjson`, but the manifest lists no `oos-issues.ndjson` path, so that branch only affects reachability inference and **never** drives a missing-file report for OOS logs. **Suggested fix:** add an `oos-issues.ndjson` row if that artifact is part of the committed contract, or remove the dead `has_file` arm.
- **Suggested revision**: Address the concern above.


