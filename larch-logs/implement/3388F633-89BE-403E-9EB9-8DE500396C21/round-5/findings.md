### FINDING_1: **Nit** `code-quality` `scripts/larch-log.md:88-91`, `scripts/larch-log-batches.md:16-18`, `scripts/ship-pr.sh:1590-1592` still describe `session-transcript` as a Step 18 capture/commit path, but this branch moves capture to Step 7a and removes the Step 18 call. Update those references so the canonical batch docs and postmerge comment match the new lifecycle.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `scripts/larch-log.md:88-91`, `scripts/larch-log-batches.md:16-18`, `scripts/ship-pr.sh:1590-1592` still describe `session-transcript` as a Step 18 capture/commit path, but this branch moves capture to Step 7a and removes the Step 18 call. Update those references so the canonical batch docs and postmerge comment match the new lifecycle.
- **Suggested revision**: Address the concern above.

### FINDING_2: **[correctness]** [scripts/ship-pr.md:101-102](scripts/ship-pr.md): The “Log Refresh” paragraph still says `scripts/refresh-run-logs.sh` re-renders and commits only `token-report` and `timing-report` before each push. The branch’s [scripts/refresh-run-logs.sh:84-98](scripts/refresh-run-logs.sh) also re-captures `session-transcript` (with `--defer-commit true`) before the same `larch-log.sh commit`. **Suggested fix:** Extend that sentence (and any downstream bullets that enumerate batches) to include `session-transcript` so ship-pr docs match runtime behavior.
- **Reviewer**: dyn-commit-handoff-output.txt
- **Concern**: - **[correctness]** [scripts/ship-pr.md:101-102](scripts/ship-pr.md): The “Log Refresh” paragraph still says `scripts/refresh-run-logs.sh` re-renders and commits only `token-report` and `timing-report` before each push. The branch’s [scripts/refresh-run-logs.sh:84-98](scripts/refresh-run-logs.sh) also re-captures `session-transcript` (with `--defer-commit true`) before the same `larch-log.sh commit`. **Suggested fix:** Extend that sentence (and any downstream bullets that enumerate batches) to include `session-transcript` so ship-pr docs match runtime behavior.
- **Suggested revision**: Address the concern above.

### FINDING_3: **[correctness]** [scripts/verify-run-log-completeness.sh:48-54](scripts/verify-run-log-completeness.sh): The new `has_file session-transcript.jsonl` disjunct makes `condition_reached step7a` true whenever that file exists, including a degenerate directory that contains `session-transcript.jsonl` but none of the token/timing/execution witnesses. Because `condition_reached step5` ORs into `condition_reached step7a` ([scripts/verify-run-log-completeness.sh:42-46](scripts/verify-run-log-completeness.sh)), that lone file can force Step 5–scoped manifest rows to be evaluated and reported `MISSING` for review artifacts that were never part of that tree. **Suggested fix:** Treat `session-transcript.jsonl` as a dependent artifact (e.g. only count it toward `step7a` when at least one of token-report, timing-report, or execution-issues is also present), or document this strict edge as intentional if hand-corrupted dirs are out of scope.
- **Reviewer**: dyn-commit-handoff-output.txt
- **Concern**: - **[correctness]** [scripts/verify-run-log-completeness.sh:48-54](scripts/verify-run-log-completeness.sh): The new `has_file session-transcript.jsonl` disjunct makes `condition_reached step7a` true whenever that file exists, including a degenerate directory that contains `session-transcript.jsonl` but none of the token/timing/execution witnesses. Because `condition_reached step5` ORs into `condition_reached step7a` ([scripts/verify-run-log-completeness.sh:42-46](scripts/verify-run-log-completeness.sh)), that lone file can force Step 5–scoped manifest rows to be evaluated and reported `MISSING` for review artifacts that were never part of that tree. **Suggested fix:** Treat `session-transcript.jsonl` as a dependent artifact (e.g. only count it toward `step7a` when at least one of token-report, timing-report, or execution-issues is also present), or document this strict edge as intentional if hand-corrupted dirs are out of scope.
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

