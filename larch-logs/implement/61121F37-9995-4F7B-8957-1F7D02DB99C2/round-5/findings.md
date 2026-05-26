### FINDING_1: code-quality: scripts/test-render-cost-line-callsites.sh:40
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Callsite lint greps a Step 18 Bash pattern that no longer exists in implement SKILL.md. Running make lint or scripts/test-render-cost-line-callsites.sh fails on this branch (verified). Update the grep pin to match the current _wfr_emit_cost/_wfr_new_cost touch guard or replace substring lint with a harness that executes the Step 18 fence.
- **Suggested revision**: Address the concern above.

### FINDING_2: code-quality: skills/implement/scripts/write-final-report.sh:390-430
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Parallel self-composed fallback bodies duplicate render-run-summary schema in implement and design scripts. Future renderer schema edits can leave one fallback path stale while tests still pass on the happy path. Add a shared ordered-bullet contract test or a tiny shared fallback helper despite FINDING_3 deferral.
- **Suggested revision**: Address the concern above.

### FINDING_3: code-quality: skills/implement/SKILL.md:1808-1828
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 18 cost re-emit and sentinel rules live in orchestrator Bash+prose and are only partially pinned by tests. Agents may skip the cost-changed emit path; lint does not catch SKILL/test drift (see callsite failure). Consolidate behavior in write-final-report.sh flags or add an integration harness for the full Step 18 fence.
- **Suggested revision**: Address the concern above.

### FINDING_4: correctness: skills/design/scripts/render-final-summary.sh:388-408
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] preserved_cost_line awk rewrite is fragile if cost text contains special characters. Rare formatting change could corrupt final-summary.md on post-phase render failure. Use safer line replacement or preserve cost via a dedicated renderer flag instead of awk -v injection.
- **Suggested revision**: Address the concern above.

### FINDING_5: code-quality: skills/implement/scripts/test-write-final-report.sh:372-385
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 18 conditional --print-stdout logic is triplicated across SKILL callsite lint and harness. Editors update SKILL but forget harness/lint copies. Extract one shell helper used by tests (and optionally sourced from docs).
- **Suggested revision**: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] code-quality: scripts/test-render-cost-line-callsites.sh:35-50
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] SKILL.md substring lints are brittle to whitespace and wording edits. Unrelated doc edits break CI without functional regression. Prefer structural tests or fenced-block extraction over long grep literals.
- **Suggested revision**: Address the concern above.

### FINDING_7: correctness: scripts/test-render-cost-line-callsites.sh:40-43
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Stale grep pins for Step 18 sentinel and cost-emit prose no longer match skills/implement/SKILL.md after round-4 edits. bash scripts/test-render-cost-line-callsites.sh exits 1 at the Step 18 sentinel grep; make lint fails on this target. Update greps to match _wfr_emit_cost / _wfr_new_cost and current Step 18 orchestrator prose at skills/implement/SKILL.md:1817-1828.
- **Suggested revision**: Address the concern above.

### FINDING_8: correctness: skills/design/scripts/render-final-summary.sh:384-409
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] preserved_cost_line is restored only on render failure; successful post render with --cost-unavailable overwrites a pre-publish usable cost. Pre-publish writes real breakdown; post-publish token-report fails or is all-zero; post invoke_render succeeds with N/A; user loses per-agent costs in final-summary.md and chat. After successful post render, if preserved_cost_line is set and new cost is N/A, splice preserved line; or skip overwrite when pre file has usable cost.
- **Suggested revision**: Address the concern above.

### FINDING_9: correctness: skills/implement/SKILL.md:1751-1754
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] .step17-printed is set on script exit 0 plus any Cost line, even if tracking upsert fails after chat print. write-final-report prints via --print-stdout then exits non-zero on upsert; sentinel is set; Step 18 skips --print-stdout and may skip cost re-emit despite refreshed token data. Gate sentinel on full success only, or use a separate marker for chat-print vs comment upsert.
- **Suggested revision**: Address the concern above.

