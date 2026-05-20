### FINDING_1: **Important** `correctness` `skills/review/scripts/collect-findings.sh:281-284` — Once the parser sees `## Commits since merge-base`, `skip=1` is only cleared by canonical `### In-Scope Findings` / `### Out-of-Scope Observations` headings. Concrete failing scenario: reviewer output with a merge-base preamble followed by `## Findings` and `- Real bug in scripts/foo.sh:42` now yields `FINDINGS_COUNT=0`, silently dropping the real finding. Clear `skip` on the next non-preamble heading in addition to the canonical section headings, then continue fail-open parsing.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Important** `correctness` `skills/review/scripts/collect-findings.sh:281-284` — Once the parser sees `## Commits since merge-base`, `skip=1` is only cleared by canonical `### In-Scope Findings` / `### Out-of-Scope Observations` headings. Concrete failing scenario: reviewer output with a merge-base preamble followed by `## Findings` and `- Real bug in scripts/foo.sh:42` now yields `FINDINGS_COUNT=0`, silently dropping the real finding. Clear `skip` on the next non-preamble heading in addition to the canonical section headings, then continue fail-open parsing.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/compose-review-findings.sh:113-214
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] REJ_C and OOS_C ids restart per parse_artifact so duplicate id across rounds. Two rounds each REJ_C1 consumer keyed on id alone merges distinct findings. Include round in id or document composite key id plus round_num.
- **Suggested revision**: Address the concern above.


### FINDING_15: risk-integration: scripts/test-compose-review-findings.md:11-12 scripts/compose-review-findings.sh:184-190
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Legacy OOS heading path is documented and implemented but not exercised by the regression harness. A typo or logic change in the ### OOS_…: branch could ship without failing CI while older oos.md files stop producing JSONL rows. Add an oos.md fixture using ### OOS_1: and assert ids outcome reviewer body.
- **Suggested revision**: Address the concern above.


### FINDING_2: **Important** `security` `scripts/compose-review-findings.sh:228` — The new OOS ingestion reads `round-*/oos.md` directly, but `skills/review/scripts/tally-code-votes.sh:354-359` writes security-tagged accepted OOS blocks there before holding them back from public OOS artifacts. Concrete failing scenario: an accepted OOS block containing unfenced `focus-area = security` is appended to `round-1/oos.md`; `compose-review-findings.sh` now emits it into committed `review-findings-full.jsonl`, exposing prose that the security policy says must remain local. Add the same security-tag classifier/holdback before emitting `code-review-oos` records, or consume a visibility-safe OOS artifact instead.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `security` `scripts/compose-review-findings.sh:228` — The new OOS ingestion reads `round-*/oos.md` directly, but `skills/review/scripts/tally-code-votes.sh:354-359` writes security-tagged accepted OOS blocks there before holding them back from public OOS artifacts. Concrete failing scenario: an accepted OOS block containing unfenced `focus-area = security` is appended to `round-1/oos.md`; `compose-review-findings.sh` now emits it into committed `review-findings-full.jsonl`, exposing prose that the security policy says must remain local. Add the same security-tag classifier/holdback before emitting `code-review-oos` records, or consume a visibility-safe OOS artifact instead.
- **Suggested revision**: Address the concern above.