### FINDING_10: **correctness**, [`scripts/verify-run-log-completeness.sh:80`](scripts/verify-run-log-completeness.sh): `MANIFEST_STATUS` is derived with `awk -F'"' '/"status"[[:space:]]*:/ { print $4; exit }'`, which breaks on pretty-printed JSON, reordered keys where `"status"` is not on the first matching line the way `awk` expects, escaped quotes inside the value, or non-standard quoting. **`[ "$MANIFEST_STATUS" = "done" ]`** in [`scripts/verify-run-log-completeness.sh:64-65`](scripts/verify-run-log-completeness.sh) then mis-infers `step9a1`. **Suggested fix:** parse with `python3 -c` / `jq` like `manifest_pr_number`, or reuse the same JSON reader for both fields; extend tests with a real multi-line `manifest.json` fixture.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness**, [`scripts/verify-run-log-completeness.sh:80`](scripts/verify-run-log-completeness.sh): `MANIFEST_STATUS` is derived with `awk -F'"' '/"status"[[:space:]]*:/ { print $4; exit }'`, which breaks on pretty-printed JSON, reordered keys where `"status"` is not on the first matching line the way `awk` expects, escaped quotes inside the value, or non-standard quoting. **`[ "$MANIFEST_STATUS" = "done" ]`** in [`scripts/verify-run-log-completeness.sh:64-65`](scripts/verify-run-log-completeness.sh) then mis-infers `step9a1`. **Suggested fix:** parse with `python3 -c` / `jq` like `manifest_pr_number`, or reuse the same JSON reader for both fields; extend tests with a real multi-line `manifest.json` fixture.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] **[correctness]** [scripts/refresh-run-logs.sh:111-116](scripts/refresh-run-logs.sh): `larch-log.sh commit` is wrapped with `2>/dev/null || true`, and any non-empty stdout that lacks `^UNCHANGED=true` yields `REFRESH_COMMITTED=true`, including commit failure with empty stdout. This pattern predates the inserted transcript block (per [round-5/diff.txt:757-765](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch5-DmdX7Y/round-5/diff.txt)); the branch adds more content that could be left uncommitted if that path misfires, but the false-success structure itself is not introduced here.
- **Reviewer**: dyn-commit-handoff-output.txt
- **Concern**: - **[correctness]** [scripts/refresh-run-logs.sh:111-116](scripts/refresh-run-logs.sh): `larch-log.sh commit` is wrapped with `2>/dev/null || true`, and any non-empty stdout that lacks `^UNCHANGED=true` yields `REFRESH_COMMITTED=true`, including commit failure with empty stdout. This pattern predates the inserted transcript block (per [round-5/diff.txt:757-765](file:///Users/zhupanov/.cache/larch/sessions/claude-implement-larch5-DmdX7Y/round-5/diff.txt)); the branch adds more content that could be left uncommitted if that path misfires, but the false-success structure itself is not introduced here.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] **[correctness]** [skills/implement/SKILL.md:1698-1700](skills/implement/SKILL.md): Final `larch-log.sh commit` uses a bare `|| true` without the adjacent `append-tool-failure.sh` pattern mandated in the same paragraph for other tools; that tension appears to be pre-existing relative to the transcript relocation (the commit line is unchanged aside from surrounding new steps in the diff chunk).
- **Reviewer**: dyn-commit-handoff-output.txt
- **Concern**: - **[correctness]** [skills/implement/SKILL.md:1698-1700](skills/implement/SKILL.md): Final `larch-log.sh commit` uses a bare `|| true` without the adjacent `append-tool-failure.sh` pattern mandated in the same paragraph for other tools; that tension appears to be pre-existing relative to the transcript relocation (the commit line is unchanged aside from surrounding new steps in the diff chunk).
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] **correctness** (pre-existing product surface, not introduced by this diff’s core transcript move): behavior of [`scripts/capture-session-transcript.sh`](scripts/capture-session-transcript.sh) and Step-7a wiring is outside the manifest-reachability focus requested here.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness** (pre-existing product surface, not introduced by this diff’s core transcript move): behavior of [`scripts/capture-session-transcript.sh`](scripts/capture-session-transcript.sh) and Step-7a wiring is outside the manifest-reachability focus requested here.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] **correctness** (scout item 1 — `set -e`): Disjuncts in `a || b || condition_reached …` are evaluated in a context where a failing intermediate command does **not** trigger `set -e` exit; recursive `condition_reached` returning non-zero inside an `||` chain is likewise safe.
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness** (scout item 1 — `set -e`): Disjuncts in `a || b || condition_reached …` are evaluated in a context where a failing intermediate command does **not** trigger `set -e` exit; recursive `condition_reached` returning non-zero inside an `||` chain is likewise safe.
- **Suggested revision**: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] **correctness** (scout item 1 — verified): `condition_reached` is a **linear forward** graph `step5 → step7a → step8 → step9a1` with **no** backward calls from `step9a1`; there is **no** cycle. When `MANIFEST_PR_NUMBER` is set, `step8` short-circuits on [`scripts/verify-run-log-completeness.sh:58`](scripts/verify-run-log-completeness.sh) and does **not** call `condition_reached step9a1`, so the scout’s “step9a1 pulls in step8 pulls in step7a…” backward cascade does **not** match this implementation (each `condition` arm is evaluated independently per TSV row).
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness** (scout item 1 — verified): `condition_reached` is a **linear forward** graph `step5 → step7a → step8 → step9a1` with **no** backward calls from `step9a1`; there is **no** cycle. When `MANIFEST_PR_NUMBER` is set, `step8` short-circuits on [`scripts/verify-run-log-completeness.sh:58`](scripts/verify-run-log-completeness.sh) and does **not** call `condition_reached step9a1`, so the scout’s “step9a1 pulls in step8 pulls in step7a…” backward cascade does **not** match this implementation (each `condition` arm is evaluated independently per TSV row).
- **Suggested revision**: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] **correctness** (scout item 4 — verified): `manifest_pr_number` swallowing parse errors with `sys.exit(0)` yields an empty string, **`[ -n "$MANIFEST_PR_NUMBER" ]` is false**, so PR-based reachability is **not** spuriously enabled on corrupt/empty JSON (it under-triggers rather than over-triggers).
- **Reviewer**: dyn-manifest-reachability-output.txt
- **Concern**: - **correctness** (scout item 4 — verified): `manifest_pr_number` swallowing parse errors with `sys.exit(0)` yields an empty string, **`[ -n "$MANIFEST_PR_NUMBER" ]` is false**, so PR-based reachability is **not** spuriously enabled on corrupt/empty JSON (it under-triggers rather than over-triggers).
- **Suggested revision**: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] risk-integration: scripts/refresh-run-logs.sh:111-117
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Commit outcome inferred only from UNCHANGED grep while commit uses `\|\| true`. Commit failure can be misclassified as committed refresh; pre-existing relative to this diff’s hunk focus. Fail-closed parsing of larch-log commit exit/status if you touch this path later.
- **Suggested revision**: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] security: scripts/capture-session-transcript.sh:125-134
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Session transcript recovery uses newest jsonl under ~/.claude/projects; wrong file could be chosen. Mis-attribution of transcript content across sessions if discovery misfires; not introduced by this diff (basename-only change in warnings). None for this review; separate hardening if desired.
- **Suggested revision**: Address the concern above.

