## Goal
Implement issue #4935: [IMPLEMENTING] [Bug] /implement terminal: _output_file_success false-positive on reviewer prose mentioning NOT_SUBSTANTIVE (transient-infra at 5).

## Implementation Plan
## Report metadata
- **Report kind**: `terminal-failure`
- **Failure class**: `transient-infra`
- **Step**: `5`
- **Bail reason**: `redacted`
- **Run ID**: `140E920E-31B5-4023-A6FA-31E3EC7654E9`
- **Branch**: `unknown`
- **PR URL**: `unknown`

## Root-cause finding

verdict=larch-defect
confidence=high
summary=_output_file_success false-positive on reviewer prose mentioning NOT_SUBSTANTIVE

`_output_file_success` in `python/review_pipeline.py:1501-1505` uses
`re.search(r"(^|[^A-Z_])NOT_SUBSTANTIVE([^A-Z_]|$)", text)` to determine
whether a reviewer output file represents a valid (non-failed) reviewer slot.
This regex fires on any occurrence of NOT_SUBSTANTIVE in the text — including
prose in reviewer findings that discuss the NOT_SUBSTANTIVE concept.

Observed behavior (run 140E920E, round 2): All 4 static reviewer slots
returned STATUS=OK in collector-results.env. However, each raw output file
contained NOT_SUBSTANTIVE in finding prose. The threshold checker's
--reviewer-output-files loop called _output_file_success on each file, returned
False, and downgraded all 4 collector-OK slots to ERROR. With 3/4 static slots
failed, THRESHOLD_OK=false and REVIEW_CORE_STATUS=panel-failed.

Why this happened here: PR #4891 fixes NOT_SUBSTANTIVE classification in
python/research_eval.py and python/agents.py. Reviewers correctly analyzed this
code and mentioned NOT_SUBSTANTIVE in their findings. The heuristic was not
designed for PRs that discuss NOT_SUBSTANTIVE as subject matter.

Evidence:
- round-2/review-core-threshold.env: INTENDED_SLOTS=4, SUCCEEDED_SLOTS=1,
  FAILED_SLOTS=3, THRESHOLD_REASON=3 of 4 panel slots failed
- round-2/collector-results.env: all 6 slots STATUS=OK, EXIT_CODE=0
- cursor-specialist-correctness-output.txt line 11: "classified as NOT_SUBSTANTIVE"
- cursor-specialist-edge-cases-output.txt line 8: "slot is still classified NOT_SUBSTANTIVE"
- cursor-specialist-testing-output.txt: "no NOT_SUBSTANTIVE"
- codex-generic-output.txt line 1: "classified as NOT_SUBSTANTIVE"
- python/review_pipeline.py:1501-1505: _output_file_success uses substring
  regex, not a structured STATUS= line match

Fix direction: Narrow _output_file_success to match STATUS=NOT_SUBSTANTIVE as a
structured key=value line (e.g., re.search(r"^STATUS=NOT_SUBSTANTIVE$", text,
re.MULTILINE)), or skip the output-file downgrade for reviewers already
classified OK by the collector.



## Attempts

| Attempt | Class | Resume hint | Outcome | UTC |
|---|---|---|---|---|
| `1` | `transient-infra` | `step5-review` | `retry` | `unknown` |
| `2` | `transient-infra` | `step5-review` | `failed` | `unknown` |

## Test plan
(no test plan section in plan-file)
