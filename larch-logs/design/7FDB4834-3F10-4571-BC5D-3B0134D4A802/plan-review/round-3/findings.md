### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1042
- **Concern**: Plan repoints only the two intro Out-of-Scope Handling citations; Exit 1 remediation still cites the phantom section. Scenario: On checkpoint exit 1, operators are told to append rejected-OOS markers per the Out-of-Scope Handling section, which does not exist; remediation guidance breaks while the intro citations are fixed
- **Proposed resolution**: Extend the SKILL.md UPDATED scope to repoint the Exit 1 remediation phrase to ## Execution Issues Tracking (rejected-OOS / oos-issues NDJSON carve-outs); add a fixed-string structure-test pin if desired

### FINDING_2:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/implement/scripts/oos-file-conflict-deps.md:73-76; skills/implement/scripts/oos-issue-cap.md:88-91
- **Concern**: Helper Edit-in-sync lists Step 9a.1 procedure in SKILL.md but the plan moves executable procedure to oos-pipeline.md and only repoints the see-also line. Scenario: Future helper changes will follow edit-in-sync to the wrong file; procedure and helper contracts drift apart
- **Proposed resolution**: Replace the Edit-in-sync Step 9a.1 procedure bullet in both helper .md files with skills/implement/references/oos-pipeline.md; keep the SKILL.md narrative bullet for triage policy only

### FINDING_3:
- **Reviewer(s)**: Codex-Arch
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/implement/SKILL.md:955
- **Concern**: The Python `oos-filing` dispatch remains an executable Step 9a.1 OOS pipeline entry, but the plan only adds mandatory `oos-pipeline.md` loads to the two bash Step 8+ OOS branches.. Scenario: With `LARCH_SHIP_PR_IMPL=python`, a needs_user_reason=oos-filing result can run the OOS pipeline without loading the new canonical procedure, preserving the drift this PR is meant to remove.
- **Proposed resolution**: Add the same mandatory load directive to the Python `oos-filing` clause or route that clause explicitly through the OOS checkpoint block after it loads `oos-pipeline.md`; update the fixed-string load-count guard if needed.

### FINDING_4:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/test-implement-structure.sh (planned assertion 9)
- **Concern**: Structure guard uses OR for sentinel-recovery run-statistics ownership. Scenario: Plan requires same-PR NEVER #5 narrowing (skills/implement/SKILL.md:40) but proposed assertion 9 passes if only oos-pipeline.md forbids pre-checkpoint run-statistics; NEVER #5 How to apply can still instruct larch-log write --batch run-statistics on idempotent sentinel recovery, contradicting NEVER #14 and oos-pipeline step 3 while CI stays green
- **Proposed resolution**: Require AND pins: grep that narrowed NEVER #5 How to apply omits run-statistics on the sentinel-recovery branch and grep that oos-pipeline.md step 3 repeats the same prohibition; drop the NEVER #5 narrowed or oos-pipeline precedence escape hatch

### FINDING_5:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-gate.sh:173-200; planned skills/implement/references/oos-pipeline.md Step 4/6
- **Concern**: Partial /issue failure only suppresses oos-issues-created.md, but the gate also treats any URL in oos-issues.ndjson as sufficient disposition. Scenario: If a partial batch creates or deduplicates one issue, then fails another, and the pipeline appends the partial URL to accepted oos-issues rows as a breadcrumb, the checkpoint exits 0 on filed_urls>0 and can clear OOS_PENDING while failed OOS items have no disposition
- **Proposed resolution**: Revise oos-pipeline.md Step 4/6 and the structure-test pin to state that on non-zero /issue or ISSUES_FAILED>0 the pipeline must not append accepted disposition URL rows to the gate-read oos-issues batch before checkpoint; log the partial failure only outside gate satisfaction surfaces until the batch is rerun or manually resolved

### FINDING_6:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1042
- **Concern**: Step 8+ still has a third phantom Out-of-Scope Handling pointer the plan does not name. Scenario: UPDATED repoints Exit 0 and the OOS-checkpoint intro only. Exit 1 disposition-gap remediation in the same block still says append rejected-OOS markers per the Out-of-Scope Handling section. An implementer can fix the two named sites and leave Exit 1 pointing at a section that does not exist.
- **Proposed resolution**: Repoint every Step 8+ Out-of-Scope Handling literal (including Exit 1 remediation) to ## Execution Issues Tracking for triage policy and skills/implement/references/oos-pipeline.md for Step 9a.1 procedure; optionally add a fixed-string guard that the phrase is absent from Step 8+ after the change.

