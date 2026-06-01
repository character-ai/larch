### OOS_1: [OUT_OF_SCOPE] Unrelated `upgrade-larch.sh` changes on Phase 5 branch
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unrelated upgrade-larch changes mixed into the Phase 5 branch make Phase 5 review harder in isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] `rebase.py` / version_bump edits outside Phase 5 scope
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Rebase/version_bump changes are not on the Phase 5 module list; bundled adjacent parity work adds review noise without being a Phase 5 fidelity gap unless scope is expanded.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### OOS_3: [OUT_OF_SCOPE] `select_push_remote` hardcodes origin; optional fork upstream
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: `select_push_remote` hardcodes `origin` and `remotes()` is unused; no bash regression vs `git-push.sh`/`create-pr.sh` today—optional future fork/upstream selection if product requires it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_4: [OUT_OF_SCOPE] `gh.py` body temp file permissions on shared `/tmp`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: GH body temp files use default permissions without explicit `chmod` hardening; shared-host `/tmp` readers might read a body file between write and `gh` consumption (pre-existing bash `mktemp` pattern).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

