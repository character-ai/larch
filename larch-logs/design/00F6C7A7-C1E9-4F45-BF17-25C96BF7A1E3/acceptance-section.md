## Acceptance

- `safe_exit_code_value` exists in `stall-recovery-report.sh` next to `safe_step_value` / `safe_phase_value`: empty or non-numeric input → `unknown`; all-digit input passes through unchanged.
- `cmd_classify` emits `EXIT_CODE=unknown` when no captured exit code is present in state; a real `0` emits `EXIT_CODE=0` and a seeded `4` emits `EXIT_CODE=4` (numeric pass-through preserved).
- The report body (`bug-body`, `bug-comment`, and the verbatim `chat-print`) renders `| Exit code | \`unknown\` |` for an uncaptured code and `| Exit code | \`0\` |` for a captured zero.
- The report body renders a `| Bail reason | … |` row: allowlisted tokens (e.g. `orchestrator-envelope-invalid`, `wrapper-validation-failure`) verbatim, empty → `none`, non-allowlisted → `redacted`.
- `--bail-reason` remains classifier evidence (NOT report-only): the existing argv-only `--bail-reason "network timeout while posting issue"` → `transient-infra` case stays green, and an argv-only `wrapper-validation-failure` still routes to `dispatch-failure`.
- Step-2 hard-bail sites in `skills/implement/SKILL.md` mirror `IMPLEMENT_BAIL_REASON` alongside `FINAL_BAIL_REASON` at §2.1.5 (`orchestrator-envelope-invalid`), §2.2 `STATUS=bailed` (dispatcher `REASON`, with unconditional `STALL_TRACKING=true`), and the post-dispatch branch-mismatch site (`main-branch-post-dispatch`); `skills/implement/references/stall-recovery.md` passes `--bail-reason "${IMPLEMENT_BAIL_REASON:-${FINAL_BAIL_REASON:-}}"`.
- `stall-recovery-report.sh lint` passes: the `bail_reason` rows and the `integer-or-unknown` `exit_code` transform are byte-consistent across `stall-recovery-report-allowlists.tsv`, `code_allowlist_lines`, and the `stall-recovery-report.md` allowlist table; the documented `BAIL_REASON` enum matches `safe_bail_reason_value`.
- `SECURITY.md` documents the new public `Bail reason` field (closed-enum sanitized: verbatim / `none` / `redacted`) and `exit_code` as `integer-or-unknown`.
- All green: `bash skills/implement/scripts/test-stall-recovery-report.sh`, `bash scripts/test-implement-structure.sh`, `skills/implement/scripts/stall-recovery-report.sh lint`, `bash scripts/relevant-checks.sh`.
- No change to classifier branch tables (`retry_cap_for`, `resume_hint_for`, dispatch-failure rules), retry caps, or the sanitization boundary.
