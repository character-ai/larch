### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: **Important** `code-quality` `skills/design/SKILL.md:649-672` and `skills/design/SKILL.md:813-842` — The SIMPLE sentinel repair block (~30 lines: classification read, artifact verification, conflict refusal, sentinel writes, completion markers) is copy-pasted almost verbatim in the Step 2a entry fence and the Step 2a.5 resume guard. A future fix to conflict detection or write ordering must be applied in two SKILL locations, and the blocks can drift (the 2a.5 version adds an `elif` marker-only branch the entry fence lacks). **Suggested fix:** Extract a thin shared script (e.g. `skills/design/scripts/design-simple-sketch-sentinel.sh`) invoked from both fences, mirroring how `design-driver.sh` centralizes ACTION dispatch. Keep orchestrator fences as one-liner callers plus pause prelude.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 1. **Important** `code-quality` `skills/design/SKILL.md:649-672` and `skills/design/SKILL.md:813-842` — The SIMPLE sentinel repair block (~30 lines: classification read, artifact verification, conflict refusal, sentinel writes, completion markers) is copy-pasted almost verbatim in the Step 2a entry fence and the Step 2a.5 resume guard. A future fix to conflict detection or write ordering must be applied in two SKILL locations, and the blocks can drift (the 2a.5 version adds an `elif` marker-only branch the entry fence lacks). **Suggested fix:** Extract a thin shared script (e.g. `skills/design/scripts/design-simple-sketch-sentinel.sh`) invoked from both fences, mirroring how `design-driver.sh` centralizes ACTION dispatch. Keep orchestrator fences as one-liner callers plus pause prelude.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: correctness: skills/design/SKILL.md:683
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Prose references shell-only _design_classification as orchestrator-visible state. Orchestrator may skip the full sentinel+marker package checks in Step 2a.2 and fall through toward sketch launch on a corrupted SIMPLE resume. Rephrase to require read-design-classification.sh plus the full package checks from Step 2a.2.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: correctness: scripts/test-design-structure.sh:333-358
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Routing guard allow-list only matches the phrase step 3b completion boundary. A future edit could bypass FINALIZE using only FINALIZE + step-3b wording and still pass the guard. Also allow-list FINALIZE + step-3b or .completed/step-3b on the same line.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: risk-integration: skills/design/SKILL.md:649-672
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] SIMPLE repair logic is duplicated across Step 2a entry Step 2a.5 repair and test-design-pause-resume.sh without a shared helper. Future edits can update one copy and leave resume tests passing while live orchestration diverges. Extract one shared shell helper or documented fragment used by SKILL and harness.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_14: risk-integration: scripts/test-design-structure.sh:153-178
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] assert_no_direct_step3b_step4_routes has no negative self-tests. A regressed awk rule could stop flagging bare Step 3b-to-Step-4 routes while CI stays green. Add self-tests with intentionally invalid routing lines like thin-fence self-tests.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_15: risk-integration: scripts/test-design-structure.sh:153-178
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Routing guard scans eight files only; other design docs are not guarded. New bare Step 3b to Step 4 prose in uncovered docs would not fail test-design-structure.sh. Extend the guard or add cross-links in assessor and similar references.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_16: risk-integration: skills/design/scripts/test-design-pause-resume.sh:2023-2040
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] No harness runs successful Step 3b completion boundary with valid plan.txt and diff-lines.txt. FINALIZE success ordering regressions would only be caught by grep pins not executed driver paths. Add one pause-resume success fixture asserting finalize and step-3b markers.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: FINALIZE failure now hard-halts (`exit "$_finalize_rc"`) at both the Step 3b boundary and Step 4 compatibility guard, so the orchestrator cannot proceed with missing finalize artifacts.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - FINALIZE failure now hard-halts (`exit "$_finalize_rc"`) at both the Step 3b boundary and Step 4 compatibility guard, so the orchestrator cannot proceed with missing finalize artifacts.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: SIMPLE repair refuses to overwrite non-sentinel sketch/dialectic artifacts (`_simple_artifact_conflict`), which is an integrity guard against clobbering real content when classification/artifacts disagree.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - SIMPLE repair refuses to overwrite non-sentinel sketch/dialectic artifacts (`_simple_artifact_conflict`), which is an integrity guard against clobbering real content when classification/artifacts disagree.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: All new shell uses quoted `"$DESIGN_TMPDIR"` paths; `ACTION=FINALIZE` is a fixed literal piped to `design-driver.sh` (no `ARGS=` / `eval` on this path).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - All new shell uses quoted `"$DESIGN_TMPDIR"` paths; `ACTION=FINALIZE` is a fixed literal piped to `design-driver.sh` (no `ARGS=` / `eval` on this path).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: **Important** `code-quality` `skills/design/SKILL.md:1328-1341`, `skills/design/SKILL.md:1352-1362`, `skills/design/scripts/test-design-pause-resume.sh:377-499` — The FINALIZE wrapper (`set +e` → `design-driver.sh` → warn → `exit "$_finalize_rc"` → optional `step-3b` write) is duplicated five times: Step 3b boundary, Step 4 compatibility guard, and three inline `bash -c` blocks in the pause/resume harness. The repo already established the opposite pattern for Gate-B bypass sentinels via `apply_gate_b_bypass_sentinels` in `test-step3-orchestrator-fence.sh`, but FINALIZE did not get the same treatment. **Suggested fix:** Add a small sourced helper (e.g. `run_design_finalize_boundary.sh --mode fresh|compat`) used by SKILL fences and tests, or at minimum one harness helper sourced by `test-design-pause-resume.sh` so tests do not embed four copies of production shell.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 2. **Important** `code-quality` `skills/design/SKILL.md:1328-1341`, `skills/design/SKILL.md:1352-1362`, `skills/design/scripts/test-design-pause-resume.sh:377-499` — The FINALIZE wrapper (`set +e` → `design-driver.sh` → warn → `exit "$_finalize_rc"` → optional `step-3b` write) is duplicated five times: Step 3b boundary, Step 4 compatibility guard, and three inline `bash -c` blocks in the pause/resume harness. The repo already established the opposite pattern for Gate-B bypass sentinels via `apply_gate_b_bypass_sentinels` in `test-step3-orchestrator-fence.sh`, but FINALIZE did not get the same treatment. **Suggested fix:** Add a small sourced helper (e.g. `run_design_finalize_boundary.sh --mode fresh|compat`) used by SKILL fences and tests, or at minimum one harness helper sourced by `test-design-pause-resume.sh` so tests do not embed four copies of production shell.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_20

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_20: `design-driver.sh` still validates tmpdir via `larch_design_tmpdir_validate` (allowlisted under `~/.cache/larch/sessions/`, `$TMPDIR`, `/tmp`; rejects `..` segments and newlines).
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `design-driver.sh` still validates tmpdir via `larch_design_tmpdir_validate` (allowlisted under `~/.cache/larch/sessions/`, `$TMPDIR`, `/tmp`; rejects `..` segments and newlines). **Pre-existing patterns not amplified materially**
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_21

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_21: Step 4 compatibility uses `[ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]` as the sole gate. That marker is written by `design-driver.sh` only after `finalize-plan.sh` succeeds, but a pre-existing empty/symlinked marker could still skip the compatibility FINALIZE. That is the same idempotency model `design-driver` already uses (`already-completed` skip); this PR does not add new shell execution surfaces beyond relocating the call sites.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - Step 4 compatibility uses `[ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]` as the sole gate. That marker is written by `design-driver.sh` only after `finalize-plan.sh` succeeds, but a pre-existing empty/symlinked marker could still skip the compatibility FINALIZE. That is the same idempotency model `design-driver` already uses (`already-completed` skip); this PR does not add new shell execution surfaces beyond relocating the call sites.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_22

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_22: `design-driver.sh` still uses `eval` for `ARGS=` on other actions; FINALIZE in this diff does not use `ARGS`.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `design-driver.sh` still uses `eval` for `ARGS=` on other actions; FINALIZE in this diff does not use `ARGS`. **No findings in**: secret leakage, injection, SSRF, path traversal outside the existing tmpdir allowlist, authz bypass, or new dependency/CVE exposure.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: architecture: skills/design/SKILL.md:1352-1361
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Step 4 compatibility FINALIZE is gated only on missing .completed/finalize; design-driver skips FINALIZE when that sentinel exists. Restored tmpdir has .completed/finalize but missing rejected-findings.md; Step 4 skips FINALIZE and may fail on read. Also require finalize artifact files to exist or clear .completed/finalize before re-invoking FINALIZE.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_28: architecture: scripts/test-design-structure.sh:486-487
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Routing guard scans step 3 through step 3.6 but excludes the Step 3.5 SKILL.md region. Future Step 3.5 prose could add a bare Step 3b-to-Step-4 route without failing CI. Add a step-3.5 slice to assert_no_direct_step3b_step4_routes.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: **Latent** `code-quality` `skills/design/SKILL.md:1134-1158`, `skills/design/references/approval-gates.md:17-169`, `scripts/test-design-structure.sh:550-916` — The canonical routing phrase `Step 3b completion boundary (FINALIZE + step-3b)` is repeated across SKILL.md, `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `plan-review.md`, `run-step3-review.sh`, and multiple `contains()` harness pins. Any future rename requires a synchronized edit across ~8 surfaces; a typo in one file passes others until CI hits the specific pin. **Suggested fix:** Define the phrase once in `approval-gates.md` (or a shared routing snippet) and use a shorter stable token elsewhere (`Step 3b completion boundary` only), with harness pins keyed to the normative definition file rather than every consumer copy.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 3. **Latent** `code-quality` `skills/design/SKILL.md:1134-1158`, `skills/design/references/approval-gates.md:17-169`, `scripts/test-design-structure.sh:550-916` — The canonical routing phrase `Step 3b completion boundary (FINALIZE + step-3b)` is repeated across SKILL.md, `approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `plan-review.md`, `run-step3-review.sh`, and multiple `contains()` harness pins. Any future rename requires a synchronized edit across ~8 surfaces; a typo in one file passes others until CI hits the specific pin. **Suggested fix:** Define the phrase once in `approval-gates.md` (or a shared routing snippet) and use a shorter stable token elsewhere (`Step 3b completion boundary` only), with harness pins keyed to the normative definition file rather than every consumer copy.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_32

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_32: **correctness** `skills/design/SKILL.md:1174` — Gate B’s settled-path prose still says only “proceed to Step 3.6 … before Step 3b” and never names the Step 3b completion boundary (FINALIZE + `step-3b`) before Step 4. The normative tail fence at lines 1326–1341 is correct, but this Gate B handoff is outside the harness’s Step 3b→Step 4 routing guard (the Step 3 slice ends at `<!-- step:3.6`, so Step 3.5 is covered, yet this line has no `Step 4` token and would not be caught anyway). An orchestrator that treats Gate B completion as “enter 3.6, then 3b, then Step 4” can skip the embedded FINALIZE fence on architectural plans and reach Step 4 without `rejected-findings.md` / `.completed/finalize` on paths where voting was skipped or panel-failed. **Suggested fix:** Mirror `approval-gates.md` and retarget line 1174 (and the similar assessor Continue handoff at line 1265) to “Step 3.6 → Step 3b → **Step 3b completion boundary (FINALIZE + step-3b)** → Step 4”.
- **Reviewer**: dyn-workflow-resume-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:1174` — Gate B’s settled-path prose still says only “proceed to Step 3.6 … before Step 3b” and never names the Step 3b completion boundary (FINALIZE + `step-3b`) before Step 4. The normative tail fence at lines 1326–1341 is correct, but this Gate B handoff is outside the harness’s Step 3b→Step 4 routing guard (the Step 3 slice ends at `<!-- step:3.6`, so Step 3.5 is covered, yet this line has no `Step 4` token and would not be caught anyway). An orchestrator that treats Gate B completion as “enter 3.6, then 3b, then Step 4” can skip the embedded FINALIZE fence on architectural plans and reach Step 4 without `rejected-findings.md` / `.completed/finalize` on paths where voting was skipped or panel-failed. **Suggested fix:** Mirror `approval-gates.md` and retarget line 1174 (and the similar assessor Continue handoff at line 1265) to “Step 3.6 → Step 3b → **Step 3b completion boundary (FINALIZE + step-3b)** → Step 4”.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_36

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_36: **correctness** `scripts/test-design-structure.sh:166-176` — `assert_no_direct_step3b_step4_routes` matches routing verbs as substrings (`enter`, `go`, `route`, etc.), not as words, so innocent prose can fail CI (e.g. a line mentioning Step 3b and Step 4 that also contains “**center**”, “on**go**ing”, or “**route**r”) even when it already names the completion boundary elsewhere on the line. **Suggested fix:** Tighten the awk patterns with word boundaries (`\<continue\>`, `\<proceed\>`, …) or require the verb to appear in the substring between `step 3b` and `step 4`, and add a small fixture block in `test-design-structure.sh` that must pass/fail deterministically.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:166-176` — `assert_no_direct_step3b_step4_routes` matches routing verbs as substrings (`enter`, `go`, `route`, etc.), not as words, so innocent prose can fail CI (e.g. a line mentioning Step 3b and Step 4 that also contains “**center**”, “on**go**ing”, or “**route**r”) even when it already names the completion boundary elsewhere on the line. **Suggested fix:** Tighten the awk patterns with word boundaries (`\<continue\>`, `\<proceed\>`, …) or require the verb to appear in the substring between `step 3b` and `step 4`, and add a small fixture block in `test-design-structure.sh` that must pass/fail deterministically.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_37

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_37: **correctness** `scripts/test-design-structure.sh:171` — Any line containing `step 3b completion boundary` is skipped entirely before the bare-route checks run, so a single line can document both a forbidden shortcut and the boundary (e.g. “do not use Step 3b → Step 4; use the Step 3b completion boundary…”) without failing the guard. **Suggested fix:** Only skip the arrow/comma shorthand rules when the boundary phrase appears between `step 3b` and `step 4`; still run the verb-based rule, or split the line into clauses before matching.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:171` — Any line containing `step 3b completion boundary` is skipped entirely before the bare-route checks run, so a single line can document both a forbidden shortcut and the boundary (e.g. “do not use Step 3b → Step 4; use the Step 3b completion boundary…”) without failing the guard. **Suggested fix:** Only skip the arrow/comma shorthand rules when the boundary phrase appears between `step 3b` and `step 4`; still run the verb-based rule, or split the line into clauses before matching.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_38

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_38: **correctness** `scripts/test-design-structure.sh:153-177` — The guard only fires when **both** `step 3b` and `step 4` appear on the same line, so normative text that routes to Step 3b without mentioning Step 4 is never checked. The harness even **requires** that shape in `approval-gates.md` via the positive pin at line 1733 (`…bypass Step 3.5 and Step 3.6 before Step 3b`), while other surfaces must name the completion boundary. That is a blind spot relative to the Phase 6 FINALIZE contract. **Suggested fix:** Add a separate check (or extend the awk pass) for Gate-B-bypass / Step-3b entry prose that must mention the completion boundary before Step 4 is reached, not only for same-line `Step 3b … Step 4` chains.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:153-177` — The guard only fires when **both** `step 3b` and `step 4` appear on the same line, so normative text that routes to Step 3b without mentioning Step 4 is never checked. The harness even **requires** that shape in `approval-gates.md` via the positive pin at line 1733 (`…bypass Step 3.5 and Step 3.6 before Step 3b`), while other surfaces must name the completion boundary. That is a blind spot relative to the Phase 6 FINALIZE contract. **Suggested fix:** Add a separate check (or extend the awk pass) for Gate-B-bypass / Step-3b entry prose that must mention the completion boundary before Step 4 is reached, not only for same-line `Step 3b … Step 4` chains.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_39

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_39: **correctness** `scripts/test-design-structure.sh:72-73` — `closing_fi_line` is chosen as the **last** line that equals exactly `fi` after the SIMPLE guard, not the `fi` that closes that `if`. A later standalone `fi` line (debug residue, copy-paste, or nested structure edits) makes the “inside the SIMPLE guard” line-range checks pass while artifact writes sit outside the real block. **Suggested fix:** Track `if` depth from the guard line (increment on `if … then`, decrement on a line-equal `fi`) or require the first `fi` at depth zero after the guard.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:72-73` — `closing_fi_line` is chosen as the **last** line that equals exactly `fi` after the SIMPLE guard, not the `fi` that closes that `if`. A later standalone `fi` line (debug residue, copy-paste, or nested structure edits) makes the “inside the SIMPLE guard” line-range checks pass while artifact writes sit outside the real block. **Suggested fix:** Track `if` depth from the guard line (increment on `if … then`, decrement on a line-equal `fi`) or require the first `fi` at depth zero after the guard.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: **Nit** `code-quality` `skills/design/SKILL.md:1134-1141` — Six `LOOP_STATUS` short-circuit bullets each repeat the full suffix `Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4`. This inflates SKILL.md line count and review noise without adding semantics per bullet. **Suggested fix:** Define the suffix once at the top of the post-loop branch matrix (“All Gate-B-bypass short-circuits below route: Step 3b → completion boundary → Step 4”) and shorten bullets to status-specific breadcrumbs only.
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: 4. **Nit** `code-quality` `skills/design/SKILL.md:1134-1141` — Six `LOOP_STATUS` short-circuit bullets each repeat the full suffix `Step 3b, then the Step 3b completion boundary (FINALIZE + step-3b), then Step 4`. This inflates SKILL.md line count and review noise without adding semantics per bullet. **Suggested fix:** Define the suffix once at the top of the post-loop branch matrix (“All Gate-B-bypass short-circuits below route: Step 3b → completion boundary → Step 4”) and shorten bullets to status-specific breadcrumbs only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_40

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_40: **correctness** `scripts/test-design-structure.sh:112-118` vs `896-899` — Step 4 region slicing uses two markers: `assert_step3b_finalize_boundary` uses `<!-- step:4 —` while the older (15b) slice uses `<!-- step:4 ` (prefix). They match today, but a marker edit to em-dash-only form could split the slices and make FINALIZE checks pass on a different region than the architecture-diagram pins. **Suggested fix:** Centralize one `STEP4_MARKER` variable / helper used by every `step3b_between` / `step4_between` extractor.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:112-118` vs `896-899` — Step 4 region slicing uses two markers: `assert_step3b_finalize_boundary` uses `<!-- step:4 —` while the older (15b) slice uses `<!-- step:4 ` (prefix). They match today, but a marker edit to em-dash-only form could split the slices and make FINALIZE checks pass on a different region than the architecture-diagram pins. **Suggested fix:** Centralize one `STEP4_MARKER` variable / helper used by every `step3b_between` / `step4_between` extractor.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_41

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_41: **correctness** `scripts/test-design-structure.sh:130-135` — Ordering is validated with line numbers for `ACTION=FINALIZE`, `_finalize_rc=$?`, `exit "$_finalize_rc"`, and `: > …/step-3b`, but not that `step-3b` is absent from the failure branch (e.g. a mistaken marker write before `exit`). **Suggested fix:** Parse only the Step 3b completion ` ```bash ` fence (same pattern as `extract_first_bash_fence_after`) and assert `step-3b` appears only after the `if [ "$_finalize_rc" -ne 0 ]` block / after `set -e` following a zero rc.
- **Reviewer**: dyn-bash-harness-output.txt
- **Concern**: - **correctness** `scripts/test-design-structure.sh:130-135` — Ordering is validated with line numbers for `ACTION=FINALIZE`, `_finalize_rc=$?`, `exit "$_finalize_rc"`, and `: > …/step-3b`, but not that `step-3b` is absent from the failure branch (e.g. a mistaken marker write before `exit`). **Suggested fix:** Parse only the Step 3b completion ` ```bash ` fence (same pattern as `extract_first_bash_fence_after`) and assert `step-3b` appears only after the `if [ "$_finalize_rc" -ne 0 ]` block / after `set -e` following a zero rc.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_8: architecture: skills/design/SKILL.md:649-672,813-841
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Duplicated SIMPLE sentinel/repair shell between Step 2a entry and Step 2a.5 repair fences. Future fix applied to only one copy changes fresh-run vs resume behavior silently. Extract shared helper or add harness byte-alignment check between both fences.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: correctness: skills/design/SKILL.md:663-667
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Partial SIMPLE artifact write under set -e can leave non-sentinel files that trigger conflict refusal on retry. First printf succeeds, second fails; retry exits 1 with repair refused and requires manual tmpdir cleanup. Use atomic write-then-rename for the three artifacts or delete partial files before rewrite.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0

