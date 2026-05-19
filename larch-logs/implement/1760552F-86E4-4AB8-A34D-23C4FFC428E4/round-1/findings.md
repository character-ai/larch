### FINDING_1: **Nit** `code-quality` `skills/review/scripts/tally-code-votes.md:28`, `skills/design/scripts/tally-plan-review.md:19` — The sibling docs for the changed tally scripts still document parser-fallback votes as `NEUT` / `NEUTRAL`, while the scripts now render `JERR` and `JUDGE_ERROR`. This can mislead contributors about the artifact contract after the rename. Update these docs to use `JERR` / `JUDGE_ERROR`, while keeping `NEUTRAL_COUNT` and finding-level `neutral` wording for tied-result semantics.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Nit** `code-quality` `skills/review/scripts/tally-code-votes.md:28`, `skills/design/scripts/tally-plan-review.md:19` — The sibling docs for the changed tally scripts still document parser-fallback votes as `NEUT` / `NEUTRAL`, while the scripts now render `JERR` and `JUDGE_ERROR`. This can mislead contributors about the artifact contract after the rename. Update these docs to use `JERR` / `JUDGE_ERROR`, while keeping `NEUTRAL_COUNT` and finding-level `neutral` wording for tied-result semantics.
- **Suggested revision**: Address the concern above.

### FINDING_2: **Nit** `code-quality` `skills/review/scripts/test-tally-code-votes.sh:84`, `skills/design/scripts/test-tally-plan-review.sh:158`, `scripts/test-compose-review-findings.sh:65` — Several harness fixtures/descriptions still encode the old parser-fallback label (`neutral_count` diag fields and `NEUTRAL` vote-tally/descriptive text). The tests may still pass because those fields are not parsed for the count name, but they no longer verify the renamed contract. Update these fixtures/descriptions to `judge_error_count` / `JUDGE_ERROR` where they refer to parser fallback, leaving tied-result `neutral` assertions unchanged.
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 2. **Nit** `code-quality` `skills/review/scripts/test-tally-code-votes.sh:84`, `skills/design/scripts/test-tally-plan-review.sh:158`, `scripts/test-compose-review-findings.sh:65` — Several harness fixtures/descriptions still encode the old parser-fallback label (`neutral_count` diag fields and `NEUTRAL` vote-tally/descriptive text). The tests may still pass because those fields are not parsed for the count name, but they no longer verify the renamed contract. Update these fixtures/descriptions to `judge_error_count` / `JUDGE_ERROR` where they refer to parser fallback, leaving tied-result `neutral` assertions unchanged.
- **Suggested revision**: Address the concern above.

