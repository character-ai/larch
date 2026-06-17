# Review Round 1

- Mode: `diff`
- 6 accepted, 2 rejected (2 neutral)

## Accepted Findings

### FINDING_1: Empty-batch success stamps `step9a1=false` despite passing checkpoint
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt
- **Severity**: important
- **Concern**: When there are zero accepted OOS blocks but prior filed evidence exists, `cmd_file` still runs a successful disposition checkpoint and writes `run-statistics.md`, yet calls `_after_checkpoint(..., stamp_value=bool(filed))` which resolves to `false` at `python/oos_filer.py:662`. `_step9a1_heuristic` then treats explicit `steps_ran.step9a1=false` as authoritative and reports Step 9a.1 incomplete even though checkpoint success evidence is on disk.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Stamp `step9a1=true` on successful checkpoint paths including empty batches; use `false` only on checkpoint failure or explicit skip.
  - From codex-specialist-correctness-output.txt: Stamp `true` or leave `step9a1` unset on checkpoint-success empty batches; use `false` only for checkpoint failure or true skips.


### FINDING_2: Checkpoint-failed retry dedup can re-file duplicate GitHub issues
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-oos-retry-output.txt
- **Severity**: important
- **Concern**: After a checkpoint failure, retry idempotency in `_split_persisted_matches` (`python/oos_filer.py:237-250`) and `FiledIssue` creation (`python/oos_filer.py:526`) is brittle. Persisted `stable_id` values are derived from renumbered `OOS_{item_index}` rather than accepted-block header IDs; Codex combine can rewrite titles so title fallback misses; URL correlation is not attempted even when sentinel/ndjson carry a filed URL; and when multiple accepted blocks collapse into one public issue, only one block can match the persisted URL/stable ID so sibling blocks re-file on retry.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Persist header-derived `stable_id` from `AcceptedBlock` or combined body when filing.
  - From cursor-specialist-correctness-output.txt: Match persisted `FiledIssue.url` before normalized-title fallback.
  - From codex-specialist-correctness-output.txt: Persist all original stable IDs covered by a combined filed issue and let the retry matcher satisfy all covered accepted blocks from the same URL.
  - From codex-specialist-edge-cases-output.txt: Preserve source stable IDs through combine and issue creation, write them into persisted evidence, and allow one filed URL to satisfy all source blocks it covered.
  - From cursor-specialist-edge-cases-output.txt: Match on filed URL in accepted blocks when `stable_id` is absent, or short-circuit filing when sentinel URLs already cover the batch.
  - From codex-specialist-testing-output.txt: Propagate original accepted-block IDs through render/combine/issue-cap/create; persist all source IDs for rollups and match them before title fallback.
  - From dyn-oos-retry-output.txt: Add a third match pass that pairs a remaining `AcceptedBlock` to an unused persisted `FiledIssue` when the block body contains the persisted URL (or when ndjson/sentinel URL can be tied to the block via stable content hash). Keep stable-id and title as fallbacks, and add a regression test where persisted evidence has only URL + rewritten title.


### FINDING_3: `_step9a1_heuristic` honors stale `steps_ran.step9a1=true` without non-provisional success evidence
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-oos-retry-output.txt, dyn-runlog-step9a1-output.txt
- **Severity**: important
- **Concern**: At `python/run_logs.py:1435-1436`, explicit manifest `steps_ran.step9a1=true` returns `True` before checking `run-statistics.md` or whether only provisional `oos-issues.ndjson` exists. Checkpoint-failed or legacy runs with stale `true` plus ndjson-only evidence therefore stay marked complete on refresh/audit, contradicting the plan rule that ndjson alone is provisional and refresh should downgrade stale `true` when `run-statistics.md` is absent. `python/test_run_logs.py:670-671` may encode the wrong expectation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Treat ndjson-without-stats as incomplete even when manifest says `true`, or document explicit-true precedence.
  - From cursor-specialist-edge-cases-output.txt: Require `run-statistics.md` (or equivalent success evidence) alongside explicit `true`; return `False` when only provisional ndjson exists. Mirror in `audit_runs.py` and `verify_completeness`.
  - From dyn-oos-retry-output.txt: In `_step9a1_heuristic()`, only honor explicit `step9a1=true` when `run-statistics.md` is also present (or another non-provisional success signal exists). If manifest says `true` but evidence is ndjson-only, return `False` so `refresh_run_logs_main()` at `python/run_logs.py:1210-1213` overwrites the stale marker. Mirror the same rule in `python/audit_runs.py:532-537` and `python/run_logs.py:2517-2534` so audit/verify paths stay aligned.
  - From dyn-runlog-step9a1-output.txt: After reading the manifest, treat non-empty provisional `oos-issues.ndjson` without `run-statistics.md` as incomplete even when `steps_ran.step9a1` is explicitly `true` (unless both completion signals are present); add a `flush_logs_pre` regression in `python/test_run_logs.py` with stale `step9a1=true` + ndjson-only evidence asserting refresh writes `step9a1=false`.


