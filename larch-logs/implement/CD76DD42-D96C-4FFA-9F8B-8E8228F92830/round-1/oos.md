### FINDING_1: [OUT_OF_SCOPE] Helper rc=2 fail-opens or is inconsistently specified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Step 0b proceeds on `lib-design-reentry-guard.sh` return code 2, so invalid input, an empty `HOME`, or a corrupted/badly bound PPID can bypass an existing marker. The prose, plan, and reference Bash contract also disagree on this behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Treat return 2 as refuse after ISSUE_NUMBER validation or add explicit re-validate before proceed.
  - From cursor-specialist-edge-cases-output.txt: Refuse or abort on return 2 when issue/ppid were bound from gh; only soft-fail for pre-binding errors.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan and reference bash with item 4, or remove item 4 to match plan-only miss/hit semantics.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted

### FINDING_12: [OUT_OF_SCOPE] Marker write follows local symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `touch "$marker_path"` follows symlinks at a predictable cache path, so a local actor who can plant that symlink can mutate another file’s mtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_13: [OUT_OF_SCOPE] Weak sessions-directory posture can allow local marker planting
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If `~/.cache/larch/sessions/` is writable by another local UID, that user can plant guard markers and deny `/design` for the TTL window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_18: [OUT_OF_SCOPE] Stale markers are only swept for a matching key
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Old markers for dead PPIDs linger because cleanup only happens when the same issue/PPID key is checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional periodic sweep follow-up; plan already notes footprint.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=exonerated

### FINDING_21: [OUT_OF_SCOPE] Step ordering test does not anchor sub-step 2.6
- **Reviewer(s)**: dyn-prompt-orchestrator-output.txt
- **Severity**: nit
- **Concern**: The existing structure test still pins `2 → 2.5 → 3` without anchoring the new sub-step 2.6 in that ordering check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestrator-output.txt: Check (20) still pins ordering `2 → 2.5 → 3` without anchoring sub-step **2.6**; check (24) covers guard placement but (20) could be extended so both checks fail if 2.6 regresses.

Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_5: [OUT_OF_SCOPE] Broken marker mtime is treated as absent and not cleaned
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-bash32-output.txt
- **Severity**: latent
- **Concern**: Existing marker files with mtime `0`, unreadable/non-numeric stat output, or failed stat resolution are reported as absent and left in place, which can silently neutralize the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document edge case or accept mtime 0 when stat succeeds.
  - From cursor-specialist-correctness-output.txt: On non-positive mtime use invalid-mtime path with best-effort rm -f.
  - From cursor-specialist-edge-cases-output.txt: Align comment with !=0 check or allow 0 if ever needed.
  - From dyn-shell-bash32-output.txt: On the `[ -f "$marker_path" ]` branch, if mtime resolution fails, best-effort `rm -f "$marker_path"` (or return a distinct `REASON=unreadable` and treat as hit) so a broken marker cannot silently neutralize the guard; add a harness fixture that creates a marker and forces both stat paths to fail (e.g., permission fixture where feasible).


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_6: [OUT_OF_SCOPE] Guard placement does not address the `[DESIGNED]` re-entry path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-bash32-output.txt
- **Severity**: latent
- **Concern**: The new session-cache guard runs after the lifecycle title/body filter, so re-entry on an already `[DESIGNED]` issue still reaches the skill and exits at Step 2.5 rather than the new guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Accept as defense-in-depth only, or add follow-up to stop orchestrator re-invocation; do not treat this PR alone as satisfying feature acceptance #1 for the reported path.
  - From cursor-specialist-edge-cases-output.txt: Acknowledge scope limit or file follow-up for external re-entry; guard targets untagged-title gap only.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

