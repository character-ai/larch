### FINDING_6: risk-integration: skills/design/scripts/test-run-step3-review.sh:255-275
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Missing-plan tests discard stdout; warning emission not asserted Renderer could stop emitting the warning while sentinel logic stays correct (or vice versa); operator loses the intended re-warn signal Capture stdout and assert_contains the exact missing-plan warning on first call
- **Suggested revision**: Address the concern above.