### FINDING_10: correctness: skills/design/scripts/render-final-summary.sh:399-406
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] preserved_cost_line passed to awk -v without escaping. Cost line containing & or backslashes could produce a wrong substituted bullet. Use sed with a safe delimiter or pass the line via a file/ENVIRON instead of awk -v.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/implement/SKILL.md:1760
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] ROOT CAUSE G fix is prose-only; agents may still omit verbatim cost emit. User sees collapsed Bash only; orchestrator never emits plain-text cost line. Out of scope unless a hook enforces emit; NEVER #20 is best-effort.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: skills/design/scripts/render-final-summary.sh:136-151
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] _cost_unavailable triggers on all-zero totals without requiring stderr. Valid zero-token run shows N/A instead of $0.00. Document as intentional or require stderr for unavailable path.
- **Suggested revision**: Address the concern above.

### FINDING_13: risk-integration: scripts/test-render-cost-line-callsites.sh:40
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Grep pin expects Step 18 touch gated on `_wfr_printed=true` plus cost-line grep, but SKILL.md now uses `_wfr_emit_cost` and cost-change detection. Running `make lint` / `test-render-cost-line-callsites` fails even when Step 18 behavior is correct, blocking merge. Update the pin to match current Step 18 bash (grep `_wfr_emit_cost` / refreshed-cost branch or a stable substring from SKILL.md:1828).
- **Suggested revision**: Address the concern above.

### FINDING_14: risk-integration: scripts/test-render-cost-line-callsites.sh:43
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Grep pin for Step 18 orchestrator-text emit prose no longer matches reordered SKILL.md text after round 4. Same harness fails CI on a prose-only SKILL refinement that did not regress runtime behavior. Replace stale literal with grep for substrings present in the current Step 18 emit paragraph at skills/implement/SKILL.md:1828.
- **Suggested revision**: Address the concern above.

### FINDING_15: risk-integration: skills/implement/scripts/test-write-final-report.sh:491-514
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Nine-outcome matrix validates `--print-stdout` only; never asserts `$fixture/summary-final.md`. Chat print and persisted summary could diverge without failing CI, violating plan dual-assertion and design harness parity. Assert the same markers on summary-final.md each iteration; compare summary body in stdout (pre-STATUS lines) to the file.
- **Suggested revision**: Address the concern above.

### FINDING_16: risk-integration: skills/design/scripts/test-render-final-summary.sh:98-106
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Per-agent breakdown happy path checks markers only in final-summary.md, not post-phase stdout. Post-phase chat-print could lose per-agent breakdown while the file still passes, missing acceptance #4 chat-output intent. Grep std_codex for the same five markers or cmp stdout to final-summary.md in that case.
- **Suggested revision**: Address the concern above.

### FINDING_17: risk-integration: skills/implement/scripts/test-write-final-report.sh:7
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] All summary harnesses set LARCH_QUIET_DISABLE=1, leaving FD-3 chat-print paths untested. Quiet-mode routing regression in production would pass CI while chat summaries disappear or misroute. Add one quiet-enabled case per wrapper asserting bytes on FD 3.
- **Suggested revision**: Address the concern above.

### FINDING_18: risk-integration: skills/implement/SKILL.md:1819-1828
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness covers Step 18 cost-line orchestrator emit when sentinel exists but refreshed cost changed. Cost refresh after Step 17 could stop emitting collapse-resistant cost text without test failure. Add harness: sentinel present, differing pre/post cost lines, assert emit conditions or extend callsite pin for the change branch.
- **Suggested revision**: Address the concern above.

### FINDING_19: risk-integration: scripts/test-render-cost-line-callsites.sh:38
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Callsite lint does not verify sentinel check and --print-stdout live in the same Step 18 bash block. Future refactor could split conditional print into another fence without failing lint. Windowed grep/awk inside the Step 18 fence for both patterns.
- **Suggested revision**: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] risk-integration: skills/implement/SKILL.md:1760
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] ROOT CAUSE G orchestrator-text emit is prompt-side only; no shell harness can enforce model behavior. Inherent limitation; not amplified by this diff. Accept prose pins; optional E2E manual verification per plan acceptance #6.
- **Suggested revision**: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] architecture: skills/design/scripts/render-final-summary.sh:1676-1700
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Pre-publish cost preservation on post render failure extends beyond plan’s pure N/A fallback wording. Intentional enhancement with test coverage at test-render-final-summary.sh:118-145. No change required unless policy wants always-N/A on render failure.
- **Suggested revision**: Address the concern above.

