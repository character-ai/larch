## Proposed Design Outline

### Goals
- Append a detail block to `/design` and `/implement` final summaries listing each unique exec issue and warning by label (collapsed duplicates with ×N count).
- Include a one-sentence LLM-generated materiality assessment per unique entry.

### Non-goals
- No changes to how `execution-issues.md` is written or what it contains during a run.
- No LLM assessment for historical/archived summaries.
- No real-time streaming of assessments; assessment runs only at final-summary time.

### Approach sketch
- New shared module `python/exec_issue_detail.py`: parse `execution-issues.md` (and ndjson fallback) for bold labels; collapse duplicates; call Claude Haiku in one batched subprocess to generate assessments; format the detail block.
- `python/design_summary.py`: after `invoke_render` + `review_phase_detail.append_review_phase_detail`, call the new module and append the detail block to `final-summary.md` (and to `body` before write/stdout).
- `python/final_report.py`: same treatment after `body` is assembled.
- Graceful degradation: on LLM timeout/failure, show labels without assessments.

### Surfaces in scope
- `python/exec_issue_detail.py` (new)
- `python/design_summary.py`
- `python/final_report.py`
- `python/test_exec_issue_detail.py` (new)

### Open questions
- None.
