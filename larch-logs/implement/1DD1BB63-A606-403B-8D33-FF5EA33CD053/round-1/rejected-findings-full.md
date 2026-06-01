### [rejected] FINDING_1

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_1: code-quality: scripts/test-implement-timing-rehydration.sh:39-76
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] Invariant B no longer applies to fences that delegate timing marks to step-telemetry-mark.sh A broken or regressed helper could write marks against the wrong ledger while SKILL.md still passes test-implement-timing-rehydration invariant B Teach the awk to treat step-telemetry-mark.sh fences as timing-rehydrated or add an explicit structural check plus cross-reference to test-step-telemetry-mark
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_10

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_10: risk-integration: scripts/test-step-telemetry-mark.sh:53-61
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Never-fatal paths only assert exit 0, not that marks are still emitted. A regression could skip ledger writes on bad/empty inputs while remaining exit 0 and passing CI. Assert both ledger files receive mark rows after bad tmpdir, omitted tmpdir, and missing --label cases.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_11

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_11: risk-integration: scripts/test-step-telemetry-mark.sh:45
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] Happy path requires jq without an explicit prerequisite check. CI or dev environments without jq fail with an unclear error. Add command -v jq guard at harness start.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_12

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_12: risk-integration: scripts/test-implement-timing-rehydration.sh:39-76
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Invariant B no longer applies to fences that only call step-telemetry-mark.sh. A broken helper could drop per-run timing isolation without failing the structural SKILL timing-fence check. Extend structural tests or add integration coverage that validates helper rehydration matches inline semantics.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_14

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_14: **`--implement-tmpdir` and `--label`** are passed only through double-quoted expansions into `read-session-env-key.sh` and `mark` subcommands — no `eval`, no unquoted interpolation.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`--implement-tmpdir` and `--label`** are passed only through double-quoted expansions into `read-session-env-key.sh` and `mark` subcommands — no `eval`, no unquoted interpolation.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_15

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_15: **Labels** at `/implement` call sites are fixed literals in `SKILL.md`, not user input.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Labels** at `/implement` call sites are fixed literals in `SKILL.md`, not user input.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_16

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_16: **`read-session-env-key.sh`** still uses awk extraction (no `source` of `session-env.sh`); keys are constants in the helper.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`read-session-env-key.sh`** still uses awk extraction (no `source` of `session-env.sh`); keys are constants in the helper.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_17

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_17: **`token-ledger.sh mark`** builds JSON with `jq --arg step "$step"`; **`timing-ledger.sh mark`** runs labels through `sanitize_field` before TSV append.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **`token-ledger.sh mark`** builds JSON with `jq --arg step "$step"`; **`timing-ledger.sh mark`** runs labels through `sanitize_field` before TSV append.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_18

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_18: **Ledger path resolution** still goes through existing `validate_under_tmp` / `validate_env_ledger` / `timing_allowed_roots` logic; the helper exports `IMPLEMENT_TMPDIR` the same way the old inline fence did so timing fallback behavior is preserved.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Ledger path resolution** still goes through existing `validate_under_tmp` / `validate_env_ledger` / `timing_allowed_roots` logic; the helper exports `IMPLEMENT_TMPDIR` the same way the old inline fence did so timing fallback behavior is preserved.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_19

**Rejected subtype:** dismissed (no acceptance threshold met)

### FINDING_19: **Subprocess isolation**: ledger-key `export`s inside the helper do not persist to the orchestrator shell, but marks run inside the helper with freshly read values; downstream scripts like `run-step5-review.sh` re-read `session-env` themselves. That is a behavioral/env-scope change, not a new trust-boundary bypass for marks themselves.
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: - **Subprocess isolation**: ledger-key `export`s inside the helper do not persist to the orchestrator shell, but marks run inside the helper with freshly read values; downstream scripts like `run-step5-review.sh` re-read `session-env` themselves. That is a behavioral/env-scope change, not a new trust-boundary bypass for marks themselves. ---
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0

