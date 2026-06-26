# Review Round 1

- Mode: `diff`
- 1 accepted, 6 rejected (3 neutral)

## Accepted Findings

### FINDING_3: Pre-vote OOS gate rewrites ballot before durable audit/env writes succeed
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-dyn-round-artifacts-output.txt
- **Severity**: important
- **Concern**: `_apply_pre_vote_oos_gate` rewrites `findings_file` before `oos-dropped-before-vote.md` and `pre-vote-oos-gate.env` writes are guaranteed. On audit/env I/O failure after the ballot rewrite, OOS blocks are stripped from the ballot but durable audit evidence may be missing; stdout can still emit `PRE_VOTE_OOS_DROPPED_COUNT>0` from in-memory gate state, leaving operators and `/issue` follow-up with counts but no matching audit bytes.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-dyn-round-artifacts-output.txt: Write dropped audit and `pre-vote-oos-gate.env` first (or use a temp-and-rename sequence for all three artifacts), and on any late I/O failure roll back the ballot from a pre-gate snapshot or re-raise only after restoring the original ballot so partial rewrites cannot survive.