### FINDING_19: architecture: skills/implement/SKILL.md (Step 7a pre-bump flush);scripts/capture-session-transcript.sh
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Step 7a wiring and helper flags diverge from the plan’s verbatim bash snippet (defer-commit split flush vs inline capture before commit). Line-by-line plan audits report a mismatch even though the merged design intent (transcript in the same log flush commit as other Step 7a batches, CI retry refresh) appears met. Update the implementation plan archive / add a short SKILL comment tying the defer-commit plus post-transcript flush to the single larch-log commit contract, or align prose to the plan snippet if the team wants strict traceability.
- **Suggested revision**: Address the concern above.

### FINDING_20: architecture: skills/implement/SKILL.md:1703 vs skills/implement/SKILL.md:1658-1666
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 7a prose mandates append-tool-failure capture for token/timing/write/commit failures and forbids bare `\|\| true`, but the adjacent Bash still uses bare `\|\| true` on token-report/timing-report and token/timing larch-log writes. This PR tightens the documented contract (adds flush-execution-issues explicitly) without changing those lines, widening the doc↔script gap; failed token/timing renders can still vanish silently aside from optional tmp logs. Either add the documented capture/append pattern for those commands or narrow the prose to match the intentional best-effort behavior.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: docs/run-logs-required-files.tsv:1-15 + scripts/verify-run-log-completeness.sh:28-63
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Manifest omits oos-issues (and only gates step9a1 on run-statistics) while SKILL Step 9a.1 lists oos-issues as a batch. A committed run dir could lack oos-issues.ndjson yet still print OK once step9a1 is considered reached. Add oos-issues.ndjson (and align token/timing refresh rows if required) to the TSV and tests, or document that oos-issues is intentionally optional and adjust SKILL wording.
- **Suggested revision**: Address the concern above.

