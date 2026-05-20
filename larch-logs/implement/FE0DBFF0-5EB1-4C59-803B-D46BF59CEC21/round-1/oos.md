### FINDING_10: [OUT_OF_SCOPE] correctness: scripts/session-setup.sh:195-198
- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [nit] Preflight output is already re-emitted through emit on failure Behavior predates this diff; not introduced by stale-plugin work None required for this review scope
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=2 EXON=1 JUDGE_ERROR=0 Result=rejected

### FINDING_11: [OUT_OF_SCOPE] correctness: skills/fix-issue/SKILL.md (unchanged)
- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [nit] Feature description says fix-issue Step 0; skill uses Step 1 for session-setup Stakeholder-facing wording mismatch only; implementation follows implementation plan None in this PR; update feature text or skill docs separately if desired
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=0 EXON=3 JUDGE_ERROR=0 Result=rejected

### FINDING_21: correctness: feature_description vs skills/fix-issue/SKILL.md:118
- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [nit] Feature text says /fix-issue Step 0 but session-setup runs in Step 1 Operators search Step 0 for a warning that is emitted during Step 1 setup Update feature/issue wording to match SKILL step numbering
- **Suggested revision**: Address the concern above.


Vote tally: YES=1 NO=0 EXON=2 JUDGE_ERROR=0 Result=exonerated

### FINDING_5: [OUT_OF_SCOPE] **Awk parsing:** For the script’s actual `KEY=value` lines (no embedded `=` in semver values), `awk -F=` with `$2` and `END { print v }` behaves predictably on empty capture (blank `_stale_check`, no warning branch) and on the normal three-line stdout bundle from `working-tree-ahead`.
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **Awk parsing:** For the script’s actual `KEY=value` lines (no embedded `=` in semver values), `awk -F=` with `$2` and `END { print v }` behaves predictably on empty capture (blank `_stale_check`, no warning branch) and on the normal three-line stdout bundle from `working-tree-ahead`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_6: [OUT_OF_SCOPE] **Same-directory / `--plugin-dir` case:** When `CLAUDE_PLUGIN_ROOT` points at the working tree, `check-stale-plugin.sh` reads the same `.claude-plugin/plugin.json` for both installed and working-tree roots (via `git rev-parse --show-toplevel`), so extracted versions should match and `STALE_PLUGIN_CHECK` should resolve to `versions-match`, avoiding a false `working-tree-ahead` warning by design (`scripts/check-stale-plugin.sh:48-48` vs `71-71`, comparison `107-121`).
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **Same-directory / `--plugin-dir` case:** When `CLAUDE_PLUGIN_ROOT` points at the working tree, `check-stale-plugin.sh` reads the same `.claude-plugin/plugin.json` for both installed and working-tree roots (via `git rev-parse --show-toplevel`), so extracted versions should match and `STALE_PLUGIN_CHECK` should resolve to `versions-match`, avoiding a false `working-tree-ahead` warning by design (`scripts/check-stale-plugin.sh:48-48` vs `71-71`, comparison `107-121`).
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_7: [OUT_OF_SCOPE] **`emit` wiring:** The warning uses `emit` with a single formatted string, matching `emit()` in `scripts/lib-quiet.sh:97-103` and the existing `emit "$PREFLIGHT_OUTPUT"` pattern in `scripts/session-setup.sh:197-197`, so the call shape is consistent with the quiet/contract stream conventions.
- **Reviewer**: dyn-session-wiring-output.txt
- **Concern**: - **`emit` wiring:** The warning uses `emit` with a single formatted string, matching `emit()` in `scripts/lib-quiet.sh:97-103` and the existing `emit "$PREFLIGHT_OUTPUT"` pattern in `scripts/session-setup.sh:197-197`, so the call shape is consistent with the quiet/contract stream conventions.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_8: [OUT_OF_SCOPE] correctness
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - **correctness** `scripts/session-setup.sh:207` — Wrapping `"$SCRIPT_DIR/check-stale-plugin.sh"` in `… || true` avoids aborting session setup if `check-stale-plugin.sh` ever exits non-zero, but it also means any future hard failure in that helper (including the `grep`/`pipefail` case above) becomes a silent no-op for the stale-plugin warning; tightening `check-stale-plugin.sh` to always exit 0 on benign inputs remains the better fix, with this wrapper as a secondary safety net only.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=1 EXON=2 JUDGE_ERROR=0 Result=rejected

### FINDING_9: [OUT_OF_SCOPE] No Bash 4+ constructs (`declare -A`/`declare -n`, `mapfile`/`readarray`, `${var^^}`/`${var,,}`, `&>>`, `coproc`) appear in the new or modified shell hunks in `scripts/check-stale-plugin.sh`, `scripts/test-check-stale-plugin.sh`, or the inserted block in `scripts/session-setup.sh`; `local`, `[[ … ]]`, `$()`, `${param//pat/repl}`, `${param:0:32}`, and the embedded `awk` (ternary, `split`) are consistent with macOS Bash 3.2 and typical BSD `awk`.
- **Reviewer**: dyn-bash32-portability-output.txt
- **Concern**: - No Bash 4+ constructs (`declare -A`/`declare -n`, `mapfile`/`readarray`, `${var^^}`/`${var,,}`, `&>>`, `coproc`) appear in the new or modified shell hunks in `scripts/check-stale-plugin.sh`, `scripts/test-check-stale-plugin.sh`, or the inserted block in `scripts/session-setup.sh`; `local`, `[[ … ]]`, `$()`, `${param//pat/repl}`, `${param:0:32}`, and the embedded `awk` (ternary, `split`) are consistent with macOS Bash 3.2 and typical BSD `awk`.
- **Suggested revision**: Address the concern above.


Vote tally: YES=0 NO=3 EXON=0 JUDGE_ERROR=0 Result=rejected

