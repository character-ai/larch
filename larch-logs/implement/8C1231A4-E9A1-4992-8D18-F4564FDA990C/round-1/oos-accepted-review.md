### OOS_1: correctness: python/implement_dispatch.py:1412,1584,1640
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Three _append_warning calls still omit - / bold-bullet prefix so exec_issue_detail drops them from final summary Warnings at 1412/1584/1640 are stored in execution-issues.md but absent from ## Exec Issues and Warnings and under-counted in the header — same class as the 614EEA92 path-only regression Reformat to single-line bold bullets like lines 1646/1650
- **Suggested revision**: Address the concern above.


### OOS_2: correctness: python/design_postplan.py:91
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] _self_log_check_size_failure hardcodes site design Step 2b.5 but runs from postplan_emit_main (Step 2b) Check-size failures on the drafter postplan path appear in the final summary as Step 2b.5 warnings Pass the actual site (e.g. design Step 2b) via parameter
- **Suggested revision**: Address the concern above.


### OOS_3: risk-integration: python/implement_dispatch.py:1412,1584,1640
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Three _append_warning call sites still omit the - ** bold-bullet prefix required by exec_issue_detail parsing Git-probe skip, plan-read failure, and Codex nonzero-exit salvage warnings are written to execution-issues.md but dropped from the enriched final-summary Warnings list Reformat remaining _append_warning entries to the same - **Step …**: description shape used at 1646/1650
- **Suggested revision**: Address the concern above.


### OOS_4: correctness: python/implement_dispatch.py:1375-1376
- **Reviewer**: codex-specialist-edge-cases-output.txt
- **Concern**: [important] _append_warning still allows non-bullet warning entries, while the final-summary detail parser only renders bullet entries. When the working-tree touched-path probe fails, python/implement_dispatch.py:1640 appends a plain Step 7a.1 warning that remains in execution-issues.md but is omitted from the rendered Warnings detail block. Normalize warning entries in _append_warning or convert every implement_dispatch warning caller to the - **label**: detail format.
- **Suggested revision**: Address the concern above.


### OOS_5: risk-integration: python/implement_dispatch.py:1375-1650
- **Reviewer**: codex-specialist-testing-output.txt
- **Concern**: [important] _append_warning still writes several plain non-bullet warning entries, while final-summary detail parsing only records bullet lines. When plan-file read fails, the launcher exits nonzero after writing a manifest, or git touched-path probes fail, execution-issues.md can contain a warning that is omitted from the detailed Warnings block. Normalize _append_warning or convert all callers to bold-bullet entries, and add a final-summary parser regression for one of these warning paths.
- **Suggested revision**: Address the concern above.