### FINDING_22: code-quality: scripts/capture-session-transcript.sh:405-451 + skills/implement/SKILL.md:1670-1695
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Extra flags and double flush vs minimal plan. Higher cognitive load for future edits; risk of refresh vs Step 7a drift. Add a one-line cross-reference in SKILL linking Step 7a and refresh-run-logs defer-commit contract.
- **Suggested revision**: Address the concern above.

### FINDING_23: code-quality: scripts/test-verify-run-log-completeness.sh:336-337
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] assert_manifest_matches_batch_table || true is easy to misread. A future edit might remove || true or fail() and silently skip batch alignment checks. Comment why || true is required under set -e next to that call.
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

### FINDING_27: risk-integration: SECURITY.md:143-144
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] SECURITY documents refresh MERGE_RESULT short-circuit. If state file semantics drift, doc could contradict runtime. Re-verify against refresh-run-logs.sh whenever MERGE_RESULT handling changes.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: scripts/test-verify-run-log-completeness.sh:71
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] `assert_manifest_matches_batch_table \|\| true` swallows non-zero exit from the manifest↔batch-table alignment guard. Slug/extension drift between docs/run-logs-required-files.tsv and scripts/larch-log-batches.sh ships green while the verifier’s assumptions are wrong; regressions hide until runtime consumers break. Remove `\|\| true` and fail the harness when alignment fails; or structure the function to exit the script directly on mismatch.
- **Suggested revision**: Address the concern above.

### FINDING_29: security: scripts/capture-session-transcript.sh:177-212
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Unredacted subprocess stderr is embedded into execution-issue warning text that can be committed in larch-logs. Git or helper stderr may include credential-bearing URLs or token-shaped material; truncating to 300 chars still leaks partial secrets into pushed run logs. Pipe stderr snippets through redact-secrets.sh (and/or omit detail from committed warnings).
- **Suggested revision**: Address the concern above.

### FINDING_30: security: scripts/capture-session-transcript.sh:48-50 scripts/capture-session-transcript.sh:79-88
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] --warning-step-label is unconstrained and interpolated into markdown execution-issue entries. A malicious or buggy caller can inject markdown structure into execution-issues.md via the step label, undermining audit readability and section integrity. Allowlist characters for WARNING_STEP_LABEL or sanitize before append-execution-issue.
- **Suggested revision**: Address the concern above.

