### FINDING_39: [OUT_OF_SCOPE] Branch mixes non–Phase-5 commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Non–Phase-5 commits (e.g., upgrade-larch/version noise) are mixed into the branch, making Phase 5 regressions harder to spot in review and CI attribution.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_40: [OUT_OF_SCOPE] `rebase.py` changes outside Phase 5 plan
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Large `rebase.py` changes are not in the Phase 5 plan; unrelated rebump API changes ride with merge/logging port work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_41: [OUT_OF_SCOPE] Push tests use stale argv tuples
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Push tests use stale argv tuples; index-based runner masks refspec regressions—tests would not detect if `push_branch` changed `git` argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_42: [OUT_OF_SCOPE] Inline-triage test does not exercise counting
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Inline-triage test uses a JSON accepted file so `non_security_count` stays 0; test passes without exercising inline-triage counting.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=1 Result=accepted

### FINDING_43: [OUT_OF_SCOPE] `pr_checks_all_pass` text fallback (bash parity)
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `pr_checks_all_pass` text fallback inherited from `merge-pr.sh`; misleading `gh` checks text could contribute to merge when JSON path fails—same as bash; tighten only with coordinated `merge-pr.sh` change.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

### FINDING_44: [OUT_OF_SCOPE] `capture-session-transcript.sh` `TRANSCRIPT_PATH` not root-confined
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `TRANSCRIPT_PATH` is not confined to session/project roots in bash (pre-existing); arbitrary file read into transcript pipeline.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_45: [OUT_OF_SCOPE] Bash `ship-pr.sh` refresh vs Python in-merge flush contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Bash merge path does not call refresh before `merge-pr.sh`; Phase 7 must define whether Python in-merge flush replaces or duplicates push-time refresh.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=1 Result=exonerated

### FINDING_46: [OUT_OF_SCOPE] Comprehensive bash merge harness vs Python parity gap
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/test-merge-pr.sh` remains comprehensive while Python parity is the gap; Phase 7 cutover risk is Python-specific, not bash regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---

**Merge notes (diagnostic, not votes):** Input items 61–63 and duplicate OOS echoes of FINDING_1–2 were subsumed into in-scope FINDING_1–2 or dropped as non-actionable positive observation (61). Dyn slots contributed substantive fix text only where quoted above; other slots uniformly said “Address the concern above.” Total: **38** normalized blocks (**32** in-scope, **6** `[OUT_OF_SCOPE]`).

Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=1 Result=exonerated

