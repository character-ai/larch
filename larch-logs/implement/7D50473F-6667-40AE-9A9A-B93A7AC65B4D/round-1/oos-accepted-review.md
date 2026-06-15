### OOS_1: [OUT_OF_SCOPE] `ingest_launcher_token_sidecar` ignores subprocess return codes
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/agents.py:5076-5086` — `ingest_launcher_token_sidecar` does not check return codes from token CLI subprocesses. Rebase conflict-fix launches with `allow_output_fallback=True` may report success while append-record or record-vendor-sidecar failed, losing token accounting silently.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Check runner.run return codes and emit operator-visible warnings on non-zero ingestion exits.

---


### OOS_2: [OUT_OF_SCOPE] Duplicated MAIN_ADVANCED pre-rebase block in `ship.py`
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: latent
- **Concern**: `python/ship.py:1553-1717` MAIN_ADVANCED handling duplicates the `monitor.goto_rebase` rebase block verbatim. A later fix to pre-rebase flush policy, stall shape, or PrePushConflictHandoff state may land in only one copy, reintroducing divergent ship behavior.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Extract a shared `_run_pre_merge_rebase(...)` helper the next time either path is edited.

---


