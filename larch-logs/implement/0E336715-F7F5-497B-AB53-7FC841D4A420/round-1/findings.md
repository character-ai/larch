Here is the normalized structured finding list after merging duplicate concerns and ordering by first-seen distinct issue.

```text
### FINDING_1: SKILL Step 1 implies wrong stdout key order
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-edge-cases-output.txt, cursor-specialist-plan-fidelity-output.txt
- **Concern**: Step 1 prose chains keys with “then” (e.g. `RELEASE_ALREADY_LATEST=false` before `RELEASE_TAG=…`) in an order that does not match `promote-latest-release.sh` emission (e.g. tag and `RELEASE_WAS_*` prelude before `RELEASE_ALREADY_LATEST`, with `RELEASE_IS_*` only after the promotion path). Operators or naive stdout parsers may treat the doc order as ground truth and mis-validate or mis-diagnose healthy runs.
- **Suggested revision**: Reword Step 1 to match actual stdout order, or document required keys without a misleading sequential “then” chain.

### FINDING_2: Contract bullets overstate when `RELEASE_IS_*` appears on live runs
- **Reviewer(s)**: cursor-specialist-structure-output.txt, cursor-specialist-security-output.txt
- **Concern**: The machine-readable key list in `promote-latest-release.md` reads as if `RELEASE_IS_PRERELEASE` / `RELEASE_IS_LATEST` always appear on successful live runs; on the early-exit path (`RELEASE_ALREADY_LATEST=true`) they are absent. Integrations or readers assuming a fixed key superset after every live success may mis-parse or fail.
- **Suggested revision**: Qualify that `RELEASE_IS_*` are emitted only when `RELEASE_ALREADY_LATEST=false` (promotion path), or group keys by phase (pre-check vs post-`gh release edit`).

### FINDING_3: [OUT_OF_SCOPE] Dry-run contract omits some printed keys
- **Reviewer(s)**: cursor-specialist-structure-output.txt
- **Concern**: The dry-run documentation does not list `RELEASE_REPO` and `RELEASE_PUBLISHED_AT` even though the script prints them before exit in dry-run mode, so enumerating keys from the doc alone is incomplete.
- **Suggested revision**: If tightening dry-run documentation is desired, extend the dry-run bullet to include those keys (or explicitly scope the dry-run key list); treat as optional follow-up.

### FINDING_4: Correctness review — no implementation defects reported
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Concern**: Reviewer reports that the script guard (post–dry-run live path), dry-run behavior (`RELEASE_ALREADY_LATEST` not printed under `--dry-run`), documentation updates, and the noted run-log diff align with the plan and feature description, with no contradiction flagged.
- **Suggested revision**: None (informational).

### FINDING_5: No automated coverage for early-exit / no-edit path
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: No harness or CI assertion covers the new “already latest” early-exit branch or absence of `gh release edit`; shellcheck-only safety means a regression in comparisons or guard logic could ship unnoticed.
- **Suggested revision**: Add an offline harness with mocked `gh`/`jq` or fixture JSON plus a Makefile/CI target, or explicitly document that this behavior is manual-only if that is acceptable.

### FINDING_6: Manual checks from plan not evidenced in the patch
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Plan-listed manual steps (e.g. `relevant-checks`, `bash -n`) are not verifiable from the diff alone; reviewers cannot confirm they were run from the patch.
- **Suggested revision**: Rely on PR CI status at merge time, or attach evidence in the PR description if process requires patch-visible proof.
```
