### FINDING_20: [OUT_OF_SCOPE] Review session used empty branch delta / wrong diff base (HEAD == `main`, empty precomputed diff)
- **Reviewer(s)**: cursor-specialist-correctness-output.txt, cursor-specialist-plan-fidelity-output.txt, dyn-shell-robustness-output.txt, dyn-audit-scan-correctness-output.txt, dyn-test-coverage-output.txt
- **Concern**: Reviewers note empty precomputed diff and no commits on `$(git merge-base HEAD main)..HEAD`, so review was against the current tree rather than an intended branch patch; re-run with correct base or non-empty diff as appropriate.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-correctness-output.txt: Re-run session with non-empty diff or compare against intended base ref.
  - From cursor-specialist-plan-fidelity-output.txt: Reviewer must use origin/main or another correct base to see the branch patch. Use correct precomputed diff or diff against origin/main.
  - From dyn-shell-robustness-output.txt: The precomputed diff at `<TMPDIR>/round-4/diff.txt` was empty and `git log "$(git merge-base HEAD main)"..HEAD --oneline` produced no commits because this checkout’s `HEAD` and `main` both resolve to `df3dd544671eae219be3a78c800a14f03f370be2`, so the review used the current tree rather than a non-empty branch delta.
  - From dyn-audit-scan-correctness-output.txt: The path `<TMPDIR>/round-4/diff.txt` was empty, and in this workspace `HEAD` equals `main` at `df3dd544`, so there was no merge-base diff to attribute line-by-line; the finding above is from the shipped layout of `audit-scan-run.sh` (353-381), `scans.tsv` (line 7), and `larch-log.sh` (67-97) together.
  - From dyn-test-coverage-output.txt: The path `<TMPDIR>/round-4/diff.txt` was empty and `git log $(git merge-base HEAD main)..HEAD` produced no commits in this workspace, so this review is based on the current tree contents of [`scripts/test-launch-cursor-ci.sh`](scripts/test-launch-cursor-ci.sh) and the sidecar producer in [`scripts/lib-cursor-launcher-common.sh`](scripts/lib-cursor-launcher-common.sh), not on a non-empty branch diff artifact.

---


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=0 Result=neutral

### FINDING_21: [OUT_OF_SCOPE] CI runs harnesses via Makefile shards (workflow grep not the source of truth for “which script runs where”)
- **Reviewer(s)**: cursor-specialist-testing-output.txt
- **Concern**: Context for where tests run; none for this PR scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-testing-output.txt: Address the concern above.

---


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_22: [OUT_OF_SCOPE] `ship-pr.sh` Phase 2 stall-aware retry policy not in branch diff
- **Reviewer(s)**: cursor-specialist-security-output.txt, cursor-specialist-edge-cases-output.txt
- **Concern**: Track as follow-up PR / not applicable to judging Phase 1 code.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Track in follow-up PR
  - From cursor-specialist-edge-cases-output.txt: Not applicable to judging Phase 1 code; track as separate follow-up PR. Implement Phase 2 when diagnostics justify policy changes.

---


Vote tally: YES=1 NO=1 EXON=0 JUDGE_ERROR=0 Result=neutral

### FINDING_23: [OUT_OF_SCOPE] NDJSON composition style in `audit-scan-run.sh` pre-exists new scan work
- **Reviewer(s)**: cursor-specialist-security-output.txt
- **Concern**: No change required for this review scope.
- **Suggested revisions (informational for voters; coder decides)**:
  - From cursor-specialist-security-output.txt: Address the concern above.

---


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

### FINDING_24: [OUT_OF_SCOPE] Reviewer-noted positives / confirmed-good behaviors (not actionable defects in this pass)
- **Reviewer(s)**: dyn-shell-robustness-output.txt, dyn-sidecar-integrity-output.txt, dyn-audit-scan-correctness-output.txt, dyn-test-coverage-output.txt
- **Concern**: Multiple reviewers recorded positives or confirmed existing robustness (timeouts around probes, `pipefail` isolation for `lsof|head`, `jq`-based encoding, basename/temp collision notes, audit aggregation fallbacks matching tests/docs, macOS Bash 3.2 compatibility in new fixture blocks).
- **Suggested revisions (informational for voters; coder decides)**:
  - From dyn-shell-robustness-output.txt: Positives not tied to defects: `lsof` is wrapped with `timeout`/`gtimeout` when available and explicitly skipped otherwise (`scripts/lib-cursor-launcher-common.sh:200-217`); the subshell around `lsof|head` disables `pipefail` to avoid SIGPIPE clobbering the capture (`scripts/lib-cursor-launcher-common.sh:202-206`); `git status` / `git rebase --show-current-patch` use wall-clock wrappers or are omitted when no `timeout` exists (`scripts/lib-cursor-launcher-common.sh:265-286`); argv “full tree” probing uses `grep '[c]ursor'` and uid-scoped `ps` instead of a naive `ps -ef|grep cursor` (`scripts/lib-cursor-launcher-common.sh:192-197`), which is more robust on shared hosts.
  - From dyn-sidecar-integrity-output.txt: JSON assembly uses `jq` with `--arg` / `--argjson` / `--rawfile`, so `ps`, `lsof`, `git_state` strings, and `last_transcript_lines` (array of strings from `split("\n")`) are encoded as proper JSON values without manual string concatenation; invalid UTF-8 or other jq-hard failures drop the sidecar and append a `cursor-ci-stall-json: jq assembly failed` line to the diag file rather than writing truncated JSON (`scripts/lib-cursor-launcher-common.sh:295-333`).
  - From dyn-sidecar-integrity-output.txt: Basenames use `cursor-ci-stall-$(date +%s)-$$-${RANDOM}.json` plus `mktemp` for the staging file; with at most one stall emission per `cursor_launcher_run_stall_monitor` invocation before `return`, same-second collisions are not a practical concern (`scripts/lib-cursor-launcher-common.sh:288-333`, `scripts/lib-cursor-launcher-common.sh:453-504`).
  - From dyn-sidecar-integrity-output.txt: The `cursor-ci-stall-causes` audit scan treats non-`jq -e` parseable files as unparsed while still bucketing them as `UNKNOWN` in the histogram, so malformed sidecars do not silently skew parsed JSON aggregation (`.claude/skills/audit-runs/scripts/audit-scan-run.sh:354-380`, mirrored in `test-audit-runs.sh` around the `not json` fixture).
  - From dyn-audit-scan-correctness-output.txt: The aggregation loop in `audit-scan-run.sh:366-381` uses `shopt -s nullglob`, `jq -e .` for `parsed_files`, and a fallback `UNKNOWN` line per file when per-file `jq` fails; `channels_detail` mirrors `ns-retry-sidecars` when the histogram `jq` fails; this matches `test-audit-runs.sh:1269-1285` and the prose in `audit-scan-run.md:37`. The `expected_outcome` text in `scans.tsv:7` is descriptive (registry is not parsed for pass/fail semantics beyond human docs), and is consistent with emitting `result:"informational"` whenever any matching file exists.
  - From dyn-test-coverage-output.txt: Stall fixtures 7–8 use constructs compatible with macOS Bash 3.2 (`shopt -s nullglob`, `[[ ]]`, arithmetic `$(())`, `case`), with no obvious Bash 4-only features in the added blocks.

---


Vote tally: YES=0 NO=2 EXON=0 JUDGE_ERROR=0 Result=rejected

