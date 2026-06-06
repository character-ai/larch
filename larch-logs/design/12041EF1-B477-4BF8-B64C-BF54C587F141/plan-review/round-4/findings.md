### FINDING_1:
- **Reviewer(s)**: Cursor-Arch
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-subprocess.sh:179-182
- **Concern**: Proposed test adds content redact/escape assertions (FINDING_4) but the script delta is scoped to path-attribute escaping only (~8 lines), with content hardening assumed from branch tip rather than a verify-first step. Scenario: Item 5 test-launch-claude-subprocess.sh requires &lt; / &amp; escaping, absent raw secrets/tags, and untrusted framing inside context blocks; on current main the renderer still raw-cats context bytes (no redact-secrets or &lt;&gt;&amp; escape). An implementer following the Files section literally can land path-attribute fixes plus failing tests, or pass tests while SECURITY.md claims subprocess bodies are literal-redacted
- **Proposed resolution**: Mirror Item 3 revise verify-first in launch-claude-subprocess.sh: read post-#3548 main; if context bodies still use raw cat, add redact-secrets.sh plus &lt;&gt;&amp; escaping (and framing if missing) before or alongside path-attribute work; skip content edits only when a harness read proves hardening already present

### FINDING_2:
- **Reviewer(s)**: Codex-Arch
- **Severity**: important
- **Focus area**: security
- **Location**: <TMPDIR>/plan.txt:83-87
- **Concern**: Claude subprocess content hardening is assumed rather than verify-first. Scenario: Current scripts/launch-claude-subprocess.sh still cats context bodies raw; if post-3548 main does too, this plan only escapes the path attribute while SECURITY.md will claim arbitrary context bodies are redacted and escaped
- **Proposed resolution**: Make Item 5 verify content redaction escaping and framing first; if missing, patch context body rendering to pass through redact-secrets.sh and escape <>& in addition to escaping the path attribute

### FINDING_3:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-claude-subprocess.sh:177-182
- **Concern**: Proposed script delta covers path-attribute escaping only (~8 lines) while new test harness mandates full context-body redact/escape assertions. Scenario: On current main context bodies are raw-catted with no redact-secrets or &lt;/&amp; escaping; unconditional test additions (~30 lines) will fail unless content hardening already landed outside the scoped script edit
- **Proposed resolution**: Gate content-body tests verify-first like other surfaces, or expand the launch-claude-subprocess.sh delta to pipe context through redact_untrusted_stream when post-merge read proves content escape is still absent

### FINDING_4:
- **Reviewer(s)**: Codex-Edge
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:195-203
- **Concern**: Plan assumes context body redaction/escaping may already exist but current renderer still cats raw context bytes. Scenario: The PR could only escape the path attribute while still embedding raw secret-like tokens or raw <tag> content in Claude subprocess prompts
- **Proposed resolution**: Make the launch-claude-subprocess.sh step verify-first for context bodies too: if raw cat remains, pipe context through redact-secrets.sh and escape <>& before closing the block

### FINDING_5:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/launch-claude-subprocess.sh:179-181
- **Concern**: Files section mandates path-attribute escape only while test delta requires content redact/escape assertions. Scenario: On post-#3548 main content may still use raw cat; implementer adds tests per plan but only ~8 lines of path escaping → harness fails or SECURITY.md overclaims subprocess coverage
- **Proposed resolution**: Add verify-first wording to launch-claude-subprocess.sh UPDATED (mirror run-step3-review.sh): patch content redact/escape/framing only when post-merge read proves raw cat remains; tie test additions to that proven gap

### FINDING_6:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:180-181
- **Concern**: Item 5 only requires escaping the context path attribute and assumes context body redaction/escaping already exists, but this block currently appends raw context bytes.. Scenario: If post-#3548 still has this shape, a context file containing `</context_file_1>`, `<tag>`, or a secret-like token remains prompt-injected/leaked while SECURITY.md claims arbitrary subprocess context bodies are redacted and escaped.
- **Proposed resolution**: Make Item 5 verify-first for the context body too: if the block still cats `$ctx` raw, pipe it through `redact-secrets.sh` and escape `<>&` before writing it, then keep the planned path-attribute escaping and tests.

