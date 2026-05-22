# Review Round 4

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 0
- Exonerated findings: 6
- Neutral findings: 0

## Accepted Findings

### FINDING_1: Revision traceability relies on a weak six-word prefix heuristic
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: In `revision_traceable_in_blocks` (and related advisory traceability), a six-word normalized prefix can match unrelated prose in the same scoped block, so a fabricated or paraphrased bullet whose head collides with common text can pass without a full normalized substring match—undermining verbatim-trace intent and risking false passes or noisy diagnostics on odd punctuation or large inputs.
- **Suggested revision**: Prefer full normalized substring matching for `From:`-slot bullets (or isolate any prefix fallback behind an explicit legacy/opt-in path); add a regression where prefix matches but full normalized text does not; optionally add a strict full-string-only mode if policy requires it.


### FINDING_2: `compose_coder_prompt` diverges from the plan’s shape, length, and emphasis
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: The coder prompt is one long `printf` with many clauses (higher token load), emphasizes “substantive issue behind” revisions versus the plan’s informational framing, risks treating quoted multi-reviewer bullets as ambiguous between hard constraints and hints, and may reference multi-reviewer bullets even when absent; the plan called for a minimal additive sentence but the change rewrote the whole directive—so regressions in wording could ship without dispatch harness pins.
- **Suggested revision**: Shorten and align wording with the plan (informational revisions, minimal change, clear status of bullets), prefer the minimal additive edit or document the broader rewrite as the canonical contract, and add stable `grep -Fq` pins on generated coder prompt text in `test-review-and-fix.sh` (or equivalent) alongside voter-style coverage.


### FINDING_3: Suggested-revisions sub-list parsing can drop or truncate content
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: `suggested_revisions_bullets` can silently ignore lines between the “Suggested revisions” header and the first `From:` bullet; sub-list termination keyed on top-level heading patterns can cut off early when verbatim fix text contains lines resembling field headings (for example a line like `- **Concern**:`), hiding suffix content from advisory scans.
- **Suggested revision**: Warn or fail validation on unexpected pre-`From` lines; narrow end-of-sub-list detection with real structural boundaries (or document forbidden patterns inside verbatim fixes) and add fixtures/tests for those shapes.


### FINDING_6: OOS disposition gate may run without authoritative `--oos-issues-ndjson`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: When session id is empty and no ndjson is discovered under `larch-logs/implement`, the gate may omit `--oos-issues-ndjson` while still evaluating other signals—risking divergence from combined-evidence intent for NDJSON-only filed URLs or rejected-OOS markers.
- **Suggested revision**: Persist the authoritative `oos-issues.ndjson` path from the issue pipeline and fail closed when non-security OOS blocks exist but that path is missing, instead of running the gate without the flag.