### FINDING_22: security: skills/design/scripts/render-final-summary.sh:398-407
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] preserved_cost_line is bash-expanded into awk -v cost_line= Poisoned final-summary.md cost line with shell metacharacters could execute during fallback splice Pass cost line via file or validate against allowed cost-line regex before awk
- **Suggested revision**: Address the concern above.

### FINDING_23: security: skills/implement/SKILL.md:1760-1828
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Orchestrator verbatim cost-line emit trusts any line matching - **Cost**: prefix Poisoned summary-final.md could inject prompt-shaped text into collapse-resistant assistant chat Require structural validation (TOTAL breakdown or N/A) before emit; extend callsite tests
- **Suggested revision**: Address the concern above.

### FINDING_24: security: skills/implement/scripts/write-final-report.sh:443-447
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] wfr-fallback-stage1.log retains unredacted renderer stderr on disk API/auth tokens in token-cost stderr may persist locally until tmpdir cleanup Redact or delete sidecar after append-tool-failure --redact
- **Suggested revision**: Address the concern above.

### FINDING_25: [OUT_OF_SCOPE] security: skills/implement/scripts/write-final-report.sh:536
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] gh upsert ERROR= uses raw err_file without redaction Failed upsert may leak tokens into STATUS/ERROR machine lines on chat or logs Route through redact_gh_error like other gh helpers
- **Suggested revision**: Address the concern above.

### FINDING_26: [OUT_OF_SCOPE] security: scripts/render-run-summary.sh:147-149
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] token-cost stderr echoed to FD2 unredacted Diagnostic stderr may expose secrets to terminal/logs during normal render Redact cost_errf before cat or document as secret-bearing diagnostic only
- **Suggested revision**: Address the concern above.

### FINDING_27: correctness: scripts/test-render-cost-line-callsites.sh:40
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Callsite lint greps for a Step 18 Bash fragment that is not in implement SKILL.md. make lint fails every build though Step 18 conditional print is implemented elsewhere. Update grep to match _wfr_emit_cost / touch .step17-printed block in skills/implement/SKILL.md.
- **Suggested revision**: Address the concern above.

### FINDING_28: correctness: scripts/test-render-cost-line-callsites.sh:46
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 18 grep pins sentinel-touch logic (_wfr_printed && cost-line grep) that is not in implement SKILL.md. test-render-cost-line-callsites.sh exits 1 today (FAIL: Step 18 must gate .step17-printed…), so make lint / acceptance gate 7 fails even though runtime scripts are updated. Update greps to match the shipped _wfr_emit_cost / _wfr_new_cost Step 18 block, or restore SKILL prose the test expects.
- **Suggested revision**: Address the concern above.

### FINDING_29: correctness: scripts/test-render-cost-line-callsites.sh:49
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Step 18 orchestrator cost-line emit grep uses stale prose not present in implement SKILL.md. After fixing line 46, the harness would fail on the Step 18 emit substring; gate 5 prose pins are not fully enforced. Change the grep to the current paragraph at skills/implement/SKILL.md:1828 (sentinel absent OR cost changed).
- **Suggested revision**: Address the concern above.

### FINDING_30: correctness: skills/design/scripts/test-render-final-summary.sh:281-294
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Empty-mode regression uses cancelled-tier-gate without run-params.json instead of plan’s cancelled-title-filter scenario. Fence N/A default is tested, but the plan-named early-cancel path is only partially mirrored. Add a title-filter empty-mode variant or rename the test comment to document equivalence.
- **Suggested revision**: Address the concern above.

