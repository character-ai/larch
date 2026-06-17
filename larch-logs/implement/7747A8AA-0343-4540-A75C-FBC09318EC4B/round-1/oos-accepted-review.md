### OOS_1: correctness: python/review_and_fix.py:1325-1344
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Cursor vendor timing is recorded as complete on returncode==0 before verifying coder output exists. Cursor exits 0 but writes no coder-cursor.log and no usable stdout; _run_coder_cursor returns False yet timing row has status=complete, so final Gantt shows a successful cursor/apply bar with no actual apply. Move _record_coder_vendor_task after success checks, or record signal/failed when output validation fails despite returncode 0.
- **Suggested revision**: Address the concern above.


