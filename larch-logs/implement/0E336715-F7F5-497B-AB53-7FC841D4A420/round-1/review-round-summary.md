# Review Round 1

- Mode: `diff`
- Accepted findings: 2
- Rejected findings: 2
- Exonerated findings: 1
- Neutral findings: 0

## Accepted Findings

### FINDING_1: SKILL Step 1 implies wrong stdout key order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Step 1 prose chains keys with “then” (e.g. `RELEASE_ALREADY_LATEST=false` before `RELEASE_TAG=…`) in an order that does not match `promote-latest-release.sh` emission (e.g. tag and `RELEASE_WAS_*` prelude before `RELEASE_ALREADY_LATEST`, with `RELEASE_IS_*` only after the promotion path). Operators or naive stdout parsers may treat the doc order as ground truth and mis-validate or mis-diagnose healthy runs.
- **Suggested revision**: Reword Step 1 to match actual stdout order, or document required keys without a misleading sequential “then” chain.


### FINDING_2: Contract bullets overstate when `RELEASE_IS_*` appears on live runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: The machine-readable key list in `promote-latest-release.md` reads as if `RELEASE_IS_PRERELEASE` / `RELEASE_IS_LATEST` always appear on successful live runs; on the early-exit path (`RELEASE_ALREADY_LATEST=true`) they are absent. Integrations or readers assuming a fixed key superset after every live success may mis-parse or fail.
- **Suggested revision**: Qualify that `RELEASE_IS_*` are emitted only when `RELEASE_ALREADY_LATEST=false` (promotion path), or group keys by phase (pre-check vs post-`gh release edit`).