### FINDING_31: correctness: Plan acceptance gate 8
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] OOS #2915 acknowledgment comment is required by the plan but not present in the branch. Tracking issue may stay open after merge despite corrupt-JSON fix landing in code. Post the brief closure comment on #2915 when shipping.
- **Suggested revision**: Address the concern above.

### FINDING_32: **correctness** `skills/implement/scripts/write-final-report.sh:249-263` — When `$IMPLEMENT_TMPDIR/execution-issues.md` is missing or empty, `refresh_issue_counts` falls through to `jq -r '.body // empty' "$run_dir/execution-issues.ndjson" | awk …`. NDJSON `body` fragments are bare bullets (no `### Tool Failures` / `### Warnings` headers), so the section-aware awk never sets `sec` and every `- **Step …` line is ignored; `EXEC_N`/`WARN_N` stay 0 even when flushed NDJSON has warning records. Round 4 removed the upfront `grep -c '"category":"Warnings"'` block, so this path is easier to hit on early-bail / empty-md runs than on main. **Suggested fix:** For the NDJSON branch, keep the old category `grep -c` counts when the piped body lacks section headers (detect with `grep -q '^### Warnings$'` on the combined stream), or rebuild per-category bodies with `jq` before awk (e.g. filter by `.category` and wrap with the right `###` header).
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:249-263` — When `$IMPLEMENT_TMPDIR/execution-issues.md` is missing or empty, `refresh_issue_counts` falls through to `jq -r '.body // empty' "$run_dir/execution-issues.ndjson" | awk …`. NDJSON `body` fragments are bare bullets (no `### Tool Failures` / `### Warnings` headers), so the section-aware awk never sets `sec` and every `- **Step …` line is ignored; `EXEC_N`/`WARN_N` stay 0 even when flushed NDJSON has warning records. Round 4 removed the upfront `grep -c '"category":"Warnings"'` block, so this path is easier to hit on early-bail / empty-md runs than on main. **Suggested fix:** For the NDJSON branch, keep the old category `grep -c` counts when the piped body lacks section headers (detect with `grep -q '^### Warnings$'` on the combined stream), or rebuild per-category bodies with `jq` before awk (e.g. filter by `.category` and wrap with the right `###` header).
- **Suggested revision**: Address the concern above.

### FINDING_33: **correctness** `skills/implement/scripts/write-final-report.sh:236-244` — The md-path awk only increments `ex`/`wa` on `/^- \*\*Step /`. Entries under `### External Reviewer Issues` such as `- **findings aggregator**:` (see `larch-logs/design/072C28F7-468B-43C4-9F71-28C635D34463/execution-issues.md:1-3`) never match, so `EXEC_N` in the final summary under-reports external-reviewer failures whenever a non-empty session `execution-issues.md` exists. Main counted NDJSON records via `grep -c '"category":"External Reviewer Issues"'` (and siblings), so this is a behavioral regression for typical runs with a populated md log. **Suggested fix:** Under `sec == 1`, also count bullets matching `/^- \*\*(Step |findings aggregator)/` (or any non-empty `- **…` line in Tool Failures / External Reviewer sections), and add a harness case with an aggregator-only external-reviewer bullet asserting `EXEC_N >= 1`.
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:236-244` — The md-path awk only increments `ex`/`wa` on `/^- \*\*Step /`. Entries under `### External Reviewer Issues` such as `- **findings aggregator**:` (see `larch-logs/design/072C28F7-468B-43C4-9F71-28C635D34463/execution-issues.md:1-3`) never match, so `EXEC_N` in the final summary under-reports external-reviewer failures whenever a non-empty session `execution-issues.md` exists. Main counted NDJSON records via `grep -c '"category":"External Reviewer Issues"'` (and siblings), so this is a behavioral regression for typical runs with a populated md log. **Suggested fix:** Under `sec == 1`, also count bullets matching `/^- \*\*(Step |findings aggregator)/` (or any non-empty `- **…` line in Tool Failures / External Reviewer sections), and add a harness case with an aggregator-only external-reviewer bullet asserting `EXEC_N >= 1`.
- **Suggested revision**: Address the concern above.