### FINDING_7:
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Focus area**: correctness
- **Location**: scripts/launch-claude-subprocess.sh:173-182
- **Concern**: Script delta is path-attribute escape only while the paired harness delta requires content redaction escaping and untrusted framing. Scenario: On post-merge main content is still raw-catted into context blocks (current `cat "$ctx"`); implementing only the ~8-line path change leaves the new `test-launch-claude-subprocess.sh` cases and SECURITY.md subprocess claims failing or false
- **Proposed resolution**: Add verify-first content hardening to the `launch-claude-subprocess.sh` delta (redact-secrets + `<>&` escape + framing prose when absent), matching the harness and SECURITY.md surface-2 contract—not path escape alone

### FINDING_8:
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:179-182
- **Concern**: Issue #3547 item 5 requires delimiter-safe context embedding but the UPDATED block only specifies path-attribute escaping and assumes content redact/escape already exists on the branch. Scenario: Post-#3548 main still uses raw cat for context bodies (current tree has framing prose only); implementer following the ~8-line script delta adds path escape while tests demand redact-secrets, &lt;/&amp; escaping, and no raw delimiter lines — item 5 stays open or tests fail without an explicit script step
- **Proposed resolution**: Add verify-first to the launch-claude-subprocess.sh entry mirroring Item 3: if context bodies are not already redacted/escaped via redact-secrets.sh (or emit_untrusted_file_block), migrate the append path before path-attribute work; keep the planned regression cases as the acceptance gate

### FINDING_9:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:71-81,132-134
- **Concern**: Marker-helper absence branch still leaves an unconditional make target in the run command. Scenario: The plan says to skip Item 4 when scripts/check-scope-reduction-marker.sh is still absent, but the Testing strategy still runs make test-check-scope-reduction-marker; that branch fails before validation can complete
- **Proposed resolution**: Qualify the Testing strategy command: include test-check-scope-reduction-marker only when the helper/target exists, matching the verify-first skip contract

### FINDING_10:
- **Reviewer(s)**: Cursor-dyn-dependency-verify-first
- **Severity**: important
- **Focus area**: architecture
- **Location**: plan.txt:24-34,45-48
- **Concern**: PR #3548 (#3511) forbids tally --scope-anchor-file and re-tally argv; this plan adds tally flag, loop tally passthrough, and SKILL re-tally --scope-anchor-file. Scenario: After #3548 merges with env-sourced SCOPE_ANCHOR_FILE in emit_loop_kvs/write_step3_result_env, #3547 re-implements relay via tally stdout and reintroduces flag plumbing #3548 explicitly rejected (larch-logs/design/65E69D6B-137F-4487-AEBE-AD0DCC54BB04/plan.txt:23,202,217)
- **Proposed resolution**: Drop tally --scope-anchor-file and re-tally argv from this plan; verify-first only loop parse/persist gaps #3548 leaves; refresh re-tally env from existing SCOPE_ANCHOR_FILE per #3548

### FINDING_11:
- **Reviewer(s)**: Codex-dyn-dependency-verify-first
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: Makefile:4,87,212-213; <TMPDIR>/plan.txt:80-81
- **Concern**: Makefile registration is described as net-new even though PR #3548 already owns it. Scenario: Post-#3548 implementer may duplicate the phony entry, shard prerequisite, or target recipe while doing Item 4
- **Proposed resolution**: Revise the Makefile item to verify-first/no-op when test-check-scope-reduction-marker is already in .PHONY, a harness shard, and has the existing recipe; only add missing wiring if one of those surfaces is absent

### FINDING_12:
- **Reviewer(s)**: Codex-dyn-env-var-propagation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:45-48, skills/design/SKILL.md:1128
- **Concern**: MainAgent re-tally plan does not preserve the input/output split for SCOPE_ANCHOR_FILE. Scenario: The proposed text passes --scope-anchor-file "$SCOPE_ANCHOR_FILE" and then parses/persists SCOPE_ANCHOR_FILE; if re-tally omits the KV, prompt-side code can keep the input or an exported stale value and refresh both env files with it, contrary to FINDING_8/FINDING_12
- **Proposed resolution**: Use separate variables such as _RETALLY_SCOPE_ANCHOR_IN and _RETALLY_PARSED_SCOPE_ANCHOR_FILE; unset parsed state before parsing; persist only the parsed non-empty KV on ok and omit it on tally-error or missing stdout KV

