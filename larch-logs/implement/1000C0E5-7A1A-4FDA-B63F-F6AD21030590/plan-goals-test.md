## Goal
Preserve NS-retry first-pass reviewer output as a sidecar file before the mv overwrites it, mirroring the voter parse-retry sidecar pattern.

## Implementation Plan
Preserve cursor specialist NS-retry first-pass output as a sidecar before the mv overwrites it (parallel to #2396 for voters).


### Problem
When `collect-agent-results.sh` NS-retry succeeds, `RESULTS[IDX]` is updated to point to `NS_RETRY_OUTPUT`. The original `ORIG_OUTPUT` (first-pass) is excluded from the committed run-log by `larch-log.sh` (line 77: `cursor-specialist-*-output.txt` is explicitly excluded as an artifact to keep logs lean, while `cursor-specialist-*-output-ns-retry.txt` matches `*-output-*.txt` and IS committed). The first-pass content is therefore unrecoverable.

### Files to Modify

**1. `scripts/collect-agent-results.sh`** (lines 1241-1252)

In BOTH NS-retry success branches (structured and substantive), after validation succeeds and before updating RESULTS[IDX]:
- Compute `_ns_first_pass_sidecar` from `ORIG_OUTPUT`:
  ```bash
  case "$ORIG_OUTPUT" in
      *.txt) _ns_first_pass_sidecar="${ORIG_OUTPUT%.txt}-first-pass.txt" ;;
      *) _ns_first_pass_sidecar="${ORIG_OUTPUT}-first-pass" ;;
  esac
  ```
- Save first-pass: `if cp "$ORIG_OUTPUT" "$_ns_first_pass_sidecar" 2>/dev/null; then emit_breadcrumb "ns-retry: first-pass content preserved at $(basename "$_ns_first_pass_sidecar")" >&2; fi`
- Overwrite original with retry: `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"`
- For structured case: also move sidecar file:
  ```bash
  _ns_sidecar_ext="${STRUCTURED_SIDECAR##*.}"
  _ns_new_sidecar="${ORIG_OUTPUT}.${_ns_sidecar_ext}"
  mv "$STRUCTURED_SIDECAR" "$_ns_new_sidecar" 2>/dev/null || true
  STRUCTURED_SIDECAR="$_ns_new_sidecar"
  ```
- Update RESULTS[IDX] to use `$ORIG_OUTPUT` (not `$NS_RETRY_OUTPUT`)

**2. `scripts/larch-log.sh`** (line 92)

Add `*-output-first-pass.txt` to the explicit allow-list alongside `*-vote-output-first-pass.txt`. The sidecar would already be committed via `*-output-*.txt`, but explicit inclusion mirrors the voter pattern and documents intent.

**3. `scripts/test-collect-agent-results.sh`**

- Update existing C_NSR assertion: REVIEWER_FILE now points to ORIG_OUTPUT (not ns-retry path)
- Update existing C_NSS assertions: REVIEWER_FILE points to ORIG_OUTPUT; STRUCTURED_SIDECAR points to ORIG_OUTPUT.tsv (not ns-retry paths)
- Add C_NS_FP_SUCCESS: verify `-first-pass.txt` exists with first-pass content and ORIG_OUTPUT has retry content
- Add C_NS_FP_FAILURE: NS-retry fails (no sentinel), assert no `-first-pass.txt` created
- Add C_NO_RETRY_FP: substantive first-pass (no retry), assert no `-first-pass.txt` created

**4. `scripts/test-larch-log-write-round.sh`**

Add assertion that a file named `cursor-specialist-*-output-first-pass.txt` is included in the round-N commit set (passes `round_artifact_included`).

**5. `scripts/collect-agent-results.md`** — update to document first-pass sidecar behavior

**6. `scripts/larch-log.md`** — update allow-list documentation

### Testing Strategy
Run `make lint` / `bash scripts/test-collect-agent-results.sh` to verify the new tests pass. Verify `bash scripts/test-larch-log-write-round.sh` passes.

## Test plan
(no test plan section in plan-file)
