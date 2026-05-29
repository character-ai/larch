### FINDING_1: [OUT_OF_SCOPE] Round-2 prose still routes discussion only via Gate B Switch
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: After passive-summary removal on `LOOP_STATUS=converged|cap-hit` auto runs, `skills/design/SKILL.md:1148` still describes Round-2 discussion re-entry only through Gate B’s **Switch to discussion mode**. On those runs Gate B no longer presents that prompt; discussion re-entry is at Gate C (**Discuss further**). Manual Gate B paths are unchanged. Orchestrators may search for a Gate B switch that no longer exists instead of Gate C.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: add “or Gate C **Discuss further**” for accuracy on passive-summary runs.
  - From cursor-specialist-structure-output.txt: Reword to distinguish manual Gate B Switch vs passive-summary Gate C Discuss further or generalize to both gates.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_3: [OUT_OF_SCOPE] Step 3.5 groups passive-summary with Step 2b.5-dependent paths (`SKILL.md:1145`)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Step 3.5 still groups `passive-summary auto-continue` with paths that require “**and Step 2b.5 returns**” before Step 3.6, while `approval-gates.md` passive-summary explicitly skips re-apply and the shared post-apply pipeline (hence no Gate B–driven Step 2b.5). Pre-existing tension; `approval-gates.md` is normative and already routes passive-summary straight to Step 3.6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: qualify that clause so Step 2b.5 applies only to paths that run `ACTION=EMIT_PLAN` at Gate B (auto-apply / Apply all / one-by-one), not passive-summary auto-continue.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_5: [OUT_OF_SCOPE] Global anti-halt reminder omits passive-summary table (`SKILL.md:30`)
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Global anti-halt reminder does not cite passive-summary table output. Pre-existing; branch-specific mitigation added in `approval-gates.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional cross-reference in SKILL anti-halt bullet.

Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

