### FINDING_3: Input-side slot / OOS membership sets disagree with output-side normalization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Output reviewer labels are normalized before `input_slot_set` and OOS-only checks, while input-derived sets store raw tokens. A suffixed input label that normalizes like output can be absent from the raw set (false validation failure). Conversely, `oos_only_slots` built from raw tokens may not match normalized merge output, so an OOS-only rule can fail to apply and forbidden non-OOS attribution could pass when raw vs normalized keys diverge (including “bare vs `(via …)`” style pairs).
- **Suggested revision**: Build input and OOS membership keys with the same `normalize_slot` (or align both sides on an explicit canonical key), or document and enforce that input labels never use patterns the normalizer strips.


### FINDING_5: Zero-findings regression should assert `INPUT_COUNT`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The zero-findings regression checks merged count and reason but not `INPUT_COUNT` against the known three-block ballot, so a regression in `INPUT_COUNT` computation or emit ordering could slip through while headings and `MERGED_COUNT` still look correct, misleading downstream consumers of `INPUT_COUNT`.
- **Suggested revision**: Assert `INPUT_COUNT=3` on the emitted env file (e.g. grep) alongside existing `MERGED_COUNT` and `REASON` checks.


### FINDING_6: Accepting zero merged FINDING blocks after non-empty input risks silent ballot replacement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Empty structured output can pass Python validation while narrative text remains; a non-empty staged copy may then replace `findings.md` with `MERGED_COUNT=0`, so a faulty or prompt-injected aggregator could drop all FINDING blocks without an obvious machine-readable failure mode.
- **Suggested revision**: Add compensating controls: distinct `REASON` or warning when input had findings but merge has zero blocks; an explicit allow flag; or a required machine-readable sentinel before accepting zero-block merges.


