### FINDING_3: **code-quality** `scripts/git-force-push.sh:24-27` — The script header’s “Exit codes” comment still says exit 1 is only `PUSHED=false` with `STATUS=diverged_retry_failed`, with no mention of the new dirty-tree exit 1 or partial stdout (`BRANCH=` only). That contradicts the updated sibling contract in `scripts/git-force-push.md` from the same diff and violates the repo’s “keep script headers aligned with behavior” expectation. **Suggested fix:** Update the header block so exit 1 documents both dirty-tree (no `PUSHED`/`STATUS`) and `diverged_retry_failed`, matching `scripts/git-force-push.md`.
- **Reviewer**: dyn-caller-contracts-output.txt
- **Concern**: - **code-quality** `scripts/git-force-push.sh:24-27` — The script header’s “Exit codes” comment still says exit 1 is only `PUSHED=false` with `STATUS=diverged_retry_failed`, with no mention of the new dirty-tree exit 1 or partial stdout (`BRANCH=` only). That contradicts the updated sibling contract in `scripts/git-force-push.md` from the same diff and violates the repo’s “keep script headers aligned with behavior” expectation. **Suggested fix:** Update the header block so exit 1 documents both dirty-tree (no `PUSHED`/`STATUS`) and `diverged_retry_failed`, matching `scripts/git-force-push.md`.
- **Suggested revision**: Address the concern above.



