### OOS_1: [OUT_OF_SCOPE] PR mixes unrelated feature commits
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: PR mixes design-publish extraction with upgrade-larch, version bump, and larch-logs commits. Harder review and bisect; unrelated failures blur feature signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Split PRs or isolate commits when possible.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### OOS_2: [OUT_OF_SCOPE] Makefile shard 16 growing heavier
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Shard 16 is already heavy; two more targets were added. Full CI shard runs take longer; harder to attribute timeouts.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Consider shard split in a follow-up (not introduced solely by design-publish).


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### OOS_3: [OUT_OF_SCOPE] Step 0b init driver lacks exit-3 continue handling
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Step 0b init driver handoff lacks exit-3 continue handling. Same abort pattern as Step 5c would apply if `design-init-runparams` ever adopts exit 3. Not introduced by this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: fix only if init driver gains exit 3.

Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

