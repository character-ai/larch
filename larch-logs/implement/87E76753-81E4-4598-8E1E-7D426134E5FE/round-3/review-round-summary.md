# Review Round 3

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 0
- Exonerated findings: 5
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Coder prompt treats suggested revisions as mandatory implementation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-security-output.txt, cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Concern**: `compose_coder_prompt` / related copy stresses implementing what suggested revisions call for, without a clear, plan-aligned statement that bullets are informational hints and the coder designs the minimal fix and decides the exact change. That mismatch can push external coders to over-scope or literalize merged bullets versus the informational-fix protocol.
- **Suggested revision**: Reword the coder handoff so proposals guide but do not mandate patches; add an explicit single-sentence coder-autonomy line consistent with docs and the agreed plan.


### FINDING_2: Unplanned `PLAN_FILE` / `diff_lines` snippet injected into coder prompt
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, cursor-specialist-structure-output.txt
- **Concern**: Injecting plan-file diff line metadata couples the coder dispatch to `PLAN_FILE`, adds I/O and prompt noise, and was not described as in-scope in the implementation plan; behavior and bounds are undocumented.
- **Suggested revision**: Remove the injection unless separately specified; if kept, document the contract, cap reads, and align review/voting handoff docs.


### FINDING_3: Revision traceability uses an over-broad input corpus per slot
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Trace checks can draw from a global per-slot corpus keyed only by overlapping reviewers (not the specific contributing input finding blocks), and an empty reviewer-intersection path can widen to all slot blocks. That allows substring matches against unrelated “From” text from another finding for the same slot, weakening advisory traceability and enabling wrong cross-merge quotes to pass.
- **Suggested revision**: Narrow the searchable corpus to merged-source provenance (e.g., per contributing finding id/block) or require matches within a single contributing block; on empty scoped sets, warn or fail instead of widening candidates; document advisory, non-cryptographic semantics if intentional.


### FINDING_7: Voter informational-fix guardrail lacks regression coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: `dispatch-code-voters.sh` adds informational-fix guidance without a harness assertion, so refactors could drop or alter the line while CI still passes.
- **Suggested revision**: Add a substring/golden check in `test-dispatch-code-voters*` on the generated vote prompt (and retry wrapper if applicable).


### FINDING_8: Voter prompt wording drift vs agreed “dislike/distrust” protocol copy
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: The voter prompt may omit or soften the plan’s “dislike or distrust” phrasing, slightly misaligning with agreed protocol copy in docs/plan.
- **Suggested revision**: Restore plan-aligned dislike/distrust wording to match docs and the agreed plan.


