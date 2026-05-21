Structured finding list after merging duplicate themes and renumbering in first-seen topic order.

```text
### FINDING_1: run-logs cross-reference vs heading and anchors
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Concern**: References to run-logs use wording (“tracking-issue comment contracts”) that does not match the visible section title in `docs/run-logs.md` (e.g. “Tracking issue comments”), increasing search/Ctrl+F friction and risking missed navigation; no stable fragment anchor is cited.
- **Suggested revision**: Point the cross-reference at the real heading text and/or an explicit fragment link such as `docs/run-logs.md#tracking-issue-comments` so visible anchor text matches what readers will find.

### FINDING_2: Clarify-request id rules — duplicates, gaps, and ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: The spec calls out duplicate-response behavior but not duplicate `larch:clarify-request` comments with the same id, non-monotonic ids, or gaps before any response, leaving no canonical pairing or progress rule for automation (concurrent posts / edit glitches).
- **Suggested revision**: Add normative ambiguity/reconciliation rules analogous to duplicate-response handling (e.g. treat duplicate same-id requests as ambiguous; require a single canonical request per id before pairing).

### FINDING_3: STATE machine vs GitHub labels — alignment, decoupling, and clean boundaries
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: `response-pending` and `clean` are easy to misread relative to label presence/absence: operators may assume labels reflect all STATE values; label removal after a design response can diverge from STATE (label gone while STATE is not clean); lead copy can imply labels participate in STATE derivation though rows are marker-only; the transition from `response-pending` to `clean` and mutual exclusion with “post-response but pre-recheck” situations are underspecified, risking wrong readiness/handoff or skipped re-audit.
- **Suggested revision**: Tie the STATE table to the label semantics above (which STATE rows correspond to label present vs absent); state explicitly that labels and marker-derived STATE can be decoupled; tighten wording so labels are not implied unless defined as inputs to STATE; define `clean` vs `response-pending` with a clear ordering/mutual-exclusion rule and the event that exits `response-pending` (e.g. tied to implement re-audit completion).

### FINDING_4: Intro “not parsed/emitted” scope vs shipped `larch:plan` v1 tracking digest
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt
- **Concern**: The opening claim that markers are not parsed or emitted by shipped skills/scripts is read as universal; readers may infer the existing tracking-issue `larch:plan` v1 digest does not exist and mis-diagnose real `/implement` behavior, mis-plan integrations, or duplicate investigation of emission paths.
- **Suggested revision**: Narrow the claim to issue-body plan markers and clarification markers only, and explicitly exclude shipped tracking-issue `larch:plan` v1 from the “not emitted / not parsed” statement.

### FINDING_5: Normative typography — curly quotes around `end`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Curly quotes around `end` are inconsistent with ASCII-first normative spec style.
- **Suggested revision**: Use ASCII quotes or backticks consistently for `end` and similar tokens.

### FINDING_6: Clarification markers section reads as already shipped
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Present-tense wording for `/implement` audit and posting of clarification markers contradicts the intro disclaimer that behavior is not yet implemented, so skimmers may assume production already posts `larch:clarify-request` comments.
- **Suggested revision**: Lead the clarification subsection with a target-workflow / not-yet-implemented qualifier and use future or conditional tense for non-shipped behavior.

### FINDING_7: Lifecycle examples read as today’s runbook despite non-shipped spec
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Numbered happy-path examples read as current shipped behavior even where the doc warns the wire format is not implemented, inviting operators to follow them as a live runbook and misconfigure workflows or file false tooling gaps.
- **Suggested revision**: Prefix the lifecycle section (or each sequence) with an explicit target-sequence label and rephrase steps as conditional future behavior rather than imperative present-day procedure.

### FINDING_8: Which GitHub issue carries plan body vs clarification vs tracking summaries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Relationship between feature issue vs tracking issue for plan-body markers, clarification threads, and tracking-issue summaries is not specified; automation could attach markers to the wrong thread and break pairing rules across issues.
- **Suggested revision**: Document whether body markers and clarification markers target the same issue as tracking-issue summaries and how they relate when human plan content lives on a different issue than the tracking issue.

### FINDING_9: Plan-fidelity review inputs incomplete
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: No design plan, implementation plan, feature description, or issue-anchored plan body was supplied with the bundle, so requirement-by-requirement traceability and completeness checks against intent are indeterminate.
- **Suggested revision**: Attach the relevant plan/design/feature/issue-anchored plan artifacts when re-running plan-fidelity review.
```
