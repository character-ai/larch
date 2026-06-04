## Acceptance

- All 10 findings (FINDING_17, _11, _25, _4 and PLAN_FINDING_1–6) are fixed at the sites named in the plan; the normal full-`SESSION_ID` publish flow (approved → `[DESIGNED]` rename → reentry marker) is unchanged.
- `bash skills/design/scripts/test-design-publish.sh` passes, including the non-zero-exit + stdout `PUBLISH_OK=true` ⇒ `PUBLISH_OK=false` case and the empty-`SESSION_ID` ⇒ `publish-skipped` case (rename/marker skipped).
- `bash scripts/test-design-log-publish.sh` passes, including malformed `--repo` ⇒ `exit 1` with no success envelope; valid `owner/repo` and omitted-`--repo` cases stay green.
- `bash skills/design/scripts/test-design-pause-resume.sh` passes, including the `rc-ok-false` contradictory-envelope case (no pause marker), the `rc-false-recovery` case (`PAUSE_OK=true`, recovery branch preserved), and the malformed/argv-precedence `--repo` cases.
- `bash skills/design/scripts/test-render-final-summary.sh` passes, including `publish-skipped` in both primary and degraded-fallback paths (explicit Outcome bullet, honest skipped-publish note, no recovery prose, Run logs `N/A`, no `larch-logs/design/unknown/`).
- `bash scripts/test-render-run-summary.sh`, `bash scripts/test-render-run-summary-format.sh`, and `bash scripts/test-render-run-summary-callsites.sh` pass; `RUN_ID=unknown` and `failed-publish` keep Run logs `N/A`; an approved real run id still synthesizes `larch-logs/design/<id>/`.
- `bash skills/design/scripts/test-design-postplan-emit.sh` passes, including the internal-pause `--repo` forwarding case.
- `bash scripts/test-design-structure.sh` passes, including the preserved `(15b)` step-5c substring plus the new publish-gate, clarify sub-step 6 `SUMMARY_OUTCOME` branch, clarify fail-closed / recovery-metadata, pause-check `--repo` forwarding, and `design-init-runparams` `--repo` persistence assertions.
- `bash scripts/relevant-checks.sh` (or `make lint`) is green; every changed `.sh` has an updated `.md` sibling; `SECURITY.md` documents the `--repo` `OWNER/REPO` validation boundaries for `design-log-publish.sh` and `design-pause-save.sh`.
