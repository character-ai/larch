### FINDING_1: set -e-safe wrapper capture under global `set -euo pipefail`
- **Reviewer(s)**: Cursor-Arch, Cursor-Pragmatic
- **Severity**: important
- **Concern**: A bare command substitution to `scout-plan-archetypes-wrapper.sh --filter-manifest` runs under `set -e` in `step2-implement.sh`. If the wrapper is missing, not executable, or exits non-zero before filter mode, the whole Step 2 dispatcher aborts instead of routing through the existing `normalize_coder_scout_manifest` fail-closed path (`write_empty_coder_scout_manifest` / `missing-or-invalid`).
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Mirror launch-codex-drafter.sh:275: capture with || true (or an explicit if ! capture), then return non-zero only when input is missing or parsed SCOUT_STATUS=parse-failed; never let wrapper exit abort materialize_external_coder_scout.
  - From Cursor-Pragmatic: Document the launch-codex-drafter.sh pattern: capture stdout with 2>/dev/null and || true, parse SCOUT_STATUS, validate output file shape, then return 1 on parse-failed or missing contract without aborting step2-implement.sh


### FINDING_2: Pin `normalize_coder_scout_manifest` to SCOUT_STATUS contract, not wrapper exit or loose output heuristics
- **Reviewer(s)**: Cursor-Arch, Cursor-Innovation, Cursor-Pragmatic, Cursor-dyn-stdout-contract, Cursor-dyn-single-source-filter
- **Severity**: important
- **Concern**: The plan’s failure-mode spec is ambiguous versus the established `launch-codex-drafter.sh` / `scout-plan-archetypes-wrapper.sh --filter-manifest` contract. `--filter-manifest` always exits 0 (including on `SCOUT_STATUS=parse-failed`, which still writes valid `{"archetypes":[]}`). Gating on wrapper exit code, missing `SCOUT_STATUS`, or “unless output clearly valid” heuristics can accept unfiltered/invalid sidecars as `SCOUT_CODER_STATUS=ok`, or reject valid all-reserved (`SCOUT_STATUS=empty`) manifests as `missing-or-invalid`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Arch: Pin normalize success to the launcher contract: missing/non-readable input → non-zero; captured SCOUT_STATUS=parse-failed → non-zero; otherwise require readable output with jq .archetypes | type == array, including SCOUT_STATUS=empty after reserved/cap filtering; treat SCOUT_CODER_STATUS=ok for empty arrays.
  - From Cursor-Innovation: Mandate non-zero normalization when SCOUT_STATUS is empty or parse-failed; require readable .archetypes array; remove the unless-clearly-valid success escape hatch
  - From Cursor-Pragmatic: State explicitly that filter mode exit code is not authoritative; return non-zero only when SCOUT_STATUS=parse-failed (or input missing), and return zero for SCOUT_STATUS=ok or empty; mirror launch-codex-drafter.sh status parsing
  - From Cursor-dyn-stdout-contract: Mirror scripts/launch-codex-drafter.sh:275-277: capture stdout, awk SCOUT_STATUS, return non-zero only on parse-failed; treat ok and empty as success; drop the failure-modes unless-output-clearly-valid escape hatch
  - From Cursor-dyn-single-source-filter: State filter-mode wrapper exit is always 0; branch only on captured SCOUT_STATUS=parse-failed vs non-parse-failed (match scripts/launch-codex-drafter.sh:275-277)
  - From Cursor-dyn-single-source-filter: List ok and empty as success; only parse-failed is failure (mirror scout-plan-archetypes-wrapper.sh:224-230)


### FINDING_3: Test harness missing `SCOUT_STATUS=empty` all-reserved success path
- **Reviewer(s)**: Cursor-Requirements
- **Severity**: important
- **Concern**: The testing strategy omits the `SCOUT_STATUS=empty` success path after wrapper delegation. The plan requires all rows filtered to keep `SCOUT_CODER_STATUS=ok` and treat only `SCOUT_STATUS=parse-failed` as normalization failure; Test 13a only covers partial filter (reserved slug plus one valid slug). Mis-handling empty as failure would regress to `missing-or-invalid` and break the documented edge case.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Requirements: Add a focused Test 13a variant (or extend 13a-scout) where the stub writes only reserved plan-review slugs (e.g. requirements), assert normalized scout-coder-manifest.json has zero archetypes, STATUS=complete, and SCOUT_CODER_STATUS=ok


### FINDING_4: Test harness missing negative assertions for wrapper stdout leakage into dispatcher envelope
- **Reviewer(s)**: Codex-Requirements, Cursor-dyn-stdout-contract, Codex-dyn-stdout-contract
- **Severity**: important
- **Concern**: When `--filter-manifest` runs (e.g. Test 13a with a reserved slug, or Test 13a-scout-qa on parse-failed), the wrapper emits `WARN`, `SCOUT_STATUS`, `SCOUT_MANIFEST`, and `SCOUT_ARCHETYPE_COUNT` on stdout. If `normalize_coder_scout_manifest` fails to capture/suppress that stdout, planned positive assertions can still pass while Step 2 regresses its stdout envelope contract.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Codex-Requirements: Extend Test 13a to assert dispatcher output does not contain wrapper-only KVs such as ^SCOUT_STATUS=, ^SCOUT_MANIFEST=, ^SCOUT_ARCHETYPE_COUNT=, or reserved-slug WARN lines.
  - From Cursor-dyn-stdout-contract: Mirror scripts/launch-codex-drafter.sh:275-277: capture stdout, awk SCOUT_STATUS, return non-zero only on parse-failed; treat ok and empty as success; drop the failure-modes unless-output-clearly-valid escape hatch
  - From Codex-dyn-stdout-contract: Add negative assertions in both Test 13a and Test 13a-scout-qa that OUT lacks wrapper-owned lines such as ^WARN=, ^SCOUT_STATUS=, ^SCOUT_MANIFEST=, and ^SCOUT_ARCHETYPE_COUNT=



