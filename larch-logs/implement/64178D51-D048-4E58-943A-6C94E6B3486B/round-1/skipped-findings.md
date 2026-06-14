### OOS_2: plan_review.py is a gzip-embedded Bash relay, not an in-process Python port
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-retired-path-sweep-output.txt
- **Severity**: important
- **Concern**: Core `plan-review` verbs (`emit_plan`, `run_step3_review`, `tally_plan_review`, `gate_b_dedup_plan`, and siblings) delegate to gzip-embedded copies of deleted shell scripts via `_materialize_legacy_root()` / `_run_legacy()` instead of native Python. `python3 python/cli.py plan-review tally` still materializes and runs `tally-plan-review.sh`. Retired scripts are frozen blobs while live `scripts/` dependencies are symlinked, creating a hidden dual-maintenance surface that can desync from HEAD and fails the C3a1 "direct cutover, no shims" goal; `plan_quality` in-process integration never lands.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Complete the in-process port or document as legacy relay and adjust acceptance criteria
  - From codex-specialist-correctness-output.txt: Replace the compatibility asset layer with real Python implementations and explicit subprocess seams.
  - From cursor-specialist-edge-cases-output.txt: Complete native port or add CI pinning/decoding checks and explicit compatibility-layer docs
  - From codex-specialist-edge-cases-output.txt: Replace _LEGACY_ASSETS and _run_legacy with native Python implementations, or keep shell scripts until the real port lands.
  - From codex-specialist-testing-output.txt: Port the absorbed script logic into real Python functions and remove the legacy asset materialization/delegation layer.
  - From dyn-retired-path-sweep-output.txt: Either finish the in-process port per the plan, or document and test blob regeneration from HEAD whenever absorbed scripts' live dependencies change; do not treat `python/plan_review.py` as migrated while it shells frozen snapshots.



