# Review Round 2

- Mode: `diff`
- 4 accepted, 2 rejected (0 neutral)

## Accepted Findings

### FINDING_1: Stale retired voting-script references remain in contract docs
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-migration-parity-output.txt
- **Severity**: important
- **Concern**: Tracked docs and skill contracts still reference retired `write-tally.sh` and `lib-vote-tally.sh` paths after the Python voting cutover. This can fail `make lint-retired-scripts` and mislead maintainers about the live voting surface.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, codex-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-testing-output.txt, dyn-migration-parity-output.txt: Address the concern above.


### FINDING_18: `_plain_diagnostic` ignores `LARCH_QUIET_DISABLE`
- **Reviewer(s)**: dyn-io-stream-routing-output.txt
- **Severity**: latent
- **Concern**: `_plain_diagnostic` treats inherited quiet variables as active without checking `LARCH_QUIET_DISABLE`. That can route warnings to fd 4 even when quiet routing was explicitly disabled.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-io-stream-routing-output.txt: Address the concern above.


### FINDING_4: Voting CLI consumers lack fail-fast `cli.py` existence guards
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-migration-parity-output.txt, dyn-shell-cutover-safety-output.txt
- **Severity**: important
- **Concern**: Several hot-path voting consumers define `CLI="$PLUGIN_ROOT/python/cli.py"` but do not validate that it exists before invoking `python3 "$CLI" voting ...`. Broken installs can fail mid-dispatch or mid-tally with opaque Python errors instead of a clear preflight failure.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, dyn-migration-parity-output.txt, dyn-shell-cutover-safety-output.txt: Address the concern above.


### FINDING_5: `review-and-fix.sh` write-tally command lacks override/default gates
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-shell-cutover-safety-output.txt
- **Severity**: important
- **Concern**: `WRITE_TALLY_CMD` does not fail fast when `REVIEW_AND_FIX_WRITE_TALLY_SH` is non-executable or when the default `python/cli.py` path is missing. A bad setup can fail late, skip tally output, or produce generic flush-time errors.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt, cursor-specialist-edge-cases-output.txt, codex-specialist-testing-output.txt, dyn-shell-cutover-safety-output.txt: Address the concern above.