### FINDING_13:
- **Reviewer(s)**: Codex-dyn-env-var-propagation
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:39-40, skills/design/scripts/run-step3-review.sh:233-245, skills/design/scripts/run-step3-review.sh:341-366
- **Concern**: run-step3-review plan includes early panel-failed result-env writes with empty SCOPE_ANCHOR_FILE. Scenario: The stated contract is ok and main-agent-vote-required only; adding SCOPE_ANCHOR_FILE= on early panel-failed widens the relay surface and conflicts with the omit-on-non-terminal rule
- **Proposed resolution**: Do not write or emit SCOPE_ANCHOR_FILE on panel-failed; initialize or unset local state to prevent stale carry, then write/emit the key only when parsed from loop output/result env with status ok or main-agent-vote-required

### FINDING_14:
- **Reviewer(s)**: Codex-dyn-env-var-propagation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:42-43, <TMPDIR>/plan.txt:56-57, skills/design/scripts/test-step3-orchestrator-fence.sh:61-120
- **Concern**: Stale-seed coverage does not cover every described relay path. Scenario: The run-step3 stale test is only required when the relay is already complete, and the MainAgent re-tally path only gets argv/parse/dual-env pins; a patched relay or prompt-side re-tally can still leak an exported stale SCOPE_ANCHOR_FILE
- **Proposed resolution**: Add one stale-seed assertion after any run-step3 relay patch as well as when already complete, and add an orchestrator-fence/MainAgent re-tally stale case that exports a stale value, omits the re-tally KV, and asserts neither refreshed env file nor argv uses the stale value

### FINDING_15:
- **Reviewer(s)**: Cursor-dyn-security-doc-accuracy
- **Severity**: important
- **Focus area**: security
- **Location**: scripts/launch-claude-subprocess.sh:179-181
- **Concern**: SECURITY.md Item 6 would require subprocess context bodies to use redact-secrets.sh and `<>&` escaping, and test-launch-claude-subprocess.sh additions assert escaped secrets/tags, but the only launch-claude-subprocess.sh delta is path-attribute escaping (~8 lines) with content hygiene deferred to “already on the branch.”. Scenario: On main the context path still raw-cats file bytes after a one-line framing sentence; landing SECURITY.md plus the new tests without a verify-first content hardening step (or an explicit script delta) overstates delimiter/secret coverage and CI fails.
- **Proposed resolution**: Add a verify-first subprocess content block mirroring revise Item 3: if post-#3548 read shows no redact/escape, migrate the context loop to the same redact_untrusted_stream / emit_untrusted_file_block pattern as scripts/render-specialist-prompt.sh before asserting full “other inline” coverage in SECURITY.md; tie SECURITY.md subprocess bullets to that gate like line 11 does for assessor.

### FINDING_16:
- **Reviewer(s)**: Codex-dyn-security-doc-accuracy
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md proposed in plan.txt:89-94; plan.txt:83-87; scripts/launch-claude-subprocess.sh:177-182
- **Concern**: Proposed SECURITY.md claims arbitrary Claude subprocess context bodies are redacted and escaped, but the launch-claude-subprocess change only covers path attribute escaping and assumes content hardening already exists. Current code still raw-cats context bodies.. Scenario: After implementation, SECURITY.md can overstate coverage if only path attributes are escaped while context bytes remain raw legacy prompt input.
- **Proposed resolution**: Change the launch-claude-subprocess.sh plan item to verify-first migrate context body rendering when still raw: run redact-secrets.sh, escape <>&, and keep untrusted framing; otherwise remove subprocess context bodies from the SECURITY.md covered-surface claim.

### FINDING_17:
- **Reviewer(s)**: Codex-dyn-security-doc-accuracy
- **Severity**: latent
- **Focus area**: correctness
- **Location**: SECURITY.md proposed in plan.txt:90-94; plan.txt:59-63; plan.txt:36-37
- **Concern**: Proposed SECURITY.md names revise waterfall plan/findings but omits the revise feature block, while the code plan migrates plan, findings, and feature and the loop plan says revise receives the staged scope-anchor path.. Scenario: The trust-model section can drift from the proposed code surface: revise feature content is neither clearly listed as a scope-anchor consumer nor as a source-specific inline block.
- **Proposed resolution**: Add the revise waterfall feature block to the inline-renderer wording, with staged-anchor provenance only when --feature-file is the staged anchor and source-specific provenance otherwise.

### OOS_1:
- **Description**: Plan rewrites brainstorm/tally cases but does not mention updating expected_legacy_layout for post-#3548 anchor artifacts. Scenario: After #3548 materializes plan-review-scope-anchor.txt (and related context files) the legacy golden layout case may fail unless #3548 already updated the pin
- **Reviewer**: Cursor-Edge
- **Severity**: latent
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/test-plan-review-loop.sh:1304-1305
- **Phase**: design
