### FINDING_1: Conflicting ownership of sentinel-recovery `run-statistics` writes
- **Reviewer(s)**: Cursor-Arch, Cursor-Edge, Cursor-Innovation, Codex-Arch, Codex-Edge, Codex-Innovation, Cursor-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-contract-cartographer, Codex-dyn-contract-cartographer
- **Severity**: important
- **Concern**: The plan preserves NEVER #5 byte-stable even though it still instructs sentinel recovery in Step 9a.1 to write `run-statistics`, while the new OOS pipeline/checkpoint flow requires `run-statistics` to be written only after `oos-disposition-checkpoint.sh` succeeds. This creates conflicting instructions and can reintroduce pre-checkpoint stats drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Edge, Cursor-Innovation: An orchestrator that loads oos-pipeline.md then follows NEVER #5 can write run-statistics before oos-disposition-checkpoint.sh, conflicting with NEVER #14, the Step 8+ OOS checkpoint block (~1042), and the plan’s pre-checkpoint-stats failure mode In the SKILL.md update, narrow NEVER #5 How-to-apply to oos-issues append (and terminal-summary refresh if needed) on sentinel recovery, or add an explicit precedence line in oos-pipeline.md Contract that post-checkpoint SKILL.md owns run-statistics and overrides NEVER #5 for that batch
  - From Codex-Arch, Codex-Edge: Revise the plan to minimally edit NEVER #5 so sentinel recovery writes only recovered oos-issues evidence and terminal summary content; keep run-statistics owned by the post-checkpoint Step 8+ block
  - From Codex-Innovation: Update NEVER #5 minimally to remove the run-statistics write from sentinel recovery and state that only the oos-issues batch is written there; keep run-statistics in the post-checkpoint block
  - From Cursor-Pragmatic: In `oos-pipeline.md` step 3/7 (or **Contract**), state explicitly that idempotent recovery writes only the `oos-issues` batch here and that NEVER #5’s `run-statistics` half is satisfied solely by the existing post-checkpoint Step 8+ block after checkpoint exit 0
  - From Cursor-Requirements: Add explicit precedence in oos-pipeline.md step 3 or Contract: sentinel branch writes oos-issues only; run-statistics stays post-checkpoint per NEVER #14 and the Step 8+ block—or allow a minimal NEVER #5 How-to-apply edit removing the run-statistics clause
  - From Codex-Requirements: Make the minimal SKILL.md exception: update NEVER #5 to require only the recovered oos-issues log write on sentinel recovery, and state run-statistics remains owned by the post-checkpoint block.
  - From Cursor-dyn-contract-cartographer: Reconcile explicitly: either narrow NEVER #5 to `oos-issues` append only on sentinel recovery (stats only after `oos-disposition-checkpoint.sh` exit 0 per skills/implement/SKILL.md:1042-1042) or add a one-line exception in oos-pipeline step 3 that cites NEVER #5 — do not leave both texts unchanged
  - From Codex-dyn-contract-cartographer: Do not keep NEVER #5 byte-stable here; revise only its run-statistics clause so sentinel recovery writes the oos-issues batch/summary evidence and explicitly leaves run-statistics to the post-checkpoint block.


### FINDING_3: Security filtering predicate does not match checkpoint counting predicate
- **Reviewer(s)**: Codex-Pragmatic, Codex-dyn-contract-cartographer
- **Severity**: important
- **Concern**: The proposed OOS pipeline security-filter language may exclude blocks using a broader `focus-area=security` token than the checkpoint actually recognizes. The current gate/counting logic excludes only a dedicated `- **focus-area**: security` field line, so a block filtered or privately routed by the new procedure may still be counted as non-security by the checkpoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Align the new reference with the current gate rule, or add the minimal gate/awk/checkpoint or accepted-artifact cleanup step so security-routed blocks are not counted after Step 9a.1.
  - From Codex-dyn-contract-cartographer: In oos-pipeline.md Step 1 cite oos-disposition-gate.md Counting rules or oos-non-security-block-count.awk and state the exact dedicated field-line predicate; do not use the broader shared voting token unless gate/tests are also changed.

