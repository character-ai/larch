Here is the normalized structured finding list (merged by shared risk, stable IDs in first-seen theme order, sources preserved).

```text
### FINDING_1: Validation contract prose is hard to maintain
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The validation-contract bullet in aggregate-findings documentation is one very long sentence, which makes it harder to maintain and verify completeness as behavior grows.
- **Suggested revision**: Split into multiple shorter bullets with the same semantics.

### FINDING_2: `normalize_slot` trailing-parenthetical stripping is incomplete for nested and stacked suffixes
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-normalization-coverage-output.txt
- **Concern**: A single-pass regex using `[^)]*` only strips one flat trailing `(…)` group. Nested parentheses in the suffix (e.g. `(via C.2 (gap))`, `(see Foo (bar))`) may not strip to the intended base token; stacked flat suffixes like `(note1) (note2)` can normalize only once and still disagree with a bare input key. That yields false `validation-failed` for otherwise-correct base slots or inconsistent slot identity versus expectations.
- **Suggested revision**: Document explicitly unsupported shapes (and keep tests aligned), or tighten parsing: loop until stable with a small cap, strip repeated trailing `\s*\([^)]*\)` segments, or use a narrower allowed suffix rule; add regression coverage if stacked flat suffixes are meant to be valid.

### FINDING_3: Input-side slot / OOS membership sets disagree with output-side normalization
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Output reviewer labels are normalized before `input_slot_set` and OOS-only checks, while input-derived sets store raw tokens. A suffixed input label that normalizes like output can be absent from the raw set (false validation failure). Conversely, `oos_only_slots` built from raw tokens may not match normalized merge output, so an OOS-only rule can fail to apply and forbidden non-OOS attribution could pass when raw vs normalized keys diverge (including “bare vs `(via …)`” style pairs).
- **Suggested revision**: Build input and OOS membership keys with the same `normalize_slot` (or align both sides on an explicit canonical key), or document and enforce that input labels never use patterns the normalizer strips.

### FINDING_4: Test harness FINDING heading pattern may diverge from merge count semantics
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: The harness counts headings with `^### FINDING_` while `aggregate-findings.sh` uses a stricter pattern (e.g. `^### FINDING_[0-9]` / canonical numeric headings), so odd non-canonical heading lines could make the test’s block count disagree from `MERGED_COUNT` / `count_finding_blocks` semantics.
- **Suggested revision**: Align the test grep with `count_finding_blocks` (and the intended canonical heading contract).

### FINDING_5: Zero-findings regression should assert `INPUT_COUNT`
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: The zero-findings regression checks merged count and reason but not `INPUT_COUNT` against the known three-block ballot, so a regression in `INPUT_COUNT` computation or emit ordering could slip through while headings and `MERGED_COUNT` still look correct, misleading downstream consumers of `INPUT_COUNT`.
- **Suggested revision**: Assert `INPUT_COUNT=3` on the emitted env file (e.g. grep) alongside existing `MERGED_COUNT` and `REASON` checks.

### FINDING_6: Accepting zero merged FINDING blocks after non-empty input risks silent ballot replacement
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: Empty structured output can pass Python validation while narrative text remains; a non-empty staged copy may then replace `findings.md` with `MERGED_COUNT=0`, so a faulty or prompt-injected aggregator could drop all FINDING blocks without an obvious machine-readable failure mode.
- **Suggested revision**: Add compensating controls: distinct `REASON` or warning when input had findings but merge has zero blocks; an explicit allow flag; or a required machine-readable sentinel before accepting zero-block merges.

### FINDING_7: Zero-block acceptance path reduces stderr observability for structured validation
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Concern**: When there are zero output FINDING blocks, the prior stderr signal may be absent, making it harder to tell from validator stderr alone whether structured checks were intentionally skipped vs failed elsewhere.
- **Suggested revision**: Add optional verbose stderr or debug logging when accepting zero blocks.

### FINDING_8: [OUT_OF_SCOPE] Implement run log artifacts in the branch
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-normalization-coverage-output.txt
- **Concern**: Committed implement run material under `larch-logs/implement/2E97A1B1-00F0-4ED0-9846-7608AD1C6016/` (and a commit that is logs-only) has no runtime impact on the aggregator but widens PR surface versus a small targeted diff.
- **Suggested revision**: None for functional aggregator review; treat as scope/process (drop, split PR, or accept as intentional run-log policy).

### FINDING_9: [OUT_OF_SCOPE] Python validator path handling from `sys.argv`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: The validator opens paths from `sys.argv` without extra hardening; if invoked outside the bash wrapper, that could read/write unintended paths (pre-existing surface).
- **Suggested revision**: Keep execution confined to the bash wrapper; only if hardening is required, validate paths against an allowlisted root.

### FINDING_10: [OUT_OF_SCOPE] Bash vs Python FINDING heading pattern skew for malformed headings
- **Reviewer(s)**: dyn-normalization-coverage-output.txt
- **Concern**: Bash `count_finding_blocks` uses `^### FINDING_[0-9]` while the Python validator expects `^### FINDING_[0-9]+:`; the skew predates the current change and mainly matters for malformed headings, not the new zero-block or labelled-slot paths.
- **Suggested revision**: None required for this change set unless tightening malformed-heading behavior is in scope later; align patterns if that surface becomes user-visible.
```
