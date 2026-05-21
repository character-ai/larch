# Review Round 3

- Mode: `diff`
- Accepted findings: 5
- Rejected findings: 0
- Exonerated findings: 8
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Orchestrator example may teach Markdown fences around the empty-merge attestation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The orchestrator prompt shows a plain-text attestation inside a fenced Markdown block; models may echo ``` fences, so no line equals the bare full-line token and mechanical validation fails aggregation.
- **Suggested revision**: Remove the fence around the example or show a single-line literal with no wrapper lines; reinforce the exact full-line token requirement.


### FINDING_10: Stderr guidance claims exact raw-line token equality while validation uses stripped-line equality
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators debugging whitespace cases get misleading error text relative to the actual acceptance predicate.
- **Suggested revision**: Reword stderr to match the real predicate (trimmed-line equality / full-line token semantics as implemented).


### FINDING_2: Empty-merge attestation removal uses raw-line `grep -x` while Python validation uses `str.strip()`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-attestation-protocol-output.txt, dyn-test-completeness-output.txt
- **Concern**: Lines that validate as the attestation only after stripping (padding, stray whitespace, CR, or other characters `strip` removes) can pass Python yet survive into persisted `findings.md`, breaking the “strip before replace” contract and brittle substring/`grep -Fq` checks.
- **Suggested revision**: Strip or filter using the same trimmed-line equality predicate as validation (for example a tiny Python/stdin pass, or `awk` that drops lines whose trimmed content equals the token), and add a padded-token regression case.


### FINDING_6: Harness lacks coverage for symmetric normalization on input-side reviewer lines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The labelled-slot fixture exercises output-side parentheticals but not input-side suffix normalization interacting with OOS-only rules, so regressions could slip past CI.
- **Suggested revision**: Add a harness case with parenthetical suffixes on input reviewer lines and assert expected ok/failure behavior.


### FINDING_7: Spurious full-line empty-merge token can persist when merge output also contains real FINDING blocks
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Non-empty structured merges copy vendor text verbatim, so a stray attestation line can remain in the rewritten ballot and surface as machine-only noise downstream.
- **Suggested revision**: Fail closed in Python when blocks exist and a stripped line equals the token, or strip full-line attestation tokens during staging regardless of block count (consistent with validation acceptance rules).


