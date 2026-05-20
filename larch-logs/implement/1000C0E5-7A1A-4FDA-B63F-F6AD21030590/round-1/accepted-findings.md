### FINDING_1: **Important** `risk-integration` [scripts/collect-agent-results.sh:1268](<OPERATOR_REPO_PATH>/scripts/collect-agent-results.sh:1268)  
- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` [scripts/collect-agent-results.sh:1268](<OPERATOR_REPO_PATH>/scripts/collect-agent-results.sh:1268)      Successful NS-retry output is now moved back onto `cursor-specialist-*-output.txt`, but [scripts/larch-log.sh:77](<OPERATOR_REPO_PATH>/scripts/larch-log.sh:77) still excludes that canonical specialist output from committed round logs. Concrete scenario: a cursor specialist first pass is `NOT_SUBSTANTIVE`, the NS retry succeeds with `NO_ISSUES_FOUND`, then `write-round` commits `cursor-specialist-*-output-first-pass.txt` but neither the promoted `cursor-specialist-*-output.txt` nor the old `*-ns-retry.txt` retry artifact, so the committed log preserves only the failed first pass and loses the successful retry transcript. Add an allow-listed final retry sidecar, keep a copy of the retry artifact under an included name before the `mv`, or otherwise update `larch-log.sh`/tests so both first-pass and successful retry content are recoverable.
- **Suggested revision**: Address the concern above.


### FINDING_11: code-quality: scripts/collect-agent-results.md:24-25
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Docs imply copy always succeeds Operators misread observability guarantees vs voter contract Add best-effort / stderr warning language consistent with dispatch-code-voters.md
- **Suggested revision**: Address the concern above.


### FINDING_14: code-quality: scripts/collect-agent-results.sh:1246-1267
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] NS-retry first-pass cp is silent on failure while retry mv still runs Full disk or EPERM on sidecar: first-pass is lost with no stderr warning (voter path uses larch_err) Add else branch with larch_err after failed cp; document best-effort in collect-agent-results.md like dispatch-code-voters.md
- **Suggested revision**: Address the concern above.


### FINDING_16: code-quality: scripts/test-collect-agent-results.sh:307-315
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] C_NS_FP_FAILURE comment describes sentinel absence; test uses missing .meta / no launch. Maintainers may misread which failure mode is pinned. Rewrite comment to match the fixture or add coverage for the described scenario.
- **Suggested revision**: Address the concern above.


### FINDING_17: correctness: scripts/collect-agent-results.sh:1246-1251
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] cp of first-pass to *-first-pass.txt swallows errors; mv overwrite still proceeds. cp can fail (disk full, RO FS); first pass is lost with no diagnostic while NS-retry is still treated as success. Fail loud or gate the mv/RESULTS update on successful preservation.
- **Suggested revision**: Address the concern above.


### FINDING_18: correctness: scripts/collect-agent-results.sh:1246-1251 scripts/collect-agent-results.sh:1265-1268
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] cp of first-pass to -first-pass.txt errors are swallowed; mv still overwrites ORIG_OUTPUT. cp fails (ENOSPC permission) mv overwrites orig; first-pass unrecoverable despite plan goal. Do not overwrite ORIG_OUTPUT if cp failed or fail the promotion.
- **Suggested revision**: Address the concern above.


### FINDING_19: correctness: scripts/collect-agent-results.sh:1246-1268
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Silent cp failure is followed by mv that overwrites ORIG_OUTPUT, destroying the only first-pass copy. Disk full or permission error on sidecar: cp fails, mv still runs; first-pass bytes are unrecoverable, worse than pre-change where first-pass often remained at ORIG_OUTPUT on disk. Require cp success (or temp+atomic publish) before mv; otherwise skip promotion and keep prior RESULTS row.
- **Suggested revision**: Address the concern above.


### FINDING_2: **correctness** [`scripts/collect-agent-results.sh:1246-1247`](scripts/collect-agent-results.sh:1246-1247) and [`scripts/collect-agent-results.sh:1265-1266`](scripts/collect-agent-results.sh:1265-1266) — `cp` errors are fully silent (`2>/dev/null`); on `cp` failure the subsequent `mv` still overwrites `ORIG_OUTPUT`, so the stated observability goal (“preserve first-pass”) is **best-effort only** with no stderr signal and no test coverage for the failure mode. **Suggested fix:** on `cp` failure, either skip the overwrite/`RESULTS` update, or surface a non-ignored diagnostic and treat as collector-side failure for that index.
- **Reviewer**: dyn-mv-atomicity-output.txt
- **Concern**: - **correctness** [`scripts/collect-agent-results.sh:1246-1247`](scripts/collect-agent-results.sh:1246-1247) and [`scripts/collect-agent-results.sh:1265-1266`](scripts/collect-agent-results.sh:1265-1266) — `cp` errors are fully silent (`2>/dev/null`); on `cp` failure the subsequent `mv` still overwrites `ORIG_OUTPUT`, so the stated observability goal (“preserve first-pass”) is **best-effort only** with no stderr signal and no test coverage for the failure mode. **Suggested fix:** on `cp` failure, either skip the overwrite/`RESULTS` update, or surface a non-ignored diagnostic and treat as collector-side failure for that index.
- **Suggested revision**: Address the concern above.


### FINDING_20: correctness: scripts/collect-agent-results.sh:1246-1268
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Silent cp failure still runs mv onto ORIG_OUTPUT. Disk or permission error drops first-pass copy then overwrites original losing content. Abort or warn and skip mv when cp fails or run cp without silencing and handle non-zero.
- **Suggested revision**: Address the concern above.


### FINDING_21: correctness: scripts/collect-agent-results.sh:1251-1253
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] Structured sidecar mv errors are ignored but STRUCTURED_SIDECAR is always rewritten to the new path. mv fails (IO/permissions): RESULTS advertises ORIG_OUTPUT sidecar path but file remains at old *-ns-retry.* path; STATUS=OK with broken STRUCTURED_SIDECAR. Assign STRUCTURED_SIDECAR only after successful mv, or fail closed and avoid partial promotion.
- **Suggested revision**: Address the concern above.


### FINDING_22: correctness: scripts/collect-agent-results.sh:1251-1253
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Structured sidecar mv errors ignored but STRUCTURED_SIDECAR retargets anyway Rare mv failure after successful validation: RESULTS points at missing path while sidecar remains under *-ns-retry.* Only update STRUCTURED_SIDECAR on successful mv or emit failure and keep old path
- **Suggested revision**: Address the concern above.


### FINDING_23: correctness: scripts/collect-agent-results.sh:1251-1253
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] STRUCTURED_SIDECAR set after optional mv with || true. mv failure leaves structured file at old path while RESULT points to new path. Only set STRUCTURED_SIDECAR to new path when mv succeeds or keep old path and log failure.
- **Suggested revision**: Address the concern above.


### FINDING_24: correctness: scripts/collect-agent-results.sh:1251-1254
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Structured NS-retry success forces STRUCTURED_SIDECAR to ORIG_OUTPUT.* after a sidecar mv that is ignored on failure. After moving retry prose onto ORIG_OUTPUT, the structured sidecar mv can fail; RESULTS still points at the new basename while the validated file may remain on the old *-ns-retry.* path or be missing, breaking consumers under STATUS=OK. Require successful rename (or post-mv file probe) before updating STRUCTURED_SIDECAR/RESULTS; do not use || true without a fallback path.
- **Suggested revision**: Address the concern above.


### FINDING_25: correctness: scripts/collect-agent-results.sh:1251-1269
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] NS-retry success path promotes retry onto ORIG_OUTPUT and rewrites RESULTS without checking mv exit status; script has no set -e. mv fails (permissions EXDEV etc.) while NS retry file remains; RESULTS still emits STATUS=OK and REVIEWER_FILE=ORIG_OUTPUT but disk at ORIG_OUTPUT is still first-pass text validated only at NS_RETRY_OUTPUT. Check mv exit status and skip or fail-closed RESULTS update unless promotion succeeds.
- **Suggested revision**: Address the concern above.


### FINDING_26: correctness: scripts/collect-agent-results.sh:1252-1253
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Structured sidecar relocation uses mv ... || true then always sets STRUCTURED_SIDECAR to the new path. Sidecar mv fails after prose mv succeeds; RESULTS points STRUCTURED_SIDECAR at ORIG_OUTPUT.ext while TSV/jsonl still lives at NS_RETRY path or is inconsistent. Only set STRUCTURED_SIDECAR to new path when mv succeeds; otherwise fail closed or retain old path.
- **Suggested revision**: Address the concern above.


### FINDING_27: correctness: scripts/test-collect-agent-results.sh (C_NS_FP_FAILURE hunk in branch diff)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Planned label was NS-retry fails (no sentinel); test covers no-retry-launched (no .meta). Mild plan-to-test wording mismatch; optional gap for other failure shapes not asserted. Rename/recomment or add a sentinel-specific failure fixture if literal plan wording matters.
- **Suggested revision**: Address the concern above.


### FINDING_3: **correctness** [`scripts/collect-agent-results.sh:1251-1253`](scripts/collect-agent-results.sh:1251-1253) — If the prose `mv` fails but execution continues, the next line still runs `mv "$STRUCTURED_SIDECAR" "$_ns_new_sidecar" … || true`, which can place the **retry** structured file next to `ORIG_OUTPUT` while `ORIG_OUTPUT` still contains **first-pass** prose, splitting prose and structured artifacts across incompatible content. **Suggested fix:** chain moves (only relocate the structured sidecar after a successful prose `mv`) and abort the branch on any failed required `mv`.
- **Reviewer**: dyn-mv-atomicity-output.txt
- **Concern**: - **correctness** [`scripts/collect-agent-results.sh:1251-1253`](scripts/collect-agent-results.sh:1251-1253) — If the prose `mv` fails but execution continues, the next line still runs `mv "$STRUCTURED_SIDECAR" "$_ns_new_sidecar" … || true`, which can place the **retry** structured file next to `ORIG_OUTPUT` while `ORIG_OUTPUT` still contains **first-pass** prose, splitting prose and structured artifacts across incompatible content. **Suggested fix:** chain moves (only relocate the structured sidecar after a successful prose `mv`) and abort the branch on any failed required `mv`.
- **Suggested revision**: Address the concern above.


### FINDING_30: risk-integration: scripts/test-collect-agent-results.sh:318-325
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [important] Structured NS-retry test does not assert first-pass sidecar. A regression that omits or breaks cp only on the structured NS-retry success path could ship while C_NSS still passes. After C_NSS collector run assert expected first-pass path exists and contains the heredoc body (and retry body at OUT_NSS).
- **Suggested revision**: Address the concern above.


### FINDING_31: risk-integration: scripts/test-collect-agent-results.sh:358-360
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Comment overstates covered scenarios vs test name. Maintainers may think failure-after-launch is covered. Align comment with tests or add the failure scenario.
- **Suggested revision**: Address the concern above.


### FINDING_32: risk-integration: scripts/test-collect-agent-results.sh:358-372
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Negative test only covers retry-not-launched not NS-retry failure paths. Plan asked for no sidecar when retry fails no sentinel; launched-but-failed cases are untested. Add a case with valid meta and replay stub but missing or bad sentinel or failing validation assert no -first-pass.txt.
- **Suggested revision**: Address the concern above.


### FINDING_4: **correctness** [`scripts/collect-agent-results.sh:1251-1254`](scripts/collect-agent-results.sh:1251-1254) — After NS structured-retry validation succeeds, `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"` is not checked. With `set -u` / `pipefail` but **without** `set -e` (see [`scripts/collect-agent-results.sh:81-82`](scripts/collect-agent-results.sh:81-82)), a non-zero `mv` (permissions, cross-device rename, transient IO) leaves `ORIG_OUTPUT` unchanged while the block still sets `RESULTS[IDX]` to `STATUS=OK` with `REVIEWER_FILE=$ORIG_OUTPUT`, so emitted results claim the canonical path holds validated retry prose when it may still hold first-pass `NOT_SUBSTANTIVE` content. **Suggested fix:** require `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"` to succeed before updating `RESULTS[IDX]`; on failure, skip the OK rewrite (or fail closed for that index).
- **Reviewer**: dyn-mv-atomicity-output.txt
- **Concern**: - **correctness** [`scripts/collect-agent-results.sh:1251-1254`](scripts/collect-agent-results.sh:1251-1254) — After NS structured-retry validation succeeds, `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"` is not checked. With `set -u` / `pipefail` but **without** `set -e` (see [`scripts/collect-agent-results.sh:81-82`](scripts/collect-agent-results.sh:81-82)), a non-zero `mv` (permissions, cross-device rename, transient IO) leaves `ORIG_OUTPUT` unchanged while the block still sets `RESULTS[IDX]` to `STATUS=OK` with `REVIEWER_FILE=$ORIG_OUTPUT`, so emitted results claim the canonical path holds validated retry prose when it may still hold first-pass `NOT_SUBSTANTIVE` content. **Suggested fix:** require `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"` to succeed before updating `RESULTS[IDX]`; on failure, skip the OK rewrite (or fail closed for that index).
- **Suggested revision**: Address the concern above.


### FINDING_5: **correctness** [`scripts/collect-agent-results.sh:1252-1253`](scripts/collect-agent-results.sh:1252-1253) — `mv "$STRUCTURED_SIDECAR" "$_ns_new_sidecar" 2>/dev/null || true` swallows failure but `STRUCTURED_SIDECAR="$_ns_new_sidecar"` is always applied, so `STRUCTURED_SIDECAR` can name a path that was never created while the real file may still live on the `-ns-retry` basename. **Suggested fix:** set `STRUCTURED_SIDECAR` only when the `mv` succeeds, or treat a required move failure like validation failure (do not emit `STRUCTURED_SIDECAR=` for a missing path).
- **Reviewer**: dyn-mv-atomicity-output.txt
- **Concern**: - **correctness** [`scripts/collect-agent-results.sh:1252-1253`](scripts/collect-agent-results.sh:1252-1253) — `mv "$STRUCTURED_SIDECAR" "$_ns_new_sidecar" 2>/dev/null || true` swallows failure but `STRUCTURED_SIDECAR="$_ns_new_sidecar"` is always applied, so `STRUCTURED_SIDECAR` can name a path that was never created while the real file may still live on the `-ns-retry` basename. **Suggested fix:** set `STRUCTURED_SIDECAR` only when the `mv` succeeds, or treat a required move failure like validation failure (do not emit `STRUCTURED_SIDECAR=` for a missing path).
- **Suggested revision**: Address the concern above.


### FINDING_6: **correctness** [`scripts/collect-agent-results.sh:1268-1269`](scripts/collect-agent-results.sh:1268-1269) — Same unchecked `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"` on the substantive NS-retry success path: failure still leads to `RESULTS[IDX]=…STATUS=OK…REVIEWER_FILE=$ORIG_OUTPUT` while `ORIG_OUTPUT` may not contain the validated retry body (and `NS_RETRY_OUTPUT` may still hold the only copy). **Suggested fix:** gate the `RESULTS[IDX]` assignment on successful `mv` (and align cleanup of stale `-ns-retry` files if you fail closed).
- **Reviewer**: dyn-mv-atomicity-output.txt
- **Concern**: - **correctness** [`scripts/collect-agent-results.sh:1268-1269`](scripts/collect-agent-results.sh:1268-1269) — Same unchecked `mv "$NS_RETRY_OUTPUT" "$ORIG_OUTPUT"` on the substantive NS-retry success path: failure still leads to `RESULTS[IDX]=…STATUS=OK…REVIEWER_FILE=$ORIG_OUTPUT` while `ORIG_OUTPUT` may not contain the validated retry body (and `NS_RETRY_OUTPUT` may still hold the only copy). **Suggested fix:** gate the `RESULTS[IDX]` assignment on successful `mv` (and align cleanup of stale `-ns-retry` files if you fail closed).
- **Suggested revision**: Address the concern above.


