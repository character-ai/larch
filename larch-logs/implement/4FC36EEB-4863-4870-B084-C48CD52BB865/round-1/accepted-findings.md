### FINDING_1: code-quality: agents/orchestrator-aggregator.md:46-52
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Fenced ```text example illustrates empty-merge layout adjacent to rules forbidding fences in real output. Model may emit closing fence lines so the last line is not the bare token; validation still fails until synthesis, undermining prompt-side hardening. Add an explicit anti-fence sentence under the example or show the layout without triple-backtick fences.
- **Suggested revision**: Address the concern above.


### FINDING_10: risk-integration: agents/orchestrator-aggregator.md:46-52
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Example wraps the attestation token in a Markdown fenced code block while adjacent rules forbid fences for real output. Model may echo the example and emit fenced or wrapped token lines so trimmed-line validation still fails or synthesis fires more often, undermining prompt-side hardening. Reformat the example so the token appears as the final plain line with no surrounding ``` fences, consistent with checklist item 2.
- **Suggested revision**: Address the concern above.


### FINDING_12: correctness: skills/review/scripts/aggregate-findings.sh:473-622
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Synthesis turns former validation failures into success whenever Python sees zero FINDING blocks, even if the vendor text contains malformed or non-conforming FINDING headings that no longer match the strict split regex. Model returns merge text where headings drift (missing colon, spacing, etc.): previously validation failed and findings.md was preserved; now attestation is appended, validation passes, and the ballot can be replaced with narrative or broken headings—silent loss of structured merge compared to the old fail-closed path. Tighten the synthesis gate so accidental non-empty pseudo-heading output cannot use the empty-merge recovery path, or document the deliberate tradeoff and add a structural precheck aligned with real FINDING headers.
- **Suggested revision**: Address the concern above.


### FINDING_13: risk-integration: agents/orchestrator-aggregator.md:40-54
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] The worked example embeds the attestation inside a Markdown fenced code block while the contract forbids fenced wrapping in real aggregator output. Models may copy fences into real aggregator-output.txt, conflicting with formatting rules and complicating downstream reading even though script-side recovery may paper over missing standalone lines. Replace the fenced example with a fence-free ASCII layout or add an explicit anti-copy instruction separating example scaffolding from required production shape.
- **Suggested revision**: Address the concern above.


### FINDING_16: correctness: skills/review/scripts/aggregate-findings.sh:603-622
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] Plan Breaking changes claimed aggregator-output.txt still exposes raw vendor-only bytes; implementation overwrites staged cand with repaired text before validation. Consumers or audits diffing dispatch capture vs aggregator-output.txt on synthesis rounds see extra attestation line not emitted by the vendor; any automation assuming byte-identical model output breaks. Revise consumer contract to post-repair staged output or add a separate vendor-only artifact if needed.
- **Suggested revision**: Address the concern above.


