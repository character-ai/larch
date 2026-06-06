### FINDING_1: [OUT_OF_SCOPE] Security routing predicates diverge across OOS producers, gates, and skipped-routing paths
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-pipeline-output.txt, dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: Multiple code paths classify security-routed OOS with different predicates. In particular, tally/lib-vote-tally recognizes newer `- **focus-area**: security` forms while review-and-fix skipped routing uses a narrower local classifier, so skipped security OOS can be normalized into public accepted-OOS sinks. Other producer/gate/Python/AWK paths also diverge, making public-vs-held routing inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.
  - From dyn-shell-portability-output.txt: Address the concern above.

### FINDING_2: oos-serialize duplicates canonical OOS header normalization instead of using the shared helper
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: `oos-serialize.sh` performs its own inline header rewrite instead of delegating to `normalize-oos-block-header.sh`, despite docs describing the helper as the shared normalization authority. That creates another normalization surface likely to drift.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.

### FINDING_3: [OUT_OF_SCOPE] OOS_WRITE_SEQ initialization counts broader headers than the gate-visible non-security count
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-reader-parity-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: latent
- **Concern**: Producer sequence initialization uses bespoke header-counting AWK that can count bare `FINDING_` headers the disposition gate intentionally ignores. This can inflate OOS sequence numbers or desynchronize numbering from gate-visible non-security blocks.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-reader-parity-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.

### FINDING_4: emit-tally contract docs do not match preserve/rebuild/fail runtime behavior
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: important
- **Concern**: Docs say `OOS_ACCEPTED_COUNT>0` preserves `oos-accepted-review.md`, but implementation also checks sink count and may rebuild from `oos.md` or exit 1. Maintainers reading the contract could reintroduce overwrite/truncation or misunderstand desync handling.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.

### FINDING_5: oos-serialize contract and harness do not pin Result=accepted filtering or canonical OOS header output
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-testing-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: latent
- **Concern**: Serializer behavior changed to filter `Result=accepted` and rewrite legacy headers to `### OOS_<seq>:`, but tests/docs still under-cover or misdescribe those behaviors, including rejected-block exclusion and scope-drift non-recovery.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.

### FINDING_6: [OUT_OF_SCOPE] OOS_ACCEPTED_COUNT includes security-held OOS while public sink counts only non-security blocks
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-oos-pipeline-output.txt
- **Severity**: latent
- **Concern**: Mixed security-held and public accepted OOS rounds can produce permanent count-vs-sink mismatches. Warning-only behavior can mask partial-write regressions because the expected public count is not separated from total accepted OOS.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.

### FINDING_7: [OUT_OF_SCOPE] Parent accepted-OOS mirror semantics can split from accumulated OOS
- **Reviewer(s)**: cursor-specialist-structure-output.txt, dyn-oos-pipeline-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: latent
- **Concern**: Existing mirror/truncation behavior around `oos-accepted-review.md` and `accumulated-oos.md` can leave compatibility mirrors empty or redundantly written across rounds, creating split-brain between durable accumulated state and gate input.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-structure-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.

### FINDING_8: Header-level bare “security” matching falsely withholds non-security accepted OOS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-oos-pipeline-output.txt, dyn-shell-portability-output.txt
- **Severity**: important
- **Concern**: New header heuristics treat ordinary titles containing “security” as security-routed, causing legitimate non-security accepted OOS to be withheld from `oos-accepted-review.md` and possibly never filed. The AWK implementation also raises portability inconsistency on macOS/BSD.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.
  - From dyn-shell-portability-output.txt: Address the concern above.

### FINDING_9: [OUT_OF_SCOPE] Tally and serializer disagree on `[OOS]` tag recognition
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: latent
- **Concern**: `oos-serialize` accepts `[OOS]`, while tally OOS detection requires `[OUT_OF_SCOPE]`. `[OOS]`-only findings may not enter the OOS pipeline on tally-first paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.

### FINDING_10: [OUT_OF_SCOPE] emit-tally rebuild/desync path can silently lose accepted OOS
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-pipeline-output.txt, dyn-artifact-contracts-output.txt
- **Severity**: latent
- **Concern**: When accepted-count state and the accepted sink diverge, rebuild from `oos.md` relies on serializer logic that can drop scope-drift bare findings, and serializer failures may be swallowed. Coverage does not fully pin fail-closed behavior or the primary scope-drift preserve chain.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.
  - From dyn-artifact-contracts-output.txt: Address the concern above.

### FINDING_11: End-to-end accepted-OOS filing path lacks parse-input batch coverage
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Tests stop at gate/counter behavior and do not verify that normalized legacy-derived OOS blocks parse through `/issue` batch filing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_12: Reader gate lacks a bare FINDING_ pass-through regression
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: No harness documents that bare `FINDING_` blocks without disposition should be ignored by the reader/gate, so future reader changes could miscount mixed files.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_13: [OUT_OF_SCOPE] review-core stubs do not exercise production tally→emit integration
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: The production tally→emit chain is not covered through review-core stubs, so integration regressions need to remain pinned in dedicated tally and emit harnesses.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

### FINDING_14: [OUT_OF_SCOPE] No shared AWK/Python OOS counter parity fixture
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-reader-parity-output.txt
- **Severity**: latent
- **Concern**: Bash/AWK and Python OOS counting have parallel tests but no shared golden fixture that runs both counters over the same markdown cases, leaving future one-sided regex drift uncaught.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.
  - From dyn-reader-parity-output.txt: Address the concern above.

### FINDING_15: Backtick-wrapped security tokens can fail open into public OOS filing
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: `is_security_block` strips backticks before matching and can miss backtick-wrapped security focus-area/header tokens, allowing security-routed accepted OOS prose to be normalized, preserved, and filed publicly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

### FINDING_16: [OUT_OF_SCOPE] Security classifier errors are suppressed and can fail open
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-pipeline-output.txt
- **Severity**: latent
- **Concern**: Tally suppresses classifier stderr/errors, so helper failures may route security OOS into the public sink without visible operator signal, unlike safer fail-closed behavior elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-oos-pipeline-output.txt: Address the concern above.

### FINDING_17: [OUT_OF_SCOPE] Degraded retry may double-append round OOS
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Pre-existing degraded retry behavior may append the same round OOS twice to `accumulated-oos.md`, inflating disposition gate counts across retries.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.

### FINDING_18: Python legacy-header regex accepts trailing tags beyond the stated plan form
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Severity**: latent
- **Concern**: Python legacy-header matching accepts trailing `[OUT_OF_SCOPE]` tags via `.*`, while the plan’s regex was narrower. The behavior may be intentional parity with AWK, but docs/plan need alignment or the regex should be tightened.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-plan-fidelity-output.txt: Address the concern above.

### FINDING_19: tally-code-votes uses command substitution for multi-line normalized OOS blocks
- **Reviewer(s)**: dyn-shell-portability-output.txt
- **Severity**: nit
- **Concern**: Capturing normalized accepted OOS via shell command substitution loads whole blocks into shell memory and strips trailing newlines, unlike the streaming append pattern used elsewhere.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-portability-output.txt: Address the concern above.

### FINDING_20: [OUT_OF_SCOPE] Rejected-marker counting still recognizes only OOS_N identifiers
- **Reviewer(s)**: dyn-reader-parity-output.txt
- **Severity**: latent
- **Concern**: Rejected-marker disposition counting remains keyed to `OOS_<n>` and does not count legacy `FINDING_N` identifiers in rejected sections, even though accepted legacy headers are now counted.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-reader-parity-output.txt: Address the concern above.
