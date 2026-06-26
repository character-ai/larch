# Review Round 1

- Mode: `diff`
- 3 accepted, 1 rejected (1 neutral)

## Accepted Findings

### FINDING_1: correctness: Fix B dedup can stall post-notification recovery after sentinel probe
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: Fix B identical-notification dedup conflicts with the sentinel-present post-notification rule and can stall recovery after a DONE probe. After an initial premature notification and WAIT probe, byte-identical replays can skip further probes and never retry post-notification routing after the background task exits, even when a sentinel is written later without content change. Scope dedup to prior WAIT probes only, exempt when step-3-terminal is already confirmed, or add an explicit one-shot sentinel re-probe when the background process has completed or exited regardless of fingerprint; align line 23 with line 25.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Address the concern above.
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


### FINDING_6: correctness: review_pipeline.py dispatch_panel never appends generic Codex row
- **Reviewer(s)**: codex-specialist-correctness-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt
- **Severity**: important
- **Concern**: dispatch_panel never calls _append_round_generic_codex_row; the helper at python/review_pipeline.py:898-900 is dead code. On review rounds 1 or 2 (and related generic_codex rounds) with Codex available, the panel launches only static specialists and dynamic scouted slots, so the intended generalist vote never runs and STATIC_SLOT_COUNT/SLOT_COUNT are too low. Call _append_round_generic_codex_row during manifest construction before recount/prune when _generic_codex_enabled(round_num) is true, and add regression coverage that round-1/2 manifests include the generic row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-correctness-output.txt: Address the concern above.
  - From codex-specialist-edge-cases-output.txt: Address the concern above.
  - From codex-specialist-testing-output.txt: Address the concern above.


### FINDING_11: risk-integration: test_plan_review.py does not assert sentinel before KV stdout emission
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: important
- **Concern**: New tests verify step-3-terminal exists after normalize exits but not that it is written before KV stdout emission. Reordering sentinel write after _step3_emit_normalize_envelope_with_next_action would restore premature notifications and WAIT/probe loops while all #5418 tests still pass. Add a monkeypatch test that asserts (tmpdir / ".completed" / "step-3-terminal").is_file() inside _step3_emit_normalize_envelope_with_next_action before emit proceeds.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.