### FINDING_7:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/implement/SKILL.md:955
- **Concern**: Python driver oos-filing path is omitted from the proposed mandatory oos-pipeline load wiring. Scenario: With LARCH_SHIP_PR_IMPL=python, needs_user_reason=oos-filing runs the Step 9a.1 /issue pipeline from this clause; the proposed at-least-two directive guard can pass while this runtime path never reads the new canonical procedure, allowing sentinel recovery and run-statistics ownership rules to drift
- **Proposed resolution**: Add the same mandatory oos-pipeline.md read directive or an explicit route to the loaded OOS checkpoint procedure in the Python oos-filing branch, and make the structure test cover all Step 9a.1 pipeline invocation sites rather than exactly the two bash-path mentions

### FINDING_8:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: security
- **Location**: skills/implement/references/oos-pipeline.md proposed Step 1; conflicts with SECURITY.md:24 and skills/shared/voting-protocol.md:281-284
- **Concern**: The proposed security-routing predicate treats only dedicated `- **focus-area**:` field lines as security-routed, while the repo security policy and voting contract still define security OOS by unfenced `focus-area\s*=\s*security`.. Scenario: A security-tagged OOS block using the existing canonical token can slip into Step 9a.1 and be filed publicly because the new procedure explicitly says `focus-area = security` prose does not route privately.
- **Proposed resolution**: Keep Step 9a.1 aligned with SECURITY.md/lib-vote-tally for public-filing exclusion, or update SECURITY.md, voting-protocol.md, lib-vote-tally docs/tests, and the gate predicate together so there is one canonical security OOS predicate.

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:400 and skills/implement/references/codex-manifest-schema.md:3-7
- **Concern**: Planned Step 9a.1 collection omits external-implementer manifest harvest. Scenario: The issue history names manifest harvest as part of the restored procedure, and codex-manifest-schema.md still declares downstream Step 9a.1 consumption of `oos_observations[]`; with the plan as written, a Codex/Cursor manifest can contain filed-OOS candidates that never reach `oos-accepted-main-agent.md`, so no OOS issue is filed
- **Proposed resolution**: Extend `oos-pipeline.md` step 1 with a minimal `$MANIFEST_PATH` harvest of `oos_observations[]` into `$IMPLEMENT_TMPDIR/oos-accepted-main-agent.md`, preserving existing security routing and the no rules-1-2 inline-triage note; add a fixed-string guard for `oos_observations[]`/manifest harvest in the new reference

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-cross-ref-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/SKILL.md:1024,1042
- **Concern**: Step 8+ Exit 0 and OOS checkpoint still tell the orchestrator to use policy from the earlier Out-of-Scope Handling section, but that heading does not exist (triage lives under ## Execution Issues Tracking). The UPDATED SKILL.md section repoints a phantom citation and adds MANDATORY load lines, yet also says to preserve OOS prose byte-stable except citation/load repoints without explicitly replacing these two runtime sentences; new structure tests only count load-directive occurrences.. Scenario: After the PR an implementer can add the two MANDATORY READ lines while leaving the broken earlier-section pointer at both consumption sites; operators following SKILL.md without re-reading oos-pipeline.md still chase a non-existent section.
- **Proposed resolution**: In the same SKILL.md edit, replace using the canonical OOS policy from the earlier "Out-of-Scope Handling" section at both sites with executing per ${CLAUDE_PLUGIN_ROOT}/skills/implement/references/oos-pipeline.md (or drop the clause because the new MANDATORY READ already binds the procedure). Add a fixed-string regression in scripts/test-implement-structure.sh that fails if Out-of-Scope Handling section remains in SKILL.md.

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-cross-ref-integrity
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/implement/scripts/oos-disposition-checkpoint.sh:61-90,192-197
- **Concern**: oos-disposition-checkpoint.sh does not accept --filed-urls-file as a caller flag; it rejects unknown args and always passes only $IMPLEMENT_TMPDIR/oos-issues-created.md to oos-disposition-gate.sh. Scenario: If oos-pipeline.md tells Step 9a.1 or all-already-filed recovery to pass an arbitrary filed-URLs sidecar to the checkpoint, the checkpoint exits 2 before the gate sees the URLs
- **Proposed resolution**: Keep the new reference/test wording on fixed checkpoint-visible surfaces: write loose URL evidence to $IMPLEMENT_TMPDIR/oos-issues-created.md or rely on design - **Filed URL** lines; refer to --filed-urls-file only as a gate flag, not a checkpoint flag

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-cross-ref-integrity
- **Severity**: latent
- **Focus area**: correctness
- **Location**: plan.txt:131
- **Concern**: Historical skeleton source path is incomplete: git show c53086d96^:anchor-template-oos-pipeline.md fails; the file exists in that commit at skills/implement/references/anchor-template-oos-pipeline.md. Scenario: Implementer following the plan literally cannot recover the skeleton source
- **Proposed resolution**: Change the source citation to c53086d96^:skills/implement/references/anchor-template-oos-pipeline.md and keep reconstruction minimum
