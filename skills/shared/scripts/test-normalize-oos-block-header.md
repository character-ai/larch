# test-normalize-oos-block-header.sh Contract

Regression harness for `skills/shared/scripts/normalize-oos-block-header.sh` (canonical `### OOS_<seq>:` line-1 header rewrite; full contract in `normalize-oos-block-header.md`).

It pins: tagged `### FINDING_N: [OUT_OF_SCOPE]` and bare scope-drift `### FINDING_N:` normalization, `### OOS_N:` renumbering, title preservation, the `NR==1`-only guard (line-2 `### FINDING_N:` headings pass through), stdin mode, non-header line-1 pass-through, and `--seq` / `--block-file` validation exits.

Run with `bash skills/shared/scripts/test-normalize-oos-block-header.sh` or `make test-normalize-oos-block-header`.
