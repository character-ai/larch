```text
### FINDING_1: Orchestrator example may teach Markdown fences around the empty-merge attestation
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The orchestrator prompt shows a plain-text attestation inside a fenced Markdown block; models may echo ``` fences, so no line equals the bare full-line token and mechanical validation fails aggregation.
- **Suggested revision**: Remove the fence around the example or show a single-line literal with no wrapper lines; reinforce the exact full-line token requirement.

### FINDING_2: Empty-merge attestation removal uses raw-line `grep -x` while Python validation uses `str.strip()`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-attestation-protocol-output.txt, dyn-test-completeness-output.txt
- **Concern**: Lines that validate as the attestation only after stripping (padding, stray whitespace, CR, or other characters `strip` removes) can pass Python yet survive into persisted `findings.md`, breaking the “strip before replace” contract and brittle substring/`grep -Fq` checks.
- **Suggested revision**: Strip or filter using the same trimmed-line equality predicate as validation (for example a tiny Python/stdin pass, or `awk` that drops lines whose trimmed content equals the token), and add a padded-token regression case.

### FINDING_3: Trailing parenthetical slot label stripping is one-shot per call
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Only one trailing `(...)` suffix is stripped per pass; double-suffix or nested-paren labels can remain partially annotated and fail unknown-slot or missing-reviewer checks.
- **Suggested revision**: Document a one-suffix contract, or loop strip until stable, or add regression coverage if double suffixes are realistic.

### FINDING_4: Comment overclaims `input_slot_set` implies structured parsed reviewer findings
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Non-empty `input_slot_set` is described as implying structured input findings even when ballots have headings but no parsed reviewer lines, misleading maintainers debugging malformed ballots.
- **Suggested revision**: Reword to reference parsed reviewer labels only.

### FINDING_5: Shipped empty-merge + slot-normalization contract diverges from shorter plan/prompt text operators may follow
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Runtime behavior requires `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` for attested empty merges (not an unconditional “zero FINDING blocks” clean pass) and applies symmetric slot normalization beyond “output-only” expectations; external aggregators and mirrored docs can drift from `aggregate-findings.md` / `SECURITY.md` / orchestrator guidance and fail validation or mis-set operator expectations.
- **Suggested revision**: Align issue text, implementation plan, and release notes with the authoritative docs and prompts; call out the stricter attestation contract for downstream integrators.

### FINDING_6: Harness lacks coverage for symmetric normalization on input-side reviewer lines
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The labelled-slot fixture exercises output-side parentheticals but not input-side suffix normalization interacting with OOS-only rules, so regressions could slip past CI.
- **Suggested revision**: Add a harness case with parenthetical suffixes on input reviewer lines and assert expected ok/failure behavior.

### FINDING_7: Spurious full-line empty-merge token can persist when merge output also contains real FINDING blocks
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Non-empty structured merges copy vendor text verbatim, so a stray attestation line can remain in the rewritten ballot and surface as machine-only noise downstream.
- **Suggested revision**: Fail closed in Python when blocks exist and a stripped line equals the token, or strip full-line attestation tokens during staging regardless of block count (consistent with validation acceptance rules).

### FINDING_8: Minor contract drift: validator accepts attestation on any matching line vs orchestrator “end-of-file” wording
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Low practical risk, but prompt and mechanical rule disagree on placement semantics.
- **Suggested revision**: Align prompt text with the validator, or tighten validation to last-line semantics with tests.

### FINDING_9: `count_finding_blocks` is looser than Python’s structured block detection, risking wrong persist branch, uncleared attestation, and `MERGED_COUNT` skew
- **Reviewer(s)**: cursor-specialist-security-output.txt, dyn-slot-normalization-coverage-output.txt
- **Concern**: Bash counting can treat malformed `### FINDING_...` lines as blocks while Python sees zero parseable blocks, letting an attested empty-merge validation succeed while persistence takes the non-empty path—leaving tokens and mismatched counts relative to the validator’s structured-output definition.
- **Suggested revision**: Share one definition of a structured FINDING block across validation, counting, and stripping (tighten `count_finding_blocks` to match Python’s heading contract, or gate empty-merge success/strip paths on the Python block count).

### FINDING_10: Stderr guidance claims exact raw-line token equality while validation uses stripped-line equality
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Operators debugging whitespace cases get misleading error text relative to the actual acceptance predicate.
- **Suggested revision**: Reword stderr to match the real predicate (trimmed-line equality / full-line token semantics as implemented).

### FINDING_11: Symmetric trailing-parenthetical normalization on input collides distinct reviewers and conflicts with “output-only normalization” plan language
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Reviewers differing only by trailing parentheticals become indistinguishable for membership/OOS/coverage checks; plan text implied output-only normalization but implementation is symmetric on input.
- **Suggested revision**: Choose symmetric vs asymmetric normalization explicitly and make plan/docs match; keep/extend explicit operator warnings and avoid relying on parentheticals as the sole disambiguator.

### FINDING_12: Plan traceability gap: `SECURITY.md` and `agents/orchestrator-aggregator.md` changes not reflected in the implementation plan file list
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Reviewers diffing only the three-file plan miss contract edits that expanded the behavioral surface.
- **Suggested revision**: Amend the implementation plan or issue checklist to list all contract-touching files when behavior changes.

### FINDING_13: Plan regression documentation omits the negative empty-merge path (`zero_findings_no_attest`)
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Future plan reviews may treat the negative attestation path as unspecified even though the harness covers it.
- **Suggested revision**: Document the negative path in the plan’s regression section.

### FINDING_14: [OUT_OF_SCOPE] Product limitation: aggregation still no-ops for ballots with fewer than two FINDING blocks
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Empty-merge validation cannot apply to single-finding ballots without a separate product change.
- **Suggested revision**: None unless product wants aggregation for `INPUT_COUNT==1`.

### FINDING_15: [OUT_OF_SCOPE] Committed implement plan artifact may overshoot the chat plan snippet’s contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: Cross-artifact confusion for reviewers comparing plan snapshots to pasted chat plans; not a runtime code defect.
- **Suggested revision**: Align future planning copy with the chosen contract (process hygiene only).

### FINDING_16: [OUT_OF_SCOPE] Review prompt `<feature_description>` implies unconditional clean pass on zero FINDING blocks vs stricter attested empty merge in branch
- **Reviewer(s)**: dyn-attestation-protocol-output.txt
- **Concern**: The stricter branch behavior is internally consistent with updated orchestrator/docs/security guidance, but contradicts that one-liner in the review prompt context.
- **Suggested revision**: Treat as prompt/process alignment outside core runtime logic unless you intentionally unify all prompt surfaces.

### FINDING_17: [OUT_OF_SCOPE] Committed `larch-logs/implement/2E97A1B1-00F0-4ED0-9846-7608AD1C6016/*` may be PR noise vs aggregator logic
- **Reviewer(s)**: dyn-attestation-protocol-output.txt, dyn-slot-normalization-coverage-output.txt
- **Concern**: Process/release-surface additions (manifest/plan snapshot/tally) may warrant split/drop per `larch-logs/` policy, depending on merge conventions.
- **Suggested revision**: Confirm against run-log commit conventions and repo policy before merge packaging.
```
