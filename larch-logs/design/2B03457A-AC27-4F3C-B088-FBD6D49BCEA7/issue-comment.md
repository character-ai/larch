### Design-rationale notes from a parallel /design session

Two empirical observations from a separate session that bear on this issue and have been incorporated into the implementation plan's **Approach** section:

**1. The outer-fallback layer (in `aggregate-findings.sh`) is itself unreliable, so the gate must live at the *inner* dispatch boundary.**

In that session, round 1 produced `MERGE_PIPELINE_RC=1` (`empty_merge_from_nonempty_input`). The contract says that condition should continue to the Codex outer phase — but no `aggregator-output-codex.txt` was produced in round 1. Round 2 did fire the outer fallback. This means relying on outer-phase reordering or hardening alone would leave a real failure mode. A content-aware gate at the inner `scripts/dispatch-with-waterfall.sh` boundary (the structural fix in this plan via `--require-result-pattern`) catches narration-only outputs at the per-slot level *before* they ever land on the outer aggregator's queue, regardless of how the outer fallback behaves on any given run.

**2. The Cursor failure is a planning-mode *abstention*, not a launcher failure — so the right fix is at the dispatch layer (pattern check), not the launcher layer (mode flag).**

Concrete metrics from a failing Cursor run on this very issue's class of slot: `outputTokens=6086`, with a final `.result` field of `~106 bytes` of narration text. The model ran to completion, generated thousands of output tokens, and *chose* at presentation time to emit only the planning trace. So:

- Swapping `cursor agent -p --trust --mode plan --output-format json --model composer-2.5` to `--mode auto` would be a bet on upstream Cursor behavior under a different mode.
- Adding `--require-result-pattern '^[[:space:]]*## Recommendation'` at the dispatcher (this plan) is a defensive structural guard that works regardless of upstream model behavior or future mode changes. It promotes Cursor's "I'll stop here and just narrate" from a silent `STATUS=OK` into a normal waterfall failure that phase-2/phase-3 fallback recovers from.

Both observations confirm the chosen approach in the implementation plan rather than change it; they have been added to the **Approach → "Why the inner-dispatch layer is the right home for this gate"** paragraph as supporting context for the implementer.
