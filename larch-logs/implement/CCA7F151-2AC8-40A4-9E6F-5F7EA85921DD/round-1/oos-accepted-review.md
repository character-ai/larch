### OOS_1: [OUT_OF_SCOPE] Bash lint-fix path does not clear stale token ledger env
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bash lint-fix path at `scripts/lint-fix-loop.sh:442-451` still uses `IMPLEMENT_TMPDIR=...` prefix without clearing stale `LARCH_TOKEN_LEDGER` / `LARCH_TOKEN_SESSION_ID`. Plan kept this path unchanged; Python `checks.py` path is hardened.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_2: [OUT_OF_SCOPE] Warning relay for token ingestion remains path-dependent across Bash vs Python ship drivers
- **Reviewer(s)**: dyn-warning-surface-output.txt
- **Severity**: latent
- **Concern**: Bash lint-fix still discards all token CLI stderr on successful ingestion (`>/dev/null 2>&1`); the branch improved warning relay only on the Python `checks._run_codex` path used by the default Python ship driver, so warning behavior remains path-dependent across `/implement` (bash) vs `python/ship.py` (in-process).
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_3: [OUT_OF_SCOPE] Research Codex sidecar ingestion is prompt-only with no mechanical enforcement
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: Research Codex sidecar ingestion is documented prompt-side only with no script-level hook or structural harness. If the orchestrator skips the ingestion block or doc drift occurs, research lanes can finish with billable Codex sidecars but no ledger or NDJSON rows, and CI will not catch regressions on item 6.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Add a script-level post-collector hook or harness assertion if durable ingestion is required.
  - From cursor-specialist-testing-output.txt: Add a reference pin harness or check-contains-pins coverage for the ingestion block and env `-u` list.


### OOS_4: [OUT_OF_SCOPE] Codex drafter copy failure leaves orphaned sidecar while `TOKEN_RECORD` advertises stable path
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-warning-surface-output.txt
- **Severity**: latent
- **Concern**: On copy failure the launcher warns via `larch_err` and still succeeds, but every exit path emits `TOKEN_RECORD=${OUTPUT_CANON}.token-record` without verifying the stable destination exists. Downstream design ingestion gates on the stable path, so billable usage can remain on the orphaned `${_codex_raw}.token-record` while `TOKEN_RECORD=` still names the missing stable file. Residual gap from the intentional minimal Item 1 fix (warn, do not fail).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-warning-surface-output.txt: When `cp` fails, omit `TOKEN_RECORD` or point it at the existing raw sidecar; alternatively teach `design-step2b-drafter.sh` to fall back to the raw path and emit its own operator-visible warning when the stable copy is missing.


### OOS_5: [OUT_OF_SCOPE] Default Python ship driver lacks Bash recovery sidecar ingestion parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: Bash-only `ship-pr.sh` recovery ingestion remains unavailable on the default Python ship driver. CI-fix recovery on `LARCH_SHIP_PR_IMPL=python` paths may still drop sidecar ingestion present in the Bash driver. Explicitly out of scope per plan (no `ship.py` recovery port); filed as follow-up (#4153 for validation lanes).
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Track as follow-up if parity with Bash recovery is desired.


