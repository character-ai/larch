### [Plan Review] FINDING_19

### FINDING_19: KV envelope should be in a dedicated file or bracketed markers
- **Reviewers**: Codex-Innovation (item 5 latent security)
- **Concern**: Plan emits the final envelope as the "last lines" of stdout. The wrapper already emits many `emit_kv` lines per round to stdout. A tail-anchored parser can latch onto the wrong line if any helper adds late stdout, and arbitrary stdout parsing is fragile.
- **Proposed resolution**: Emit the final envelope to a dedicated file `$IMPLEMENT_TMPDIR/step5-review-loop.env` (atomic write at loop exit) AND echo a single sentinel line on stdout (`STEP5_LOOP_ENVELOPE_FILE=...`). Main agent reads the file via `read-session-env-key.sh`-style helper. Pin the contract in structure tests.


### [Plan Review] FINDING_26

### FINDING_26: Prefer child-process loop over in-process refactor
- **Reviewers**: Codex-Innovation (item 1, the dialectic antithesis at second glance)
- **Concern**: The in-process refactor (extract `_implement_round_body`, add `run_implement_loop`) is risky because the current script is "exit-heavy" — multiple deep helpers call `exit` directly. Auditing all exit sites and converting them is non-trivial. A child-process loop (a thin wrapper script that invokes `review-and-fix.sh --mode diff --round-num N` per iteration) avoids the exit audit entirely and keeps `review-and-fix.sh` unchanged for the round primitive.
- **Proposed resolution**: Reconsider DECISION_1: implement the loop as a CHILD-PROCESS LOOP in a new (or extended) wrapper script that invokes the existing `--mode diff --round-num N` CLI per iteration. The Step 2a.5 dialectic resolution stood by default because Cursor antithesis truncated; this finding reopens the architectural choice with new evidence (count of `exit` sites in the script) that wasn't part of the original synthesis.


