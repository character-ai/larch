### [Plan Review] FINDING_1

### FINDING_1: Binding convention still names orchestrator severity rubric as normative
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan rewrites Gate B severity handling into Python-owned surfaces but does not update the file-level `### Binding convention` in `skills/design/references/approval-gates.md` (line 11), which still lists "the severity-classification rubric used in Gate B" as normative orchestrator input. Step 3.5 loaders can treat deleted or superseded manual rubric prose as still authoritative alongside `gate-b-counts` and preview KVs, undermining removal of read-classify-format orchestration.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In `### Binding convention`, replace the severity-rubric clause with Python-owned Gate B surfaces (`plan-review gate-b-counts`, `preview --variant gate-b`, `plan-review gate-b-finding-line`) as the sole severity/table/one-by-one sources.
  - From Cursor-Innovation: In `### UPDATED: skills/design/references/approval-gates.md`, replace line 11 so Gate B severity mode, counts, table rows, and one-by-one fields are authoritative from the three Python verbs only; drop "severity-classification rubric" as orchestrator-owned input.
  - From Cursor-Pragmatic: In the `### UPDATED: skills/design/references/approval-gates.md` section, replace Binding convention text so Gate B severity mode, counts, table rows, and one-by-one fields are authoritative only from the three Python verbs; remove any claim that an orchestrator-owned rubric remains normative.
  - From Cursor-Requirements: Add a Binding convention bullet in the approval-gates.md update: Gate B severity mode, counts, table rows, and one-by-one prompt fields are authoritative only from python/cli.py plan-review gate-b-counts, preview --variant gate-b, and gate-b-finding-line; remove severity-classification rubric as orchestrator input.


### [Plan Review] FINDING_2

### FINDING_2: Gate B preview must emit raw rejected/OOS artifacts, not emit-rejected filtering
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-Requirements
- **Severity**: important
- **Concern**: The plan requires rejected/OOS context in `--variant gate-b` preview but does not forbid reusing `emit_rejected_findings`, which filters blocks against the cumulative applied-finding ledger (#4849). At Gate B (pre-apply, often with prior-round ledger entries), filtered output can hide rejected blocks the operator still needs for the explicit chooser and context.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: In the `gate-b` preview branch, read and print `rejected-findings.md` and `oos.md` directly when non-empty; do not call `plan-review emit-rejected`. Add a test with a populated applied ledger plus rejected blocks asserting preview stdout still contains them.
  - From Cursor-Innovation: In the `gate-b` preview branch, read and print raw `rejected-findings.md` / `oos.md` bytes (symlink-safe like other artifacts); explicitly do not call `emit_rejected_findings`. Add a test with a prior-round applied key plus a re-raised rejected block to lock unfiltered Gate B context.
  - From Cursor-Pragmatic: In the `emit_design_plan_preview` `gate-b` branch spec, require direct byte-faithful reads of on-disk `rejected-findings.md` and `oos.md` (symlink/non-file treated like missing) and explicitly forbid `emit_rejected_findings` / applied-ledger filtering. Add a regression test where ledger keys would filter a block under `emit-rejected` but `preview --variant gate-b` still prints it.
  - From Cursor-Requirements: In the gate-b early-return branch, read and print raw file bytes for rejected-findings.md and oos.md; explicitly forbid emit_rejected_findings and any applied-ledger filtering; add a fixture test with a populated ledger proving unfiltered rejected blocks still appear.


### [Plan Review] FINDING_3

### FINDING_3: Prompt still cross-references deleted Severity classification rubric
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Requirements
- **Severity**: important
- **Concern**: The `### Prompt` rewrite covers count interpolation and forbids block re-classification but does not repoint the "Question text depends on which rubric applies (see **Severity classification rubric**)" line or replace structured/fallback template selection with `GATE_B_SEVERITY_MODE`-driven wording. After the rubric section is deleted, explicit-mode Gate B can reference a missing anchor or reintroduce manual rubric selection instead of binding solely to `GATE_B_SEVERITY_MODE` from `gate-b-counts`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Replace the Prompt rubric pointer with `GATE_B_SEVERITY_MODE` from `gate-b-counts` and keep the two question templates keyed only on that KV; remove any remaining link to `### Severity classification rubric`.
  - From Cursor-Innovation: In the Prompt rewrite, delete the rubric cross-reference; branch question text only on `GATE_B_SEVERITY_MODE=structured|fallback` from `gate-b-counts`, using the two existing count templates without re-reading blocks.
  - From Cursor-Requirements: Rewrite the ### Prompt intro to branch on GATE_B_SEVERITY_MODE from gate-b-counts stdout and delete the see Severity classification rubric pointer.


