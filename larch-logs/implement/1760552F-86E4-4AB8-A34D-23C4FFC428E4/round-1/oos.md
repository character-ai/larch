### FINDING_1: **Nit** `code-quality` `skills/review/scripts/tally-code-votes.md:28`, `skills/design/scripts/tally-plan-review.md:19` — The sibling docs for the changed tally scripts still document parser-fallback votes as `NEUT` / `NEUTRAL`, while the scripts now render `JERR` and `JUDGE_ERROR`. This can mislead contributors about the artifact contract after the rename. Update these docs to use `JERR` / `JUDGE_ERROR`, while keeping `NEUTRAL_COUNT` and finding-level `neutral` wording for tied-result semantics.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `skills/review/scripts/tally-code-votes.md:28`, `skills/design/scripts/tally-plan-review.md:19` — The sibling docs for the changed tally scripts still document parser-fallback votes as `NEUT` / `NEUTRAL`, while the scripts now render `JERR` and `JUDGE_ERROR`. This can mislead contributors about the artifact contract after the rename. Update these docs to use `JERR` / `JUDGE_ERROR`, while keeping `NEUTRAL_COUNT` and finding-level `neutral` wording for tied-result semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_10: [OUT_OF_SCOPE] code-quality: scripts/test-compose-review-findings.sh:65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fixture embeds legacy NEUTRAL=0 vote tally line. Not introduced by this diff; tests do not assert that literal in output. Optional: update fixture to JUDGE_ERROR=0 for consistency with new producer strings.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] code-quality: scripts/test-compose-review-findings.sh:65
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fixture Vote tally line still uses NEUTRAL=0. Not introduced by this diff; not in written plan. Optional align to JUDGE_ERROR=0 for parity with new producer output.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_12: [OUT_OF_SCOPE] correctness: skills/review/scripts/test-tally-code-votes.sh:84-157
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness-built parse-rate diag fixtures still use neutral_count= key while dispatch-code-voters.sh emits judge_error_count=. Tally binding ignores the key name so no functional failure; confusion when comparing harness fixtures to real dispatch diags. Rename neutral_count to judge_error_count in printf fixture lines for consistency.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_13: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/tally-plan-review.md:19,35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Quorum/coverage prose still refers to NEUTRAL abstentions/votes while tally-plan-review.sh now labels the per-judge column JErr and uses JUDGE_ERROR counts in vote tally lines. Same operator-facing doc drift as code-review tally doc. Update tally-plan-review.md quorum section to use JUDGE_ERROR parser-fallback language and distinguish finding-level neutral where needed.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_14: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/tally-code-votes.md:28-78
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Sibling script doc still documents NEUT column and NEUTRAL= tally suffix and NEUTRAL abstention language after tally-code-votes.sh switched to JERR/JUDGE_ERROR= and JUDGE_ERROR parse-rate wording. Operators or tests reading only the .md get a mismatched picture of on-disk tally artifacts vs this branch’s script output. Update tally-code-votes.md to match JERR/JUDGE_ERROR terminology and clarify JUDGE_ERROR vs NEUTRAL_COUNT.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_19: code-quality: skills/review/scripts/test-tally-code-votes.sh:279-290
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test case labels still say 2 NEUTRAL for per-judge missing votes. Misleading when scanning test output for JUDGE_ERROR terminology. Rename echo/assert descriptions to JUDGE_ERROR for consistency with other harnesses.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_2: **Nit** `code-quality` `skills/review/scripts/test-tally-code-votes.sh:84`, `skills/design/scripts/test-tally-plan-review.sh:158`, `scripts/test-compose-review-findings.sh:65` — Several harness fixtures/descriptions still encode the old parser-fallback label (`neutral_count` diag fields and `NEUTRAL` vote-tally/descriptive text). The tests may still pass because those fields are not parsed for the count name, but they no longer verify the renamed contract. Update these fixtures/descriptions to `judge_error_count` / `JUDGE_ERROR` where they refer to parser fallback, leaving tied-result `neutral` assertions unchanged.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/review/scripts/test-tally-code-votes.sh:84`, `skills/design/scripts/test-tally-plan-review.sh:158`, `scripts/test-compose-review-findings.sh:65` — Several harness fixtures/descriptions still encode the old parser-fallback label (`neutral_count` diag fields and `NEUTRAL` vote-tally/descriptive text). The tests may still pass because those fields are not parsed for the count name, but they no longer verify the renamed contract. Update these fixtures/descriptions to `judge_error_count` / `JUDGE_ERROR` where they refer to parser fallback, leaving tied-result `neutral` assertions unchanged.
- **Suggested revision**: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_20: code-quality: skills/review/scripts/test-tally-code-votes.sh:279-291
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test case prose still says NEUTRAL / neutral quorum for a scenario driven by empty voter outputs (judge_error counts). Vocabulary drifts from renamed semantics; assertions remain numeric. Rename echo/assert descriptions to JUDGE_ERROR / judge_error column wording.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_21: code-quality: skills/review/scripts/test-tally-code-votes.sh:84-157
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Parse-rate diag fixtures still use neutral_count= while dispatch-code-voters.sh writes judge_error_count=. No CI breakage (diag matcher ignores that field), but fixture vs production diag shape diverges. Rename fixture field to judge_error_count for parity.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_22: risk-integration: scripts/test-compose-review-findings.sh:65
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fixture Vote tally line still uses NEUTRAL=0 while producers moved to JUDGE_ERROR=. Low risk today; encourages wrong assumptions about canonical vote tally key. Change fixture to JUDGE_ERROR=0 for consistency with tally output.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=1 EXON=0 NEUTRAL=0 Result=accepted

### FINDING_25: risk-integration: skills/design/scripts/tally-plan-review.md:19,35
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] tally-plan-review.md still says NEUTRAL abstentions / NEUTRAL votes for quorum behavior. Cross-doc readers see JUDGE_ERROR in shared voting docs but NEUTRAL for the same parser fallback in the plan-review tally doc. Align wording with voting-protocol.md / lib-vote-tally.md (keep scoreboard Neutral/Exon as tied-vote semantics).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_26: risk-integration: skills/design/scripts/tally-plan-review.md:19-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Invariants/harness text still says NEUTRAL abstentions / NEUTRAL votes for quorum. tally-plan-review.sh now labels JErr/JUDGE_ERROR; doc reinforces the old conflation between parser fallback and tied-vote neutral. Reword to JUDGE_ERROR per-judge parser fallback vs finding-level neutral/NEUTRAL_COUNT as in run-logs.md note.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_27: risk-integration: skills/review/scripts/tally-code-votes.md:28-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Producer doc still specifies NEUT column and NEUTRAL= vote tally suffix while tally-code-votes.sh emits JERR and JUDGE_ERROR=. Downstream docs/tests or humans matching documented literals misread real rejected-findings and voting-tally artifacts. Update tally-code-votes.md table header suffix line NEUTRAL= to JUDGE_ERROR=; change NEUT to JERR; refresh quorum and harness lines at :70 and :78.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_28: risk-integration: skills/review/scripts/tally-code-votes.md:28-31,70
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] tally-code-votes.md still documents NEUT column and NEUTRAL= vote tally lines and NEUTRAL wording for missing votes, but tally-code-votes.sh now emits JERR and JUDGE_ERROR=. A contributor or harness author following this doc asserts legacy tokens against new voting-tally.md or rejected-findings tails and gets false failures or wrong expectations. Update the artifact and threshold sections to JERR / JUDGE_ERROR and clarify distinction from NEUTRAL_COUNT (finding-level neutral).
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_29: risk-integration: skills/review/scripts/tally-code-votes.md:28-78 skills/design/scripts/tally-plan-review.md:19-35
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sibling tally markdown still documents NEUT column and NEUTRAL= vote tally lines plus NEUTRAL abstention wording after code/docs rename to JERR/JUDGE_ERROR. Downstream readers treat markdown as contract and grep or parse stale tokens missing real tallies. Update tally-code-votes.md and tally-plan-review.md to match script outputs and distinguish JUDGE_ERROR vs finding-level neutral.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_31: risk-integration: skills/review/scripts/test-tally-code-votes.sh:84-157
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate diag harness fixtures still emit neutral_count= while dispatch writes judge_error_count=. Future diag validation or human diffing sees format skew vs production without functional failure today. Rename fixture field to judge_error_count= to mirror dispatch-code-voters.sh.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 NEUTRAL=0 Result=accepted

### FINDING_7: [OUT_OF_SCOPE] **[correctness]** Under [`larch-logs/implement/`](larch-logs/implement/) there are many historical artifacts with `| NEUT |` headers and `NEUTRAL=` in vote tally lines; they were not in the provided diff. Updating them is a policy/content choice, not a functional regression in code paths.
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** Under [`larch-logs/implement/`](larch-logs/implement/) there are many historical artifacts with `| NEUT |` headers and `NEUTRAL=` in vote tally lines; they were not in the provided diff. Updating them is a policy/content choice, not a functional regression in code paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] **[correctness]** [`scripts/write-tally.sh`](scripts/write-tally.sh):24,114 and [`scripts/compose-tally-record.sh`](scripts/compose-tally-record.sh):18,49 — `NEUTRAL` / `--neutral` refer to **envelope** tied-vote counts for JSON/tally records, which correctly remain per the plan (“do not rename finding-level neutral…”).
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** [`scripts/write-tally.sh`](scripts/write-tally.sh):24,114 and [`scripts/compose-tally-record.sh`](scripts/compose-tally-record.sh):18,49 — `NEUTRAL` / `--neutral` refer to **envelope** tied-vote counts for JSON/tally records, which correctly remain per the plan (“do not rename finding-level neutral…”). **What looked solid in the diff:** [`scripts/lib-vote-tally.sh`](scripts/lib-vote-tally.sh) and [`scripts/dispatch-code-voters.sh`](scripts/dispatch-code-voters.sh) `BEGIN { result="JUDGE_ERROR" }` plus `grep -c '^JUDGE_ERROR'` stay aligned; [`skills/review/scripts/tally-code-votes.sh`](skills/review/scripts/tally-code-votes.sh) preserves `classify_result` → `neutral` / `NEUTRAL_COUNT` paths; [`docs/run-logs.md`](docs/run-logs.md) note correctly separates `neutral_count` vs `JUDGE_ERROR` / `JERR`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 NEUTRAL=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Historical run logs retain NEUT/NEUTRAL= strings. Pre-existing committed snapshots; not part of this rename diff’s runtime surface. None unless a separate log-normalization change is desired.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 NEUTRAL=0 Result=rejected

