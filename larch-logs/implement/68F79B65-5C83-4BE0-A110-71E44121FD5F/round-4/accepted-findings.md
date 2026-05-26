### FINDING_1: Duplicated vote aggregation between TSV writer and markdown tally loop
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Vote aggregation for `voting_result` is duplicated in `write_findings_classification` and the markdown tally loop in `tally-plan-review.sh`. A future change to quorum, MainAgent, or `JUDGE_ERROR` handling updated in only one path would leave `findings-classification.tsv` `voting_result` inconsistent with `voting-tally.md` while both could still pass separate harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_11: Plan-mandated tally harness cases split across two test scripts
- **Reviewer(s)**: cursor-specialist-testing-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan-mandated tally argv/TSV cases (including error-path and sanitization) live mainly in `test-findings-classification.sh`, not `test-tally-plan-review.sh`. Edits to mutex, deprecation, or 21-field logic could break `test-findings-classification` while `test-tally-plan-review` still passes, giving false confidence that both harnesses guard the contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


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


### FINDING_22: No `--verification-context code` regression case in render-voter harness
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: nit
- **Concern**: `test-render-voter-prompt.sh` has no `--verification-context code` regression case. An unconditional renderer change could break code-review voter prompts without CI catching it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_3: `--voter` column placement uses basename/tool heuristics, not dispatch order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: `--voter` column placement uses basename/tool heuristics rather than argv or panel dispatch order (`vN_tool` comes from SLOT label). Manual or partial-panel invocations with mismatched `SLOT:PATH` pairs can record ratings under the wrong `vN` column while `vN_tool` shows the declared tool, corrupting analytics (e.g. sole slot-2 judge landing in `v1`). Plan wording on dispatch order vs tally canonical-slot authority is also inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


### FINDING_8: MainAgent-only TSV `voting_result` disagrees with plan/docs contract
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Severity**: important
- **Concern**: Plan acceptance requires sole MainAgent TSV rows with `voting_result=rejected`, but tally treats MainAgent votes as `eligible=1` and derives `voting_result` from votes. Analytics or checks expecting `rejected` on every `--voter MainAgent` run will mislabel adjudicated YES/NO outcomes. `docs/run-logs.md` describes vote-derived `voting_result`, conflicting with plan acceptance.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.


