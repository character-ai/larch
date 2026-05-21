### FINDING_10: [OUT_OF_SCOPE] security: scripts/compose-review-findings.sh:171-188
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] jq-based JSONL emission with redacted reviewer fields Existing compose path already avoids shell expansion of reviewer prose; schema split to reviewer_slots does not materially change injection class. No change required for this review scope beyond maintaining redact-then-jq discipline.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_2: **correctness** `skills/review/scripts/aggregate-findings.sh:229-277` — OOS classification for both input and merged output uses `is_oos = "[OUT_OF_SCOPE]" in head` / `is_oos_out = "[OUT_OF_SCOPE]" in head` on the entire first line of the block (`### FINDING_n: …`), not the post-colon title. Any in-scope finding whose title mentions the marker as prose (for example a discussion of out-of-scope handling) would be treated as OOS for slot accounting, shrinking `in_scope` and inflating `oos`, so `only_oos` can omit reviewers who truly also have normal in-scope rows. Conversely, a merged heading that keeps reviewers who are OOS-only but decorates the title with `[OUT_OF_SCOPE]` only as a substring after other text could set `is_oos_out` true and skip the guard that is meant to catch dropping the tag from the merged first line, weakening the rejection the scout notes describe. **Suggested fix:** parse the `### FINDING_n:` line, take the substring after the first colon (the same title surface `collect-findings.sh` emits), and treat a row as OOS only when that title strip-prefix-matches `[OUT_OF_SCOPE]` the same way downstream consumers expect (for example `title.strip().startswith("[OUT_OF_SCOPE]")`), then run `only_oos_reviewer_slots` and the non-OOS output checks against that boolean.
- **Reviewer**: dyn-oos-validator-logic-output.txt
- **Concern**: - **correctness** `skills/review/scripts/aggregate-findings.sh:229-277` — OOS classification for both input and merged output uses `is_oos = "[OUT_OF_SCOPE]" in head` / `is_oos_out = "[OUT_OF_SCOPE]" in head` on the entire first line of the block (`### FINDING_n: …`), not the post-colon title. Any in-scope finding whose title mentions the marker as prose (for example a discussion of out-of-scope handling) would be treated as OOS for slot accounting, shrinking `in_scope` and inflating `oos`, so `only_oos` can omit reviewers who truly also have normal in-scope rows. Conversely, a merged heading that keeps reviewers who are OOS-only but decorates the title with `[OUT_OF_SCOPE]` only as a substring after other text could set `is_oos_out` true and skip the guard that is meant to catch dropping the tag from the merged first line, weakening the rejection the scout notes describe. **Suggested fix:** parse the `### FINDING_n:` line, take the substring after the first colon (the same title surface `collect-findings.sh` emits), and treat a row as OOS only when that title strip-prefix-matches `[OUT_OF_SCOPE]` the same way downstream consumers expect (for example `title.strip().startswith("[OUT_OF_SCOPE]")`), then run `only_oos_reviewer_slots` and the non-OOS output checks against that boolean.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_22: risk-integration: scripts/test-lib-vote-tally.sh:89-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] reviewer_for_block unit harness not extended for new Reviewer(s) awk alternations awk typo could ship while only integration comma-merge case passes add **Reviewer(s)** and Reviewer(s): fixtures with expected strings
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_3: **correctness** `skills/review/scripts/test-aggregate-findings.sh:220-246` — The `oos_drop_tag` case proves the “OOS-only reviewer merged into a non-tagged block” rejection path, but there is no counterpart proving the mixed case the scout notes call out: the same slot label appearing on both an `[OUT_OF_SCOPE]`-tagged input finding and an in-scope input finding must not land in `only_oos`, so a stubbed merged in-scope block that lists that slot should still validate and replace `findings.md`. **Suggested fix:** add a stub merge kind plus fixture with two input blocks sharing one reviewer label across in-scope and OOS titles, assert `AGGREGATED=true` / `REASON=ok`, and assert the merged file content matches the stub so future edits to `only_oos_reviewer_slots` cannot regress that set difference without failing CI.
- **Reviewer**: dyn-oos-validator-logic-output.txt
- **Concern**: - **correctness** `skills/review/scripts/test-aggregate-findings.sh:220-246` — The `oos_drop_tag` case proves the “OOS-only reviewer merged into a non-tagged block” rejection path, but there is no counterpart proving the mixed case the scout notes call out: the same slot label appearing on both an `[OUT_OF_SCOPE]`-tagged input finding and an in-scope input finding must not land in `only_oos`, so a stubbed merged in-scope block that lists that slot should still validate and replace `findings.md`. **Suggested fix:** add a stub merge kind plus fixture with two input blocks sharing one reviewer label across in-scope and OOS titles, assert `AGGREGATED=true` / `REASON=ok`, and assert the merged file content matches the stub so future edits to `only_oos_reviewer_slots` cannot regress that set difference without failing CI.
- **Suggested revision**: Address the concern above.


