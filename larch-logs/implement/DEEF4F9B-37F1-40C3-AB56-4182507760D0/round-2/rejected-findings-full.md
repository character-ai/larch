### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: skills/design/scripts/test-design-pause-resume.sh:261-291
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] The Step 4 FINALIZE compatibility guard bash block is duplicated three times verbatim. A future SKILL.md tweak to warn/exit semantics could update only one copy; pause/resume tests would still pass while no longer matching production orchestration. Extract a single run_step4_finalize_compat_guard helper and invoke it from all three test sites.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_10: `e7327f1e9` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `e7327f1e9` — Address code review feedback (round 1) **Verdict:** The refactor largely matches the plan — FINALIZE moved to the Step 3b completion boundary, SIMPLE sentinels folded into the Step 2a entry fence, cross-doc routing updated, and harness coverage expanded. One correctness gap remains around SIMPLE skip logic. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_13

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_13: **Nit** `correctness` `skills/design/SKILL.md:782` — Step 2a success-boundary prose says it applies “including the zero-sketch sentinel path,” but the HARD zero-sketches guard at 2a.3 routes directly to Step 2b and bypasses 2a.4, so that boundary write is never reached on that path. This is pre-existing misleading prose, not introduced by the fold, but it can confuse resume debugging. **Suggested fix:** Clarify that the zero-sketch path must explicitly write `.completed/step-2a` in its own branch, or remove “including the zero-sketch sentinel path” from the 2a.4 boundary line.
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: 3. **Nit** `correctness` `skills/design/SKILL.md:782` — Step 2a success-boundary prose says it applies “including the zero-sketch sentinel path,” but the HARD zero-sketches guard at 2a.3 routes directly to Step 2b and bypasses 2a.4, so that boundary write is never reached on that path. This is pre-existing misleading prose, not introduced by the fold, but it can confuse resume debugging. **Suggested fix:** Clarify that the zero-sketch path must explicitly write `.completed/step-2a` in its own branch, or remove “including the zero-sketch sentinel path” from the 2a.4 boundary line. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: skills/design/SKILL.md:1291-1326
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 3b completion-boundary and Step 4 entry FINALIZE fences are near-duplicates. Drift between fresh-run and legacy-resume paths could reintroduce warning-only failure or missing step-3b ordering on one path only. Optional: centralize the fence body in a references/finalize-boundary.md byte-preserved block cited by both SKILL sites.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_23: `08a83a6b2` — Fold design setup into existing boundaries
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `08a83a6b2` — Fold design setup into existing boundaries
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_24: `07ee0c2a1` — chore(larch-logs) flush (run log only; not reviewed as a security surface)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `07ee0c2a1` — chore(larch-logs) flush (run log only; not reviewed as a security surface)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_25: `e7327f1e9` — Address code review feedback (round 1)
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - `e7327f1e9` — Address code review feedback (round 1) **Changed surfaces:** orchestration prose and bash fences in `skills/design/SKILL.md`, routing docs (`approval-gates.md`, `flags.md`, `configuration-and-permissions.md`, `sketch-launch.md`), caller docs (`design-driver.md`, `finalize-plan.md`), one stdout breadcrumb in `run-step3-review.sh`, and harness updates (`test-design-structure.sh`, `test-design-pause-resume.sh`). No changes to `design-driver.sh`, `finalize-plan.sh`, or other runtime validators. ## Security assessment This is a caller-relocation refactor: two trivial file-setup turns are folded into existing fences. From a security/trust-boundary lens:
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_26: **No new command injection.** New bash fences pipe a literal `ACTION=FINALIZE` into `design-driver.sh` with `"$DESIGN_TMPDIR"` quoted. `design-driver.sh` and `finalize-plan.sh` are unchanged; `larch_design_tmpdir_validate` still gates tmpdir paths.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new command injection.** New bash fences pipe a literal `ACTION=FINALIZE` into `design-driver.sh` with `"$DESIGN_TMPDIR"` quoted. `design-driver.sh` and `finalize-plan.sh` are unchanged; `larch_design_tmpdir_validate` still gates tmpdir paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_27: **No new untrusted-input handling.** Issue/ballot/reviewer trust-boundary prose is untouched. The 2a.2 skip heuristic (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`) operates on session-local artifacts, same trust model as before.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No new untrusted-input handling.** Issue/ballot/reviewer trust-boundary prose is untouched. The 2a.2 skip heuristic (`approach-synthesis.txt` contains `NO_SKETCHES_CLASSIFIED_SIMPLE`) operates on session-local artifacts, same trust model as before.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_28: **Integrity improved on failure paths.** Both the Step 3b completion boundary and the Step 4 compatibility guard now hard-halt with `exit "$_finalize_rc"` after the repair warning, rather than allowing a warning-only continue.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Integrity improved on failure paths.** Both the Step 3b completion boundary and the Step 4 compatibility guard now hard-halt with `exit "$_finalize_rc"` after the repair warning, rather than allowing a warning-only continue.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_29

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_29: **No secrets, auth, crypto, SSRF, deserialization, or dependency changes** in the functional diff.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **No secrets, auth, crypto, SSRF, deserialization, or dependency changes** in the functional diff. The Step 4 guard’s `[ ! -f "$DESIGN_TMPDIR/.completed/finalize" ]` check follows the same sentinel pattern `design-driver.sh` already used for idempotent FINALIZE skips; it does not introduce a new remote trust boundary. Local tmpdir tampering (empty/symlink sentinel) could skip validation, but that threat model predates this PR and requires write access to the session directory.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/test-design-structure.sh:276-305
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 4 region slicing uses two different HTML comment needles (<!-- step:4 — vs <!-- step:4 ). A marker rename could break one assertion while leaving another passing, masking structural regressions. Unify on one marker string or one region-extraction helper for all Step 3b/4 assertions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_33

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_33: risk-integration: scripts/test-design-structure.sh:288-304
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Structure harness does not pin FINALIZE repair warning text on Step 3b boundary failure. Step 3b boundary could regress to exit-only failure without operator-visible repair breadcrumb; only Step 4 compatibility failure is tested in pause-resume harness. Add grep pin for repair warning in assert_step3b_finalize_boundary for Step 3b and Step 4 regions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_41

**Rejected subtype:** split panel (YES votes did not clear NO votes; not accepted)

### FINDING_41: **correctness** `skills/design/SKILL.md:796-804` — The new Step 2a.5 legacy-SIMPLE compatibility fence writes `.completed/step-2a.5` with plain `mkdir` / `: >` and no `set -e` or non-zero exit on failure. If `mkdir -p "$DESIGN_TMPDIR/.completed"` fails, the subshell still exits 0 and line 806 proceeds to Step 2b, so pause-save can keep resuming at `STEP=2a.5` even though the repair marker was never written. That is a new path introduced by this branch for pre-PR paused SIMPLE sessions. **Suggested fix:** Mirror the Step 2a SIMPLE entry fail-fast pattern: wrap the marker write in `set -e` (or explicit `if ! mkdir …; then exit 1; fi`) and halt before the SIMPLE skip prose when the repair write fails.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:796-804` — The new Step 2a.5 legacy-SIMPLE compatibility fence writes `.completed/step-2a.5` with plain `mkdir` / `: >` and no `set -e` or non-zero exit on failure. If `mkdir -p "$DESIGN_TMPDIR/.completed"` fails, the subshell still exits 0 and line 806 proceeds to Step 2b, so pause-save can keep resuming at `STEP=2a.5` even though the repair marker was never written. That is a new path introduced by this branch for pre-PR paused SIMPLE sessions. **Suggested fix:** Mirror the Step 2a SIMPLE entry fail-fast pattern: wrap the marker write in `set -e` (or explicit `if ! mkdir …; then exit 1; fi`) and halt before the SIMPLE skip prose when the repair write fails.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=1 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_42

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_42: **correctness** `skills/design/SKILL.md:649-650` — The Step 2a entry fence classifies tier via `read-design-classification.sh … 2>/dev/null || printf '%s\n' HARD)`. If the helper is missing, not executable, or otherwise fails before emitting stdout, stderr is discarded and the fallback silently treats the run as HARD, so a SIMPLE design skips sentinel writes and launches the full sketch path instead. The old SIMPLE sentinel fence lived behind SIMPLE-only prose and did not depend on this reader. **Suggested fix:** Do not swallow classification failures into HARD on the SIMPLE write path: run the reader without `2>/dev/null`, or on non-zero exit print a loud warning and `exit 1` (or re-read `run-params.json` with an explicit SIMPLE/HARD test) before deciding whether to write sentinels; only default to HARD when the script itself documents that default on stdout with exit 0.
- **Reviewer**: dyn-bash-fences-output.txt
- **Concern**: - **correctness** `skills/design/SKILL.md:649-650` — The Step 2a entry fence classifies tier via `read-design-classification.sh … 2>/dev/null || printf '%s\n' HARD)`. If the helper is missing, not executable, or otherwise fails before emitting stdout, stderr is discarded and the fallback silently treats the run as HARD, so a SIMPLE design skips sentinel writes and launches the full sketch path instead. The old SIMPLE sentinel fence lived behind SIMPLE-only prose and did not depend on this reader. **Suggested fix:** Do not swallow classification failures into HARD on the SIMPLE write path: run the reader without `2>/dev/null`, or on non-zero exit print a loud warning and `exit 1` (or re-read `run-params.json` with an explicit SIMPLE/HARD test) before deciding whether to write sentinels; only default to HARD when the script itself documents that default on stdout with exit 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_53

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_53: **code-quality** `scripts/test-design-structure.sh:127-153` — The new `assert_no_direct_step3b_step4_routes` awk has no negative self-tests, unlike the existing `run_thin_fence_self_tests` / `run_gate_b_bypass_branch_sentinel_self_tests` helpers. A regex edit that stops matching `Step 3b, Step 4` or starts false-positiving on innocent prose will not be caught until someone edits `SKILL.md` and runs the full harness. **Suggested fix:** Add a `run_step3b_route_guard_self_tests` block with minimal temp files: one bare `Step 3b → Step 4` line (must fail), one boundary-qualified line (must pass), and one split across two lines if you want to document that limitation explicitly.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:127-153` — The new `assert_no_direct_step3b_step4_routes` awk has no negative self-tests, unlike the existing `run_thin_fence_self_tests` / `run_gate_b_bypass_branch_sentinel_self_tests` helpers. A regex edit that stops matching `Step 3b, Step 4` or starts false-positiving on innocent prose will not be caught until someone edits `SKILL.md` and runs the full harness. **Suggested fix:** Add a `run_step3b_route_guard_self_tests` block with minimal temp files: one bare `Step 3b → Step 4` line (must fail), one boundary-qualified line (must pass), and one split across two lines if you want to document that limitation explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_54

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_54: **code-quality** `scripts/test-design-structure.sh:140-149` — The route guard is strictly line-scoped and the verb alternation is substring-based (`go` matches inside `Go through each`, `undergo`, etc.). It also misses routes that omit the chosen verbs (`run`, `follow`, `advance`) or split `Step 3b` and `Step 4` across adjacent lines. That leaves real bypass blind spots the six-surface scan cannot catch, even though current files happen to pass. **Suggested fix:** Tighten verb matching with word boundaries (`\\<go\\>`), add the plan’s missing verb forms if needed, and either scan a paragraph window or add positive `contains` pins for the highest-risk multi-line routes (Gate-B-bypass matrix bullets in `skills/design/SKILL.md:1096-1118`).
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:140-149` — The route guard is strictly line-scoped and the verb alternation is substring-based (`go` matches inside `Go through each`, `undergo`, etc.). It also misses routes that omit the chosen verbs (`run`, `follow`, `advance`) or split `Step 3b` and `Step 4` across adjacent lines. That leaves real bypass blind spots the six-surface scan cannot catch, even though current files happen to pass. **Suggested fix:** Tighten verb matching with word boundaries (`\\<go\\>`), add the plan’s missing verb forms if needed, and either scan a paragraph window or add positive `contains` pins for the highest-risk multi-line routes (Gate-B-bypass matrix bullets in `skills/design/SKILL.md:1096-1118`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_55

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_55: **code-quality** `scripts/test-design-structure.sh:871,99,335` — Step 4 region slicing uses three different marker needles in one file: `<!-- step:4 ` (architecture-diagram pin and `assert_step3b_entry_guard_threads_repo`), `<!-- step:4 —` (FINALIZE boundary + route-guard end), and a loose `<!-- step:4 /` awk end test. All work on today’s `skills/design/SKILL.md:1308`, but the inconsistent pins make the harness brittle if the HTML comment format changes slightly. **Suggested fix:** Centralize one `STEP4_MARKER` constant (or helper) and reuse it for `sed` slices, route-guard end detection, and entry-guard awk.
- **Reviewer**: dyn-harness-regex-output.txt
- **Concern**: - **code-quality** `scripts/test-design-structure.sh:871,99,335` — Step 4 region slicing uses three different marker needles in one file: `<!-- step:4 ` (architecture-diagram pin and `assert_step3b_entry_guard_threads_repo`), `<!-- step:4 —` (FINALIZE boundary + route-guard end), and a loose `<!-- step:4 /` awk end test. All work on today’s `skills/design/SKILL.md:1308`, but the inconsistent pins make the harness brittle if the HTML comment format changes slightly. **Suggested fix:** Centralize one `STEP4_MARKER` constant (or helper) and reuse it for `sed` slices, route-guard end detection, and entry-guard awk.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_6

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_6: code-quality: skills/design/SKILL.md:689
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Step 2a.3 still gates SIMPLE skip on mental design_classification while 2a.2 uses sentinel/re-read. If run-params and entry-fence outcomes diverge on resume, 2a.2 could skip to 2b while 2a.3 prose still references a different classification source. Align 2a.3 and 2a.5 SIMPLE skip guards with the 2a.2 sentinel-or-re-read predicate.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0

### [rejected] FINDING_8

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_8: `08a83a6b2` — Fold design setup into existing boundaries  
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `08a83a6b2` — Fold design setup into existing boundaries
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_9: `07ee0c2a1` — chore(larch-logs) flush (out of scope per instructions)  
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: - `07ee0c2a1` — chore(larch-logs) flush (out of scope per instructions)
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0

