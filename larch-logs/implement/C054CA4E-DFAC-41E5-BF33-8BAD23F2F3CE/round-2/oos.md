### OOS_1: [OUT_OF_SCOPE] Clarify path re-resolves `REPO` after sub-step 2
- **Reviewer(s)**: cursor-specialist-correctness-output.txt
- **Severity**: nit
- **Concern**: Clarify path re-resolves `REPO` after sub-step 2 resolve (`SKILL.md` ~338). Extra `gh` resolution on clarify-only runs.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Reuse sub-step 2 REPO in clarify sub-step 3.2.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### OOS_10: [OUT_OF_SCOPE] `validate_repo` regex matches existing helpers
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `[[ … =~ ^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$ ]]` in `validate_repo` matches existing repo helpers (`design-pause-load.sh`, `write-design-current-env.sh`).


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_11: [OUT_OF_SCOPE] `${REPO:+--repo "$REPO"}` quoting pattern
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `${REPO:+--repo "$REPO"}` in drivers and SKILL fences correctly omits `--repo` when `REPO` is empty and quotes it when set.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_12: [OUT_OF_SCOPE] `plan_block_present` grep count / orchestrator array usage (portability OK)
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `start_count=$(grep -c …) || start_count=0` in `plan_block_present` mirrors `plan-block-read.sh:113-114` and is safe under `set -euo pipefail`. `SKILL.md` uses `for _w in "${_route_warn_lines[@]}"` without `[@]+` guard but arrays are initialized with `=()` first — safe on Bash 3.2 with `set -u`.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_13: [OUT_OF_SCOPE] Route KV key parity between driver and orchestrator
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: `emit_route_result` and SKILL `case` lists cover the same routing keys; `WARN`/`ERROR` intentionally not stored via `printf -v`. No missing driver↔orchestrator routing keys found.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_14: [OUT_OF_SCOPE] `cancel-pause-load` present in branch; not a silent protocol gap
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: `cancel-pause-load` emitted by driver and handled in orchestrator `case` with abort banner — present in diff though absent from plan acceptance ROUTE enum; reviewer treats as documentation/acceptance gap, not missing protocol wiring.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_15: [OUT_OF_SCOPE] `env-refresh-failed` KV is read before abort
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: Orchestrator reads merged `INIT_STATUS` before abort; issue is contract documentation and operator messaging, not silent KV drop (overlaps in-scope FINDING_20 for actionable doc/acceptance work).


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_16: [OUT_OF_SCOPE] Harness does not assert immediate vs deferred WARN print timing
- **Reviewer(s)**: dyn-kv-protocol-output.txt
- **Severity**: nit
- **Concern**: `test-design-structure.sh:786-787` only checks `WARN)`/`ERROR)` presence in `SKILL.md`, not immediate vs deferred printing — weak relative to Round 5 wording; pre-existing test precision limit (related to in-scope FINDING_3).


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_17: [OUT_OF_SCOPE] Case 8 stub path adequately exercises jq-failure spy
- **Reviewer(s)**: dyn-harness-regression-output.txt
- **Severity**: nit
- **Concern**: `test-step0b-router-flag-recovery.sh` case 8 stubs are sufficient for `design-init-runparams.sh` to reach jq-merge block; `grep -Fq '--tool jq(router-flags-merge)'` on spy proves failure path despite `-s "$SPY8"` alone being insufficient.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_18: [OUT_OF_SCOPE] OR check at 122–124 largely redundant with driver pin 645–646
- **Reviewer(s)**: dyn-harness-regression-output.txt
- **Severity**: nit
- **Concern**: OR at `test-design-structure.sh:122-124` adds little beyond stricter driver-only grep at 645–646 (related to in-scope FINDING_22).

Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_2: [OUT_OF_SCOPE] Unrelated `test-plan-review-loop.sh` poll interval change
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: Unrelated poll interval change bundled on branch (`skills/design/scripts/test-plan-review-loop.sh` 4–6). May alter CI duration for plan-review-loop tests only.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: No action for #3245 unless CI flakes; note in PR test plan.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_3: [OUT_OF_SCOPE] `larch-logs` excluded from markdown literal-count lint
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Severity**: nit
- **Concern**: `scripts/lint-literal-counts.py:56` excludes `larch-logs` from markdown literal-count lint (reduces false positives from committed run logs). No action for Step 0b review.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_4: [OUT_OF_SCOPE] Reentry `for _rkv in $_reentry_out` word-splitting brittleness
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `design-route.sh:258` — `for _rkv in $_reentry_out` relies on word-splitting; safe for current `MARKER_HIT=true MARKER_AGE=…` output but brittle if `REASON=` values gain spaces. Same pattern existed pre-refactor in `SKILL.md`.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Parse with a `while IFS= read -r` loop or strict `MARKER_HIT=*` case on whole lines.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0 Result=neutral

### OOS_5: [OUT_OF_SCOPE] File-first `printf -v` allowlist does not reject newlines in values
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: `SKILL.md` 245–264 file-first / stdout merge uses allowlisted `case` keys before `printf -v` (blocks arbitrary assignment) but does not reject `\n`/`\r` in values unlike `phase_driver_read_result_env`. Tmpdir trust model unchanged.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Reuse `phase_driver_read_result_env` allowlists or reject `\n`/`\r` in values when sourcing result env.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### OOS_6: [OUT_OF_SCOPE] Rename stderr merge / pre-existing behavior class
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Severity**: nit
- **Concern**: Rename stderr merged via `2>&1`; non-`RENAMED=*` output falls through to `RENAMED=true` — pre-existing class, not introduced by routing extraction. No hard-coded secrets, unsafe `eval`, or path traversal in changed driver `--repo` handling. `larch-logs/` churn out of scope per review instructions.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_7: [OUT_OF_SCOPE] Empty-array `[@]+` idiom in drivers
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `${WARN_LINES[@]+"${WARN_LINES[@]}"}` in `design-route.sh` and `design-init-runparams.sh` matches existing empty-array / `set -u` idiom (e.g. `scripts/launch-review.sh`).


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_8: [OUT_OF_SCOPE] `local -a kvs` in `emit_route_result` on Bash 3.2
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `local -a kvs=(…)` with conditional `kvs+=()` in `emit_route_result` is valid on macOS Bash 3.2.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### OOS_9: [OUT_OF_SCOPE] `printf -v` in Step 0b fences
- **Reviewer(s)**: dyn-bash-compat-output.txt
- **Severity**: nit
- **Concern**: `printf -v` in `skills/design/SKILL.md` Step 0b fences is available in Bash 3.1+.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

