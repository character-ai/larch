### OOS_3: [OUT_OF_SCOPE] Multibyte split test missing lossless reassembly check
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: `test_split_to_github_limit_multibyte_over_byte_limit` asserts chunk count and per-chunk byte caps but not lossless reassembly. A UTF-8 boundary bug could drop codepoints while those assertions still pass. The ASCII oversize split test already strips part headers/footers and asserts full body equality.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Mirror `test_split_to_github_limit_over_limit_splits_without_loss` with strip-and-equals for multibyte input.
  - From cursor-specialist-edge-cases-output.txt: Add the same strip-header/footer reassembly assertion used in `test_split_to_github_limit_over_limit_splits_without_loss`.


### OOS_4: [OUT_OF_SCOPE] Multi-part continuation issues lack linkage to part 1
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Continuation parts are filed as separate issues with prose markers only. Part 2+ are not linked to part 1 via `blocked-by`, and sentinel recovery does not carry `source_stable_ids` for continuation parts. Part 2+ can be orphaned from part 1 in sentinel/idempotency paths; retries match only via the part 1 stable ID. Operators must search by title suffix `(part N/M)`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: File `add-blocked-by` from each continuation part to part 1, and record all part URLs under the primary stable ID in the sentinel.
  - From cursor-specialist-edge-cases-output.txt: Add part 1's issue URL to `_BODY_PART_HEADER` or file `blocked-by` from part 2+ to part 1.


### OOS_5: [OUT_OF_SCOPE] No test for mid multi-part create failure cleanup
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/test_oos_filer.py` has no test that `fail_create_after` mid multi-part sequence triggers cleanup of earlier parts. A similar pattern exists for multi-item failure at line 294.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add `test_oversized_body_partial_part_failure_cleans_up` using `fail_create_after` with an oversized body.


