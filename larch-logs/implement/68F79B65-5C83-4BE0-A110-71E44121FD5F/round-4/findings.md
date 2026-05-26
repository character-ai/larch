
Aggregating the 33 reviewer inputs into merged findings. User constraints forbid file writes, so the structured list is the response body (no `CreatePlan` file).
Merged 33 raw slots into 24 findings (22 in-scope, 2 `[OUT_OF_SCOPE]`). Duplicates combined on shared behavioral risk; distinct fixes or code paths kept separate.

### FINDING_1: Duplicated vote aggregation between TSV writer and markdown tally loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Vote aggregation for `voting_result` is duplicated in `write_findings_classification` and the markdown tally loop in `tally-plan-review.sh`. A future change to quorum, MainAgent, or `JUDGE_ERROR` handling updated in only one path would leave `findings-classification.tsv` `voting_result` inconsistent with `voting-tally.md` while both could still pass separate harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_2: Findings-classification lib is header-only; tally internals not shared
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: `lib-findings-classification.sh` only defines the TSV header; slot assignment and TSV write logic remain in the enlarged tally script. Issue #2675 and future forensic work must copy or re-source tally internals instead of a small shared module, increasing merge-conflict surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_3: `--voter` column placement uses basename/tool heuristics, not dispatch order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `--voter` column placement uses basename/tool heuristics rather than argv or panel dispatch order (`vN_tool` comes from SLOT label). Manual or partial-panel invocations with mismatched `SLOT:PATH` pairs can record ratings under the wrong `vN` column while `vN_tool` shows the declared tool, corrupting analytics (e.g. sole slot-2 judge landing in `v1`). Plan wording on dispatch order vs tally canonical-slot authority is also inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_4: Redundant `vote_for_id` calls per voter per finding in TSV write
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: `write_findings_classification` calls `vote_for_id` twice per voter per finding. Large ballots multiply awk subprocess cost on every TSV write with no functional benefit.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_5: Unused `kind` and `security` locals in TSV write path
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: nit
- **Concern**: Unused locals `kind` and `security` in `write_findings_classification` mislead readers into expecting security/OOS handling in the TSV path that exists only in the markdown loop.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Header-only TSV paths inline header emission instead of central helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Header-only `findings-classification.tsv` paths in `plan-review-loop.sh` call `emit_findings_classification_header` inline instead of delegating through tally or a single lib helper. A 22nd schema column could be updated in tally/tests but missed on zero-findings early exits.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_7: Axis parser treats `KEY=value` tokens in free-form rationale
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `parse-judge-vote-and-rating.sh` treats any pre-delimiter `QUALITY=` / `CORRECTNESS=` token as real even in rationale without `--`. Judge output like `QUALITY=good` followed by prose containing `QUALITY=weak` can record `weak` in committed TSV, corrupting forensic analytics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_8: MainAgent-only TSV `voting_result` disagrees with plan/docs contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires sole MainAgent TSV rows with `voting_result=rejected`, but tally treats MainAgent votes as `eligible=1` and derives `voting_result` from votes. Analytics or checks expecting `rejected` on every `--voter MainAgent` run will mislabel adjudicated YES/NO outcomes. `docs/run-logs.md` describes vote-derived `voting_result`, conflicting with plan acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: Parse-rate does not require four forensic axis tokens
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: Parse-rate validation does not require `CORRECTNESS` / `SEVERITY` / `QUALITY` / `UNCERTAIN`. Judges can emit vote-only lines; TSV gets empty forensic axes despite a successful run.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: `vN_vote` from `vote_for_id` not cross-checked against parser output
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: TSV `vN_vote` comes from `vote_for_id`, not `PARSED_VOTE`. Future line-shape changes could let vote and rating parsers disagree on the same row without detection.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_11: Plan-mandated tally harness cases split across two test scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-mandated tally argv/TSV cases (including error-path and sanitization) live mainly in `test-findings-classification.sh`, not `test-tally-plan-review.sh`. Edits to mutex, deprecation, or 21-field logic could break `test-findings-classification` while `test-tally-plan-review` still passes, giving false confidence that both harnesses guard the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Sole MainAgent TSV path omits forensic rating axes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: MainAgent sole-voter adjudication sets `voting_result` from votes but does not parse forensic rating axes into TSV. Zero-judge MainAgent rerun files with `CORRECTNESS`/`SEVERITY` tokens produce empty `vN` rating columns in committed larch-logs, defeating Lesson 2 analytics on that path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: `test-design-log-publish.sh` omits `plan-review` as regular file
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Harness omits the case where `DESIGN_TMPDIR/plan-review` exists but is not a directory. A regular file at that path could reach production publish and fail at runtime without CI catching the regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: No assertion that panel-failed path writes header-only classification TSV
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `test-plan-review-loop.sh` does not assert that panel-failed `write_empty_review_artifacts` writes header-only `findings-classification.tsv`. Panel dispatch failure could regress to a missing TSV while zero-findings paths keep working.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_15: Parser exit matrix for missing args/unreadable file untested
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Parser exit matrix case (a) for missing args or unreadable `voter_file` is untested. Broken usage handling or quiet-init interaction could ship until later code-review tally depends on the same parser.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_16: Plan case 5 naming conflated with MainAgent adjudication harness
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Plan case 5 (sole MainAgent, `voting_result=rejected`) is conflated with main-agent adjudication (`accepted`) in `test-findings-classification.sh`. Readers tracing plan case numbers to harness names may think zero-voter `rejected` semantics are untested when they only live in `test-tally` zero-voter block.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_17: Retry prefix constants lack grep harness coverage for 4-axis shape
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Retry prefix constants were updated for 4-axis shape without grep harness coverage. Drift between renderer and retry text might not fail CI until runtime voter retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_18: `--voter` paths not confined under `--design-tmpdir`
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--voter SLOT:PATH` accepts any readable path without requiring it under `--design-tmpdir`. Mis-invoked tally or tampered `VOTER_N_PATH` can aim vote parsing at arbitrary host files; parsed votes/ratings can enter `findings-classification.tsv` and be published after redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_19: Tally failure replaces classification TSV with header-only
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: On tally `rc!=0`, `plan-review-loop.sh` replaces `findings-classification.tsv` with header-only. Publish can still stage an empty forensic file; analytics cannot distinguish tally-error from zero-findings.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: `parse_rating_for` swallows parser hard failures
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `parse_rating_for` uses `|| true` on parser failure. A parser crash yields empty `vN_uncertain` cells instead of the contract’s `uncertain=true` default.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_21: Whitespace tokenization misses hyphen-glued axis forms
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Whitespace-only axis tokenization misses hyphen-glued forms (e.g. `YES-CORRECTNESS=true`). Vote may record as YES while axes stay empty and `uncertain=true`, reducing forensic fidelity without parse-rate retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_22: No `--verification-context code` regression case in render-voter harness
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-render-voter-prompt.sh` has no `--verification-context code` regression case. An unconditional renderer change could break code-review voter prompts without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_23: [OUT_OF_SCOPE] Optional tally invocation for zero-findings header-only path
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Zero-findings header is written via inline helper rather than tally invocation. Acceptable per plan fallback with no functional gap; optional improvement is invoking tally for a single source of truth on header-only paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_24: [OUT_OF_SCOPE] Quiet-mode dual-path not fully split-tested
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: Quiet-mode dual-path behavior in `test-findings-classification.sh` is not fully split-tested per plan failure mode 4. Low risk given symmetric `emit_kv` wrapper.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
