# Review Round 1

- Mode: `diff`
- 2 accepted, 3 rejected (1 neutral)

## Accepted Findings

### FINDING_1: Stale latest-reviewer-status.tsv on degraded post-collection terminals
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-code-robustness-output.txt, dyn-architecture-output.txt
- **Severity**: important
- **Concern**: `round-N/reviewer-status.tsv` is written after collection on degraded terminals (`tally-error`, `main-agent-vote-required`, `degraded-empty-collector`, post-collection `panel-failed`, etc.), but `latest-reviewer-status.tsv` is copied only on the `execute_round` success tail. In multi-round Step 3 runs where round 1 completes and round 2 exits via a non-success terminal, `skills/design/SKILL.md` reads `latest-reviewer-status.tsv` first (not merely when missing), so the post-notification table can show stale round-1 slot statuses while the per-round file for the current round is correct.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Copy to latest immediately after write_reviewer_status_tsv (or on every terminal that wrote the per-round file), or change SKILL.md to prefer the FINAL_ROUND_NUM per-round file when bound
  - From codex-specialist-correctness-output.txt: Factor status write plus latest copy into one helper and call it before every post-collection return path, or copy to latest immediately after write_reviewer_status_tsv succeeds.
  - From cursor-specialist-edge-cases-output.txt: Copy round-N/reviewer-status.tsv to latest on every post-collection terminal exit, not only the success tail; add a regression test for a non-complete terminal
  - From codex-specialist-edge-cases-output.txt: Copy the per-round reviewer-status.tsv to latest-reviewer-status.tsv immediately after write_reviewer_status_tsv succeeds, before any post-collection early returns; also cover collect_rc != 0 with no records when a manifest exists.
  - From cursor-specialist-testing-output.txt: Copy to latest-reviewer-status.tsv whenever write_reviewer_status_tsv succeeds (or on every post-collection exit), not only on complete; add a degraded/multi-round regression test
  - From codex-specialist-testing-output.txt: Centralize status finalization. Write the per-round file and copy it to latest-reviewer-status.tsv before every terminal return, or clear latest when no current status can be produced. Add a multi-round regression for a non-success terminal.
  - From dyn-code-robustness-output.txt: **Suggested fix:** Copy to `latest` immediately after a successful `write_reviewer_status_tsv` (or extract a small helper and call it from every post-collection exit path). Add tests for `tally-error` / `degraded-empty-collector` asserting `latest` matches the current round file.
  - From dyn-architecture-output.txt: **Suggested fix:** Move "sync `latest` from per-round file" into `write_reviewer_status_tsv` (or a single shared helper invoked immediately after every successful producer write), and drop the success-only copy at the tail of `execute_round`. Align `plan_review.py:1278-1280` with the same helper so subprocess and in-process paths share one contract.
  - From dyn-architecture-output.txt: **Suggested fix:** Centralize round-file production and `latest` sync in one function (e.g. `materialize_reviewer_status(design, round_num) -> Path | None`) called from `execute_round` after collection and from the subprocess fallback in `_run_round_body`; avoid exposing a write-only primitive that callers must pair with copy logic themselves.


### FINDING_3: Status join uses exact output paths; retry and waterfall paths mislabeled skipped
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-testing-output.txt, dyn-code-robustness-output.txt
- **Severity**: important
- **Concern**: `write_reviewer_status_tsv` joins manifest `output` to collector `REVIEWER_FILE` via exact string equality. Collectors can record successful results on alternate paths: slot retries land on `{base}-retry.txt` while the manifest still names `{base}-output.txt`, and `agent_waterfall` can land on `-phase2.txt` / `-phase3.txt` while the manifest retains phase-1 paths. The retired shell producer normalized with `os.path.realpath` and `base_candidates()`; without equivalent matching, rows are mislabeled `skipped` instead of `done`/`failed` even when `STATUS=OK`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Join using orig output plus _retry_output_path(output) and/or normalized basename matching
  - From codex-specialist-testing-output.txt: Normalize retry output paths back to their original manifest output, or map both original and retry paths to the same slot. Add a regression with a collector record whose REVIEWER_FILE is the retry path.
  - From dyn-code-robustness-output.txt: **Suggested fix:** Reuse or port the old `base_candidates` / `realpath` matching (or index by manifest `slot` and resolve collector paths through the same candidate set `_compose_findings_from_collector` relies on). Add a unit test where manifest `output` is phase-1 and `REVIEWER_FILE` is phase-3.


