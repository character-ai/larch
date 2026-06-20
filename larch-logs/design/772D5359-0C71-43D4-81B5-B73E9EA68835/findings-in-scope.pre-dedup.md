### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: blocking
- **Focus area**: correctness
- **Location**: plan.txt:51-58
- **Concern**: Unclosed ```markdown example fence absorbs the Files to modify/create section. Scenario: In markdown renderers and quick scans, everything after line 51 can appear inside one code block, so `### UPDATED:` file targets may be treated as example text rather than plan steps
- **Proposed resolution**: Close the example fence immediately after `<filtered rejected body>` before the first `### UPDATED:` heading



### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:49-60,91-93
- **Concern**: The planned Step 3 wait rules say print the compact reviewer status table before parsing `.step3-review-result.env`, but the Compact reviewer status table item still says parse that env for round binding then show statuses. Scenario: Strict orchestrators that follow the nested cadence item will still parse `.step3-review-result.env` before building the table, contradicting both wait-rule edits; when `latest-reviewer-status.tsv` is missing the per-round fallback needs `FINAL_ROUND_NUM` / `STEP3_REVIEW_ROUND_NUM` / `ROUNDS_COMPLETED` before choosing `plan-review/round-N/reviewer-status.tsv`, so table-before-env ordering without an explicit round-binding source yields an empty or wrong-round table
- **Proposed resolution**: Update the Compact reviewer status table item in the same edit: post-notification only; read `latest-reviewer-status.tsv` first; if missing bind round from task-notification stdout KVs before the per-round fallback; parse `.step3-review-result.env` only after the table for loop routing



### FINDING_3:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:1242-1245
- **Concern**: `--report-framing` must wrap the no-ledger early-return path. Scenario: The `plan_review.py` section lists framing for filtered bodies but not the `if not applied: print(text)` branch at lines 1243-1245. Edge cases say ledger-missing output should still be framed when the flag is set; without an explicit wrap on that branch, wrapper `--report-framing` can emit bare rejected blocks (no considered-not-adopted heading/annotation) and partially reintroduce #4884 misleading output.
- **Proposed resolution**: In `emit_rejected_findings`, apply the same `--report-framing` wrapper to every non-empty stdout path, including the `not applied` early return; add a test mirroring `test_emit_rejected_without_ledger_emits_verbatim` with `--report-framing` asserting heading/annotation presence.



### FINDING_4:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:52-53,91-94
- **Concern**: Post-notification table before env parse breaks round fallback when `latest` is absent. Scenario: Current Compact table item 2 parses `.step3-review-result.env` first so `FINAL_ROUND_NUM` / `STEP3_REVIEW_ROUND_NUM` / `ROUNDS_COMPLETED` bind before the per-round `reviewer-status.tsv` fallback. The plan relocates printing to before result-env parse. If `latest-reviewer-status.tsv` is missing (degraded/partial terminals still possible), the fallback defaults to round 1 and can show the wrong reviewer set.
- **Proposed resolution**: Keep primary use of `latest-reviewer-status.tsv`. When it is missing, bind round from `.step3-review-result.env` (or notification stdout KVs) before choosing the per-round fallback; or document and test that latest is always present whenever the table prints. Update Compact table item 2 text to match the chosen order so it does not still say parse-then-show.



### FINDING_5:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/design-step3b-tail.sh:112-114
- **Concern**: CLI-failure fallback must not reintroduce unframed raw output. Scenario: The plan requires shell fallback to print heading/annotation before `cat rejected-findings.md`, but the tail script today only cats on non-zero exit. If framing lives only inside Python `--report-framing`, any CLI failure bypasses reframing and can surface stale unimplemented semantics under markers.
- **Proposed resolution**: In the `if ! ... emit-rejected --report-framing` branch, print the same heading/annotation strings before `cat`, or call a small shared framing helper; add a wrapper/contract test that non-zero `emit-rejected` still yields framed operator output.



### FINDING_6:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: plan.txt:51-71
- **Concern**: Unclosed markdown example fence swallows the design-step3b-tail.sh and design-step3b-tail.md file sections. Scenario: The plan opens a ```markdown fence at line 51 for the framing example but never closes it, so the following ### UPDATED subsections for design-step3b-tail.sh/.md sit inside the example block and may be skipped or mis-parsed during /implement
- **Proposed resolution**: Close the example fence immediately after the <filtered rejected body> line (after line 56) so the design-step3b-tail.sh and design-step3b-tail.md ### UPDATED sections are normal plan headings again



