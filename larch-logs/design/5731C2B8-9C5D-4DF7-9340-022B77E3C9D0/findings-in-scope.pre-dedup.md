### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-fence-shape.sh:235-255
- **Concern**: Plan updates fence counts but not the legacy compose-write ordering assertions still pinned to inline authorship branches. Scenario: After SKILL.md drops per-kind compose writers, the harness still requires `step-architectural-invariants-write-compose.sh` before `step-architectural-guidelines-write-compose.sh` and a guidelines-only compose relaunch, so the approved adapter-only Step 8 shape fails CI even when the skill text is correct
- **Proposed resolution**: Extend the `scripts/test-implement-fence-shape.sh` plan item to replace those slices with adapter-first checks: one `step-8-assessment.sh` launcher through `implement-run-$PPID.sh`, no prompt-side assessment start/wait pair, and exactly one post-validation `step-8-ship.sh` relaunch



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Requested-kind validation must compare canonical normalized kinds, not raw handoff `DETAIL` text. Scenario: The plan preserves valid combined `DETAIL` payloads while requiring `ASSESSMENT_REQUESTED_KINDS` to match the canonical normalized request; the adapter emits Piece-2 order (`invariants,guidelines`) via `normalize_kinds`, so a handoff like `DETAIL=guidelines,invariants` can pass normalization yet fail a naive string compare and route a false tool-failure
- **Proposed resolution**: In the shared adapter validation block, require the orchestrator to compute expected kinds with the same normalization rules as the frozen adapter (order, dedupe, allowed tokens) and compare that canonical set/string to adapter `ASSESSMENT_REQUESTED_KINDS` and `ASSESSMENT_RESULTS` coverage; forbid direct comparison to pre-adapter `DETAIL`/`DETAIL_FILE` text



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Terminal validation should name `ASSESSMENT_RESULTS` explicitly, not only `ASSESSMENT_STATUS` and abstract completeness wording. Scenario: The plan’s failure modes warn against trusting `ASSESSMENT_STATUS=complete` alone, but the SKILL.md update bullets omit the `ASSESSMENT_RESULTS` KV that `step-8-assessment.md` requires on success; an implementer can treat status-only success as sufficient and relaunch ship when only one requested kind is covered
- **Proposed resolution**: Add `ASSESSMENT_RESULTS` to the mandatory terminal KV checklist in SKILL.md and require per-requested-kind `kind:state` coverage validation before the single `step-8-ship.sh` relaunch



### FINDING_4:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: minor
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37-44
- **Concern**: Exit-matrix durable handoff prose still describes independent back-compat relaunch and inline materialization consumption. Scenario: The plan rewrites branch semantics but does not explicitly require rewriting the handoff paragraph that says back-compat `invariants-assessment` and `guidelines-assessment` branches relaunch independently and consume per-kind materialization for main-agent authorship, leaving a contradictory inline-authorship escape hatch beside the adapter route
- **Proposed resolution**: Add an explicit `ship-pr-exit-matrix.md` task to rewrite the durable handoff paragraph so all three assessment tokens normalize to `NEXT_ACTION=assessments`, invoke the combined adapter once, validate its envelope, and relaunch ship once; remove independent back-compat relaunch and materialized-diff authorship language



### FINDING_5:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:682-685
- **Concern**: The alias-normalization step is specified only as prose, with no concrete safe operation or executable verification. Scenario: `invariants-assessment` or `guidelines-assessment` can still reach the frozen adapter with the legacy `NEXT_ACTION`, or normalization can rewrite the handoff while dropping unrelated keys. The adapter then rejects the request or processes the wrong route, reproducing the accepted prior-round compatibility defect. Add an explicit normalization operation that atomically preserves all unrelated handoff keys, rewrites only `NEXT_ACTION` and the canonical `DETAIL`, and routes malformed input to the existing Tool Failures hard stop. Add a focused test that exercises the three handoff shapes rather than only asserting prompt wording.
- **Proposed resolution**: 



### FINDING_6:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Post-adapter validation must bind expected kinds in canonical adapter order, not raw DETAIL text. Scenario: The frozen adapter keeps handoff DETAIL order but emits ASSESSMENT_REQUESTED_KINDS in canonical order (invariants before guidelines). If SKILL validation string-matches terminal kinds to retained DETAIL such as guidelines,invariants, a successful adapter run can be rejected and route to tool-failure
- **Proposed resolution**: In the normalization and validation sections, bind expected kinds once (legacy alias synthesis or combined-route canonicalization) using the same ordering rules as the frozen adapter, and compare terminal ASSESSMENT_REQUESTED_KINDS only to that bound value; forbid raw DETAIL or DETAIL_FILE string equality



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Terminal validation must require ASSESSMENT_RESULTS per-kind coverage, not only ASSESSMENT_STATUS=complete. Scenario: The SKILL deliverable lists BGJOB_RC, STEP, fingerprint, requested kinds, and status but never names ASSESSMENT_RESULTS. An orchestrator could treat status=complete as sufficient and skip verifying each requested kind appears exactly once in the terminal envelope before the single ship relaunch
- **Proposed resolution**: Add ASSESSMENT_RESULTS to the required terminal KV checklist and require coverage for every normalized requested kind per the frozen step-8-assessment.md contract before relaunching step-8-ship.sh



### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Combined-route validation must bind expected kinds via adapter canonical ordering, not raw DETAIL text. Scenario: The plan tells the orchestrator to retain a valid combined DETAIL payload and later require ASSESSMENT_REQUESTED_KINDS to match the canonical normalized request, but it never pins how that expected kind list is derived. The frozen adapter always emits normalize_kinds order (invariants,guidelines) even when handoff DETAIL is guidelines,invariants. String-comparing adapter output to raw DETAIL rejects a successful adapter run and routes to tool-failure.
- **Proposed resolution**: During pre-adapter normalization, bind EXPECTED_ASSESSMENT_REQUESTED_KINDS using the same split/trim/duplicate-reject rules plus canonical invariants,guidelines ordering the adapter uses; compare adapter ASSESSMENT_REQUESTED_KINDS to that binding only. State explicitly that raw DETAIL order is not the validation key.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: major
- **Focus area**: architecture
- **Location**: skills/implement/references/ship-pr-exit-matrix.md:37
- **Concern**: Durable handoff paragraph still describes inline materialization consumption and independent back-compat relaunches. Scenario: The ship-pr-exit-matrix update bullets target branch semantics and the assessments row, but line 37 still says the assessments branch consumes materialized diff files and that back-compat invariants-assessment and guidelines-assessment branches relaunch independently. That contradicts the single adapter plus one ship relaunch contract and recreates an inline-authorship escape hatch via the mandatory Step 8 matrix read.
- **Proposed resolution**: Rewrite the durable handoff paragraph to state that all assessment tokens normalize to NEXT_ACTION=assessments, the adapter owns assessment work from existing materialization inputs, legacy aliases do not relaunch independently, and only one post-validation step-8-ship.sh relaunch is allowed. Add a harness negative assertion against relaunch independently and main-agent materialized-diff consumption prose.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: minor
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md
- **Concern**: Terminal validation must name ASSESSMENT_RESULTS explicitly. Scenario: The plan requires complete per-kind result coverage and lists BGJOB_RC, STEP, ASSESSMENT_COVERED_FINGERPRINT, ASSESSMENT_REQUESTED_KINDS, and ASSESSMENT_STATUS, but the SKILL.md update bullets never require parsing ASSESSMENT_RESULTS from the adapter terminal envelope. step-8-assessment.md treats ASSESSMENT_RESULTS as required on ASSESSMENT_STATUS=complete, and the adapter already enforces per-kind coverage internally. An implementer can treat ASSESSMENT_STATUS=complete as sufficient and relaunch ship when only one kind is present in ASSESSMENT_RESULTS.
- **Proposed resolution**: Add ASSESSMENT_RESULTS to the SKILL.md and test-architectural-guidelines-step.sh validation pin list, requiring one kind:state token per requested kind in canonical order before the single ship relaunch. ## Findings ### 1. [correctness] Combined-route validation must bind expected kinds via adapter canonical ordering **Location:** `skills/implement/SKILL.md` **Concern:** The plan says to retain a valid combined `DETAIL` payload and later require `ASSESSMENT_REQUESTED_KINDS` to match the canonical normalized request. It does not say how that expected list is produced. The frozen adapter always canonicalizes to `invariants,guidelines` via `normalize_kinds`, even when handoff `DETAIL` is `guidelines,invariants` (see `step-8-assessment.sh` and `architectural_assessment.normalize_kinds`). Comparing adapter output to raw `DETAIL` text would reject valid runs and hard-stop on `tool-failure`. **Suggested revision:** During pre-adapter normalization, bind an expected kind list using the same split/trim/duplicate-reject rules and canonical `invariants,guidelines` ordering the adapter uses. Compare `ASSESSMENT_REQUESTED_KINDS` only to that binding. Say explicitly that raw `DETAIL` order is not the validation key. This closes the remaining gap from round 1 FINDING_2. ### 2. [architecture] Durable handoff paragraph still describes inline consumption and independent relaunches **Location:** `skills/implement/references/ship-pr-exit-matrix.md:37` **Concern:** The plan updates branch semantics but does not explicitly require rewriting the durable handoff paragraph. That paragraph still tells the orchestrator that the `assessments` branch consumes materialized diff files and that back-compat branches "relaunch independently." That conflicts with the single adapter route and one ship relaunch, and it survives the mandatory Step 8 matrix read. **Suggested revision:** Extend the `ship-pr-exit-matrix.md` update to rewrite line 37: all assessment tokens normalize to the combined adapter; the adapter consumes existing materialization inputs; legacy aliases do not relaunch independently. Add a negative harness assertion against `relaunch independently` and main-agent materialized-diff consumption language. ### 3. [correctness] Terminal validation must name `ASSESSMENT_RESULTS` explicitly **Location:** `skills/implement/SKILL.md` **Concern:** The plan requires complete per-kind coverage conceptually but the SKILL.md validation bullets omit the `ASSESSMENT_RESULTS` KV that `step-8-assessment.md` requires when `ASSESSMENT_STATUS=complete`. An implementer could validate status and fingerprint only, miss partial per-kind coverage, and still relaunch ship. The plan edge case ("both kinds complete, but only one result is present") is not wired into the SKILL validation checklist. **Suggested revision:** Add `ASSESSMENT_RESULTS` to the SKILL.md terminal validation list and to `test-architectural-guidelines-step.sh` pins, requiring one `kind:state` token per requested kind before ship relaunch. --- **[OUT_OF_SCOPE]** `skills/implement/references/conflict-resolution.md:85` still promises a fresh `NEXT_ACTION=guidelines-assessment` after HEAD/diff changes. That contradicts scoped reassessment, but the piece-4 scope lock excludes this file. Track as a follow-up issue; do not expand the eight approved surfaces here.



