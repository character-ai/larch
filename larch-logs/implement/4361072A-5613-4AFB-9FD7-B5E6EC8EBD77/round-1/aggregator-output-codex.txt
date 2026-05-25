### FINDING_1: Duplicated vote tally logic can desync TSV and markdown results
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: important
- **Concern**: Duplicated per-block vote-count loops in `tally-plan-review.sh` can drift, causing `findings-classification.tsv` and `voting-tally.md` to report different outcomes after future vote or judge-error changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_2: Duplicated findings-classification TSV header can drift
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: The TSV header literal is duplicated between the tally writer and empty-artifact paths, so future schema changes could update only one path and publish inconsistent headers.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_3: Forensic axis enums are duplicated across parser, renderer, and retry logic
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Forensic axis enum definitions are maintained in multiple scripts, so renaming or changing an axis in one place could leave parser or retry behavior accepting stale tokens until a late harness failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_4: Parser vote and tally vote semantics can diverge
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `vN_vote` uses parser output while `voting_result` uses `vote_for_id`; insufficient parity coverage could let edge-case vote lines produce different forensic columns and panel outcomes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_5: Per-cell parser subprocess calls add avoidable tally overhead
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Severity**: latent
- **Concern**: Calling `parse-judge-vote-and-rating.sh` per voter cell can add unnecessary fork overhead on larger ballots or repeated Gate C runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.

### FINDING_6: Duplicate voter slots corrupt vote totals and forensic columns
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Repeating `--voter` for the same slot can double-count votes for `voting_result` while only the last file populates the corresponding `vN_*` columns, corrupting published forensics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_7: Publish harness lacks absent or empty plan-review success coverage
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Publish tests do not fully lock successful handling of absent or empty `plan-review/` directories, so allowlist regressions could break valid runs without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_8: Voter-sourced TSV cell sanitization is not fully tested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Harness coverage checks `finding_reviewers` sanitization but not all `vN_*` voter-sourced columns, so tabs or newlines in judge output could break TSV alignment while CI passes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_9: Panel-dispatch-failed path lacks header-only TSV coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Only the zero-findings empty-artifact path asserts header-only `findings-classification.tsv`; panel dispatch failure could stop writing the TSV unnoticed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_10: Parse-rate accepts vote-only lines despite retry text requiring axes
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: Retry text requires four forensic axis tokens, but substantive parse-rate still accepts vote-only lines, allowing empty axes and `uncertain=true` without retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_11: Tally doc references the wrong Makefile shard
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `tally-plan-review.md` documents `test-harnesses-1` while implementation uses `test-harnesses-9`, which can mislead contributors running coverage checks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_12: Tally abort paths can leave stale findings-classification TSV
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: After a successful tally, a later malformed-ballot run can exit without rewriting or removing `findings-classification.tsv`, allowing publish to stage stale per-round forensic data.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_13: Axis token parsing is too strict about whitespace
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Axis tokens with spaces around `=` are not tolerated, so otherwise valid judge output like `CORRECTNESS= true` can yield empty axes and `PARSED_UNCERTAIN=true`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] Render-cache publish staging remains broader than plan-review staging
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `render-cache/` staging still uses a broader `find "$rc_root" -type f` pattern without the stricter symlink and path allowlist protections added for `plan-review/`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_15: [OUT_OF_SCOPE] Arbitrary ballot IDs could alter parser regex matching
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `ballot_id` is interpolated into an awk regex; wired callers pass safe IDs today, but future arbitrary callers could introduce regex metacharacter semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Unsanitized trusted TSV fields reduce defense in depth
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `finding_id` and `voting_result` are written without `sanitize_tsv_cell`; current sources are constrained, but sanitizing all fields would align defense in depth.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Classification output path is not constrained to design tmpdir
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: `--findings-classification-out` can point outside `--design-tmpdir` for direct CLI or harness calls, though orchestrated use supplies a controlled path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_18: [OUT_OF_SCOPE] Empty plan-review publish success lacks isolated empty-dir coverage
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Empty `plan-review/` publish behavior is not separately harness-locked, so a regression could break empty-dir success without CI signal.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_19: [OUT_OF_SCOPE] Panel-failed early exit TSV assertion is missing
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: The loop harness does not assert classification header output for the panel-failed early exit path.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Loop harness does not assert voter slot argv passed to tally
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: The loop harness does not explicitly verify `--voter SLOT:PATH` argv reaching tally, so slot metadata regressions may only surface in production multi-round runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_21: [OUT_OF_SCOPE] Classification harness doc overstates sanitization coverage
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: The sibling doc claims broader sanitization coverage than the current tests provide, which can mislead readers until voter-cell sanitization coverage is added.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
