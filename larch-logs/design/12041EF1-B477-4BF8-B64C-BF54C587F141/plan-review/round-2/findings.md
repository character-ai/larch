### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:32-39,41-48,53-57
- **Concern**: Post-#3548 handoff surfaces are listed as UPDATED even though pr-3548 already wires SCOPE_ANCHOR_FILE through plan-review-loop emit_loop_kvs/write_step3_result_env, run-step3-review parse/emit/result-env allowlists, test-run-step3-review scope-anchor cases, and test-step3-orchestrator-fence allowlist assertions. Scenario: Gap #3547 net-new work is tally --scope-anchor-file argv, tally KV echo, _tally_raw stdout parse, and SKILL/approval-gates mechanical re-tally passthrough; rebasing post-#3548 and still editing ~44 lines across four settled files adds churn and merge-conflict risk without closing a remaining contract hole
- **Proposed resolution**: Trim those subsections to verify-only against post-#3548 (or drop); keep only tally threading plus assessor/revise/marker/SECURITY/SKILL re-tally deltas; narrow plan-review-loop to pass --scope-anchor-file and add SCOPE_ANCHOR_FILE to the existing _tally_raw parse case (~8 lines, not re-describing emit_loop_kvs/write_step3_result_env)

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:179-185
- **Concern**: Context file path is interpolated into an XML-ish attribute without escaping. Scenario: A context file under an allowed root with a quote or angle bracket in its basename can break the opening context_file tag even though file content is escaped, letting path text inject prompt markup
- **Proposed resolution**: Escape the path attribute for &, <, >, and quotes before printing it, or omit the path attribute; add the planned subprocess regression with a delimiter-like filename

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1079-1097
- **Concern**: Step 3 handoff parse allowlists omit SCOPE_ANCHOR_FILE while re-tally prose uses $SCOPE_ANCHOR_FILE. Scenario: The ### UPDATED: skills/design/SKILL.md block only lists MainAgent re-tally prose (~7 lines). The Step 3 bash handoff at 1079/1096 never loads SCOPE_ANCHOR_FILE from .step3-review-result.env or run-step3-review stdout. test-step3-orchestrator-fence.sh mirrors that logic locally and does not grep SKILL.md, so CI can pass with a stale harness mirror while production leaves $SCOPE_ANCHOR_FILE unset and re-tally omits --scope-anchor-file
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to both Step 3 handoff case arms (~1079 and ~1096) in the SKILL.md ### UPDATED entry; extend test-step3-orchestrator-fence.sh and/or scripts/test-design-structure.sh with a contains pin so SKILL.md and the harness cannot drift

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/test-launch-claude-subprocess.sh:1-260
- **Concern**: Planned context-file regression only checks escaped output exists, not that raw delimiter text is absent. Scenario: A renderer that redacts secrets and emits an escaped copy while still leaving raw <tag> context text would pass the planned assertions but preserve the delimiter-injection risk
- **Proposed resolution**: Add a negative assertion in the new captured-prompt case that the raw fixture tag line, for example <tag>, is absent while &lt;tag&gt; and &amp; are present

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/tally-plan-review.sh:23-31
- **Concern**: Item 2 adds `--scope-anchor-file` and `SCOPE_ANCHOR_FILE` KV emission through tally, but tally only scores ballots and never renders scope-anchor prompts.. Scenario: Post-#3548 `plan-review-loop.sh` already sets `SCOPE_ANCHOR_FILE`, emits it in `emit_loop_kvs`, and persists it via `phase_driver_write_result_env` without tally. A tally round-trip adds argv parsing, tests, and docs for a passthrough echo with no consumer inside tally.
- **Proposed resolution**: Drop tally `--scope-anchor-file` / `SCOPE_ANCHOR_FILE` emission from item 2. Keep anchor threading in the loop and Step 3 env layers only.

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1128; skills/design/references/approval-gates.md:95
- **Concern**: MainAgent fallback preserves SCOPE_ANCHOR_FILE only after voting. Scenario: The 0-judge path can receive a staged scope anchor, but the proposed SKILL.md/approval-gates change only passes it to re-tally after the MainAgent has already voted, so scope-reduction or proportionality decisions still ignore the issue anchor when all external voters are unavailable
- **Proposed resolution**: In the MainAgent adjudication prose, read non-empty SCOPE_ANCHOR_FILE as untrusted scope evidence before casting votes, apply the same scope/proportionality rubric, then pass and persist it during re-tally as planned

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:41-57
- **Concern**: SCOPE_ANCHOR_FILE handoff is re-specified as net-new work in run-step3-review.sh test-run-step3-review.sh and test-step3-orchestrator-fence.sh but the #3548 hard dependency already adds allowlists CR/LF sanitization panel-failed env writes and fence cases for that key. Scenario: An implementer landing on post-#3548 main may re-touch already-correct layers producing redundant diffs merge noise or accidental regressions while chasing tally relay work that belongs elsewhere
- **Proposed resolution**: Narrow those three file entries to post-#3548 deltas only (tally --scope-anchor-file argv/KV relay plus SKILL re-tally flag and approval-gates mirror); treat run-step3-review and the two harnesses as verify-unless-gap after #3548 merge

