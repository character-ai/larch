### FINDING_1:
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/scripts/revise-plan-with-waterfall.sh:131-150
- **Concern**: Item 3 assumes emit_untrusted_file_block already wraps plan/findings/feature blocks and only adds framing prose. Scenario: Main (and possibly post-#3548 main) still uses raw sed into <plan>/<findings>/<feature>; framing-only leaves delimiter injection and untrusted-content contract gaps open
- **Proposed resolution**: Add verify-first to Item 3 (mirror run-step3-review): confirm blocks use emit_untrusted_file_block before adding framing; if compose_prompt still sed-cats raw bytes migrate blocks first then add framing

### FINDING_2:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: scripts/check-scope-reduction-marker.sh
- **Concern**: Item 4 marked UPDATED but helper absent on cited branch tip. Scenario: Implementer starts after #3548 only; Item 4 targets a non-existent script and fails or scope-creeps into re-landing the whole marker detector
- **Proposed resolution**: Declare the marker-script merge prerequisite beside #3548, or make Item 4 verify-first and omit when the helper is still missing

### FINDING_3:
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: Makefile:4-514
- **Concern**: Testing strategy names make test-check-scope-reduction-marker without registering it. Scenario: Marker stdin/file parity harness never runs in CI; regressions in consolidated detector slip through
- **Proposed resolution**: Add Makefile .PHONY/recipe/shard entry for test-check-scope-reduction-marker, or remove that target from the testing-strategy make line

### FINDING_4:
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:planned Trust Model section
- **Concern**: The planned provenance wording is too broad. Scenario: Line 85 applies the issue-body to larch:plan strip to staged-anchor provenance to revise waterfall plan/findings blocks and Claude subprocess context bodies, but those inputs can be plan text, reviewer findings, or arbitrary context files rather than the staged scope anchor; SECURITY.md would overstate the trust boundary.
- **Proposed resolution**: Keep the two-surface section, but say only scope-anchor renders use the issue-body to stripped/redacted staged-anchor provenance; other inline untrusted blocks are source-specific file contents that must still go through redact-secrets plus escaping and framing.

### FINDING_5:
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Focus area**: security
- **Location**: SECURITY.md:68
- **Concern**: Proposed trust-model wording omits the assessor fallback path. Scenario: The plan says assess-plan-round falls back to legacy feature-description.txt when the staged anchor is empty, but the SECURITY.md addition would claim inline renderers use issue body to larch:plan strip to redacted staged anchor provenance, creating false assurance for degraded assessor sessions
- **Proposed resolution**: Word the SECURITY.md section as staged-anchor provenance for the normal path, and explicitly note that the Step 3.6 assessor legacy fallback may read feature-description.txt directly but still renders it only as redacted escaped untrusted evidence

### FINDING_6:
- **Reviewer(s)**: Codex-Requirements
- **Severity**: important
- **Focus area**: security
- **Location**: SECURITY.md:68
- **Concern**: Proposed trust-model text assigns staged scope-anchor provenance to all inline renderers, including plan, findings, and arbitrary Claude subprocess context bodies. Scenario: SECURITY.md would imply those non-anchor inputs come from issue body to larch:plan strip to staged anchor, creating false assurance about sources and review boundaries
- **Proposed resolution**: Narrow the subsection: scope-anchor consumers get the issue-to-staged-anchor provenance; plan/findings/subprocess contexts are separate source-file inputs that still require redaction, escaping, and untrusted framing.

### FINDING_7:
- **Reviewer(s)**: Cursor-dyn-dep-boundary
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: skills/design/SKILL.md:44-48
- **Concern**: SKILL.md edits re-add SCOPE_ANCHOR_FILE allowlist binding and MainAgent pre-vote scope render already landed on #3548 tip 0dc974f1e. Scenario: Post-#3548 merge the orchestrator fence at 0dc974f1e:1082/1099 already parses SCOPE_ANCHOR_FILE and 0dc974f1e:1133 already mandates render-main-agent-scope-anchor.sh before voting; re-applying ~15 lines risks merge conflicts and violates remaining-deltas-only scope
- **Proposed resolution**: Mark those SKILL.md bullets verify-only post-#3548 (re-tally --scope-anchor-file parse/refresh only) and drop allowlist/pre-vote rewrites from the net-new file list

### FINDING_8:
- **Reviewer(s)**: Codex-dyn-dep-boundary
- **Severity**: important
- **Focus area**: risk-integration
- **Location**: <TMPDIR>/plan.txt:44-48; pr-3548:skills/design/SKILL.md:1079-1130
- **Concern**: The SKILL.md instructions still tell the implementer to add Step 3 SCOPE_ANCHOR_FILE allowlist handling and MainAgent pre-vote scope-anchor rendering, but PR #3548 already has those surfaces.. Scenario: Post-#3548 implementation may rewrite settled Step 3 prose or tests instead of limiting the change to the remaining re-tally argv/parse/env refresh gap, increasing merge-conflict and scope-creep risk.
- **Proposed resolution**: Change the SKILL.md plan bullets to verify the existing allowlist and pre-vote render, then patch only the missing MainAgent re-tally --scope-anchor-file parsing and dual env refresh.

### FINDING_9:
- **Reviewer(s)**: Cursor-dyn-kv-wire
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:36
- **Concern**: test-plan-review-loop tally passthrough names only ok persist terminal. Scenario: Plan lines 24/33/54 require SCOPE_ANCHOR_FILE on both ok and main-agent-vote-required; the new loop harness bullet persists parsed value only on ok, so main-agent-vote-required relay can ship untested and regress the 0-judge path
- **Proposed resolution**: Add main-agent-vote-required to the positive passthrough assertion (stub emits SCOPE_ANCHOR_FILE; result env and stdout retain it) alongside ok

### FINDING_10:
- **Reviewer(s)**: Codex-dyn-kv-wire
- **Severity**: important
- **Focus area**: correctness
- **Location**: <TMPDIR>/plan.txt:38-39; skills/design/scripts/run-step3-review.sh:293-301,312-366
- **Concern**: The run-step3-review plan says to verify parse allowlists, emit_kv, and result-env writes, but then says to patch only missing allowlist arms.. Scenario: After PR #3548, if SCOPE_ANCHOR_FILE is present in parse arms but missing from normalized stdout emit or .step3-review-result.env writes, the proposed verify-only/allowlist-only instruction can leave the Step 3 handoff stale or absent despite the plan requiring dual relay.
- **Proposed resolution**: Change the run-step3-review instruction to patch the exact missing surface among parse allowlists, normalized emit_kv, and .step3-review-result.env writes; keep verify-only when all three already exist.
