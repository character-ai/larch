### FINDING_2: Clarify-request id rules — duplicates, gaps, and ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: The spec calls out duplicate-response behavior but not duplicate `larch:clarify-request` comments with the same id, non-monotonic ids, or gaps before any response, leaving no canonical pairing or progress rule for automation (concurrent posts / edit glitches).
- **Suggested revision**: Add normative ambiguity/reconciliation rules analogous to duplicate-response handling (e.g. treat duplicate same-id requests as ambiguous; require a single canonical request per id before pairing).


### FINDING_6: Clarification markers section reads as already shipped
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Present-tense wording for `/implement` audit and posting of clarification markers contradicts the intro disclaimer that behavior is not yet implemented, so skimmers may assume production already posts `larch:clarify-request` comments.
- **Suggested revision**: Lead the clarification subsection with a target-workflow / not-yet-implemented qualifier and use future or conditional tense for non-shipped behavior.


### FINDING_8: Which GitHub issue carries plan body vs clarification vs tracking summaries
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Relationship between feature issue vs tracking issue for plan-body markers, clarification threads, and tracking-issue summaries is not specified; automation could attach markers to the wrong thread and break pairing rules across issues.
- **Suggested revision**: Document whether body markers and clarification markers target the same issue as tracking-issue summaries and how they relate when human plan content lives on a different issue than the tracking issue.


