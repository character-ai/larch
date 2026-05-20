### FINDING_5: correctness: skills/review-and-fix/scripts/test-review-and-fix.sh:10-20
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New --section argv loop treats unknown tokens as ignorable via default shift. Typo or stray argv leaves SECTION empty so dispatch+convergence both run and can pass, hiding a miswired Makefile or manual command. Fail on unknown arguments or stop parsing at first non-option token so mis-invocations exit non-zero.
- **Suggested revision**: Address the concern above.


