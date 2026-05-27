### FINDING_1: [OUT_OF_SCOPE] Helper rc=2 fail-opens or is inconsistently specified
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Step 0b proceeds on `lib-design-reentry-guard.sh` return code 2, so invalid input, an empty `HOME`, or a corrupted/badly bound PPID can bypass an existing marker. The prose, plan, and reference Bash contract also disagree on this behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Treat return 2 as refuse after ISSUE_NUMBER validation or add explicit re-validate before proceed.
  - From cursor-specialist-edge-cases-output.txt: Refuse or abort on return 2 when issue/ppid were bound from gh; only soft-fail for pre-binding errors.
  - From cursor-specialist-plan-fidelity-output.txt: Align plan and reference bash with item 4, or remove item 4 to match plan-only miss/hit semantics.

### FINDING_2: Final-summary marker path reconstruction can drift or use the wrong fallback
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-integration-contract-output.txt
- **Severity**: important
- **Concern**: `render-final-summary.sh` duplicates the marker-path grammar and references a fallback PPID variable that is not set on the branch. If guard state is not carried across shell boundaries, the cancelled-reentry summary can render `Marker: N/A` or reconstruct the wrong path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Source lib and call design_reentry_marker_path when env unset.
  - From dyn-integration-contract-output.txt: Extend the fallback to `${LARCH_DESIGN_REENTRY_GUARD_PPID:-${DESIGN_REENTRY_GUARD_PPID:-$PPID}}` and/or call `design_reentry_marker_path` when `ISSUE_NUMBER` is set, so the renderer self-heals without relying on non-persisted exports.

### FINDING_3: Sourced re-entry guard library is missing from dead-script excludes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `scripts/lib-design-reentry-guard.sh` is sourced-only but is not excluded in `agent-lint.toml`, so `make lint` / pre-commit can flag it as dead.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Add lib to agent-lint.toml exclude with comment mirroring lib-title-eligibility.
  - From cursor-specialist-testing-output.txt: Add scripts/lib-design-reentry-guard.sh (and .md if needed) to agent-lint.toml exclude alongside lib-title-eligibility.sh.
  - From cursor-specialist-plan-fidelity-output.txt: Add scripts/lib-design-reentry-guard.sh to exclude with sourced-only comment mirroring lib-title-eligibility.sh.

### FINDING_4: Reference Bash KV parser duplicates the library contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: The large Bash parser example in `SKILL.md` repeats the helper contract and can drift from `lib-design-reentry-guard.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Trim reference block; rely on lib-design-reentry-guard.md contract.

### FINDING_5: [OUT_OF_SCOPE] Broken marker mtime is treated as absent and not cleaned
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-bash32-output.txt
- **Severity**: latent
- **Concern**: Existing marker files with mtime `0`, unreadable/non-numeric stat output, or failed stat resolution are reported as absent and left in place, which can silently neutralize the guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Document edge case or accept mtime 0 when stat succeeds.
  - From cursor-specialist-correctness-output.txt: On non-positive mtime use invalid-mtime path with best-effort rm -f.
  - From cursor-specialist-edge-cases-output.txt: Align comment with !=0 check or allow 0 if ever needed.
  - From dyn-shell-bash32-output.txt: On the `[ -f "$marker_path" ]` branch, if mtime resolution fails, best-effort `rm -f "$marker_path"` (or return a distinct `REASON=unreadable` and treat as hit) so a broken marker cannot silently neutralize the guard; add a harness fixture that creates a marker and forces both stat paths to fail (e.g., permission fixture where feasible).

### FINDING_6: [OUT_OF_SCOPE] Guard placement does not address the `[DESIGNED]` re-entry path
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-shell-bash32-output.txt
- **Severity**: latent
- **Concern**: The new session-cache guard runs after the lifecycle title/body filter, so re-entry on an already `[DESIGNED]` issue still reaches the skill and exits at Step 2.5 rather than the new guard.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Accept as defense-in-depth only, or add follow-up to stop orchestrator re-invocation; do not treat this PR alone as satisfying feature acceptance #1 for the reported path.
  - From cursor-specialist-edge-cases-output.txt: Acknowledge scope limit or file follow-up for external re-entry; guard targets untagged-title gap only.

### FINDING_7: Marker write before `PLAN_WRITE_OK=true` can block retry after crash
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Step 5.5 writes the marker before setting `PLAN_WRITE_OK=true`; a crash between those steps can make a retry hit the session-cache refusal even though the completed-run flag was never set.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document intentional friction or gate marker write on PLAN_WRITE_OK if product wants otherwise.

### FINDING_8: No end-to-end test ties marker write to Step 0b refusal
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Current tests cover unit behavior and structure, but not a full flow where Step 5c writes a marker and the next Step 0b invocation refuses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add integration-style harness: write marker then hit; or design-driver two-entry simulation.

