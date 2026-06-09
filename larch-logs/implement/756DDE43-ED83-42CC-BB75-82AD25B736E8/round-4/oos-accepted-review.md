### OOS_10: [OUT_OF_SCOPE] Ship-pr migration-lint positive coverage is missing
- **Reviewer(s)**: dyn-migration-lint-regex-output.txt
- **Severity**: nit
- **Concern**: Existing ship-pr migration-lint tests are negative-only and do not prove a live `"$SCRIPT_DIR/resolve-repo.sh"` reference blocks retirement.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-migration-lint-regex-output.txt: Address the concern above.


### OOS_11: [OUT_OF_SCOPE] Phantom append failure diagnostics are re-appended without redaction
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Nested append failure diagnostics may include subprocess stderr containing secret-shaped values, then write them to `execution-issues.md` without redaction.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_12: [OUT_OF_SCOPE] Legacy bash CI log paths remain unredacted
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: latent
- **Concern**: Retained/deferred bash paths such as legacy `ship-pr.sh` and `gh-run-logs.sh` can still capture or forward unredacted CI tails. Reviewers marked this as pre-existing or deferred E1 work.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


### OOS_13: [OUT_OF_SCOPE] Hard cutover/deletion work is incomplete
- **Reviewer(s)**: codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt, dyn-migration-lint-regex-output.txt
- **Severity**: important
- **Concern**: Live runtime/docs/release/test paths still reference legacy bash helpers instead of the new `python/cli.py` verbs. This leaves a dual bash/Python surface, means new Python behavior may be unexercised by real workflows, and makes later deletion/manifest retirement unsafe until call sites, harnesses, docs, and `migrated-scripts.tsv` are completed.
- **Suggested revisions (informational for voters; coder decides)**:
  - From codex-specialist-security-output.txt, cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, codex-specialist-testing-output.txt, dyn-contract-parity-output.txt, dyn-migration-lint-regex-output.txt: Address the concern above.


