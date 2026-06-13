### OOS_1: [OUT_OF_SCOPE] risk-integration — `test-design-structure.sh` does not pin new breadcrumb / Step-3 contract
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt
- **Severity**: latent
- **Concern**: `scripts/test-design-structure.sh` still pins `twice-per-wait reviewer status cadence` and `END THE TURN`, but not the new plain breadcrumb literals (`⏳ 5c:`, `⏳ final-summary:`), absence of `permitted breadcrumb/status table`, Step-3-only scoping, or removal of universal immediate-background table wording. Plan relied on manual greps during implement verification; harness omission does not block stated acceptance criteria, but CI would not block regressions of this UX fix.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Add harness checks for the new breadcrumb strings and zero hits on the old universal phrasing.
  - From cursor-specialist-testing-output.txt: Add `contains` / `! grep -Fq` pins for `each immediate-background wait`, `⏳ 5c: writing plan to GitHub`, and `⏳ final-summary: writing final summary` if you want CI to block regressions of this UX fix.