### FINDING_34: **correctness** `skills/design/scripts/render-final-summary.sh:398-407` — Post-phase cost preservation passes `preserved_cost_line` into `awk -v cost_line="$preserved_cost_line"`. A cost bullet containing `&`, backslashes, or newlines can break `awk` parsing or word-splitting in the shell assignment (the happy-path line is usually safe, but the mechanism is fragile). **Suggested fix:** Avoid inline `-v` for arbitrary markdown; e.g. write the preserved line to a temp file and use `awk -v cost_file=… 'FNR==NR{cost=$0;next} …'` with `getline`, or use `sed`/`ed` to replace the first `- **Cost**:` line.
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/design/scripts/render-final-summary.sh:398-407` — Post-phase cost preservation passes `preserved_cost_line` into `awk -v cost_line="$preserved_cost_line"`. A cost bullet containing `&`, backslashes, or newlines can break `awk` parsing or word-splitting in the shell assignment (the happy-path line is usually safe, but the mechanism is fragile). **Suggested fix:** Avoid inline `-v` for arbitrary markdown; e.g. write the preserved line to a temp file and use `awk -v cost_file=… 'FNR==NR{cost=$0;next} …'` with `getline`, or use `sed`/`ed` to replace the first `- **Cost**:` line.
- **Suggested revision**: Address the concern above.

### FINDING_35: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/design/scripts/render-final-summary.sh:226-229` — The awk fix from `/^\*\*Step /` to `/^- \*\*Step /` correctly restores warning counting for `append-tool-failure.sh` bullets; external-reviewer bullets without the `Step` prefix were never counted by the old pattern either, so that gap is longstanding, not newly introduced for design.
- **Suggested revision**: Address the concern above.

### FINDING_36: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **code-quality** `skills/design/scripts/render-final-summary.sh:430` — `ups_err="$(mktemp …)"` in the post-phase upsert path is not registered on an `EXIT` trap (pre-existing pattern); only a temp-file leak on abnormal exit.
- **Suggested revision**: Address the concern above.

### FINDING_37: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:432-445` and `skills/design/scripts/render-final-summary.sh:391-394` — `set +e` / `rr=$?` / `set -e` around renderer calls and `${cost_args[@]}` / `${note_args[@]+"${note_args[@]}"}` empty-array handling under `set -u` look sound; `LARCH_QUIET_PID` re-check inside the post-phase `while read` loop is stable because `$$` does not change across iterations.
- **Suggested revision**: Address the concern above.

### FINDING_38: **correctness** `skills/design/scripts/render-final-summary.sh:384-409` — `render_or_fallback` only restores `preserved_cost_line` when `invoke_render` fails or writes an empty file; if the post-publish call succeeds while `_cost_unavailable=true` (common when the second `token-report.sh` pass yields zero buckets or missing JSON), the renderer overwrites `final-summary.md` with `- **Cost**: N/A` and the pre-publish per-agent line is dropped even though it was captured. That breaks the stated “preserve prior usable cost” behavior on the happy-path two-phase `/design` flow (pre had a breakdown, post silently regresses to N/A). **Suggested fix:** After a successful `invoke_render`, if `PHASE=post`, `preserved_cost_line` is non-empty, and the new file’s cost line is N/A (or missing), run the same first-match `awk` substitution used on the failure branch; alternatively treat “usable cost in pre file + N/A in post success body” as a trigger for that substitution.
- **Reviewer**: dyn-fallback-schema-fidelity-output.txt
- **Concern**: - **correctness** `skills/design/scripts/render-final-summary.sh:384-409` — `render_or_fallback` only restores `preserved_cost_line` when `invoke_render` fails or writes an empty file; if the post-publish call succeeds while `_cost_unavailable=true` (common when the second `token-report.sh` pass yields zero buckets or missing JSON), the renderer overwrites `final-summary.md` with `- **Cost**: N/A` and the pre-publish per-agent line is dropped even though it was captured. That breaks the stated “preserve prior usable cost” behavior on the happy-path two-phase `/design` flow (pre had a breakdown, post silently regresses to N/A). **Suggested fix:** After a successful `invoke_render`, if `PHASE=post`, `preserved_cost_line` is non-empty, and the new file’s cost line is N/A (or missing), run the same first-match `awk` substitution used on the failure branch; alternatively treat “usable cost in pre file + N/A in post success body” as a trigger for that substitution.
- **Suggested revision**: Address the concern above.

