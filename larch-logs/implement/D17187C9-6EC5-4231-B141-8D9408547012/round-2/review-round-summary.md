# Review Round 2

- Mode: `diff`
- Accepted findings: 4
- Rejected findings: 1
- Exonerated findings: 16
- Neutral findings: 0

## Accepted Findings

### FINDING_10: Zero-byte stdout warmup reuses `STALL_THRESHOLD`, stretching effective hang detection
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Warmup logic that refreshes `last_prog_ts` on synthetic zero-byte ticks can push a permanently zero-byte capture toward roughly `2 * STALL_THRESHOLD` (plus poll quantization) before SIGTERM, weakening the stated CI guardrail versus operator-facing “180s” messaging.
- **Suggested revision**: Use a shorter separate warmup bound, or stop advancing `last_prog_ts` on synthetic zero-byte ticks so the post-warmup window matches `STALL_THRESHOLD`.


### FINDING_14: Missing `--output` while wrapper PID is alive treated as perpetual progress
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-stall-logic-output.txt
- **Concern**: If the capture file never appears (or disappears and never returns) while the PID remains alive, treating each poll as progress prevents `stall_seconds` accrual; only the outer wall-clock timeout remains.
- **Suggested revision**: Time-bound “missing file counts as progress” similarly to the zero-byte grace window, or enforce/document an invariant that the capture exists before monitoring and drop the unbounded branch.


### FINDING_18: `run-external-agent.md` not updated for new capture/stdbuf behavior
- **Reviewer(s)**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: Script behavior changed but sibling markdown is stale versus the repo’s scripts `*.sh` ↔ `*.md` sibling documentation expectation.
- **Suggested revision**: Update `run-external-agent.md` in the same change set as the script changes.


### FINDING_3: `launch-cursor-ci.md` kill ordering vs launcher implementation
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: Documentation describes signaling as if only the wrapper gets SIGTERM, while code paths that have `pgrep` may terminate direct children first; operators comparing docs to `strace` can misread ordering.
- **Suggested revision**: Update prose to the child-then-wrapper sequence that matches `lib-cursor-launcher-common.sh`.


