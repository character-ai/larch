# test-revise-plan-with-waterfall.sh

Cross-tree harness for `python/cli.py plan revise-waterfall`.
The primary behavior contract lives in
`python/plan_quality.py`.

Cases cover Codex win, Cursor promotion, Claude fallback, no-patch failure,
apply failure, emit-plan failure, Codex absence, argv defects, canonical-plan
invariant, heading-loss revert, prompt-source assertions, unified-diff rejection
when optional `diff_added` / `diff_deleted` / `mechanical_churn` trailers are
dropped, and file-replacement preservation of those trailers above final
`diff_lines:`.

Makefile target: `test-revise-plan-with-waterfall`.