### FINDING_39: **correctness** `skills/implement/scripts/write-final-report.sh:396`, `skills/design/scripts/render-final-summary.sh:347` — Self-composed fallbacks print `- **Duration**: ${DURATION:-N/A}`, but an empty `DURATION` string is not unset, so the bullet can be blank. `scripts/render-run-summary.sh:108,180,235` uses `na()` so the renderer always emits `N/A` for empty duration. The same `${VAR:-N/A}` pattern affects any field that can be set to `""` by `jq` (duration is the concrete case today). **Suggested fix:** Normalize before compose (e.g. `[ -z "$DURATION" ] && DURATION=N/A`) or mirror `na()` inside `compose_self_fallback` for Mode/Path/Duration (and any other `jq`-sourced display fields).
- **Reviewer**: dyn-fallback-schema-fidelity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:396`, `skills/design/scripts/render-final-summary.sh:347` — Self-composed fallbacks print `- **Duration**: ${DURATION:-N/A}`, but an empty `DURATION` string is not unset, so the bullet can be blank. `scripts/render-run-summary.sh:108,180,235` uses `na()` so the renderer always emits `N/A` for empty duration. The same `${VAR:-N/A}` pattern affects any field that can be set to `""` by `jq` (duration is the concrete case today). **Suggested fix:** Normalize before compose (e.g. `[ -z "$DURATION" ] && DURATION=N/A`) or mirror `na()` inside `compose_self_fallback` for Mode/Path/Duration (and any other `jq`-sourced display fields).
- **Suggested revision**: Address the concern above.

### FINDING_40: [OUT_OF_SCOPE] Outcome glob (`bailed*|stalled|cancelled-*|failed-*`), implement PR omission (`PR_NUMBER` empty/0), design PR/Code-review suppression, bullet ordering (Outcome → Mode → Path → Duration → Cost → …), and sentinel emission in both `compose_self_fallback` implementations match `scripts/render-run-summary.sh:228-251` on manual comparison; implement stage-2 ordering is pinned by `assert_schema_ordered` in `skills/implement/scripts/test-write-final-report.sh:328-342`, but there is no equivalent ordered-schema test for design’s `compose_self_fallback` (only renderer-fail preservation and matrix happy-path checks in `skills/design/scripts/test-render-final-summary.sh`).
- **Reviewer**: dyn-fallback-schema-fidelity-output.txt
- **Concern**: - Outcome glob (`bailed*|stalled|cancelled-*|failed-*`), implement PR omission (`PR_NUMBER` empty/0), design PR/Code-review suppression, bullet ordering (Outcome → Mode → Path → Duration → Cost → …), and sentinel emission in both `compose_self_fallback` implementations match `scripts/render-run-summary.sh:228-251` on manual comparison; implement stage-2 ordering is pinned by `assert_schema_ordered` in `skills/implement/scripts/test-write-final-report.sh:328-342`, but there is no equivalent ordered-schema test for design’s `compose_self_fallback` (only renderer-fail preservation and matrix happy-path checks in `skills/design/scripts/test-render-final-summary.sh`).
- **Suggested revision**: Address the concern above.

### FINDING_41: [OUT_OF_SCOPE] The `awk` cost-line substitution correctly targets only the first `- **Cost**:` line (`!done` guard at `skills/design/scripts/render-final-summary.sh:399-404`); dollar amounts in the preserved line are safe with `print cost_line`. Residual risk is shell/`awk -v` breakage if the cost line ever contains embedded double quotes (not seen in `lib-cost-line-format.sh` output today).
- **Reviewer**: dyn-fallback-schema-fidelity-output.txt
- **Concern**: - The `awk` cost-line substitution correctly targets only the first `- **Cost**:` line (`!done` guard at `skills/design/scripts/render-final-summary.sh:399-404`); dollar amounts in the preserved line are safe with `print cost_line`. Residual risk is shell/`awk -v` breakage if the cost line ever contains embedded double quotes (not seen in `lib-cost-line-format.sh` output today).
- **Suggested revision**: Address the concern above.

### FINDING_42: **correctness** `skills/implement/SKILL.md:1751-1754,1760,1822-1828` — The Step 17 Bash block writes `$IMPLEMENT_TMPDIR/.step17-printed` as soon as `write-final-report.sh --print-stdout` succeeds and `summary-final.md` contains a `- **Cost**:` line, but the collapse-resistant plain-text cost emit is a separate orchestrator step that runs only after that Bash block returns. If the orchestrator skips that emit (model non-compliance), Step 18 sees the sentinel, omits `--print-stdout`, and the Step 18 prose only re-emits the cost line when `--print-stdout` was used or the cost line changed (`skills/implement/SKILL.md:1819-1828`). The user is left with only collapsed Step 17 Bash output and no plain-text cost line—the exact ROOT CAUSE G failure mode this branch targets. The same ordering exists on Step 18 bail/refresh paths where lines 1822-1824 touch the sentinel before the orchestrator emit at 1828. **Suggested fix:** Split concerns into two markers (e.g. `.step17-block-printed` for suppressing duplicate full-block `--print-stdout`, and `.step17-cost-emitted` written only after the orchestrator verbatim cost-line emit), or remove `touch` from the Bash blocks and have the orchestrator write the suppress sentinel only after a successful cost-line emit; ensure Step 18 always performs the plain-text emit when the block was printed but the cost emit marker is absent.
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1751-1754,1760,1822-1828` — The Step 17 Bash block writes `$IMPLEMENT_TMPDIR/.step17-printed` as soon as `write-final-report.sh --print-stdout` succeeds and `summary-final.md` contains a `- **Cost**:` line, but the collapse-resistant plain-text cost emit is a separate orchestrator step that runs only after that Bash block returns. If the orchestrator skips that emit (model non-compliance), Step 18 sees the sentinel, omits `--print-stdout`, and the Step 18 prose only re-emits the cost line when `--print-stdout` was used or the cost line changed (`skills/implement/SKILL.md:1819-1828`). The user is left with only collapsed Step 17 Bash output and no plain-text cost line—the exact ROOT CAUSE G failure mode this branch targets. The same ordering exists on Step 18 bail/refresh paths where lines 1822-1824 touch the sentinel before the orchestrator emit at 1828. **Suggested fix:** Split concerns into two markers (e.g. `.step17-block-printed` for suppressing duplicate full-block `--print-stdout`, and `.step17-cost-emitted` written only after the orchestrator verbatim cost-line emit), or remove `touch` from the Bash blocks and have the orchestrator write the suppress sentinel only after a successful cost-line emit; ensure Step 18 always performs the plain-text emit when the block was printed but the cost emit marker is absent.
- **Suggested revision**: Address the concern above.