Vote tally: YES=2 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted

### FINDING_4: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-oos-validator-logic-output.txt
- **Concern**: - **correctness** `skills/review/scripts/collect-findings.sh:409-414` — Normal `findings.md` rows always include a parseable `- **Reviewer**:` line after label validation, so the validator’s reliance on `reviewer_line_slots` for OOS bookkeeping is aligned with the primary producer; remaining risk is mostly hand-edited or foreign-generated `findings.md`, which is outside the usual panel path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] Repo-wide search of `scripts/`, `skills/`, and `docs/` shows no remaining shell `jq` or other harness logic that projects `.reviewer` from `review-findings-full.jsonl`; `skills/review-and-fix/scripts/review-and-fix.sh:514-527` derives tallies from `phase`/`outcome` only; `scripts/larch-log-batches.md:51-55`, `scripts/compose-review-findings.md`, `scripts/test-compose-review-findings.sh`, `skills/implement/SKILL.md` (Step 5 batch section), and `.claude/skills/audit-runs/scans.tsv` were updated or do not depend on the removed key.
- **Reviewer**: dyn-schema-consumers-output.txt
- **Concern**: - Repo-wide search of `scripts/`, `skills/`, and `docs/` shows no remaining shell `jq` or other harness logic that projects `.reviewer` from `review-findings-full.jsonl`; `skills/review-and-fix/scripts/review-and-fix.sh:514-527` derives tallies from `phase`/`outcome` only; `scripts/larch-log-batches.md:51-55`, `scripts/compose-review-findings.md`, `scripts/test-compose-review-findings.sh`, `skills/implement/SKILL.md` (Step 5 batch section), and `.claude/skills/audit-runs/scans.tsv` were updated or do not depend on the removed key.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_6: [OUT_OF_SCOPE] `CHANGELOG.md` and archived `larch-logs/**/session-transcript.jsonl` examples still show historical jq snippets and prose tied to older shapes; that is historical narrative, not a runtime coupling in shipped automation.
- **Reviewer**: dyn-schema-consumers-output.txt
- **Concern**: - `CHANGELOG.md` and archived `larch-logs/**/session-transcript.jsonl` examples still show historical jq snippets and prose tied to older shapes; that is historical narrative, not a runtime coupling in shipped automation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=1 JUDGE_ERROR=0 Result=exonerated

### FINDING_7: [OUT_OF_SCOPE] architecture: scripts/lib-vote-tally.md:38-40
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Contract doc omits Reviewer(s) forms supported in lib-vote-tally.sh after this branch. Readers of .md only see a narrower contract than .sh implements. Sync lib-vote-tally.md with the expanded attribution line shapes when doing a doc pass.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_8: [OUT_OF_SCOPE] architecture: skills/review/scripts/tally-code-votes.md:78
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Harness coverage prose omits the new merged ballot comma-split scoreboard test. Doc-only gap; tests cover the behavior. Extend the coverage sentence when editing tally-code-votes.md next.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_9: [OUT_OF_SCOPE] risk-integration: skills/review/scripts/review-core.sh:165-171
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] append_review_execution_issue already swallowed append failures and stderr before this feature landed, so aggregator is not the first silent-execution-issue surface. Any fix should centralize append handling rather than blaming only aggregate-findings.sh. Refactor shared append helper with dispatch-panel-style error capture when touching this area.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

