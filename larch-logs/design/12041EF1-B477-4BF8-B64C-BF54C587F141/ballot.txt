### FINDING_1: SECURITY.md documents disallowed scope-anchor argv handoff
- **Reviewer(s)**: Cursor-Edge, Codex-Edge, Cursor-Innovation, Cursor-Pragmatic, Codex-Requirements, Codex-dyn-dependency-gate, Codex-dyn-stale-anchor-invariant, Codex-dyn-security-claim-coverage
- **Severity**: important
- **Concern**: Planned SECURITY.md trust-boundary text describes SCOPE_ANCHOR_FILE flowing through tally/MainAgent re-tally argv even though the plan requires env/stdout/result-env handoffs and forbids adding `--scope-anchor-file` tally or re-tally argv. Some sources also note the SECURITY.md wording should preserve the terminal-status gate for when the anchor may be written or relayed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Edge: Replace re-tally argv with env-sourced KV parse and dual env refresh (match FINDING_3 / FINDING_5 wording)
  - From Codex-Edge: Change the SECURITY.md planned wording to say MainAgent re-tally env/stdout parse or refreshed result-env handoff, and remove "MainAgent re-tally argv" from the path-only handoff list
  - From Cursor-Innovation: Rewrite to env-sourced handoffs only: loop stdout/result env and Step 3 relay on ok/main-agent-vote-required; MainAgent re-tally parses stdout KV with no scope-anchor argv; omit tally argv entirely or say tally may echo SCOPE_ANCHOR_FILE KV on stdout only
  - From Cursor-Pragmatic: Replace MainAgent re-tally argv with env-sourced stdout KV parse and dual result-env refresh (or omit MainAgent from the path list and point readers to the inline re-tally prose)
  - From Codex-Requirements: Change that phrase to MainAgent re-tally env/stdout/result-env refresh or remove argv from the path-only handoff list
  - From Codex-dyn-dependency-gate: Revise the SECURITY.md bullet to say path-only KV relay flows through loop stdout/result env, run-step3 relay, Step 3 result env, and MainAgent re-tally env/result refresh; remove tally/re-tally argv wording
  - From Codex-dyn-stale-anchor-invariant: Revise the SECURITY.md planned bullet to say loop relay, Step 3 relay, and MainAgent re-tally use path-only stdout/result-env KVs, never tally/re-tally argv, and write SCOPE_ANCHOR_FILE only from parsed output on ok or main-agent-vote-required while omitting tally-error, panel-failed, and other non-terminal paths
  - From Codex-dyn-security-claim-coverage: Revise surface 2 to say loop/tally stdout KV, Step 3 result-env relay, and MainAgent re-tally env/result-env refresh; remove argv wording.

### FINDING_2: Raw tally stdout can leak stale SCOPE_ANCHOR_FILE before normalized gate
- **Reviewer(s)**: Codex-Innovation
- **Severity**: important
- **Concern**: `plan-review-loop.sh` gates normalized SCOPE_ANCHOR_FILE persistence, but still reprints raw tally stdout before normalized loop KVs. If tally stdout contains a stale or error-path SCOPE_ANCHOR_FILE, the key can escape through loop stdout even when gated env outputs omit it.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Innovation: Revise the plan to filter SCOPE_ANCHOR_FILE out of raw _tally_raw before printf, then re-emit it only through the normalized gated path for ok or main-agent-vote-required; add the stale/error test with a tally stub that emits the stale key to prove stdout does not leak it

### FINDING_3: Makefile shard registration lacks verify-first guard for optional helper
- **Reviewer(s)**: Cursor-dyn-dependency-gate
- **Severity**: important
- **Concern**: The plan gates Item 4 script work on helper presence, but the Makefile update is unconditional. If `scripts/check-scope-reduction-marker.sh` is absent after #3548, adding a target or shard entry that invokes it can break `make lint`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-dependency-gate: Mark Makefile edits verify-first with the same observable gate as Item 4: test -f scripts/check-scope-reduction-marker.sh (or test -x) before adding .PHONY recipe and shard entry; omit the Makefile subsection entirely when the helper is absent

### FINDING_4: main-agent-vote-required may lose anchor when tally stdout omits the KV
- **Reviewer(s)**: Cursor-dyn-stale-anchor-invariant
- **Severity**: important
- **Concern**: The plan requires relaying SCOPE_ANCHOR_FILE for `main-agent-vote-required`, but the strict stdout-parsed persistence rule may omit it when tally stdout lacks the KV. That can cause loop/result env outputs to drop the materialized anchor and leave re-tally reading only stale shell state.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-stale-anchor-invariant: State explicitly: on ok and main-agent-vote-required when tally stdout lacks the KV, emit CR/LF-clean path from _LOOP_SCOPE_ANCHOR_IN (materialized anchor) into loop KVs/result env; keep stdout-parse guard for tally-error and other terminals only

### FINDING_5: SECURITY.md revise-waterfall coverage claim lacks verify-first qualifier
- **Reviewer(s)**: Cursor-dyn-security-claim-coverage, Codex-dyn-security-claim-coverage
- **Severity**: important
- **Concern**: Planned SECURITY.md wording conditionally qualifies subprocess context-body hardening, but appears to claim revise waterfall plan/findings/feature block coverage unconditionally even though migration is verify-first and current compose_prompt paths may still raw-sed those blocks. This could overstate protection against delimiter injection if SECURITY.md lands before migration is verified.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-dyn-security-claim-coverage: Add a revise-specific mirror of the subprocess sentence, e.g. "Revise waterfall plan/findings/feature block coverage in this section applies only after verify-first migration to emit_untrusted_file_block (or documents post-implement gap — FINDING_1)."
  - From Codex-dyn-security-claim-coverage: Add the same post-verify/open-gap qualifier for revise waterfall blocks, or make SECURITY.md conditional until all three compose_prompt blocks are confirmed migrated to redacted escaped untrusted blocks.
