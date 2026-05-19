# test-lib-vote-tally.sh

Regression harness for `scripts/lib-vote-tally.sh`. Sources the library and asserts each function in isolation.

## Coverage

- `accept_finding` threshold boundaries: 3-voter 2-YES, 3-voter 1-YES, 2-voter unanimous, 2-voter 1-YES+1-EXO, 1-voter, 0-voter.
- `vote_for_id`: YES/NO/EXONERATE matching, missing finding → JUDGE_ERROR, anchored-prefix substring guard (FINDING_1 vs FINDING_10), zero-parseable-lines voter → JUDGE_ERROR.
- `reviewer_for_block`: canonical bold singular/plural attribution, unbolded line-start fallback, prose/body `Reviewer` false-positive guards, missing attribution → `unknown`.
- `is_security_block`: unfenced detection, backtick-fenced rejection, triple-backtick-fenced rejection, no-space variant.
- `split_ballot_to_blocks`: per-ID block file creation, voter-instruction prose dropped.
- `classify_result`: accepted, neutral, exonerated, rejected.

## Invocation

```bash
scripts/test-lib-vote-tally.sh
```

Exit 0 → pass, exit 1 → at least one assertion failed (banner `FAIL: test-lib-vote-tally.sh`).

## Edit-in-sync

When the library API changes (new function, new branch in `accept_finding`/`classify_result`, new heading shape in `split_ballot_to_blocks`), add a matching assertion.