### FINDING_18: **correctness** `agents/orchestrator-aggregator.md:40-52` — The new “Example layout” shows the attestation inside a fenced ` ```text ` block, while checklist item 2 forbids Markdown code fences and wrapping the token in a fenced block; a merging model that mirrors the example can emit fence lines so no raw line’s `strip()` equals `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, keeping validation failure on the hot path (or producing non-strip-safe output) despite the intended hardening. **Suggested fix:** Present the example only as unfenced plain text (fixed-width indentation or a “file ends like this” prose block) so the literal last line is visibly a bare token line, and keep the prohibition adjacent without a contradictory fenced sample.
- **Reviewer**: dyn-synthesis-invariants-output.txt
- **Concern**: - **correctness** `agents/orchestrator-aggregator.md:40-52` — The new “Example layout” shows the attestation inside a fenced ` ```text ` block, while checklist item 2 forbids Markdown code fences and wrapping the token in a fenced block; a merging model that mirrors the example can emit fence lines so no raw line’s `strip()` equals `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED`, keeping validation failure on the hot path (or producing non-strip-safe output) despite the intended hardening. **Suggested fix:** Present the example only as unfenced plain text (fixed-width indentation or a “file ends like this” prose block) so the literal last line is visibly a bare token line, and keep the prohibition adjacent without a contradictory fenced sample.
- **Suggested revision**: Address the concern above.


### FINDING_21: **risk-integration** `skills/review/scripts/test-aggregate-findings.sh:436-441` — The synthesis regression case only checks `grep -Fq 'ATTESTATION_SYNTHESIZED=true'` on `aggregator-repair.stderr`, so CI would not catch a regression that drops the `input_slots=<N>` audit field, changes its format, or splits the breadcrumb across lines while still printing a substring match. **Suggested fix:** Assert the full single-line machine-readable record (for example anchor `aggregator-repair.stderr` with `grep -Eq '^ATTESTATION_SYNTHESIZED=true input_slots=[0-9]+$'` and, if useful, pin the expected count to `3` for the `in3.md` fixture so audits and `/audit-runs` style tooling can rely on the same contract as `skills/review/scripts/aggregate-findings.sh:500-503` and `skills/review/scripts/aggregate-findings.md:28`).
- **Reviewer**: dyn-breadcrumb-integrity-output.txt
- **Concern**: - **risk-integration** `skills/review/scripts/test-aggregate-findings.sh:436-441` — The synthesis regression case only checks `grep -Fq 'ATTESTATION_SYNTHESIZED=true'` on `aggregator-repair.stderr`, so CI would not catch a regression that drops the `input_slots=<N>` audit field, changes its format, or splits the breadcrumb across lines while still printing a substring match. **Suggested fix:** Assert the full single-line machine-readable record (for example anchor `aggregator-repair.stderr` with `grep -Eq '^ATTESTATION_SYNTHESIZED=true input_slots=[0-9]+$'` and, if useful, pin the expected count to `3` for the `in3.md` fixture so audits and `/audit-runs` style tooling can rely on the same contract as `skills/review/scripts/aggregate-findings.sh:500-503` and `skills/review/scripts/aggregate-findings.md:28`).
- **Suggested revision**: Address the concern above.


### FINDING_4: risk-integration: agents/orchestrator-aggregator.md:46-52
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Fenced Markdown example for empty-merge layout adjacent to rules forbidding fences in real output Model copies ``` fences into real aggregator output; repair synthesizes attestation; strip removes only attestation lines; persisted findings.md retains stray fence lines Use a non-fenced example or explicitly forbid copying backticks from the template
- **Suggested revision**: Address the concern above.


### FINDING_5: risk-integration: skills/review/scripts/aggregate-findings.sh:602-622
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Synthesis overwrites aggregator-output.txt (cand) so it is not strictly verbatim vendor-only output Operator assumes aggregator-output.txt is exact model bytes when breadcrumb shows synthesis; attribution/debug mismatch Document single source of truth or add pre-repair snapshot file if verbatim retention is required
- **Suggested revision**: Address the concern above.


### FINDING_6: correctness: skills/review/scripts/aggregate-findings.sh:473-490
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Breadcrumb input_slots counts unique normalized reviewer labels not finding cardinality Three findings one reviewer shows input_slots=1; audit metrics misread severity Rename metric or add finding-count field
- **Suggested revision**: Address the concern above.


### FINDING_9: risk-integration: skills/review/scripts/test-aggregate-findings.sh:439
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Breadcrumb test only matches ATTESTATION_SYNTHESIZED=true prefix, not input_slots=<N> from the plan/implementer contract. A future edit could drop the input_slots= field from stderr and tests would still pass, weakening observability promised in aggregate-findings.md. Assert the full expected line for the fixture (e.g. input_slots=3 for in3.md) or use a strict line equality check on aggregator-repair.stderr.
- **Suggested revision**: Address the concern above.