### FINDING_8:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: plan.txt:50-54
- **Concern**: SKILL.md MainAgent re-tally edit adds --scope-anchor-file and drops preserve-existing-value prose but does not cross-reference the #3548 render-main-agent-scope-anchor.sh adjudication step that must stay before ballot voting. Scenario: A minimal SKILL edit could remove or weaken the escaped scope-evidence render path while only adding the tally flag leaving MainAgent voting without sanitized anchor context
- **Proposed resolution**: Add one explicit retain render-main-agent-scope-anchor.sh before ballot adjudication bullet to the SKILL.md and approval-gates.md delta so the re-tally KV change cannot be read as replacing that render contract

### FINDING_9:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:1076-1099
- **Concern**: Initial Step 3 handoff is not explicitly updated to accept SCOPE_ANCHOR_FILE. Scenario: run-step3-review emits and persists SCOPE_ANCHOR_FILE, but the plan only calls out MainAgent re-tally use; if the SKILL handoff does not parse/filter the new KV, MainAgent re-tally can omit --scope-anchor-file or print the internal path as ordinary output
- **Proposed resolution**: Add SCOPE_ANCHOR_FILE to the Step 3 display suppression, result-env parse allowlist, and stdout fallback parse allowlist in SKILL.md, and pin the same in test-step3-orchestrator-fence.sh

### FINDING_10:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: architecture
- **Location**: skills/design/scripts/tally-plan-review.md:107-109
- **Concern**: The plan changes tally/Step 3 artifact contracts but omits the required plan-review reference sync. Scenario: The existing edit-in-sync contract says artifact-format changes to tally-plan-review must update skills/design/references/plan-review.md too; after this plan lands, that Step 3 reference would still show dispatch-plan-voters without --scope-anchor-file and omit the SCOPE_ANCHOR_FILE handoff
- **Proposed resolution**: Add a minimal UPDATED entry for skills/design/references/plan-review.md documenting the staged scope-anchor voter input and optional SCOPE_ANCHOR_FILE durable handoff; extend any existing doc-pin test only if it already covers this reference

### FINDING_11:
- **Reviewer(s)**: Cursor-dyn-state-handoff
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/plan-review-loop.sh:33-33 (plan) / plan-review-loop.sh:1405-1417;155-176
- **Concern**: Same SCOPE_ANCHOR_FILE variable used for tally input and parsed output. Scenario: On tally-error tally omits SCOPE_ANCHOR_FILE KV but loop-local var may still hold the staged path from #3548 materialization; write_step3_result_env can persist an anchor the plan says tally-error must omit
- **Proposed resolution**: Use a separate parsed-out variable (or clear SCOPE_ANCHOR_FILE before persist) and only emit/write when tally stdout carries SCOPE_ANCHOR_FILE on ok or main-agent-vote-required

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-state-handoff
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1128; skills/design/scripts/tally-plan-review.sh:452-459,553-555; skills/design/scripts/plan-review-loop.sh:1389-1413
- **Concern**: Proposed SCOPE_ANCHOR_FILE flow adds tally argv plumbing but does not anchor the MainAgent voting decision. Scenario: The 0-judge MainAgent writes votes before re-tally runs, while tally-plan-review only tallies and emits KVs; passing --scope-anchor-file to re-tally cannot affect the adjudication prompt and adds avoidable surface in a SIMPLE lane
- **Proposed resolution**: Drop tally-plan-review --scope-anchor-file; persist the staged anchor directly through plan-review-loop and run-step3-review, and update the SKILL.md/approval-gates MainAgent paragraph to render SCOPE_ANCHOR_FILE as untrusted literal evidence before voting when non-empty/readable

