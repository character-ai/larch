## Goal
Implement issue #4994: [IMPLEMENTING] [BUG] Cursor plan-review reviewers dropped NOT_SUBSTANTIVE on valid TSV findings.

## Implementation Plan
## Summary

Cursor plan-review reviewers in `/design` Step 3 are frequently dropped as `NOT_SUBSTANTIVE` ("structured records not found after repair") even when they produce real, well-reasoned findings. The cause is two compounding format defects in Cursor's TSV output that the structured-record validator (`python/research_eval.py`) rejects: (1) the `schema_version` column is filled with a per-row index (1, 2, 3...) instead of the literal constant `1`, and (2) `focus_area` is set to `completeness`, which is not in the validator's allowed enum. Together they drop every Cursor row, so the slot's findings never reach the voting ballot. This wastes Cursor reviewer spend and degrades the panel. Design output was unaffected in the observed run only because of panel redundancy.

## Original report

In `/design` Step 3 plan review, Cursor reviewer slots are frequently dropped with `FAILURE_REASON="structured records not found after repair"` even though the reviewer produced real, well-reasoned findings. Observed 3x in one run (design run `D0349E49` on issue #4971): `cursor-plan-innovation` round 1, `cursor-plan-requirements` rounds 2 and 4. The dropped findings were correct and valuable but never reached the voting ballot, wasting Cursor spend and degrading the panel. Design quality survived only because of panel redundancy: Codex and correctly-formatted Cursor archetypes independently re-raised the same concerns (orphan `test-trailer-helpers.sh`, stale `agent-lint.toml` G004 pins, byte-level `PWD` clone-tag sanitization, seed/ship prefix parity), and all of them landed in the final plan.

Root cause (verified empirically): the structured-output validator `_validate_structured_tsv` in `python/research_eval.py` (invoked by `python/collect_results.py` `_validate_structured` via `python3 cli.py eval validate-research-output --structured-reviewer-mode`, gated by `collect-results --structured-reviewer-validation`) rejects every Cursor data row because of two compounding defects. This is a recurring Cursor-vs-Codex output-conformance gap; Codex slots did not hit it in the same run. The plugin-cache 51.3.4 validator is byte-identical to the working tree, so it is not version skew.

A related but separate exec issue in the same run (the findings aggregator failing its own output validation and falling back to un-deduped findings) is intentionally out of scope for this issue.

## Reproduction scenario

Run the exact validator the collector calls, on a TSV that mimics Cursor's output (row index in column 1 and/or a `completeness` focus):

```bash
printf 'schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix\n1\tin_scope\timportant\tcompleteness\tfoo.py:1\twhat\tscenario\tfix\n2\tin_scope\timportant\tcorrectness\tbar.py:2\twhat\tscenario\tfix\n' > /tmp/repro.txt
python3 python/cli.py eval validate-research-output --structured-reviewer-mode --write-structured /tmp/repro.tsv /tmp/repro.txt
echo "RC=$?"   # prints: structured records not found after repair  /  RC=5
```

Observed during the live run on captured Cursor output: RC=5, with a per-row replay showing `REJECT focus='completeness'`, `REJECT schema='2'`, `REJECT schema='3'`, `kept rows = 0`. A row whose first column is `1` and whose `focus_area` is a valid enum value (e.g. `correctness`) does pass, confirming the two defects are the cause.

## Expected behavior

A Cursor reviewer that emits substantive, on-format findings should have those findings ingested into the ballot. The format contract the reviewer is given should be unambiguous enough that Cursor does not (a) treat column 1 as a row counter, or (b) emit a `focus_area` outside the validator's allowed set. Minor, harmless formatting deviations (a row index in column 1) should not silently discard an entire slot's findings.

## Observed behavior

Every Cursor data row is rejected by `_validate_structured_tsv`, so `validate_structured_reviewer_output` returns exit 5 ("structured records not found after repair"), the collector marks the slot `NOT_SUBSTANTIVE`, and the slot is dropped (no ns-retry, no fallback — this is terminal per the collector contract). The reviewer's real findings are lost from voting. Three Cursor slots were dropped this way in one run.

## Root cause analysis

The validator `_validate_structured_tsv` (in `python/research_eval.py`) keeps a data row only when ALL of these hold: `schema_version == "1"`, `scope in {in_scope, out_of_scope}`, `severity in {blocking, important, nit, latent}`, and `focus_area in {code-quality, risk-integration, correctness, architecture, security}`. Cursor's output violates two of these on essentially every row:

1. **`schema_version` used as a row index.** Cursor writes `1`, `2`, `3`, ... in the first column (treating it like a row number). The validator requires the literal `1` on EVERY row, so all rows after the first are rejected (`schema='2'`, `schema='3'`). The reviewer prompt's data-row template is `1\t<scope>\t<severity>\t...`, which reads like a counter seed rather than a fixed constant, and the prompt never says column 1 stays `1` on every row.

2. **`focus_area = completeness` is not in the allowed enum.** The reviewer prompt enumerates the allowed `scope` and `severity` values but does NOT enumerate the allowed `focus_area` values, so Cursor invented `completeness`. The only row that survives defect #1 (the one numbered `1`) was, in all three observed failures, a `completeness` row — so it also gets rejected.

Net: 0 valid rows -> `_validate_structured_tsv` returns `""` -> exit 5 -> slot dropped. Both defects must be addressed (fixing only one still loses most rows). Codex follows the contract, so this is specifically a Cursor conformance gap that the prompt and/or validator should be hardened against.

## Evidence

- `python/research_eval.py`: `_ALLOWED_SEVERITIES = {blocking, important, nit, latent}`; `_ALLOWED_FOCUS = {code-quality, risk-integration, correctness, architecture, security}`; `_STRUCTURED_HEADER = "schema_version\tscope\tseverity\tfocus_area\tlocation\twhat\tscenario_or_breakage\tsuggested_fix"`. In `_validate_structured_tsv` the per-row guard is `if schema != "1" or scope not in {...} or severity not in _ALLOWED_SEVERITIES or focus not in _ALLOWED_FOCUS: continue`, and `if len(out) <= 1: return ""`.
- `python/collect_results.py` `_validate_structured` runs `cli.py eval validate-research-output --structured-reviewer-mode --write-structured <sidecar> <reviewer_file>`; on non-zero it sets `STATUS=NOT_SUBSTANTIVE` with `derive_ns_retry_reason(..., "structured")`. The collector contract drops `NOT_SUBSTANTIVE` (no ns-retry/fallback for result-quality failures).
- `python/rendering.py` (`render plan-review`, reviewer TSV output contract, around the `schema_version\tscope\t...` block): the data-row example is `1\t<scope>\t<severity>\t<focus_area>\t...`, and the surrounding prose enumerates allowed `scope`/`severity` values but not the allowed `focus_area` values.
- `python/test_research_eval.py` already asserts the "structured records not found after repair" message and exercises a `schema_version` guard path, so this validator is covered and a regression test can extend it.
- Captured failures in design run `D0349E49` (`execution-issues.md`, External Reviewer Issues): three `collect-results cursor NOT_SUBSTANTIVE ... FAILURE_REASON=structured records not found after repair` records for rounds 1, 2, 4; the embedded reviewer output shows correct headers/tabs but `schema_version` = 1/2/3 and `focus_area` = `completeness`.
- Empirical replay of the exact validator on the captured rows returned RC=5 with `kept rows = 0`.
- Verified against latest `origin/main` (commit `d8e3d4779`): `_ALLOWED_FOCUS` still excludes `completeness`, the `schema_version == "1"` row guard is unchanged, and the `render plan-review` prompt still enumerates only `scope` and `severity` (not `focus_area`). No fix has landed; the defect is current on main.
- Related but distinct prior issues, all CLOSED: #4790 (collector `\x1f`-vs-`KEY=VALUE` parse bug — all findings dropped) and #4885 / #4886 / #4891 (Cursor *zero-findings* `{"no_issues_found": true}` sentinel salvage tolerating a preamble). Those fixed the no-issues-sentinel and collector-parse paths. This issue is the still-open **findings-bearing** row-validation case (`_validate_structured_tsv` `schema_version` / `focus_area` guards) that #4790's comments explicitly deferred as a secondary "parity audit / hardening" item. Not a duplicate.

## Affected files

- `python/research_eval.py` — the validator (`_validate_structured_tsv`, `validate_structured_reviewer_output`, `_ALLOWED_FOCUS`, `_STRUCTURED_HEADER`). Owns the accept/reject decision and the allowed enums.
- `python/rendering.py` — `render plan-review` reviewer prompt scaffold and the TSV output-contract text shown to Cursor/Codex. Where prompt hardening (work item 1) lands.
- `python/collect_results.py` — `_validate_structured`, which maps validator exit 5 to `NOT_SUBSTANTIVE` and drops the slot. Relevant if any drop-vs-salvage policy change is considered.
- `python/test_research_eval.py` — existing coverage for the validator; regression tests for both fixes land here.

## Suggested fix(es)

Two numbered work items, one issue:

1. **(Primary, low-risk) Harden the Cursor plan-review reviewer prompt** in `python/rendering.py` (`render plan-review`). State explicitly that the first column is the LITERAL constant `1` (the `schema_version`) on EVERY row and is NOT a per-row counter, and explicitly enumerate the allowed `focus_area` values (`code-quality`, `risk-integration`, `correctness`, `architecture`, `security`) the same way `scope` and `severity` are already enumerated. Keep the example self-consistent with `_STRUCTURED_HEADER` in `python/research_eval.py`. Add a prompt-contract regression test.

2. **(Decision needed, then implement) Make `_validate_structured_tsv` more tolerant** so a well-formed finding is not silently dropped on a formatting technicality. Options to weigh in `/design`: ignore the exact value of column 1 for reviewer rows (a harmless row index should not reject the row), and/or map a small set of `focus_area` synonyms (e.g. `completeness` -> `code-quality`) or extend `_ALLOWED_FOCUS`. This is a strictness-vs-recall tradeoff. Whatever is chosen MUST preserve parity for the research-output path that shares this validator (the function is used by both `/research` output validation and plan-review reviewer validation), and must keep the `schema_version`-bearing JSON salvage guard behavior covered by `python/test_research_eval.py` intact. Add regression tests for the chosen behavior.

Item 1 is the high-value primary fix and is sufficient to stop the bleed; item 2 is defense-in-depth that reduces silent finding loss when a reviewer deviates.

## Open questions

- For item 2, should the validator relax the column-1 check, the `focus_area` enum, both, or neither (prompt-only fix)? This is the main design decision.
- Is the `focus_area` enum intentionally restricted to exactly those five values across both the `/research` and plan-review consumers, or has the finding taxonomy drifted (e.g. should `completeness` be a first-class focus area)?
- Should `NOT_SUBSTANTIVE` drops for result-quality (as opposed to launch failures) emit a louder/aggregated warning so silent reviewer loss is more visible during a run, instead of only landing in `execution-issues.md`?


## Additional occurrence — second run, `focus_area` defect in isolation

A second independent reproduction landed after this issue was filed, confirming the bug recurs across runs and issues (this issue's evidence was all from run `D0349E49` / #4971).

- **Run**: design run `C94E1D97-673E-43D9-97A9-82307B8A6A06` on issue #4972 (the `slack-issue-announce.sh` -> Python migration). Logs: `larch-logs/design/C94E1D97-673E-43D9-97A9-82307B8A6A06/`.
- **Drops**: 2 Cursor reviewer slots dropped `NOT_SUBSTANTIVE` (`FAILURE_REASON=structured records not found after repair`), both in round 1: `cursor-plan-arch` and `cursor-plan-pragmatic`. Both ran cleanly (exit 0, `completed`, 1276 / 1648 bytes of output).
- **The `focus_area` defect fired in isolation here.** Unlike `D0349E49` (multi-row output that tripped both the `schema_version` row-index defect and the `focus_area` defect), each of these two reviewers emitted exactly one finding row, numbered `1` (so the `schema_version == "1"` guard passed) with `focus_area=completeness` (so the `focus not in _ALLOWED_FOCUS` guard failed). That left only the header in `out`, so `len(out) <= 1` -> `_validate_structured_tsv` returned `""` -> exit 5 -> slot dropped. Real-world confirmation that work item 2's `focus_area` enum defect is independently sufficient to drop a slot, with the column-1 defect entirely absent. The `cursor-plan-pragmatic` output also appended a markdown numbered-list summary after the TSV row, which is harmlessly skipped (no tabs), so it did not contribute to the drop.
- **Cost of the silent drop.** Both dropped Cursor findings correctly flagged the single most material gap in the plan: the missing `### UPDATED: agent-lint.toml` S030 reachability-pin cleanup for the deleted `test-slack-issue-announce.{sh,md}` harness, which would have failed `make lint-retired-scripts` / `make lint` during `/implement`. The plan recovered the fix only because Codex (`Codex-Arch`, `Codex-dyn-Retirement Cleanup`, `Codex-dyn-Slack Parity`) independently re-raised the same concern. Panel redundancy again masked the loss; absent a conforming peer, the gap would have shipped into the plan.
- **Separate failure in the same run (not this bug, recorded for completeness).** This run also degraded to a 2/3 voter panel when the Codex voter (Voter 2) returned `EMPTY_OUTPUT` (exit 0, retried once via `codex-vote-output-retry.txt`, still empty, dropped). That is a transient voter-side failure unrelated to the `_validate_structured_tsv` row-validation defect tracked here.
- **Still current.** `python/research_eval.py` `_ALLOWED_FOCUS` (working tree and plugin-cache 51.3.4) still excludes `completeness`; no fix has landed as of this run.



## Additional occurrence — third run (issue #4967), plus a drop the two pinned defects do not explain

A third independent reproduction, on a different issue, confirms the bug keeps recurring. Two of the three drops match the pinned defects exactly. The third does NOT, and an empirical replay shows the fix as currently scoped would not recover it.

- **Run**: design run `FD971172-3DC4-4D78-83F2-4DB57339E873` on issue #4967 (`oos-file-conflict-deps.sh` -> Python union-find migration). Logs: `larch-logs/design/FD971172-3DC4-4D78-83F2-4DB57339E873/`.
- **Drops**: 3 Cursor reviewer slots dropped `NOT_SUBSTANTIVE` (`FAILURE_REASON=structured records not found after repair`), all clean runs (exit 0, `completed`): `cursor-plan-innovation` round 1 (3862 bytes), `cursor-plan-requirements` round 4 (3140 bytes), `cursor-plan-requirements` round 5 (1339 bytes).

**Two drops match the pinned defects:**

- `cursor-plan-requirements` round 4: row 1 `focus_area=completeness` (invalid enum) AND row 2 `schema_version=2` (row index). Both defects present, same as run `D0349E49`.
- `cursor-plan-requirements` round 5: single row, `schema_version=1`, `focus_area=completeness`. The focus_area defect in isolation, same shape as the `C94E1D97` / #4972 occurrence. (Output also appended a trailing `### N.` markdown summary, harmlessly skipped.)

**One drop is NOT explained by either pinned defect (third signature, empirically confirmed):**

- `cursor-plan-innovation` round 1 emitted 5 data rows. In the committed `execution-issues.md` capture, EVERY row has `schema_version=1` and a valid `focus_area` (`risk-integration`, `correctness` x3, `architecture`); all `scope` / `severity` values are valid too. By the documented `_validate_structured_tsv` guards all 5 rows should be kept, yet the slot was dropped (0 kept rows).
- **Empirical replay (current `origin/main`).** A faithful clean reconstruction of those rows (leading prose preamble, header, then 5 rows all `schema_version=1` with the captured valid focus_areas) PASSES: `python3 python/cli.py eval validate-research-output --structured-reviewer-mode --write-structured` returns RC=0 and keeps all 5 rows; the leading preamble is skipped correctly. A control row with `focus_area=completeness` still returns RC=5. So the captured-clean innovation rows would have passed; the real drop came from content NOT preserved in the markdown capture.
- **Most likely trigger**: an embedded literal tab or newline inside the long free-text fields (`what` / `scenario_or_breakage` / `suggested_fix`), which the innovation reviewer filled with multi-clause prose containing inline backticks and code-like snippets. An embedded tab adds phantom columns; an embedded newline splits the logical row into a fragment whose column 1 is prose (not `1`), failing the `schema_version == "1"` guard. Enough fragmentation drops every row to 0 kept. The raw reviewer file is gone (the `/design` tmpdir was cleaned at Step 6), so this could not be replayed on the exact bytes; the committed capture plus the clean-reconstruction replay are the evidence.
- **Implication for the fix**: neither work item as currently scoped recovers this case. Prompt hardening (item 1) and relaxing the column-1 / `focus_area` guards (item 2) do not touch field-content control characters. Item 2 should additionally make `_validate_structured_tsv` robust to embedded tabs/newlines inside the 8 expected fields: split into at most 8 columns and treat overflow as field content, or strip/escape control characters inside fields before the per-row guard. Open question 3 (instrument the validator to log the rejected line + reason) would have pinpointed this directly.

**Sibling exec issue recurred (still out of scope here).** This run also reproduced the round-1 findings-aggregator validation failure this issue scopes out: the Cursor-dispatched aggregator (`aggregator-dispatch.env` `ALL_OUTPUT_TOOLS=cursor`) failed its own output validation with an empty `aggregator-validate.stderr` and fell back to the pre-dedup findings. It remains untracked.

**Still current.** Control replay confirms `focus_area=completeness` still returns RC=5 on `origin/main`; no fix has landed.

## Test plan
(no test plan section in plan-file)