### FINDING_3: **[correctness]** [`scripts/test-compose-review-findings.sh`](scripts/test-compose-review-findings.sh):65 — Fixture markdown still contains `Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=0` while new tally output uses `JUDGE_ERROR=` (same drift as the explicitly updated [`skills/implement/scripts/test-write-rejected-findings.sh`](skills/implement/scripts/test-write-rejected-findings.sh) fixture in the diff). No assertion in that harness appears to depend on the token name, but the fixture is **stale vs current producers**. **Suggested fix:** `NEUTRAL=0` → `JUDGE_ERROR=0` for consistency with `tally-code-votes.sh`.
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** [`scripts/test-compose-review-findings.sh`](scripts/test-compose-review-findings.sh):65 — Fixture markdown still contains `Vote tally: YES=0 NO=2 EXON=0 NEUTRAL=0` while new tally output uses `JUDGE_ERROR=` (same drift as the explicitly updated [`skills/implement/scripts/test-write-rejected-findings.sh`](skills/implement/scripts/test-write-rejected-findings.sh) fixture in the diff). No assertion in that harness appears to depend on the token name, but the fixture is **stale vs current producers**. **Suggested fix:** `NEUTRAL=0` → `JUDGE_ERROR=0` for consistency with `tally-code-votes.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_4: **[correctness]** [`skills/design/scripts/tally-plan-review.md`](skills/design/scripts/tally-plan-review.md):19,35 — Still says “NEUTRAL abstentions” and “no quorum reduction for NEUTRAL votes,” but [`skills/design/scripts/tally-plan-review.sh`](skills/design/scripts/tally-plan-review.sh) (in the diff) uses the `JErr` column and `JUDGE_ERROR=` in vote tallies, matching `vote_for_id`’s `JUDGE_ERROR` fallback. **Suggested fix:** Same wording update as other voting docs (`JUDGE_ERROR` per judge, distinct from finding-level `neutral`).
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** [`skills/design/scripts/tally-plan-review.md`](skills/design/scripts/tally-plan-review.md):19,35 — Still says “NEUTRAL abstentions” and “no quorum reduction for NEUTRAL votes,” but [`skills/design/scripts/tally-plan-review.sh`](skills/design/scripts/tally-plan-review.sh) (in the diff) uses the `JErr` column and `JUDGE_ERROR=` in vote tallies, matching `vote_for_id`’s `JUDGE_ERROR` fallback. **Suggested fix:** Same wording update as other voting docs (`JUDGE_ERROR` per judge, distinct from finding-level `neutral`).
- **Suggested revision**: Address the concern above.

### FINDING_5: **[correctness]** [`skills/review/scripts/tally-code-votes.md`](skills/review/scripts/tally-code-votes.md):28-30,70,78 — The sibling doc was **not** updated in the branch while [`skills/review/scripts/tally-code-votes.sh`](skills/review/scripts/tally-code-votes.sh) now emits `JERR` / `JUDGE_ERROR=` and parse-rate copy uses `JUDGE_ERROR`. The markdown still documents `NEUT`, `Vote tally: … NEUTRAL=…`, says “NEUTRAL or missing per-item votes” in the threshold section, and describes harness coverage as “NEUTRAL abstentions,” which **misstates** per-voter parser fallback vs finding-level `neutral` / `NEUTRAL_COUNT`. **Suggested fix:** Bring lines 28-30, 70, and 78 in line with [`scripts/lib-vote-tally.md`](scripts/lib-vote-tally.md) and the current `printf` strings in `tally-code-votes.sh`.
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** [`skills/review/scripts/tally-code-votes.md`](skills/review/scripts/tally-code-votes.md):28-30,70,78 — The sibling doc was **not** updated in the branch while [`skills/review/scripts/tally-code-votes.sh`](skills/review/scripts/tally-code-votes.sh) now emits `JERR` / `JUDGE_ERROR=` and parse-rate copy uses `JUDGE_ERROR`. The markdown still documents `NEUT`, `Vote tally: … NEUTRAL=…`, says “NEUTRAL or missing per-item votes” in the threshold section, and describes harness coverage as “NEUTRAL abstentions,” which **misstates** per-voter parser fallback vs finding-level `neutral` / `NEUTRAL_COUNT`. **Suggested fix:** Bring lines 28-30, 70, and 78 in line with [`scripts/lib-vote-tally.md`](scripts/lib-vote-tally.md) and the current `printf` strings in `tally-code-votes.sh`.
- **Suggested revision**: Address the concern above.

### FINDING_6: **[correctness]** [`skills/review/scripts/test-tally-code-votes.sh`](skills/review/scripts/test-tally-code-votes.sh):84-157 (and similar `printf` blocks in that file) — Synthetic parse-rate diag fixtures still embed `neutral_count=3`. [`scripts/dispatch-code-voters.sh`](scripts/dispatch-code-voters.sh) (in the diff) now writes `judge_error_count=` into real diags. [`scripts/lib-voter-parse-rate.sh`](scripts/lib-voter-parse-rate.sh):18-32 only matches `voter_file=` / `voter_sha256=`, so tests likely **still pass**, but fixtures are **no longer representative** of production diag shape. **Suggested fix:** Rename the field in those `printf` heredocs to `judge_error_count=` (and refresh any nearby comments / echo text, e.g. around line 279 that still says “2 NEUTRAL” for a case that is really two `JUDGE_ERROR` per-judge slots).
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** [`skills/review/scripts/test-tally-code-votes.sh`](skills/review/scripts/test-tally-code-votes.sh):84-157 (and similar `printf` blocks in that file) — Synthetic parse-rate diag fixtures still embed `neutral_count=3`. [`scripts/dispatch-code-voters.sh`](scripts/dispatch-code-voters.sh) (in the diff) now writes `judge_error_count=` into real diags. [`scripts/lib-voter-parse-rate.sh`](scripts/lib-voter-parse-rate.sh):18-32 only matches `voter_file=` / `voter_sha256=`, so tests likely **still pass**, but fixtures are **no longer representative** of production diag shape. **Suggested fix:** Rename the field in those `printf` heredocs to `judge_error_count=` (and refresh any nearby comments / echo text, e.g. around line 279 that still says “2 NEUTRAL” for a case that is really two `JUDGE_ERROR` per-judge slots).
- **Suggested revision**: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] **[correctness]** Under [`larch-logs/implement/`](larch-logs/implement/) there are many historical artifacts with `| NEUT |` headers and `NEUTRAL=` in vote tally lines; they were not in the provided diff. Updating them is a policy/content choice, not a functional regression in code paths.
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** Under [`larch-logs/implement/`](larch-logs/implement/) there are many historical artifacts with `| NEUT |` headers and `NEUTRAL=` in vote tally lines; they were not in the provided diff. Updating them is a policy/content choice, not a functional regression in code paths.
- **Suggested revision**: Address the concern above.

### FINDING_8: [OUT_OF_SCOPE] **[correctness]** [`scripts/write-tally.sh`](scripts/write-tally.sh):24,114 and [`scripts/compose-tally-record.sh`](scripts/compose-tally-record.sh):18,49 — `NEUTRAL` / `--neutral` refer to **envelope** tied-vote counts for JSON/tally records, which correctly remain per the plan (“do not rename finding-level neutral…”).
- **Reviewer**: dyn-rename-completeness-output.txt
- **Concern**: - **[correctness]** [`scripts/write-tally.sh`](scripts/write-tally.sh):24,114 and [`scripts/compose-tally-record.sh`](scripts/compose-tally-record.sh):18,49 — `NEUTRAL` / `--neutral` refer to **envelope** tied-vote counts for JSON/tally records, which correctly remain per the plan (“do not rename finding-level neutral…”). **What looked solid in the diff:** [`scripts/lib-vote-tally.sh`](scripts/lib-vote-tally.sh) and [`scripts/dispatch-code-voters.sh`](scripts/dispatch-code-voters.sh) `BEGIN { result="JUDGE_ERROR" }` plus `grep -c '^JUDGE_ERROR'` stay aligned; [`skills/review/scripts/tally-code-votes.sh`](skills/review/scripts/tally-code-votes.sh) preserves `classify_result` → `neutral` / `NEUTRAL_COUNT` paths; [`docs/run-logs.md`](docs/run-logs.md) note correctly separates `neutral_count` vs `JUDGE_ERROR` / `JERR`.
- **Suggested revision**: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] code-quality: larch-logs/implement/**
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Historical run logs retain NEUT/NEUTRAL= strings. Pre-existing committed snapshots; not part of this rename diff’s runtime surface. None unless a separate log-normalization change is desired.
- **Suggested revision**: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] code-quality: scripts/test-compose-review-findings.sh:65
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Fixture embeds legacy NEUTRAL=0 vote tally line. Not introduced by this diff; tests do not assert that literal in output. Optional: update fixture to JUDGE_ERROR=0 for consistency with new producer strings.
- **Suggested revision**: Address the concern above.

### FINDING_11: [OUT_OF_SCOPE] code-quality: scripts/test-compose-review-findings.sh:65
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Fixture Vote tally line still uses NEUTRAL=0. Not introduced by this diff; not in written plan. Optional align to JUDGE_ERROR=0 for parity with new producer output.
- **Suggested revision**: Address the concern above.

### FINDING_12: [OUT_OF_SCOPE] correctness: skills/review/scripts/test-tally-code-votes.sh:84-157
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness-built parse-rate diag fixtures still use neutral_count= key while dispatch-code-voters.sh emits judge_error_count=. Tally binding ignores the key name so no functional failure; confusion when comparing harness fixtures to real dispatch diags. Rename neutral_count to judge_error_count in printf fixture lines for consistency.
- **Suggested revision**: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] risk-integration: skills/design/scripts/tally-plan-review.md:19,35
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Quorum/coverage prose still refers to NEUTRAL abstentions/votes while tally-plan-review.sh now labels the per-judge column JErr and uses JUDGE_ERROR counts in vote tally lines. Same operator-facing doc drift as code-review tally doc. Update tally-plan-review.md quorum section to use JUDGE_ERROR parser-fallback language and distinguish finding-level neutral where needed.
- **Suggested revision**: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/tally-code-votes.md:28-78
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Sibling script doc still documents NEUT column and NEUTRAL= tally suffix and NEUTRAL abstention language after tally-code-votes.sh switched to JERR/JUDGE_ERROR= and JUDGE_ERROR parse-rate wording. Operators or tests reading only the .md get a mismatched picture of on-disk tally artifacts vs this branch’s script output. Update tally-code-votes.md to match JERR/JUDGE_ERROR terminology and clarify JUDGE_ERROR vs NEUTRAL_COUNT.
- **Suggested revision**: Address the concern above.

### FINDING_15: code-quality: scripts/dispatch-code-voters.sh:138-203 scripts/lib-vote-tally.sh:12-38
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Duplicated vote_for_id awk remains after rename. Future edits to vote matching can drift between lib and dispatch copy. Optional refactor to reuse vote_for_id from sourced lib when practical.
- **Suggested revision**: Address the concern above.

### FINDING_16: code-quality: scripts/lib-vote-tally.md:276-281
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Threshold bullet names JUDGE_ERROR as if accept_finding accepts that token; API is aggregate yes/no/exo counts only. Integrators may think accept_finding has a JUDGE_ERROR parameter. Clarify wording to tie JUDGE_ERROR to vote_for_id / tally counting, not accept_finding arguments.
- **Suggested revision**: Address the concern above.

### FINDING_17: code-quality: skills/review/scripts/tally-code-votes.sh vs skills/design/scripts/tally-plan-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Column header spelling differs (JERR vs JErr) for the same judge-error count column. Minor confusion comparing plan-review vs code-review tables side by side. Standardize header spelling across both tallies.
- **Suggested revision**: Address the concern above.

### FINDING_18: code-quality: skills/review/scripts/tally-code-votes.sh vs skills/design/scripts/tally-plan-review.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent per-judge error column abbreviations (JERR vs JErr). Operators comparing plan vs code tallies see two labels for the same counter. Standardize header spelling across both scripts (or use full JUDGE_ERROR).
- **Suggested revision**: Address the concern above.

### FINDING_19: code-quality: skills/review/scripts/test-tally-code-votes.sh:279-290
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Test case labels still say 2 NEUTRAL for per-judge missing votes. Misleading when scanning test output for JUDGE_ERROR terminology. Rename echo/assert descriptions to JUDGE_ERROR for consistency with other harnesses.
- **Suggested revision**: Address the concern above.

### FINDING_20: code-quality: skills/review/scripts/test-tally-code-votes.sh:279-291
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Test case prose still says NEUTRAL / neutral quorum for a scenario driven by empty voter outputs (judge_error counts). Vocabulary drifts from renamed semantics; assertions remain numeric. Rename echo/assert descriptions to JUDGE_ERROR / judge_error column wording.
- **Suggested revision**: Address the concern above.

### FINDING_21: code-quality: skills/review/scripts/test-tally-code-votes.sh:84-157
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Parse-rate diag fixtures still use neutral_count= while dispatch-code-voters.sh writes judge_error_count=. No CI breakage (diag matcher ignores that field), but fixture vs production diag shape diverges. Rename fixture field to judge_error_count for parity.
- **Suggested revision**: Address the concern above.

### FINDING_22: risk-integration: scripts/test-compose-review-findings.sh:65
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Fixture Vote tally line still uses NEUTRAL=0 while producers moved to JUDGE_ERROR=. Low risk today; encourages wrong assumptions about canonical vote tally key. Change fixture to JUDGE_ERROR=0 for consistency with tally output.
- **Suggested revision**: Address the concern above.

### FINDING_23: risk-integration: scripts/test-lib-vote-tally.sh:54-56
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] accept_finding case descriptions say JUDGE_ERROR but only yes/no/exo/eligible integers are passed Future edits may wrongly assume accept_finding consumes JUDGE_ERROR or parser-fallback counts Rename descriptions to reflect insufficient YES / abstract non-accepting slots or tie text to vote_for_id-driven scenarios only
- **Suggested revision**: Address the concern above.

### FINDING_24: risk-integration: scripts/test-lib-vote-tally.sh:82-87
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Regression comment says zero FINDING_N: lines while fixture is prose-only (no vote lines at all) Mild mismatch between test name and literal file shape Optional tighten fixture to include non-parseable heading lines if literal alignment matters
- **Suggested revision**: Address the concern above.

### FINDING_25: risk-integration: skills/design/scripts/tally-plan-review.md:19,35
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] tally-plan-review.md still says NEUTRAL abstentions / NEUTRAL votes for quorum behavior. Cross-doc readers see JUDGE_ERROR in shared voting docs but NEUTRAL for the same parser fallback in the plan-review tally doc. Align wording with voting-protocol.md / lib-vote-tally.md (keep scoreboard Neutral/Exon as tied-vote semantics).
- **Suggested revision**: Address the concern above.

### FINDING_26: risk-integration: skills/design/scripts/tally-plan-review.md:19-35
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Invariants/harness text still says NEUTRAL abstentions / NEUTRAL votes for quorum. tally-plan-review.sh now labels JErr/JUDGE_ERROR; doc reinforces the old conflation between parser fallback and tied-vote neutral. Reword to JUDGE_ERROR per-judge parser fallback vs finding-level neutral/NEUTRAL_COUNT as in run-logs.md note.
- **Suggested revision**: Address the concern above.

### FINDING_27: risk-integration: skills/review/scripts/tally-code-votes.md:28-31
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Producer doc still specifies NEUT column and NEUTRAL= vote tally suffix while tally-code-votes.sh emits JERR and JUDGE_ERROR=. Downstream docs/tests or humans matching documented literals misread real rejected-findings and voting-tally artifacts. Update tally-code-votes.md table header suffix line NEUTRAL= to JUDGE_ERROR=; change NEUT to JERR; refresh quorum and harness lines at :70 and :78.
- **Suggested revision**: Address the concern above.

### FINDING_28: risk-integration: skills/review/scripts/tally-code-votes.md:28-31,70
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] tally-code-votes.md still documents NEUT column and NEUTRAL= vote tally lines and NEUTRAL wording for missing votes, but tally-code-votes.sh now emits JERR and JUDGE_ERROR=. A contributor or harness author following this doc asserts legacy tokens against new voting-tally.md or rejected-findings tails and gets false failures or wrong expectations. Update the artifact and threshold sections to JERR / JUDGE_ERROR and clarify distinction from NEUTRAL_COUNT (finding-level neutral).
- **Suggested revision**: Address the concern above.

### FINDING_29: risk-integration: skills/review/scripts/tally-code-votes.md:28-78 skills/design/scripts/tally-plan-review.md:19-35
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Sibling tally markdown still documents NEUT column and NEUTRAL= vote tally lines plus NEUTRAL abstention wording after code/docs rename to JERR/JUDGE_ERROR. Downstream readers treat markdown as contract and grep or parse stale tokens missing real tallies. Update tally-code-votes.md and tally-plan-review.md to match script outputs and distinguish JUDGE_ERROR vs finding-level neutral.
- **Suggested revision**: Address the concern above.

### FINDING_30: risk-integration: skills/review/scripts/tally-code-votes.sh (output contract) / consumer automation
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] Per-finding output renames Vote tally field NEUTRAL= to JUDGE_ERROR= and table column NEUT to JERR. External golden tests or grep-based tooling keyed on NEUTRAL= or NEUT headers fail after upgrade. Document migration for out-of-repo consumers; finish first-party doc updates (tally-code-votes.md).
- **Suggested revision**: Address the concern above.

### FINDING_31: risk-integration: skills/review/scripts/test-tally-code-votes.sh:84-157
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Parse-rate diag harness fixtures still emit neutral_count= while dispatch writes judge_error_count=. Future diag validation or human diffing sees format skew vs production without functional failure today. Rename fixture field to judge_error_count= to mirror dispatch-code-voters.sh.
- **Suggested revision**: Address the concern above.

