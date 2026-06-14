# Review Round 2

- Mode: `diff`
- 8 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: pytest launch-review coverage below shell-harness parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: The new `python/test_launch_review.py` suite has only ~14–15 cases while plan acceptance requires parity with the deleted multi-section shell harness (preflight bundles, retries, locking, dirty-tree, degraded response, failure logging, parser preflight retry, security parity). Regressions in auth-preflight exit-0 clean dirty-tree, transient-retry sidecar reset, Retry preflight cap-hit, degraded-response baseline, path-stream, or auth exit-code behavior in `launch_review_main` can merge with green `make test-launch-review`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port the highest-risk retired harness scenarios into python/test_launch_review.py before relying on pytest as the parity authority.
  - From cursor-specialist-testing-output.txt: Port shell-harness sections into pytest: preflight exit matrix retries serial-lock cursor baseline sidecar fields CURSOR_DEGRADED_RESPONSE CLI cap-hit design session-id


### FINDING_2: Codex NS-retry mutates prompt sidecar before sentinel replay
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Codex NS-retry prepends a strong header to the prompt sidecar before `launch-review` reads it, breaking `LARCH_PROMPT_SENTINEL` replay in `python/agents.py`. Codex specialist NS-retry sends sentinel metadata as the vendor prompt instead of a reconstructed specialist prompt, yielding garbage or empty reviewer output.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-render the specialist prompt from sentinel fields and prepend the NS header to that text, or avoid mutating the sentinel file before replay.


### FINDING_3: Cursor `.done` promoted before timing recorded
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: `_review_launch_cursor` promotes `.inner.done` to `.done` before `_review_record_timing` runs, unlike the Codex path and the plan’s terminal-order contract (“promote `.done` last”). Fast collectors or waiters that treat `.done` as completion (for example `collect-agent-results.sh` retry sentinels) can proceed before `timing record-vendor-task` finishes, so Cursor review vendor timing rows may be missing or stale in the timing ledger.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Move _review_record_timing before _promote_inner_done on the Cursor path.
  - From dyn-launcher-parity-output.txt: Move `_review_record_timing` (and keep `_review_emit_launcher_result` after it) to immediately follow `_review_append_outer_meta`, before the test trap / JSON post-processing / dirty-tree / `.done` promotion, matching the Codex ordering and the plan’s “promote `.done` last” rule.


### FINDING_5: Codex auth-setup preflight exit-0 bundle untested
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: Codex auth-setup preflight exit-0 bundle (clean static dirty-tree, `.done`, process exit 0) is plan-critical bash parity but untested. A regression can return non-zero process exit or unknown dirty-tree on auth setup failure and break collector semantics.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add pytest with mocked auth-setup failure asserting process exit 0 and static clean .dirty-tree sidecar.


### FINDING_6: preflight `.meta` writes `OUTER_LAUNCHER_STDERR_SINK` but collector reads `STDERR_SINK`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-retry-cutover-output.txt
- **Severity**: important
- **Concern**: `_review_append_outer_meta` writes `OUTER_LAUNCHER_STDERR_SINK` but `collect-agent-results.sh` only binds `STDERR_SINK` when parsing `.meta` (`parse_retry_meta` at `scripts/collect-agent-results.sh:594`) and only forwards `--stderr-sink` from `META_STDERR_SINK` on review outer retries (`scripts/collect-agent-results.sh:800-814`). Shell parity (`scripts/lib-external-launcher-common.sh:31`) and `run_external_agent` (`python/agents.py:1585`) use `STDERR_SINK`. On vendor paths that never call `run_external_agent`, especially `_review_write_preflight_bundle`, metadata can carry `OUTER_LAUNCHER_STDERR_SINK` with no `STDERR_SINK`, so collector retries omit `--stderr-sink` and lose stderr-tail / launch-stderr diagnostics parity the plan and `test-collect-agent-retry.sh` expect.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Write STDERR_SINK= in _review_append_outer_meta to match external_launcher_append_outer_meta; add pytest for preflight meta + collector retry forwarding.
  - From dyn-retry-cutover-output.txt: Write `STDERR_SINK=` (not `OUTER_LAUNCHER_STDERR_SINK`) in `_review_append_outer_meta`, or teach `parse_retry_meta` to accept both keys with `STDERR_SINK` winning; add `python/test_launch_review.py` coverage for preflight/auth-failure metadata with `--stderr-sink` and assert collector replay forwards it.


### FINDING_7: review token ledger asymmetry (Cursor double-count, Codex not ingested)
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: Cursor usage is recorded twice in the active ledger while Codex review usage is only written to a `.token-record` sidecar at `python/agents.py:3537` and not ingested into the active ledger. A Cursor review with 10 total tokens can append two active-ledger vendor rows, so `LARCH_TOKEN_BUDGET_CAP_REVIEW=15` can cap-hit too early; a Codex review with 100 tokens only writes `.token-record`, so the next cap check can still see 0 and launch another vendor despite the cap.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: For both tools, write the `.token-record` sidecar once and ingest it into the active ledger once, preferably via `token record-vendor-sidecar`, matching the Cursor sidecar path and adding the same active-ledger ingestion for Codex.


### FINDING_8: Darwin external serial lock held for full `run_external_agent` wait
- **Reviewer(s)**: codex-generic-output.txt
- **Severity**: important
- **Concern**: The review launcher holds the Darwin external serial lock for the full `run_external_agent` call instead of only around the vendor spawn window. Two parallel Cursor review slots on Darwin no longer get the old ~0.5s launch spacing; the second slot waits until the 30s TTL/try window before it can proceed, or it removes an active lock while the first vendor is still running.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-generic-output.txt: Start the release timer immediately after acquiring the lock and before the blocking `run_external_agent` wait, or add a spawn callback so the lock is released right after the child process starts.


### FINDING_9: Codex in-loop auth detection scans wider sidecar set than retired bash
- **Reviewer(s)**: dyn-launcher-parity-output.txt
- **Severity**: important
- **Concern**: In `_review_run_with_retries`, Codex auth gating calls `external_auth_verdict(tool, *sidecars)` over stderr sidecar, `.diag`, `.events.jsonl`, and the `--output-last-message` file. The retired shell launcher only consulted the stderr sidecar for Codex auth in its retry loop (`external_is_auth_failure "codex" "$SIDECAR"`). Auth-shaped text in the JSON events stream or a non-empty output file can classify a failure as auth in Python when bash would have treated it as transient and retried (or vice versa), changing retry bounds and waterfall behavior under mixed infra/auth failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-launcher-parity-output.txt: Match bash parity by restricting Codex in-loop auth detection to the stderr sidecar (and mirror quota into that sidecar first, as today), or document and test the widened sidecar set if the broader scan is intentional.