### FINDING_6: Forked-run heuristic returns `false` before checking explicit success evidence
- **Reviewer(s)**: codex-specialist-edge-cases-output.txt
- **Severity**: important
- **Concern**: `_step9a1_heuristic` at `python/run_logs.py:1421-1423` returns `False` for forked runs before inspecting manifest `step9a1=true` or `run-statistics.md`. A forked OOS path can stamp `steps_ran.step9a1=true` after a successful checkpoint, then run-log refresh overwrites it back to `false`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-edge-cases-output.txt: Check manifest `true` and `run-statistics` before the forked early return, or make the forked `oos_filer` path stamp `false` consistently.


### FINDING_7: Checkpoint-failure manifest stamp failure loses `disposition_checkpoint_failed` semantics
- **Reviewer(s)**: dyn-oos-retry-output.txt
- **Severity**: important
- **Concern**: On checkpoint failure, `_after_checkpoint()` calls `_stamp_manifest(..., value=False)`, but `_stamp_manifest()` raises `RuntimeError` when the manifest CLI fails (`python/oos_filer.py:619-621`). That exception is caught by `cmd_file()` as generic `"status": "error"` (`python/oos_filer.py:702-704`), not `"disposition_checkpoint_failed"`, even though sentinel/ndjson evidence may already exist and retry idempotency depends on recognizing a failed checkpoint.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-oos-retry-output.txt: Catch manifest-stamp failures inside `_after_checkpoint()` on the failure branch (log a warning, set `step9a1_stamped=false`, still return `disposition_checkpoint_failed` with the checkpoint rc). Reserve the outer `RuntimeError` path for unexpected failures on the success branch only.


### FINDING_8: `design-step-validator-autofix.sh` can emit success KV while audit or routing state is wrong
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-design-wrapper-output.txt
- **Severity**: important
- **Concern**: The wrapper prints the helper's raw KV block at line 179 before rc-based normalization at lines 188-190, so stdout can show `AUTOFIX_STATUS=ok` while `_autofix_status` becomes `failed` when `plan auto-fix-commands` exits non-zero; `/design` may then take the success branch (`skills/design/SKILL.md:944-947`). On the normalized `ok` path, ok-path `run-log append-failure` is redirected to `/dev/null` (`skills/design/scripts/design-step-validator-autofix.sh:203`) and has no `|| true`, yielding either hidden audit-write failure or success KV plus non-zero exit with no Warnings row.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Check append-failure exit code and escalate or fail loudly instead of redirecting stderr/stdout to `/dev/null`.
  - From dyn-design-wrapper-output.txt: Emit stdout only after normalization, or re-emit corrected `AUTOFIX_STATUS` (and related keys) after the rc override. Require wrapper exit `0` plus normalized `AUTOFIX_STATUS=ok` before the SKILL `ok` branch; add a harness assertion that false-ok stdout reports `failed`, not `ok`.
  - From dyn-design-wrapper-output.txt: Either fail closed before printing stdout (run append first, then print normalized KVs), or use the operator-cancel pattern (`|| true`) plus a follow-up `AUTOFIX_STATUS=failed` re-emission when append does not succeed. Extend `test-design-step-validator-autofix.sh` with an append-failure stub case.


