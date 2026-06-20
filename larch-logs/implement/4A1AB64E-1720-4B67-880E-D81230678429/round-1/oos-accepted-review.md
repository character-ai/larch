### OOS_1: [OUT_OF_SCOPE] Location+Concern dedup keys miss paraphrased or shifted-line re-raises
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-code-quality-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Applied-key filtering reuses `_finding_dedup_key` (normalized Location + Concern only). Round-2 re-raises with different line refs or reworded concerns (e.g. plan.txt:40-44 vs plan.txt:33-37 for the same issue) will not match ledger keys and still appear as unimplemented at Gate C. Inherited from #4808; this branch extends the gap to the Step 4 reporting surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Document limitation or extend keying (finding id or semantic match) in a follow-up.
  - From cursor-specialist-edge-cases-output.txt: Consider annotation or semantic dedup in a follow-up issue
  - From dyn-code-quality-output.txt: Filtering depends on `_finding_dedup_key` matching Location+Concern between accepted ledger rows and later rejected blocks. Re-raised findings with changed line citations (as in the live #4835 run) may still slip through. That is a correctness/limitation of the dedup key, not a code-quality defect in this diff.
  - From dyn-risk-integration-output.txt: Document the residual risk in Step 4 prose, or add a secondary match (e.g. normalized `what` / finding title) when Location+Concern diverges across rounds.


### OOS_2: [OUT_OF_SCOPE] Dynamic slot render failure silently falls back to plan-blind prompt
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Dynamic scout slots route through `render plan-review`, but on render non-zero exit `_dynamic_slot_rows` passes empty `rendered` into `_slot_row`, which writes a one-line fallback with no plan-file path or TSV contract. That revives the #4841 failure mode (reviewers grep the repo, findings dropped `NOT_SUBSTANTIVE`) for any render miss, wasting a full review round. No dedicated test covers dynamic-slot render failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Log render failures; optional hard-fail for dynamic slots.
  - From cursor-specialist-testing-output.txt: Match static-slot failure tests if render miss becomes common
  - From dyn-risk-integration-output.txt: On render failure, log to `execution-issues.md` and omit the slot from the manifest (or hard-fail panel dispatch) instead of launching a plan-blind fallback prompt.


### OOS_3: [OUT_OF_SCOPE] LARCH_PROBE_TIMEOUT_SECONDS default 30→60 doubles worst-case Step 0 probe latency
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: Doubling `LARCH_PROBE_TIMEOUT_SECONDS` default from 30s to 60s doubles worst-case Step 0 probe wall-clock when stamps are cold. `check_reviewers` runs Cursor then Codex sequentially; with default `LARCH_PROBE_TIMEOUT_RETRIES=0`, a timeout on each tool is up to ~120s before the degraded-tools gate. Doc text claiming retry latency is unchanged is now misleading. CI has no explicit test that unset `LARCH_PROBE_TIMEOUT_SECONDS` yields 60.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Track separately from #4849 merge review
  - From cursor-specialist-testing-output.txt: Optional explicit test that unset LARCH_PROBE_TIMEOUT_SECONDS yields 60
  - From dyn-risk-integration-output.txt: Document the doubled worst-case bound explicitly (e.g. “up to ~2×60s on cold double-timeout with defaults”), or keep 60s only for Step 0 session probes and leave launch-time health gates on a separate default if operators need a tighter startup SLA.


### OOS_4: [OUT_OF_SCOPE] LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT bumped to 60s for launch-time health gates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, dyn-risk-integration-output.txt
- **Severity**: important
- **Concern**: The branch bumps `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` resolver fallback and session-env persistence from 30 to 60. Every `/design` and `/implement` session now carries `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT=60` for launch-time health-gate callers. Per-launch fast-fail before full reviewer `--timeout` can wait up to 60s per unhealthy launch instead of 30s; on a Step 3 panel with many external slots, that multiplies tail latency on degraded paths.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Confirm intentional; split commits already separate concerns.
  - From dyn-risk-integration-output.txt: Confirm whether launch-time health gates should share the Step 0 probe default; if not, scope the 60s bump to `LARCH_PROBE_TIMEOUT_SECONDS` only and leave `LARCH_EXTERNAL_HEALTH_CHECK_TIMEOUT` at 30 until launch-time false-fails are reported.


