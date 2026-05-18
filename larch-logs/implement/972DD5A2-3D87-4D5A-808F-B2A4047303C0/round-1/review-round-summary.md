# Review Round 1

- Mode: `diff`
- Accepted findings: 7
- Rejected findings: 6
- Exonerated findings: 0
- Neutral findings: 1

## Accepted Findings

### FINDING_1: **Important** `risk-integration` `scripts/test-harness-timer.sh:1`  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `scripts/test-harness-timer.sh:1`      The new Makefile-only harness is not added to `agent-lint.toml`’s dead-script exclusions, so `agent-lint` fails with `G004/dead-script` for `scripts/test-harness-timer.sh`. Concrete failing scenario: the branch adds `Makefile:449-450`, then CI’s `agent-lint` job runs and rejects the PR even though `make test-harness-timer` passes. Add `scripts/test-harness-timer.sh` to the existing Makefile-only harness exclusion block near `scripts/test-harness-shards-coverage.sh` / `scripts/harness-timer.sh`; include `scripts/test-harness-timer.md` too if you want to mirror the adjacent sibling-doc pattern.
- **Suggested revision**: Address the concern above.


### FINDING_10: correctness: scripts/test-harness-timer.sh:27-33
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [latent] Regex ^[12]\.[0-9]{2}s$ rejects durations >= 3.00s. Overloaded CI can report >=3.00s after sleep 2, causing a spurious harness failure. Widen acceptable range or assert min/max with slack.
- **Suggested revision**: Address the concern above.


### FINDING_11: correctness: scripts/test-harness-timer.sh:27-33
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] `sleep 2` test only accepts 1.xx–2.xx seconds. Heavily loaded CI can report 3.00s+ while timing logic is still correct. Widen the regex upper bound or assert min plus generous max.
- **Suggested revision**: Address the concern above.


### FINDING_14: risk-integration: scripts/test-harness-timer.sh:18-25
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] sleep 0.5 upper bound 0.69s is tight vs stated ±100ms slop Reported 0.70s fails the test on rare scheduler delay Allow 0.7xs or use numeric min/max comparison
- **Suggested revision**: Address the concern above.


### FINDING_16: risk-integration: scripts/test-harness-timer.sh:27-33
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] sleep 2 assertion only allows 1.xx–2.99s Heavily loaded CI could yield 3.00s+ wall time; harness fails despite valid timer Widen regex or assert min/max duration with slack
- **Suggested revision**: Address the concern above.


### FINDING_7: correctness: scripts/test-harness-timer.sh:18-25
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Tight wall-clock window for sleep 0.5. Rare scheduler delays can exceed 0.69s and flake the test. Widen slop or use bounded tolerance logic.
- **Suggested revision**: Address the concern above.


### FINDING_9: correctness: scripts/test-harness-timer.sh:27-33
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] sleep 2 regex only allows 1.xx-2.xx s Wall time can be 3.00s+ on loaded CI so timing line matches harness but test fails Widen pattern or assert numeric bounds instead of leading digit class
- **Suggested revision**: Address the concern above.


