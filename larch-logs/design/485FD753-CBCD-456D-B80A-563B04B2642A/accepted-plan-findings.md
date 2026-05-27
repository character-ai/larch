### FINDING_1: Missing zero_findings test flip at #2536
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic, Cursor-Edge, Codex-Edge, Cursor-Innovation, Codex-Pragmatic, Cursor-Requirements, Codex-Requirements, Cursor-dyn-test-flip-inventory, Codex-dyn-test-flip-inventory
- **Severity**: important
- **Concern**: The plan omits an existing `zero_findings` harness block at `skills/review/scripts/test-aggregate-findings.sh:578-593` that uses the same attested zero-block path as the later planned flips. After the validator starts accepting attested empty merges, this test will no longer produce `AGGREGATED=false` / `REASON=validation-exhausted`, so CI will fail unless the block is updated or deduplicated.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch, Cursor-Pragmatic: Flip this block to `REASON=ok` / `AGGREGATED=true` / `MERGED_COUNT=0` and empty stripped ballot (or dedupe with the #2939 test and delete redundant assertions)
  - From Cursor-Edge: Add 578-593 to the explicit flip list (ok, AGGREGATED=true, cleared/stripped FINDINGS_FILE) or delete/merge it into the #2939 case so all three zero_findings consumers are updated together
  - From Codex-Edge: Update or merge this #2536 case into the #2939 success coverage, asserting AGGREGATED=true, REASON=ok, MERGED_COUNT=0, and an empty persisted ballot.
  - From Cursor-Innovation: Flip or remove 578-593 in the same PR; grep validation-exhausted and reconcile every zero_findings attestation hit
  - From Codex-Pragmatic: Add this test to the planned assertion flips or remove/merge the duplicate coverage, and assert the new ok/MERGED_COUNT=0/empty-persisted-ballot contract there as well
  - From Cursor-Requirements: Add ~578-593 to the flip inventory: expect REASON=ok, AGGREGATED=true, MERGED_COUNT=0, empty/stripped FINDINGS_FILE; drop cmp unchanged and validation-exhausted assertions (or dedupe with the #2939 case)
  - From Codex-Requirements: Update the plan's test section to also revise the #2536 zero output FINDING blocks test at lines 578-593 to the new valid duplicate-only semantics, or explicitly replace/merge it with the new #2939 round-trip test so every zero_findings + nonempty-input assertion expects AGGREGATED=true, REASON=ok, MERGED_COUNT=0, and a stripped empty findings file.
  - From Cursor-dyn-test-flip-inventory: Add skills/review/scripts/test-aggregate-findings.sh:578-593 to the flip inventory (or consolidate/remove as duplicate of #2782/#2939): assert REASON=ok AGGREGATED=true MERGED_COUNT=0 empty stripped FINDINGS_FILE; drop unchanged-ballot cmp
  - From Codex-dyn-test-flip-inventory: Add the lines 578-593 test block to the plan's required assertion updates: change the comment, AGGREGATED=false assertion, REASON=validation-exhausted assertion, and unchanged-file assertion to the corrected ok path with MERGED_COUNT=0 and suitable persisted-file checks.


### FINDING_2: Zero-block success can persist narrative prose
- **Reviewer(s)**: Codex-Arch, Codex-Edge, Codex-Innovation, Codex-Pragmatic, Codex-dyn-test-flip-inventory
- **Severity**: important
- **Concern**: The planned attested-empty success path is broader than the persisted ballot contract. Existing `zero_findings` fixtures include narrative plus the attestation token; the strip step removes only attestation lines, leaving narrative in `findings.md` while reporting `REASON=ok` and `MERGED_COUNT=0`. This contradicts whitespace-only ballot expectations and can send non-ballot prose downstream.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Arch: Narrow the success condition to exact attestation plus whitespace, or change the successful zero-block strip path to replace merged_tmp with a single newline regardless of other non-finding prose; then keep the whitespace-only FINDINGS_FILE assertion in the regression test
  - From Codex-Edge: In the zero-block success path, overwrite merged_tmp with a newline after stripping, or make the validator require token-stripped output to be whitespace-only before accepting; pin this with the existing narrative-plus-attestation fixture.
  - From Codex-Innovation: Either change the strip path for accepted zero-block attestation to write a newline regardless of narrative, or change the agent contract and tests to token-only and reject narrative before success
  - From Codex-Pragmatic: Revise the plan to change the success strip path for zero-block accepted candidates so persisted findings.md is forced to whitespace-only after validation, or tighten validation to accept only whitespace plus the attestation token
  - From Codex-dyn-test-flip-inventory: For current narrative-plus-attestation fixtures, assert REASON=ok, AGGREGATED=true, MERGED_COUNT=0, no surviving attestation token, and zero structured FINDING blocks. Reserve whitespace-only assertions for the new canonical fixture that emits exactly the attestation line, or explicitly change the stub used by that test.


### FINDING_3: Malformed pseudo-headings can be accepted as empty merge
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: The planned validator success predicate can accept malformed output that contains an attestation and no parsed finding blocks. Because nonconforming finding markers suppress the preamble rejection path, a pseudo-heading plus attestation could overwrite the ballot as `MERGED_COUNT=0`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Make the success condition structural: accept only whitespace plus the exact attestation, or reject any nonconforming finding markers before return 0; add a regression for pseudo-heading plus attestation


### FINDING_4: Harness docs will be stale for padded attestation
- **Reviewer(s)**: Codex-Edge
- **Severity**: nit
- **Concern**: The sibling harness documentation still describes `zero_findings_padded_attest_rejected` as rejection coverage, but the plan intends to accept padded full-line attestations. This can leave future maintainers with stale test intent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Edge: Update the sibling docs and rename or split the padded-attestation stub/test so accepted padded lines and impure suffix rejection remain distinct.


### FINDING_5: SECURITY.md still documents old empty-merge behavior
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: important
- **Concern**: `SECURITY.md` still says attestation-only empty merges are `validation-exhausted`, which will conflict with the new accepted behavior and the repo rule to update security docs for security-relevant behavior changes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Rewrite SECURITY.md narrow-trigger / fail-closed prose for attestation-only success


### FINDING_6: aggregate-findings.md contract update is incomplete
- **Reviewer(s)**: Cursor-Pragmatic, Codex-Pragmatic
- **Severity**: important
- **Concern**: The planned docs update is too narrow. `skills/review/scripts/aggregate-findings.md` also names empty attested merges as a `validation-exhausted` narrow trigger near the top of the contract, so updating only one bullet would leave the contract internally inconsistent.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Update line 27 (and related terminal REASON bullets) in same commit as line 32
  - From Codex-Pragmatic: Update both the narrow-trigger summary and the empty-merge attestation bullet so only preamble_finding_substring remains a validation-exhausted narrow trigger for zero-block attested output


### FINDING_7: Plan misclassifies padded attestation handling
- **Reviewer(s)**: Cursor-Pragmatic, Cursor-dyn-strip-before-flag-eval, Codex-dyn-strip-before-flag-eval, Codex-dyn-test-flip-inventory
- **Severity**: important
- **Concern**: The plan's edge-case text says whitespace-padded attestations are stripped or treated as no-attestation/impure, but current code trims before checking impurity. A line containing only leading/trailing whitespace around `LARCH_AGGREGATOR_EMPTY_MERGE_ATTESTED` remains an attestation and should follow the new `ok` path; suffix or adjacent junk remains rejection behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Correct plan: padded exact token after strip is ok; suffix drift stays validation-failed
  - From Cursor-dyn-strip-before-flag-eval: Edge Cases claim whitespace-padded attestation loses has_attest_line after drop_impure; Files section mandates flipping padded-attest (~726) to REASON=ok. Fixture is only leading/trailing spaces around the token; line_has_impure_empty_merge_attestation uses line.strip() so padding is not impure, drop does not remove the line, and has_attest_line stays True — same narrow-trigger path as exact attestation, not no-attestation (550-558). Implementer following Edge Cases (b) may skip the padded flip or expect validation-failed/validation-exhausted; CI fails if flip is omitted, or wrong REASON if assertions follow (b). Files-section flip to REASON=ok with AGGREGATED=true, MERGED_COUNT=0, and empty/stripped FINDINGS_FILE is correct. Align Edge Cases with code: whitespace-only padding → ok after return-0; reserve (b) for suffix/junk impure lines (zero_findings_impure_attest → validation-failed).
  - From Codex-dyn-strip-before-flag-eval: Revise the plan to state that whitespace-only padded attestation is accepted by the existing trimmed check and should be flipped to REASON=ok; reserve the no-attestation rejection discussion for suffix/adjacent-junk impure attestation lines such as zero_findings_impure_attest.
  - From Codex-dyn-test-flip-inventory: Revise the plan narrative to state that the padded-attest test is an attested zero-block case and should flip to REASON=ok. Remove the no-attestation possibility for pure leading/trailing whitespace padding; keep no-attestation only for absent token or suffix/format drift cases.


### FINDING_8: CHANGELOG is listed inconsistently
- **Reviewer(s)**: Cursor-Pragmatic
- **Severity**: nit
- **Concern**: The plan mentions `CHANGELOG.md` in the diff estimate but omits it from the explicit files-to-modify list, increasing the chance the changelog entry is missed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Pragmatic: Add CHANGELOG.md to explicit modify list### OOS_1:
- **Description**: [OUT_OF_SCOPE] Review core does not short-circuit after aggregation collapses to zero findings. Scenario: A legitimate duplicate-only merge still launches voters and tallies an empty ballot; if voters fail or parse badly, a no-findings round can surface degraded voting noise
- **Reviewer**: Codex-Innovation
- **Severity**: latent
- **Focus area**: architecture
- **Location**: skills/review/scripts/review-core.sh:598-653
- **Phase**: design