### FINDING_43: **correctness** `scripts/test-render-cost-line-callsites.sh:40-43` — The callsite linter still greps for obsolete Step 18 shapes (`if [ "$_wfr_printed" = true ] && grep -Fq -- '- **Cost**:' ...` for sentinel gating, and the old single-condition Step 18 emit sentence) that were replaced in `skills/implement/SKILL.md:1810-1828` by `_wfr_emit_cost`, `_wfr_prev_cost`/`_wfr_new_cost` comparison, and the dual-condition emit prose. Running `bash scripts/test-render-cost-line-callsites.sh` exits 1 on line 40 today, so CI cannot enforce the sentinel/orchestrator contract the branch relies on. **Suggested fix:** Update the greps to pin the current Bash block (`_wfr_emit_cost`, `_wfr_new_cost != "$_wfr_prev_cost"`, and the line-1828 emit prose) so the linter matches the implemented semantics and passes.
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `scripts/test-render-cost-line-callsites.sh:40-43` — The callsite linter still greps for obsolete Step 18 shapes (`if [ "$_wfr_printed" = true ] && grep -Fq -- '- **Cost**:' ...` for sentinel gating, and the old single-condition Step 18 emit sentence) that were replaced in `skills/implement/SKILL.md:1810-1828` by `_wfr_emit_cost`, `_wfr_prev_cost`/`_wfr_new_cost` comparison, and the dual-condition emit prose. Running `bash scripts/test-render-cost-line-callsites.sh` exits 1 on line 40 today, so CI cannot enforce the sentinel/orchestrator contract the branch relies on. **Suggested fix:** Update the greps to pin the current Bash block (`_wfr_emit_cost`, `_wfr_new_cost != "$_wfr_prev_cost"`, and the line-1828 emit prose) so the linter matches the implemented semantics and passes.
- **Suggested revision**: Address the concern above.

