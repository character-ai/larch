### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: skills/design/scripts/render-final-summary.sh:399-406
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] preserved_cost_line passed to awk -v without escaping. Cost line containing & or backslashes could produce a wrong substituted bullet. Use sed with a safe delimiter or pass the line via a file/ENVIRON instead of awk -v.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_17: risk-integration: skills/implement/scripts/test-write-final-report.sh:7
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] All summary harnesses set LARCH_QUIET_DISABLE=1, leaving FD-3 chat-print paths untested. Quiet-mode routing regression in production would pass CI while chat summaries disappear or misroute. Add one quiet-enabled case per wrapper asserting bytes on FD 3.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_18: risk-integration: skills/implement/SKILL.md:1819-1828
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness covers Step 18 cost-line orchestrator emit when sentinel exists but refreshed cost changed. Cost refresh after Step 17 could stop emitting collapse-resistant cost text without test failure. Add harness: sentinel present, differing pre/post cost lines, assert emit conditions or extend callsite pin for the change branch.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_19: risk-integration: scripts/test-render-cost-line-callsites.sh:38
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Callsite lint does not verify sentinel check and --print-stdout live in the same Step 18 bash block. Future refactor could split conditional print into another fence without failing lint. Windowed grep/awk inside the Step 18 fence for both patterns.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/implement/scripts/write-final-report.sh:390-430
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Parallel self-composed fallback bodies duplicate render-run-summary schema in implement and design scripts. Future renderer schema edits can leave one fallback path stale while tests still pass on the happy path. Add a shared ordered-bullet contract test or a tiny shared fallback helper despite FINDING_3 deferral.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_22: security: skills/design/scripts/render-final-summary.sh:398-407
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] preserved_cost_line is bash-expanded into awk -v cost_line= Poisoned final-summary.md cost line with shell metacharacters could execute during fallback splice Pass cost line via file or validate against allowed cost-line regex before awk
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: security: skills/implement/SKILL.md:1760-1828
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Orchestrator verbatim cost-line emit trusts any line matching - **Cost**: prefix Poisoned summary-final.md could inject prompt-shaped text into collapse-resistant assistant chat Require structural validation (TOTAL breakdown or N/A) before emit; extend callsite tests
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: skills/implement/SKILL.md:1808-1828
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Step 18 cost re-emit and sentinel rules live in orchestrator Bash+prose and are only partially pinned by tests. Agents may skip the cost-changed emit path; lint does not catch SKILL/test drift (see callsite failure). Consolidate behavior in write-final-report.sh flags or add an integration harness for the full Step 18 fence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_30

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_30: correctness: skills/design/scripts/test-render-final-summary.sh:281-294
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Empty-mode regression uses cancelled-tier-gate without run-params.json instead of plan’s cancelled-title-filter scenario. Fence N/A default is tested, but the plan-named early-cancel path is only partially mirrored. Add a title-filter empty-mode variant or rename the test comment to document equivalence.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_34

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_34: **correctness** `skills/design/scripts/render-final-summary.sh:398-407` — Post-phase cost preservation passes `preserved_cost_line` into `awk -v cost_line="$preserved_cost_line"`. A cost bullet containing `&`, backslashes, or newlines can break `awk` parsing or word-splitting in the shell assignment (the happy-path line is usually safe, but the mechanism is fragile). **Suggested fix:** Avoid inline `-v` for arbitrary markdown; e.g. write the preserved line to a temp file and use `awk -v cost_file=… 'FNR==NR{cost=$0;next} …'` with `getline`, or use `sed`/`ed` to replace the first `- **Cost**:` line.
- **Reviewer**: dyn-bash-mechanics-output.txt
- **Concern**: - **correctness** `skills/design/scripts/render-final-summary.sh:398-407` — Post-phase cost preservation passes `preserved_cost_line` into `awk -v cost_line="$preserved_cost_line"`. A cost bullet containing `&`, backslashes, or newlines can break `awk` parsing or word-splitting in the shell assignment (the happy-path line is usually safe, but the mechanism is fragile). **Suggested fix:** Avoid inline `-v` for arbitrary markdown; e.g. write the preserved line to a temp file and use `awk -v cost_file=… 'FNR==NR{cost=$0;next} …'` with `getline`, or use `sed`/`ed` to replace the first `- **Cost**:` line.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_39: **correctness** `skills/implement/scripts/write-final-report.sh:396`, `skills/design/scripts/render-final-summary.sh:347` — Self-composed fallbacks print `- **Duration**: ${DURATION:-N/A}`, but an empty `DURATION` string is not unset, so the bullet can be blank. `scripts/render-run-summary.sh:108,180,235` uses `na()` so the renderer always emits `N/A` for empty duration. The same `${VAR:-N/A}` pattern affects any field that can be set to `""` by `jq` (duration is the concrete case today). **Suggested fix:** Normalize before compose (e.g. `[ -z "$DURATION" ] && DURATION=N/A`) or mirror `na()` inside `compose_self_fallback` for Mode/Path/Duration (and any other `jq`-sourced display fields).
- **Reviewer**: dyn-fallback-schema-fidelity-output.txt
- **Concern**: - **correctness** `skills/implement/scripts/write-final-report.sh:396`, `skills/design/scripts/render-final-summary.sh:347` — Self-composed fallbacks print `- **Duration**: ${DURATION:-N/A}`, but an empty `DURATION` string is not unset, so the bullet can be blank. `scripts/render-run-summary.sh:108,180,235` uses `na()` so the renderer always emits `N/A` for empty duration. The same `${VAR:-N/A}` pattern affects any field that can be set to `""` by `jq` (duration is the concrete case today). **Suggested fix:** Normalize before compose (e.g. `[ -z "$DURATION" ] && DURATION=N/A`) or mirror `na()` inside `compose_self_fallback` for Mode/Path/Duration (and any other `jq`-sourced display fields).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: correctness: skills/design/scripts/render-final-summary.sh:388-408
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] preserved_cost_line awk rewrite is fragile if cost text contains special characters. Rare formatting change could corrupt final-summary.md on post-phase render failure. Use safer line replacement or preserve cost via a dedicated renderer flag instead of awk -v injection.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: **correctness** `skills/implement/SKILL.md:1751-1754,1760,1822-1828` — The Step 17 Bash block writes `$IMPLEMENT_TMPDIR/.step17-printed` as soon as `write-final-report.sh --print-stdout` succeeds and `summary-final.md` contains a `- **Cost**:` line, but the collapse-resistant plain-text cost emit is a separate orchestrator step that runs only after that Bash block returns. If the orchestrator skips that emit (model non-compliance), Step 18 sees the sentinel, omits `--print-stdout`, and the Step 18 prose only re-emits the cost line when `--print-stdout` was used or the cost line changed (`skills/implement/SKILL.md:1819-1828`). The user is left with only collapsed Step 17 Bash output and no plain-text cost line—the exact ROOT CAUSE G failure mode this branch targets. The same ordering exists on Step 18 bail/refresh paths where lines 1822-1824 touch the sentinel before the orchestrator emit at 1828. **Suggested fix:** Split concerns into two markers (e.g. `.step17-block-printed` for suppressing duplicate full-block `--print-stdout`, and `.step17-cost-emitted` written only after the orchestrator verbatim cost-line emit), or remove `touch` from the Bash blocks and have the orchestrator write the suppress sentinel only after a successful cost-line emit; ensure Step 18 always performs the plain-text emit when the block was printed but the cost emit marker is absent.
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1751-1754,1760,1822-1828` — The Step 17 Bash block writes `$IMPLEMENT_TMPDIR/.step17-printed` as soon as `write-final-report.sh --print-stdout` succeeds and `summary-final.md` contains a `- **Cost**:` line, but the collapse-resistant plain-text cost emit is a separate orchestrator step that runs only after that Bash block returns. If the orchestrator skips that emit (model non-compliance), Step 18 sees the sentinel, omits `--print-stdout`, and the Step 18 prose only re-emits the cost line when `--print-stdout` was used or the cost line changed (`skills/implement/SKILL.md:1819-1828`). The user is left with only collapsed Step 17 Bash output and no plain-text cost line—the exact ROOT CAUSE G failure mode this branch targets. The same ordering exists on Step 18 bail/refresh paths where lines 1822-1824 touch the sentinel before the orchestrator emit at 1828. **Suggested fix:** Split concerns into two markers (e.g. `.step17-block-printed` for suppressing duplicate full-block `--print-stdout`, and `.step17-cost-emitted` written only after the orchestrator verbatim cost-line emit), or remove `touch` from the Bash blocks and have the orchestrator write the suppress sentinel only after a successful cost-line emit; ensure Step 18 always performs the plain-text emit when the block was printed but the cost emit marker is absent.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_44

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_44: **correctness** `skills/implement/SKILL.md:1752-1753,73` — The `.step17-printed` sentinel is set whenever `grep -Fq -- '- **Cost**:'` matches, which includes `- **Cost**: N/A` after `--cost-unavailable` paths. That is reasonable for suppressing duplicate full prints, but NEVER #20 (`skills/implement/SKILL.md:73`) tells the orchestrator to touch the same sentinel and emit the cost line without distinguishing N/A from a per-agent breakdown; combined with the ordering bug above, a successful Step 17 render that only has `N/A` still blocks Step 18 recovery of a later real cost if token refresh at Step 18 (`skills/implement/SKILL.md:1807-1817`) would produce a non-N/A line. **Suggested fix:** Gate `.step17-printed` on a cost line that includes the breakdown markers (`💰 TOTAL` / `Claude $`) when suppressing Step 18 re-print, or always allow Step 18 `--print-stdout` when `_wfr_new_cost` differs from `_wfr_prev_cost` even if the sentinel exists (today only the plain-text emit is conditional on change, not the full block).
- **Reviewer**: dyn-sentinel-orchestration-output.txt
- **Concern**: - **correctness** `skills/implement/SKILL.md:1752-1753,73` — The `.step17-printed` sentinel is set whenever `grep -Fq -- '- **Cost**:'` matches, which includes `- **Cost**: N/A` after `--cost-unavailable` paths. That is reasonable for suppressing duplicate full prints, but NEVER #20 (`skills/implement/SKILL.md:73`) tells the orchestrator to touch the same sentinel and emit the cost line without distinguishing N/A from a per-agent breakdown; combined with the ordering bug above, a successful Step 17 render that only has `N/A` still blocks Step 18 recovery of a later real cost if token refresh at Step 18 (`skills/implement/SKILL.md:1807-1817`) would produce a non-N/A line. **Suggested fix:** Gate `.step17-printed` on a cost line that includes the breakdown markers (`💰 TOTAL` / `Claude $`) when suppressing Step 18 re-print, or always allow Step 18 `--print-stdout` when `_wfr_new_cost` differs from `_wfr_prev_cost` even if the sentinel exists (today only the plain-text emit is conditional on change, not the full block).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_5

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_5: code-quality: skills/implement/scripts/test-write-final-report.sh:372-385
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 18 conditional --print-stdout logic is triplicated across SKILL callsite lint and harness. Editors update SKILL but forget harness/lint copies. Extract one shell helper used by tests (and optionally sourced from docs).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: correctness: skills/implement/SKILL.md:1751-1754
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] .step17-printed is set on script exit 0 plus any Cost line, even if tracking upsert fails after chat print. write-final-report prints via --print-stdout then exits non-zero on upsert; sentinel is set; Step 18 skips --print-stdout and may skip cost re-emit despite refreshed token data. Gate sentinel on full success only, or use a separate marker for chat-print vs comment upsert.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0

