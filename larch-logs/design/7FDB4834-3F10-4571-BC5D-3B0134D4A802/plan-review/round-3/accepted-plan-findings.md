### FINDING_1: Repoint all remaining phantom Out-of-Scope Handling references in Step 8+
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-dyn-cross-ref-integrity
- **Severity**: important
- **Concern**: The planned SKILL.md updates do not unambiguously replace every runtime reference to the non-existent “Out-of-Scope Handling” section. Exit 0, the OOS checkpoint intro, and Exit 1 disposition-gap remediation can still direct operators to a phantom section instead of the canonical triage policy/procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Extend the SKILL.md UPDATED scope to repoint the Exit 1 remediation phrase to ## Execution Issues Tracking (rejected-OOS / oos-issues NDJSON carve-outs); add a fixed-string structure-test pin if desired
  - From Cursor-Innovation: Repoint every Step 8+ Out-of-Scope Handling literal (including Exit 1 remediation) to ## Execution Issues Tracking for triage policy and skills/implement/references/oos-pipeline.md for Step 9a.1 procedure; optionally add a fixed-string guard that the phrase is absent from Step 8+ after the change.
  - From Cursor-dyn-cross-ref-integrity: In the same SKILL.md edit, replace using the canonical OOS policy from the earlier "Out-of-Scope Handling" section at both sites with executing per ${CLAUDE_PLUGIN_ROOT}/skills/implement/references/oos-pipeline.md (or drop the clause because the new MANDATORY READ already binds the procedure). Add a fixed-string regression in scripts/test-implement-structure.sh that fails if Out-of-Scope Handling section remains in SKILL.md.


### FINDING_3: Python oos-filing path can bypass mandatory oos-pipeline load
- **Reviewer(s)**: Codex-Arch, Codex-Innovation
- **Severity**: important
- **Concern**: The proposed mandatory `oos-pipeline.md` load wiring covers only the bash Step 8+ OOS branches, leaving the Python `needs_user_reason=oos-filing` dispatch able to run the Step 9a.1 pipeline without reading the new canonical procedure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Add the same mandatory load directive to the Python `oos-filing` clause or route that clause explicitly through the OOS checkpoint block after it loads `oos-pipeline.md`; update the fixed-string load-count guard if needed.
  - From Codex-Innovation: Add the same mandatory oos-pipeline.md read directive or an explicit route to the loaded OOS checkpoint procedure in the Python oos-filing branch, and make the structure test cover all Step 9a.1 pipeline invocation sites rather than exactly the two bash-path mentions


### FINDING_4: Structure guard can pass without narrowing NEVER #5 run-statistics guidance
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: The planned structure guard uses OR semantics for sentinel-recovery run-statistics ownership, so CI can pass if only `oos-pipeline.md` forbids pre-checkpoint run-statistics while NEVER #5 still instructs writing run-statistics during idempotent sentinel recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Require AND pins: grep that narrowed NEVER #5 How to apply omits run-statistics on the sentinel-recovery branch and grep that oos-pipeline.md step 3 repeats the same prohibition; drop the NEVER #5 narrowed or oos-pipeline precedence escape hatch


### FINDING_5: Partial issue-filing failures can still satisfy the disposition gate
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Concern**: If a partial `/issue` batch failure records any URL in a gate-visible OOS surface, the disposition gate may treat that URL as sufficient and clear OOS pending state even though some accepted OOS items remain undispositioned.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Revise oos-pipeline.md Step 4/6 and the structure-test pin to state that on non-zero /issue or ISSUES_FAILED>0 the pipeline must not append accepted disposition URL rows to the gate-read oos-issues batch before checkpoint; log the partial failure only outside gate satisfaction surfaces until the batch is rerun or manually resolved


### FINDING_7: Step 9a.1 collection omits external implementer manifest OOS observations
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The planned OOS collection path does not harvest `oos_observations[]` from the external implementer manifest, so filed-OOS candidates produced by Codex/Cursor may never reach accepted OOS inputs or be filed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Extend `oos-pipeline.md` step 1 with a minimal `$MANIFEST_PATH` harvest of `oos_observations[]` into `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`, preserving existing security routing and the no rules-1-2 inline-triage note; add a fixed-string guard for `oos_observations[]`/manifest harvest in the new reference


### FINDING_9: Historical skeleton source citation uses incomplete path
- **Reviewer(s)**: Codex-dyn-cross-ref-integrity
- **Severity**: latent
- **Concern**: The plan’s historical skeleton source path omits the repository subpath, so `git show c53086d96^:anchor-template-oos-pipeline.md` fails even though the file exists at `skills/implement/references/anchor-template-oos-pipeline.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-cross-ref-integrity: Change the source citation to c53086d96^:skills/implement/references/anchor-template-oos-pipeline.md and keep reconstruction minimum

