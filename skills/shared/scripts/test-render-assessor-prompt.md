# test-render-assessor-prompt.sh

Offline regression harness for `render-assessor-prompt.sh`.

Invokes the renderer against isolated plan/feature fixtures, asserts the output
contains the required `ASSESSMENT:` / `REASONING:` / `QUALIFICATIONS:` grammar
plus the inlined original / previous / current plans, and verifies missing
inputs fail non-zero.