### FINDING_13:
- **Reviewer(s)**: Cursor-dyn-trust-boundary
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/SKILL.md:1076-1100
- **Concern**: SKILL.md edit scope names only MainAgent re-tally prose (~7 lines) but not the Step 3 run-step3-review handoff parse arms that must bind SCOPE_ANCHOR_FILE before re-tally. Scenario: After plan-review-loop/run-step3-review persist SCOPE_ANCHOR_FILE into result envs, the orchestrator fence still omits SCOPE_ANCHOR_FILE from its case arms, so $SCOPE_ANCHOR_FILE stays empty and MainAgent re-tally never passes --scope-anchor-file despite tally/loop plumbing
- **Proposed resolution**: Expand the SKILL.md Step 3 driver fence parse allowlists (and the mirrored test-step3-orchestrator-fence harness) to include SCOPE_ANCHOR_FILE alongside the existing durable KVs; document that binding happens before the MainAgent re-tally command, not only from re-tally stdout

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-trust-boundary
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:68-115; skills/design/SKILL.md:1128; scripts/scout-dynamic-archetypes.sh:349-363
- **Concern**: Proposed SECURITY.md scope-anchor subsection would group path-only/KV handoff consumers with literal-redacted block renderers. Scenario: MainAgent re-tally only passes/parses/persists SCOPE_ANCHOR_FILE, and the scout path shown today instructs agents to read a staged file; documenting both as literal-block renderers overstates the trust boundary and may cause unnecessary rendering work
- **Proposed resolution**: Word SECURITY.md as two surfaces: inline renderers use literal-redacted escaped framed blocks; path-only handoffs such as scout/MainAgent re-tally pass a redacted staged path and do not render anchor content

### FINDING_15:
- **Reviewer(s)**: Codex-dyn-trust-boundary
- **Severity**: latent
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:61-70,179-181
- **Concern**: Proposed Claude-subprocess regression covers escaped context content but not the XML-ish path attribute that is printed raw. Scenario: A context filename containing quote, angle, or ampersand bytes can break the opening <context_file_N path="..."> line before the untrusted framing text, leaving a delimiter-escaping gap even when file bytes are escaped
- **Proposed resolution**: Escape the context path attribute or reject delimiter bytes, and include that filename shape in the new regression if the #3548 implementation does not already cover it

### FINDING_16:
- **Reviewer(s)**: Cursor-dyn-harness-matrix
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1178-1199
- **Concern**: Brainstorm integration case still asserts merged feature-file-seen.txt binding. Scenario: After #3548 stages plan-review-scope-anchor.txt for panel/voter argv, this case still requires brainstorm headers in feature-file-seen.txt, so test-plan-review-loop can fail even when new SCOPE_ANCHOR passthrough cases pass
- **Proposed resolution**: Add an explicit harness step to rewrite or replace the brainstorm case: assert plan-review-scope-anchor.txt (or equivalent stub capture) is the binding dispatch path and that brainstorm content stays out of the staged anchor

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/shared/scripts/test-render-assessor-prompt.sh:12-30
- **Concern**: Planned assessor hardening test does not assert feature content is preserved. Scenario: A renderer could emit framing, encoding, escapes, and redact the token while dropping the refined problem statement; the assessor then loses scope context and the planned assertions still pass
- **Proposed resolution**: Add a safe feature line to the fixture and assert it appears inside the rendered block, while still asserting secret redaction and tag escaping

### FINDING_18:
- **Reviewer(s)**: Codex-dyn-harness-matrix
- **Severity**: important
- **Focus area**: correctness
- **Location**: skills/design/scripts/run-step3-review.sh:279-318; skills/design/scripts/test-run-step3-review.sh:610-625
- **Concern**: The planned absent SCOPE_ANCHOR_FILE case may be vacuous unless it seeds stale state. Scenario: If the script fails to initialize SCOPE_ANCHOR_FILE before parsing loop output, an exported stale value can leak into stdout or .step3-review-result.env; an absent case with no seeded stale value would still pass
- **Proposed resolution**: Seed a stale SCOPE_ANCHOR_FILE in the test environment, have the loop stub omit it, and assert stdout and .step3-review-result.env do not contain the stale key/value
