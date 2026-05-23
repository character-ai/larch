# Review Round 1

- Mode: `diff`
- Accepted findings: 8
- Rejected findings: 0
- Exonerated findings: 2
- Neutral findings: 2

## Accepted Findings

### FINDING_1: docs/agents.md dialectic + judge prose contradicts per-side / waterfall / Claude retry contract
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] `docs/agents.md` still reads as same-tool bucketing, absolute no-Claude in debate, and (in the judge block) blanket “no Claude in debate,” which conflicts with per-side assignment, degraded mode, six-tag gate, waterfall, and the Claude second-retry exception documented in `dialectic-protocol.md`, `dialectic-execution.md`, and `skills/design/SKILL.md`. Operators and contributors can mis-audit or mis-implement `/design` Step 2a.5 and trust boundaries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Mirror per-side assignment waterfall and Claude 2nd-retry exception from dialectic-protocol.md; remove obsolete bucket-homogeneity wording
  - From cursor-specialist-edge-cases-output.txt: Rewrite subsection to match per-side assignment waterfall Claude 2nd-retry exception and six-tag gate.
  - From cursor-specialist-plan-fidelity-output.txt: Rewrite the subsection to match dialectic-execution.md steps 3 and 8b and SKILL.md NEVER #2 exception wording.


### FINDING_10: `skills/design/references/dialectic-debate.md` mixes meta/SELF-CHECK rules with deliverable-only external-read constraints
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Top-level prose may conflict with internal SELF-CHECK / content rules in the same template, risking model-added headings or tag mis-ordering that re-triggers quorum failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Clarify deliverable-only prose boundary or relocate meta instructions outside verbatim external-read block.


### FINDING_11: `scripts/render-debate-retry-prompt.sh` passes unknown failure-reason tokens through verbatim into retry prompts
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: [latent] If failure strings can include debater-controlled or otherwise untrusted text, downstream Cursor/Codex/Claude calls may receive instruction-shaped content; an allowlist/sanitize/reject posture reduces that injection surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Allowlist parseable failure tokens and reject or sanitize anything else


### FINDING_2: `scripts/render-debate-retry-prompt.sh` requires `--previous-output-file` but does not consume file contents
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Mandatory `--previous-output-file` is validated for existence but prior output is not embedded or otherwise used, so the CLI contract suggests excerpting/corrective context that is not implemented; callers and maintainers can rely on behavior that does not exist (and retry prompts get weaker context than implied).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Either read bounded prior output into the template or remove the unused parameter from the contract
  - From cursor-specialist-edge-cases-output.txt: Document provenance-only or embed bounded excerpt.


### FINDING_3: `skills/design/references/dialectic-execution.md` step numbering and cross-references are inconsistent or dangling
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Internal numbering jumps (e.g. 3 to 6) without an explicit bridge to `SKILL.md` steps, while eligibility/over-cap prose references “steps 1/4/5 above” or “step 1” that are not co-located in-file, breaking maintenance and mis-anchoring cap/skip semantics for readers who treat this file as standalone.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Add explicit cross-reference or renumber internal steps.
  - From cursor-specialist-testing-output.txt: Reintroduce concise steps 1–5 or retarget prose to explicit SKILL.md Step 2a.5 anchors.
  - From cursor-specialist-edge-cases-output.txt: Point to SKILL Step 2a.5 item 1 or restate cap inline.


### FINDING_4: `skills/design/references/dialectic-execution.md` gate text implies finalization after externals, before Claude retry / waterfall completion
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Wording such as classifying or proceeding “after all external debaters return” can be read as excluding the Step 8b Claude second-retry path and final waterfall completion, risking premature disposition/ballot assembly relative to authoritative debate outputs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Reword to after all debate outputs final including retries and Claude path.


### FINDING_7: Ballot vendor/model leak coverage is weaker than protocol mandates (smoke + plan-level regression gap)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-security-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Protocol requires stripping additional vendor/model substrings from ballot/defense bodies beyond Cursor/Codex/Claude, but `scripts/dialectic-smoke-test.sh` anonymity checks appear limited to a small substring set; combined with plan failure-mode language calling for a Claude-retry ballot scan, regressions could ship while smoke still passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add harness or smoke fixture covering Claude retry2 + ballot scan.
  - From cursor-specialist-testing-output.txt: Extend validate_ballot_anonymity (and optionally add a retry2 fixture) to assert those substrings never appear in dialectic ballot bodies.
  - From cursor-specialist-security-output.txt: Extend validate_ballot_anonymity for the same substring set as the protocol or implement stripping in a dedicated ballot script with tests
  - From cursor-specialist-plan-fidelity-output.txt: Extend validate_ballot_anonymity to the protocol-listed tokens and add a minimal fixture or assertion covering a Claude-retry-shaped ballot.


### FINDING_8: `skills/design/references/dialectic-execution.md` collector discipline may be misapplied to Agent-tool Claude retry outputs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Collector guidance can be read as requiring `collect-agent-results.sh` broadly, without carving out non-sentinel Agent-tool Claude retry completion paths where `Write` completion is authoritative.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.