### FINDING_9: Marker write failure path is untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The planned `MARKER_WRITE_FAILED` / `append-tool-failure` path lacks a filesystem-failure fixture, so a regression that leaves no marker may not be caught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Add fixture with failing mkdir/touch; assert stderr KV and non-zero rc.

### FINDING_10: Session-cache banner test only matches a partial prefix
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check 26 can pass even if the refusal banner loses its wait, override, or delete instructions.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Grep full banner literal or additional required substrings.

### FINDING_11: Step 0b structural check can pass without executable guard wiring
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Check 24 can pass on prose mentions of `design_reentry_marker_hit`, without proving the guard is wired in an executable Bash block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Anchor check on _reentry_out= or source line inside Step 0b fence.

### FINDING_12: [OUT_OF_SCOPE] Marker write follows local symlinks
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `touch "$marker_path"` follows symlinks at a predictable cache path, so a local actor who can plant that symlink can mutate another file’s mtime.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] Weak sessions-directory posture can allow local marker planting
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: If `~/.cache/larch/sessions/` is writable by another local UID, that user can plant guard markers and deny `/design` for the TTL window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_14: Refusal banner hardcodes `~/.cache` instead of the actual marker path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The banner tells operators to delete a `~/.cache` path even though the helper uses `$HOME`; with a non-tilde `HOME`, the operator may delete the wrong file and remain blocked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use design_reentry_marker_path / DESIGN_REENTRY_MARKER_PATH in banner text; update Check 26 literal accordingly.

### FINDING_15: Guard key uses volatile shell `PPID` instead of stable Claude pid
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Marker write and hit both use shell `$PPID`; nested Bash invocations can change that value between Step 5c and Step 0b, causing the guard to miss.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Use the same claude-pid variable written by write-design-current-env for both write and hit; pin in test-design-structure.sh.

### FINDING_16: Five-minute TTL admits delayed spurious re-entry
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After the 300-second TTL expires, a delayed re-entry on an untagged issue with a plan can still be admitted, so the original symptom can recur outside the TTL window.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Extend TTL, refresh policy, or narrow acceptance to gap case within TTL; document late re-entry limitation.

### FINDING_17: Step 5c marker write is prose-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: The marker write is not pinned in a fenced Bash block, so an orchestrator can omit it and leave the guard ineffective.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add fenced 5.5 block with prelude + write call, or structural harness pin for mandatory execution pattern.

### FINDING_18: [OUT_OF_SCOPE] Stale markers are only swept for a matching key
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Old markers for dead PPIDs linger because cleanup only happens when the same issue/PPID key is checked.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Optional periodic sweep follow-up; plan already notes footprint.

### FINDING_19: Guard-hit reference Bash omits the final summary invocation
- **Reviewer(s)**: dyn-integration-contract-output.txt, dyn-prompt-orchestrator-output.txt
- **Severity**: important
- **Concern**: The guard-hit reference block says to run the final summary but only contains a comment before printing the refusal banner and exiting. An orchestrator following that fence literally will skip the structured cancelled-reentry summary.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-integration-contract-output.txt: Replace the comment with the full Final summary fence body (or a direct `render-final-summary.sh --outcome cancelled-reentry-guard --post-publish-only` call) between the exports and the stderr banner, and align prose/reference ordering so summary render precedes banner emission.
  - From dyn-prompt-orchestrator-output.txt: Inline the same `render-final-summary.sh --post-publish-only` callsite from the `### Final summary block` fence (lines 330–345) into the guard-hit branch before the `printf` banner, or delete the partial reference fence and point only at the shared fence like sub-step 2.5 refuses do; add a structural check that the Step 0b guard-hit path references `render-final-summary.sh` / `cancelled-reentry-guard` between `design_reentry_marker_hit` and the session-cache banner.

### FINDING_20: Guard-hit tmpdir preservation wording omits the cleanup invariant
- **Reviewer(s)**: dyn-prompt-orchestrator-output.txt
- **Severity**: nit
- **Concern**: The guard-hit path says to preserve `$DESIGN_TMPDIR` but does not explicitly mirror the sibling refusal wording that Step 6 cleanup is gated on `PLAN_WRITE_OK=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestrator-output.txt: Mirror line 190’s parenthetical on sub-step 2.6 step 3: e.g. “`$DESIGN_TMPDIR` is preserved (Step 6 cleanup gates on `PLAN_WRITE_OK=true`; it is unset on this path).”

### FINDING_21: [OUT_OF_SCOPE] Step ordering test does not anchor sub-step 2.6
- **Reviewer(s)**: dyn-prompt-orchestrator-output.txt
- **Severity**: nit
- **Concern**: The existing structure test still pins `2 → 2.5 → 3` without anchoring the new sub-step 2.6 in that ordering check.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-prompt-orchestrator-output.txt: Check (20) still pins ordering `2 → 2.5 → 3` without anchoring sub-step **2.6**; check (24) covers guard placement but (20) could be extended so both checks fail if 2.6 regresses.
