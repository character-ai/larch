### FINDING_13: `SECURITY.md` not updated for new GitHub write surfaces
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: `AGENTS.md` calls for `SECURITY.md` updates when security-relevant behavior changes; new `gh` write helpers may lack a consolidated statement of trust assumptions (repo validation, redaction, tokens, output paths).
- **Suggested revision**: Add/adjust a `SECURITY.md` subsection describing assumptions and non-goals for these helpers.


### FINDING_3: `plan-block-write.sh` temp lifecycle / EXIT trap ordering
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: The EXIT cleanup trap may be registered only after temp allocation/composition steps; failures or interrupts in the earlier window can leak `mktemp` artifacts (especially under flaky automation).
- **Suggested revision**: Register EXIT cleanup immediately after temp dirs/files are created (or consolidate to one guarded temp directory with a single lifecycle owner).


### FINDING_6: Marker id=0 parsing inconsistency between `clarify-state.sh` and `clarify-comment-post.sh`
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: `clarify-state` may accept/propagate `id=0` via regex while posting tooling rejects `id=0`, yielding inconsistent automation state for hand-crafted markers.
- **Suggested revision**: Align rules (reject/ignore `id=0`, or treat as ambiguous) and add a regression test.


### FINDING_8: `test-clarify-comment.sh` success-path assertions are too shallow vs contract
- **Reviewer(s)**: cursor-specialist-testing-output.txt, dyn-harness-coverage-output.txt
- **Concern**: Harness checks can pass on marker/first-line behavior while failing to prove the full success envelope (e.g., `POSTED`, `COMMENT_ID`, `COMMENT_URL`) or the full composed post body after the marker line—so regressions in `gh` output parsing, composition, or emitted KV keys may slip through.
- **Suggested revision**: Assert the full documented success outputs for both request/response paths, and compare captured post bodies beyond the first line.


