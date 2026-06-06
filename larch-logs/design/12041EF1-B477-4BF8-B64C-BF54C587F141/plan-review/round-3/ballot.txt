### FINDING_1: Verify untrusted block wrapping before adding waterfall framing
- **Reviewer(s)**: Cursor-Edge
- **Severity**: important
- **Concern**: Item 3 assumes plan/findings/feature blocks are already emitted through `emit_untrusted_file_block` and only adds framing prose. If the prompt composer still raw `sed`-cats bytes into XML-like blocks, framing-only changes leave delimiter injection and untrusted-content contract gaps open.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Add verify-first to Item 3 (mirror run-step3-review): confirm blocks use emit_untrusted_file_block before adding framing; if compose_prompt still sed-cats raw bytes migrate blocks first then add framing

### FINDING_2: Marker-script update depends on absent helper
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: Item 4 is marked updated but targets `scripts/check-scope-reduction-marker.sh`, which may not exist on the cited post-#3548 branch tip. Implementers starting from that state could fail or re-land the whole marker detector instead of applying a delta.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Declare the marker-script merge prerequisite beside #3548, or make Item 4 verify-first and omit when the helper is still missing

### FINDING_3: Test target named but not registered
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: important
- **Concern**: The testing strategy calls `make test-check-scope-reduction-marker`, but the target is not registered in the Makefile. The marker stdin/file parity harness may never run in CI.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Add Makefile .PHONY/recipe/shard entry for test-check-scope-reduction-marker, or remove that target from the testing-strategy make line

### FINDING_4: SECURITY provenance wording over-applies staged-anchor source
- **Reviewer(s)**: Codex-Innovation, Codex-Requirements
- **Severity**: important
- **Concern**: The planned SECURITY.md trust-model language appears to assign issue-body → `larch:plan` strip → staged-anchor provenance to all inline untrusted renderers, including plan text, reviewer findings, and arbitrary Claude subprocess context bodies. That would overstate the trust boundary for non-anchor inputs, which are source-specific files and still require redaction, escaping, and untrusted framing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Keep the two-surface section, but say only scope-anchor renders use the issue-body to stripped/redacted staged-anchor provenance; other inline untrusted blocks are source-specific file contents that must still go through redact-secrets plus escaping and framing.
  - From Codex-Requirements: Narrow the subsection: scope-anchor consumers get the issue-to-staged-anchor provenance; plan/findings/subprocess contexts are separate source-file inputs that still require redaction, escaping, and untrusted framing.

### FINDING_5: SECURITY trust model omits assessor fallback provenance
- **Reviewer(s)**: Codex-Pragmatic
- **Severity**: latent
- **Concern**: The planned SECURITY.md wording omits the Step 3.6 assessor fallback path, where `assess-plan-round` may read `feature-description.txt` directly when the staged anchor is empty. Claiming staged-anchor provenance for that degraded path would create false assurance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Pragmatic: Word the SECURITY.md section as staged-anchor provenance for the normal path, and explicitly note that the Step 3.6 assessor legacy fallback may read feature-description.txt directly but still renders it only as redacted escaped untrusted evidence

### FINDING_6: SKILL.md plan re-adds #3548 surfaces instead of remaining deltas
- **Reviewer(s)**: Cursor-dyn-dep-boundary, Codex-dyn-dep-boundary
- **Severity**: important
- **Concern**: The SKILL.md plan still instructs implementers to add Step 3 `SCOPE_ANCHOR_FILE` allowlist handling and MainAgent pre-vote scope-anchor rendering, but those surfaces reportedly already landed in PR #3548. Reapplying them post-merge risks conflicts and scope creep instead of limiting work to the remaining MainAgent re-tally argv/parse/env refresh gap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dep-boundary: Mark those SKILL.md bullets verify-only post-#3548 (re-tally --scope-anchor-file parse/refresh only) and drop allowlist/pre-vote rewrites from the net-new file list
  - From Codex-dyn-dep-boundary: Change the SKILL.md plan bullets to verify the existing allowlist and pre-vote render, then patch only the missing MainAgent re-tally --scope-anchor-file parsing and dual env refresh.

### FINDING_7: Tally passthrough test omits main-agent-vote-required status
- **Reviewer(s)**: Cursor-dyn-kv-wire
- **Severity**: important
- **Concern**: The `test-plan-review-loop` tally passthrough plan tests persistence only for `ok`, even though the plan requires `SCOPE_ANCHOR_FILE` relay for both `ok` and `main-agent-vote-required`. The 0-judge/main-agent-vote-required path could regress untested.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-kv-wire: Add main-agent-vote-required to the positive passthrough assertion (stub emits SCOPE_ANCHOR_FILE; result env and stdout retain it) alongside ok

### FINDING_8: run-step3-review plan may patch only allowlists and miss emit/env relay
- **Reviewer(s)**: Codex-dyn-kv-wire
- **Severity**: important
- **Concern**: The `run-step3-review` plan says to verify parse allowlists, normalized `emit_kv`, and result-env writes, but then narrows patching to missing allowlist arms. If `SCOPE_ANCHOR_FILE` parsing exists but stdout emit or `.step3-review-result.env` persistence is missing, the handoff could remain stale or absent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-dyn-kv-wire: Change the run-step3-review instruction to patch the exact missing surface among parse allowlists, normalized emit_kv, and .step3-review-result.env writes; keep verify-only when all three already exist.
