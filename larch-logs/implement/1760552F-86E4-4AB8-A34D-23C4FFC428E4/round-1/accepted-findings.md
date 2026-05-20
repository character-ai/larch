### FINDING_17: code-quality: skills/review/scripts/tally-code-votes.sh vs skills/design/scripts/tally-plan-review.sh
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Column header spelling differs (JERR vs JErr) for the same judge-error count column. Minor confusion comparing plan-review vs code-review tables side by side. Standardize header spelling across both tallies.
- **Suggested revision**: Address the concern above.


### FINDING_18: code-quality: skills/review/scripts/tally-code-votes.sh vs skills/design/scripts/tally-plan-review.sh
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Inconsistent per-judge error column abbreviations (JERR vs JErr). Operators comparing plan vs code tallies see two labels for the same counter. Standardize header spelling across both scripts (or use full JUDGE_ERROR).
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