### [rejected] FINDING_2

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_2: code-quality: scripts/test-implement-timing-rehydration.sh:123
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] step_telemetry_mark_count uses grep -Fc substring match unlike exact-line Fxc peers A prose or partial line mentioning the helper prefix could skew tmpdir coupling counts Use grep -Fxc on the full pinned helper invocation line
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_23

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_23: architecture: scripts/test-implement-timing-rehydration.sh:39-76,skills/implement/SKILL.md:894,1308,1343,1413
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Invariant B no longer guards converted step-ENTRY fences because they no longer call timing-ledger.sh directly in SKILL.md. A future edit removes timing-ledger.sh mark from step-telemetry-mark.sh or breaks the helper silently; structural harness stays green while Step 5/16/17/18-cleanup timing marks disappear. Add helper-specific structural pins (awk/grep) and/or a unit assertion that timing-ledger.sh mark is invoked on the happy path.
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

### [rejected] FINDING_24

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_24: risk-integration: scripts/step-telemetry-mark.sh:39-42,skills/implement/SKILL.md:1343-1348,skills/implement/scripts/write-final-report.sh:187-188
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] Helper subprocess exports do not persist LARCH_* to the orchestrator shell across Bash tool calls. Step 17 write-final-report token-report fallback uses empty LARCH_TOKEN_SESSION_ID and resolves via session-id; if session-env and session-id ever diverge token ledgers could differ from pre-refactor behavior. Re-read LARCH_TOKEN_SESSION_ID in the Step 17 write-final-report fence or harness the session-id-only fallback explicitly.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_25

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_25: architecture: scripts/step-telemetry-mark.sh:14-29
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Arg parser silently ignores unknown flags and leaves LABEL empty when --label is trailing/misspelled. Orchestrator typo like --lable drops both marks with exit 0 and no stderr signal. Warn on unknown flags and empty LABEL after parse while preserving exit 0.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_26

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_26: risk-integration: scripts/step-telemetry-mark.sh:35-37
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] read-session-env-key.sh stderr is redirected to /dev/null. Unexpected read failures are harder to diagnose during live runs than with the old inline reads. Remove blanket 2>/dev/null or limit suppression to expected unreadable-file cases.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_27

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_27: code-quality: scripts/test-step-telemetry-mark.sh:53-61
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] Negative-path tests only check exit 0 not ledger side effects. A regression writing marks to pwd-hash fallback on bad tmpdir would pass CI. Assert ledger files unchanged on never-fatal paths.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_28

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_28: code-quality: scripts/test-implement-timing-rehydration.sh:123
- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [nit] step_telemetry_mark_count uses grep -Fc substring match unlike sibling exact-line counts. A comment/prose line containing the helper prefix could false-inflate the count and fail CI confusingly. Use grep -Fxc with the full canonical line template.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_3

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_3: code-quality: scripts/step-telemetry-mark.sh:35-37
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Helper suppresses read-session-env-key stderr with 2>/dev/null Unreadable or missing session-env.sh fails more quietly than the old inline fences Drop 2>/dev/null unless stderr noise was a proven problem
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_4

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_4: risk-integration: skills/implement/SKILL.md:894,1308,1343,1413
- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] || true at call sites only masks non-executable helper (126) not helper logic errors Lost executable bit after clone drops four step marks with no structural harness failure beyond test-step-telemetry-mark when CI runs it Rely on make test-step-telemetry-mark in CI; optional note in step-telemetry-mark.md
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=2 JUDGE_ERROR=0

### [rejected] FINDING_9

**Rejected subtype:** exonerated (concern noted, not implemented in this PR)

### FINDING_9: risk-integration: scripts/test-implement-timing-rehydration.sh:123-131
- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] Harness does not pin exactly four helper calls or the four step-ENTRY mark labels required by acceptance. A follow-up could remove a step-ENTRY telemetry block or change a label without failing cardinality coupling. Add step_telemetry_mark_count == 4 and per-label grep -Fxc assertions (or a SKILL structural pin harness).
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=1 JUDGE_ERROR=0

