### FINDING_10: [OUT_OF_SCOPE] Bash ship finalize writer still emits unquoted values
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt, dyn-python-shell-parity-output.txt
- **Severity**: latent
- **Concern**: `scripts/ship-pr.sh` still writes raw `KEY=value` finalize state while restore/Python paths now quote values, leaving mixed formats and unsafe sourcing for special characters. Reviewers marked this as pre-existing or outside this branch.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.
  - From dyn-python-shell-parity-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_11: [OUT_OF_SCOPE] Static phased Codex sidecar fixtures are incomplete
- **Reviewer(s)**: cursor-specialist-edge-cases-output.txt
- **Severity**: nit
- **Concern**: Phased static Codex `.json` and `.cap-hit` sidecars lack explicit fixtures even though broad allows include them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-edge-cases-output.txt: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated


### FINDING_13: [OUT_OF_SCOPE] Final-report reader strips quotes without unescaping embedded apostrophes
- **Reviewer(s)**: dyn-bash-state-io-output.txt, dyn-python-shell-parity-output.txt
- **Severity**: latent
- **Concern**: `write-final-report.sh` only removes outer single quotes and does not reverse POSIX shell escaping for embedded apostrophes, so quoted finalize-state fields containing `'` can be decoded incorrectly.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Reuse the same unescape path as `implement-finalize.sh` (`unquote_state_value` / `sed "s/'\\\\''/'/g"`) or call a small shared helper instead of the naive awk `substr()` unquote; add a harness case with an embedded apostrophe in a finalize-state field.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_15: [OUT_OF_SCOPE] Dynamic Codex matcher appears correctly ordered in this branch
- **Reviewer(s)**: dyn-bash-state-io-output.txt, dyn-python-shell-parity-output.txt, dyn-ci-toolchain-output.txt
- **Severity**: nit
- **Concern**: Multiple reviewers reported no defect in the scoped dynamic Codex matcher ordering and negative fixture coverage.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Address the concern above.
  - From dyn-python-shell-parity-output.txt: Address the concern above.
  - From dyn-ci-toolchain-output.txt: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected


### FINDING_16: [OUT_OF_SCOPE] Finalize-state readers are split between quoted and raw parsers
- **Reviewer(s)**: dyn-bash-state-io-output.txt
- **Severity**: latent
- **Concern**: `ship.py` reads finalize state through the quoted-aware parser while `run_logs.py` uses a raw key-value reader, creating an architecture split underlying the quoted finalize-state regression.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-bash-state-io-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_22: [OUT_OF_SCOPE] Dynamic retention comment overstates independence from broad output globs
- **Reviewer(s)**: dyn-fd-contract-output.txt
- **Severity**: latent
- **Concern**: The explicit dynamic Codex allow pins scoped shapes, but retention for future or retry-shaped dynamic outputs still relies on the broad `*-output*` allow. The inline comment may overstate isolation.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-contract-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_23: [OUT_OF_SCOPE] Python quiet logs append while bash quiet logs truncate
- **Reviewer(s)**: dyn-fd-contract-output.txt
- **Severity**: nit
- **Concern**: Python quiet logs are append-only, unlike bash quiet logs, so re-invocation or crash retry can accumulate multiple runs in one log file.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-fd-contract-output.txt: Address the concern above.


Vote tally: YES=2 NO=0 EXON=1 JUDGE_ERROR=0 Result=accepted


### FINDING_25: [OUT_OF_SCOPE] OOS disposition finalize-state fallback does not unquote values
- **Reviewer(s)**: dyn-ci-toolchain-output.txt
- **Severity**: latent
- **Concern**: `oos-disposition-checkpoint.sh` fallback reads finalize-state values with `grep`/`cut` and no unquoting, so quoted fallback keys could mis-route the gate if ship-pr state lacks them.
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-ci-toolchain-output.txt: Address the concern above.

Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


### FINDING_6: [OUT_OF_SCOPE] Run-log publication still relies on scrubbers for secret safety
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: important
- **Concern**: Committed run logs remain dependent on pattern-based redaction before flush; dynamic Codex outputs can contain sensitive content if scrubbers miss a family. The reviewer marked this as pre-existing.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.


Vote tally: YES=3 NO=0 EXON=0 JUDGE_ERROR=0 Result=accepted


