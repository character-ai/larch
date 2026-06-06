### OOS_1: [OUT_OF_SCOPE] risk-integration
- **Reviewer**: dyn-cli-contracts-output.txt
- **Concern**: - **risk-integration** `scripts/implement-bootstrap-invoke.md:11` — The section heading still says “caller must export” while the table now documents self-derivation; that mismatch can push operators to keep hand-setting `CLAUDE_PLUGIN_ROOT` from the wrong tree (the #3448 ship-driver skew pattern), even though `scripts/implement-bootstrap-invoke.sh:32-36` correctly derives from `$0` when unset.
- **Suggested revision**: Address the concern above.


### OOS_2: [OUT_OF_SCOPE] code-quality
- **Reviewer**: dyn-cli-contracts-output.txt
- **Concern**: - **code-quality** `scripts/append-tool-failure.sh` — Sibling helper still omits a `USAGE=` synopsis on `fail_usage`; only `append-execution-issue.sh` gained one in this branch (#2679 follow-up territory).
- **Suggested revision**: Address the concern above.


