# test-review-design-step3-loop.sh

Regression harness for `review-design-step3-loop.sh`, the script-internal `/design` Step 3 round loop. Coverage includes terminal envelopes, bail-outs, phase resume, postplan routing, dedup restore, CR/LF sanitization before envelope emission, omission of invalid multiline scope anchors, merge-fallback sanitization, omission of sanitized-empty merged continue reasons, and visible result-env write failure warnings. The primary contract lives in `review-design-step3-loop.md`; this file exists to satisfy the script sibling rule.
