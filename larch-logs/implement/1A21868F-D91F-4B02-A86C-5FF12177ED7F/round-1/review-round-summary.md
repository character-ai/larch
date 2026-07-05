# Review Round 1

- Mode: `diff`
- 1 accepted, 1 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Rescue changes must re-emit and re-approve the combination scheme
- **Reviewer(s)**: cursor-specialist-correctness, codex-specialist-correctness, cursor-specialist-edge-cases, cursor-specialist-testing, dyn-dyn-oos-prompt-contract
- **Severity**: important
- **Concern**: Confirmed rescues can change the kept set or grouping, but the workflow can still reuse a stale combination proposal and reach `oos-5` without re-presenting and re-approving the updated scheme.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness: After confirmed rescues, if dedup/grouping changes membership or partitions, re-present the scheme, require re-approval, and forbid oos-5 until bodies match the final kept set.
  - From codex-specialist-correctness: Restore an explicit restart gate after any confirmed rescue. Rerun deduplication and grouping, re-present the proposal, and require fresh approval before applying groups or merit rejections.
  - From cursor-specialist-edge-cases: Restore prose requiring re-emit of the combination proposal and explicit re-approval before oos-5 when rescue changes kept items or grouping
  - From cursor-specialist-testing: Restore re-emit and explicit re-approval before oos-5 when kept-item set or grouping changes after confirmed rescues
  - From dyn-dyn-oos-prompt-contract: Restore explicit post-rescue regrouping prose after line 241, e.g. rerun oos-3 dedup and rebuild groups from the final kept set; if membership or grouping changed, re-present the combination scheme and require explicit approval again before any oos-5 apply or stale-only closes tied to that scheme.
  - From dyn-dyn-oos-prompt-contract: Pin ordering in prose: after confirmed rescues, rerun dedup and rebuild groups first; if the scheme changes, re-emit and re-approve; only then run merit-batch confirmation for the keys still on the staged rejection list; proceed to oos-5 only after both regroup approval (when needed) and merit-batch resolution.