### FINDING_44: **correctness** `skills/implement/SKILL.md:1752-1753,73` — The `.step17-printed` sentinel is set whenever `grep -Fq -- '- **Cost**:'` matches, which includes `- **Cost**: N/A` after `--cost-unavailable` paths. That is reasonable for suppressing duplicate full prints, but NEVER #20 (`skills/implement/SKILL.md:73`) tells the orchestrator to touch the same sentinel and emit the cost line without distinguishing N/A from a per-agent breakdown; combined with the ordering bug above, a successful Step 17 render that only has `N/A` still blocks Step 18 recovery of a later real cost if token refresh at Step 18 (`skills/implement/SKILL.md:1807-1817`) would produce a non-N/A line. **Suggested fix:** Gate `.step17-printed` on a cost line that includes the breakdown markers (`💰 TOTAL` / `Claude $`) when suppressing Step 18 re-print, or always allow Step 18 `--print-stdout` when `_wfr_new_cost` differs from `_wfr_prev_cost` even if the sentinel exists (today only the plain-text emit is conditional on change, not the full block).
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1752-1753,73` — The `.step17-printed` sentinel is set whenever `grep -Fq -- '- **Cost**:'` matches, which includes `- **Cost**: N/A` after `--cost-unavailable` paths. That is reasonable for suppressing duplicate full prints, but NEVER #20 (`skills/implement/SKILL.md:73`) tells the orchestrator to touch the same sentinel and emit the cost line without distinguishing N/A from a per-agent breakdown; combined with the ordering bug above, a successful Step 17 render that only has `N/A` still blocks Step 18 recovery of a later real cost if token refresh at Step 18 (`skills/implement/SKILL.md:1807-1817`) would produce a non-N/A line. **Suggested fix:** Gate `.step17-printed` on a cost line that includes the breakdown markers (`💰 TOTAL` / `Claude $`) when suppressing Step 18 re-print, or always allow Step 18 `--print-stdout` when `_wfr_new_cost` differs from `_wfr_prev_cost` even if the sentinel exists (today only the plain-text emit is conditional on change, not the full block).
- **Suggested revision**: Address the concern above.

### FINDING_45: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/test-write-final-report.sh:372-386` — The skip-to-Step-18 harness mirrors only `_wfr_args` / `--print-stdout` suppression; it does not exercise the Step 18 `_wfr_emit_cost` / cost-delta path or orchestrator emit obligations. Worth extending in a follow-up, but not a regression in existing pre-merge behavior.
- **Suggested revision**: Address the concern above.

### FINDING_46: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **risk-integration** `skills/implement/SKILL.md:1760,1828` — Step 17/18 orchestrator emit rules are prose-only; `_wfr_emit_cost` exists only inside Bash and is not visible to the orchestrator on the next turn. Acceptable given larch’s model-attention enforcement model, but it amplifies the sentinel-ordering defect above.
- **Suggested revision**: Address the concern above.

