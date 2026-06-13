### OOS_1: [OUT_OF_SCOPE] correctness: skills/research/references/research-phase.md has same $? capture bug
- **Reviewer(s)**: dyn-token-env-codex-output.txt
- **Severity**: latent
- **Concern**: The pre-existing research sidecar ingestion snippet has the same `if ! ...; then _rc=$?` pattern, so failed token commands also report `exit 0` there.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-token-env-codex-output.txt: Apply the same status-capture pattern used for the validation fix.


### OOS_2: [OUT_OF_SCOPE] risk-integration: scripts/ship-pr.sh legacy path lacks stale sidecar pre-clear
- **Reviewer(s)**: dyn-fallback-freshness-output.txt
- **Severity**: latent
- **Concern**: The legacy Bash CI-fix path still defaults to `${tier_out}.token-record` when stdout omits `TOKEN_RECORD=` and does not pre-clear that path before launch. Stale sidecar reuse remains possible when `LARCH_SHIP_PR_IMPL=bash`; this branch only added env cleaning to `ship_pr_ingest_token_record_once`, not freshness clearing.
- **Suggested revisions (informational for voters; coder decides)**:


### OOS_3: [OUT_OF_SCOPE] correctness: python/rebase.py conflict ingestion lacks ci_monitor output-fallback parity
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-fallback-freshness-output.txt
- **Severity**: latent
- **Concern**: Rebase conflict ingestion lacks `ci_monitor` output fallback and pre-clear parity. Codex/Cursor conflict fixers that write only `${output}.token-record` without stdout `TOKEN_RECORD=` still drop usage on the Python rebase path when `allow_output_fallback` is disabled and stale sidecars are not cleared before launch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Port allow_output_fallback and pre-clear pattern from ci_monitor if parity is desired
  - From cursor-specialist-edge-cases-output.txt: Mirror ci_monitor: pre-clear ${output}.token-record for codex/cursor and pass allow_output_fallback=True.


