### FINDING_1: Plan over-specifies post-#3548 handoff work
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: The plan treats already-landed post-#3548 SCOPE_ANCHOR_FILE handoff surfaces as net-new UPDATED work, creating churn, merge-conflict risk, and possible regressions instead of focusing only on remaining deltas.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Trim those subsections to verify-only against post-#3548 (or drop); keep only tally threading plus assessor/revise/marker/SECURITY/SKILL re-tally deltas; narrow plan-review-loop to pass --scope-anchor-file and add SCOPE_ANCHOR_FILE to the existing _tally_raw parse case (~8 lines, not re-describing emit_loop_kvs/write_step3_result_env)
  - From Cursor-Pragmatic: Narrow those three file entries to post-#3548 deltas only (tally --scope-anchor-file argv/KV relay plus SKILL re-tally flag and approval-gates mirror); treat run-step3-review and the two harnesses as verify-unless-gap after #3548 merge


### FINDING_2: Context-file path attribute is not escaped
- **Reviewer(s)**: Codex-Arch, Codex-dyn-trust-boundary
- **Severity**: important
- **Concern**: `launch-claude-subprocess.sh` escapes context file content but interpolates the context file path into an XML-ish attribute without escaping, allowing quote, angle bracket, or ampersand bytes in an allowed filename to break prompt framing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Escape the path attribute for &, <, >, and quotes before printing it, or omit the path attribute; add the planned subprocess regression with a delimiter-like filename
  - From Codex-dyn-trust-boundary: Escape the context path attribute or reject delimiter bytes, and include that filename shape in the new regression if the #3548 implementation does not already cover it


### FINDING_3: SKILL Step 3 handoff allowlists omit SCOPE_ANCHOR_FILE
- **Reviewer(s)**: Cursor-Edge, Codex-Pragmatic, Cursor-dyn-trust-boundary
- **Severity**: important
- **Concern**: The SKILL.md Step 3 handoff parse/filter arms are not explicitly updated to bind `SCOPE_ANCHOR_FILE` before MainAgent re-tally, so production can leave the variable unset even if lower layers emit or persist it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add SCOPE_ANCHOR_FILE to both Step 3 handoff case arms (~1079 and ~1096) in the SKILL.md ### UPDATED entry; extend test-step3-orchestrator-fence.sh and/or scripts/test-design-structure.sh with a contains pin so SKILL.md and the harness cannot drift
  - From Codex-Pragmatic: Add SCOPE_ANCHOR_FILE to the Step 3 display suppression, result-env parse allowlist, and stdout fallback parse allowlist in SKILL.md, and pin the same in test-step3-orchestrator-fence.sh
  - From Cursor-dyn-trust-boundary: Expand the SKILL.md Step 3 driver fence parse allowlists (and the mirrored test-step3-orchestrator-fence harness) to include SCOPE_ANCHOR_FILE alongside the existing durable KVs; document that binding happens before the MainAgent re-tally command, not only from re-tally stdout


### FINDING_4: Subprocess escaping regression lacks negative raw-delimiter assertion
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Concern**: The planned context-file regression can pass if escaped output exists even while raw delimiter-like context text is still emitted, preserving the prompt-injection risk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Add a negative assertion in the new captured-prompt case that the raw fixture tag line, for example <tag>, is absent while &lt;tag&gt; and &amp; are present


### FINDING_6: MainAgent voting may ignore scope anchor before re-tally
- **Reviewer(s)**: Codex-Innovation, Cursor-Pragmatic, Codex-dyn-state-handoff
- **Severity**: important
- **Concern**: The proposed MainAgent changes focus on preserving or re-tallying `SCOPE_ANCHOR_FILE` after votes are cast, but the scope anchor must inform the MainAgent adjudication prompt before ballot voting, especially in the 0-judge fallback path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: In the MainAgent adjudication prose, read non-empty SCOPE_ANCHOR_FILE as untrusted scope evidence before casting votes, apply the same scope/proportionality rubric, then pass and persist it during re-tally as planned
  - From Cursor-Pragmatic: Add one explicit retain render-main-agent-scope-anchor.sh before ballot adjudication bullet to the SKILL.md and approval-gates.md delta so the re-tally KV change cannot be read as replacing that render contract
  - From Codex-dyn-state-handoff: Drop tally-plan-review --scope-anchor-file; persist the staged anchor directly through plan-review-loop and run-step3-review, and update the SKILL.md/approval-gates MainAgent paragraph to render SCOPE_ANCHOR_FILE as untrusted literal evidence before voting when non-empty/readable


### FINDING_7: Plan-review reference sync is omitted
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Concern**: The plan changes tally/Step 3 artifact contracts but does not update `skills/design/references/plan-review.md`, despite the edit-in-sync requirement for tally-plan-review artifact-format changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Add a minimal UPDATED entry for skills/design/references/plan-review.md documenting the staged scope-anchor voter input and optional SCOPE_ANCHOR_FILE durable handoff; extend any existing doc-pin test only if it already covers this reference


### FINDING_8: Tally input/output variable reuse can persist stale anchors on error
- **Reviewer(s)**: Cursor-dyn-state-handoff
- **Severity**: important
- **Concern**: Reusing `SCOPE_ANCHOR_FILE` for both staged tally input and parsed tally output can cause `write_step3_result_env` to persist a staged anchor even when tally errors and omits the KV.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-state-handoff: Use a separate parsed-out variable (or clear SCOPE_ANCHOR_FILE before persist) and only emit/write when tally stdout carries SCOPE_ANCHOR_FILE on ok or main-agent-vote-required


### FINDING_9: SECURITY.md conflates literal renderers with path-only handoffs
- **Reviewer(s)**: Codex-dyn-trust-boundary
- **Severity**: important
- **Concern**: The proposed SECURITY.md scope-anchor subsection would overstate the trust boundary by grouping literal-redacted block renderers together with path-only/KV handoff consumers that only pass staged paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-trust-boundary: Word SECURITY.md as two surfaces: inline renderers use literal-redacted escaped framed blocks; path-only handoffs such as scout/MainAgent re-tally pass a redacted staged path and do not render anchor content


### FINDING_10: Brainstorm integration harness still expects old feature-file binding
- **Reviewer(s)**: Cursor-dyn-harness-matrix
- **Severity**: important
- **Concern**: The brainstorm integration case still asserts binding through `feature-file-seen.txt`, which can fail after #3548 stages `plan-review-scope-anchor.txt` for panel/voter argv.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-harness-matrix: Add an explicit harness step to rewrite or replace the brainstorm case: assert plan-review-scope-anchor.txt (or equivalent stub capture) is the binding dispatch path and that brainstorm content stays out of the staged anchor


### FINDING_11: Assessor hardening test does not prove feature content survives
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Concern**: The planned assessor renderer test checks framing, encoding, escaping, and secret redaction, but not that safe feature content remains present, so a renderer could drop the refined problem statement while passing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-matrix: Add a safe feature line to the fixture and assert it appears inside the rendered block, while still asserting secret redaction and tag escaping


### FINDING_12: Absent SCOPE_ANCHOR_FILE test may not catch stale environment leaks
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Concern**: The planned absent `SCOPE_ANCHOR_FILE` case is vacuous unless it seeds stale state; otherwise it may miss leaked exported values in stdout or `.step3-review-result.env`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-harness-matrix: Seed a stale SCOPE_ANCHOR_FILE in the test environment, have the loop stub omit it, and assert stdout and .step3-review-result.env do not contain the stale key/value

