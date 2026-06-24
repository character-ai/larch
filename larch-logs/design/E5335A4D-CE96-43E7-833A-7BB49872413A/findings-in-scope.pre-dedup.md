### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:11
- **Concern**: Gate B binding convention still names orchestrator severity rubric as normative. Scenario: The plan rewrites `### Severity classification rubric` into a Python-owned contract but does not update the file-level Binding convention, which still lists "the severity-classification rubric used in Gate B" as orchestrator input. Step 3.5 loaders can treat deleted prose as still authoritative alongside `gate-b-counts` / preview KVs, undermining removal of read-classify-format orchestration.
- **Proposed resolution**: In `### Binding convention`, replace the severity-rubric clause with Python-owned Gate B surfaces (`plan-review gate-b-counts`, `preview --variant gate-b`, `plan-review gate-b-finding-line`) as the sole severity/table/one-by-one sources.



### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:108-116
- **Concern**: Gate B preview must emit raw rejected/OOS artifacts, not `emit-rejected` filtering. Scenario: The plan requires rejected/OOS context in `--variant gate-b` preview but does not forbid reusing `emit_rejected_findings`, which filters blocks against the applied-finding ledger (#4849). At Gate B (pre-apply, often with prior-round ledger entries), filtered output can hide rejected blocks the operator still needs for the explicit chooser.
- **Proposed resolution**: In the `gate-b` preview branch, read and print `rejected-findings.md` and `oos.md` directly when non-empty; do not call `plan-review emit-rejected`. Add a test with a populated applied ledger plus rejected blocks asserting preview stdout still contains them.



### FINDING_3:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:129-132
- **Concern**: Prompt still cross-references deleted Severity classification rubric. Scenario: The `### Prompt` rewrite covers count interpolation and forbids block re-classification but does not repoint the "Question text depends on which rubric applies (see **Severity classification rubric**)" line or replace the structured/fallback template bullets with `GATE_B_SEVERITY_MODE`-driven wording. After the rubric section is deleted, explicit-mode Gate B can reference a missing anchor or reintroduce manual rubric selection.
- **Proposed resolution**: Replace the Prompt rubric pointer with `GATE_B_SEVERITY_MODE` from `gate-b-counts` and keep the two question templates keyed only on that KV; remove any remaining link to `### Severity classification rubric`.



### FINDING_4:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:11
- **Concern**: Binding convention still names orchestrator-owned Gate B severity rubric. Scenario: The plan rewrites `### Severity classification rubric` into a Python-owned contract but leaves the file-level Binding convention citing "the severity-classification rubric used in Gate B" as normative orchestrator input. Step 3.5 loaders can treat manual rubric prose as still authoritative alongside `gate-b-counts` KVs, undermining removal of read-classify-format orchestration.
- **Proposed resolution**: In `### UPDATED: skills/design/references/approval-gates.md`, replace line 11 so Gate B severity mode, counts, table rows, and one-by-one fields are authoritative from the three Python verbs only; drop "severity-classification rubric" as orchestrator-owned input.



### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py
- **Concern**: Gate B preview must emit raw rejected/OOS artifacts, not filtered emit-rejected output. Scenario: The plan says preview should print `rejected-findings.md` and `oos.md` when non-empty but does not forbid reusing `emit_rejected_findings`, which filters blocks against the cumulative applied-finding ledger (#4849). At Gate B (pre-apply, often after prior-round ledger entries), filtered output can hide rejected blocks the operator still needs for context.
- **Proposed resolution**: In the `gate-b` preview branch, read and print raw `rejected-findings.md` / `oos.md` bytes (symlink-safe like other artifacts); explicitly do not call `emit_rejected_findings`. Add a test with a prior-round applied key plus a re-raised rejected block to lock unfiltered Gate B context.



### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:129
- **Concern**: Prompt still routes mode selection through the rubric section instead of `GATE_B_SEVERITY_MODE`. Scenario: The plan updates `### Prompt` to interpolate counts from `gate-b-counts` but does not replace "Question text depends on which rubric applies (see **Severity classification rubric**)" with KV-driven mode selection. The orchestrator may re-inspect finding blocks to pick structured vs fallback wording instead of binding solely to `GATE_B_SEVERITY_MODE` from stdout.
- **Proposed resolution**: In the Prompt rewrite, delete the rubric cross-reference; branch question text only on `GATE_B_SEVERITY_MODE=structured|fallback` from `gate-b-counts`, using the two existing count templates without re-reading blocks.



### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:11
- **Concern**: Binding convention still names orchestrator severity-classification rubric as normative Gate B input. Scenario: The plan rewrites `### Severity classification rubric` into a Python-owned contract but does not update the file-level Binding convention line. Step 3.5 loaders can still treat manual rubric prose as authoritative alongside `gate-b-counts` / preview KVs, undermining the acceptance goal to remove read-classify-format orchestration.
- **Proposed resolution**: In the `### UPDATED: skills/design/references/approval-gates.md` section, replace Binding convention text so Gate B severity mode, counts, table rows, and one-by-one fields are authoritative only from the three Python verbs; remove any claim that an orchestrator-owned rubric remains normative.



### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:108-116
- **Concern**: Gate B preview must read raw rejected/OOS artifacts, not `emit_rejected_findings`. Scenario: The plan requires rejected/OOS context at Gate B (pre-apply) but only says to print `rejected-findings.md` and `oos.md` when non-empty. It does not forbid reusing `emit_rejected_findings`, which filters blocks against the applied-finding ledger (#4849). On multi-round runs with ledger entries, filtered output can hide rejected blocks the operator still needs for Gate B context.
- **Proposed resolution**: In the `emit_design_plan_preview` `gate-b` branch spec, require direct byte-faithful reads of on-disk `rejected-findings.md` and `oos.md` (symlink/non-file treated like missing) and explicitly forbid `emit_rejected_findings` / applied-ledger filtering. Add a regression test where ledger keys would filter a block under `emit-rejected` but `preview --variant gate-b` still prints it.



### FINDING_9:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/references/approval-gates.md:11
- **Concern**: The plan rewrites Gate B severity handling into Python but does not update the file-level Binding convention line that still names the orchestrator severity-classification rubric as normative Gate B input.. Scenario: Step 3.5 loads approval-gates.md as the single normative source; the binding line still tells the orchestrator the manual rubric is authoritative alongside the new gate-b-counts and preview verbs, undermining the acceptance goal to remove read-classify-format orchestration.
- **Proposed resolution**: Add a Binding convention bullet in the approval-gates.md update: Gate B severity mode, counts, table rows, and one-by-one prompt fields are authoritative only from python/cli.py plan-review gate-b-counts, preview --variant gate-b, and gate-b-finding-line; remove severity-classification rubric as orchestrator input.



### FINDING_10:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:129
- **Concern**: The plan updates ### Prompt count interpolation but does not replace the intro line that still says Question text depends on which rubric applies (see Severity classification rubric).. Scenario: After the rubric section is deleted or rewritten into a Python-owned contract, that cross-reference still routes operators and orchestrators back to removed manual classification prose instead of GATE_B_SEVERITY_MODE plus gate-b-counts KVs.
- **Proposed resolution**: Rewrite the ### Prompt intro to branch on GATE_B_SEVERITY_MODE from gate-b-counts stdout and delete the see Severity classification rubric pointer.



### FINDING_11:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: python/plan_review.py:108-116
- **Concern**: The gate-b preview variant must read rejected-findings.md and oos.md directly and must not reuse emit_rejected_findings applied-ledger filtering.. Scenario: The plan says to print those files when non-empty but does not forbid calling emit_rejected_findings; on multi-round runs with prior applied-finding ledger entries, that helper filters rejected blocks (#4849) and Gate B pre-apply presentation can hide rejected context the operator still needs.
- **Proposed resolution**: In the gate-b early-return branch, read and print raw file bytes for rejected-findings.md and oos.md; explicitly forbid emit_rejected_findings and any applied-ledger filtering; add a fixture test with a populated ledger proving unfiltered rejected blocks still appear.



### FINDING_12:
- **Reviewer(s)**: Codex-Generic
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/references/approval-gates.md:140-149; python/plan_review_tally.py:658-706
- **Concern**: Accepted Go-through-each Python-source fix still lacks ordered finding-id enumeration. Scenario: `gate-b-finding-line` requires a numeric `FINDING_N`, but `gate-b-counts` emits only totals and the plan says to iterate "for each finding" without a Python-owned ordered ID list. Accepted artifacts can be non-contiguous because tally appends only accepted items from sorted FINDING ids, for example FINDING_1 and FINDING_3 when FINDING_2 was rejected. A 1..ACCEPTED_COUNT loop would call unknown id 2, fail Step 3.5, or skip FINDING_3.
- **Proposed resolution**: Have the same Python row renderer emit an ordered machine surface, such as `FINDING_IDS=1,3` from `gate-b-counts` plus ordinal/total for headers, or add a single verb that emits all one-by-one prompt lines in order. Update the Approval Gates one-by-one instructions to iterate that Python-emitted list, not an implied contiguous range.



