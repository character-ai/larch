### FINDING_1: panel [code-review/accepted]

## **Important** `risk-integration` `skills/review/scripts/review-core.sh:83-92` writes the round log before coder artifacts exist. In `/implement` rounds with accepted in-scope findings, `skills/review-and-fix/scripts/review-and-fix.sh:678-708` creates `accepted-in-scope-findings.md`, `coder.env`, `coder-prompt.md`, `coder-output.log`, skipped-findings files, and commit logs only after `review-core.sh` has returned, and there is no later `write-round` call. The committed `round-<N>/` directory therefore misses several artifacts that `scripts/larch-log.sh:67-74` explicitly registers and that this feature is meant to preserve. Move or repeat the `write-round` flush at the end of `run_implement_round` after coder/skipped/summary artifacts are written.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `risk-integration` `skills/review/scripts/review-core.sh:83-92` writes the round log before coder artifacts exist. In `/implement` rounds with accepted in-scope findings, `skills/review-and-fix/scripts/review-and-fix.sh:678-708` creates `accepted-in-scope-findings.md`, `coder.env`, `coder-prompt.md`, `coder-output.log`, skipped-findings files, and commit logs only after `review-core.sh` has returned, and there is no later `write-round` call. The committed `round-<N>/` directory therefore misses several artifacts that `scripts/larch-log.sh:67-74` explicitly registers and that this feature is meant to preserve. Move or repeat the `write-round` flush at the end of `run_implement_round` after coder/skipped/summary artifacts are written.
- **Suggested revision**: Address the concern above.

### FINDING_11: panel [code-review/accepted]

## correctness: scripts/larch-log-batches.sh; skills/implement/SKILL.md (Step 7a)

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] No batch or flush for codex-impl-transcript.txt.meta though #2269 lists it in the per-run committed set. Codex Step 2 runs still drop dispatcher metadata at TMPDIR cleanup; post-merge diagnosis of Step 2 issues is incomplete vs acceptance criteria. Add a replace-mode batch and Step 7a write after CMD_JSON trimming (same trimmer contract as other .meta).
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/larch-log.sh:271-272

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] write-round EXIT trap deletes ${tmp:-} though tmp is never set in-branch An exported tmp=/some/path causes rm -f on that path at EXIT Trap only round_tmp or unset tmp before trap / use a unique temp variable name
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: scripts/larch-log.sh:67-74

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [important] round_artifact_included matches #2269-forbidden artifacts (*.dirty-tree, *.untracked-baseline, *.done, *.diag, specialist *.prompt via *-output*.prompt, *.sidecar) and includes coder-codex.log/coder-output.log which #2269 excludes. Committed round-<N>/ trees can include large excluded prompts/sidecars/sentinels and full coder transcripts, breaking #2269 exclude acceptance and the ≤250KB typical-run budget. Replace broad globs with the #2269 positive allowlist plus explicit denies; drop coder-codex.log and coder-output.log from the allowlist.
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## correctness: scripts/larch-log.sh; scripts/test-larch-log-write-round.sh

- **Reviewer**: cursor-specialist-plan-fidelity-output.txt
- **Concern**: [latent] Size/regression risk for #2269 acceptance remains because excluded bulky filenames are not rejected by tests. A repo with excluded sidecars/prompts present under the round tmpdir could silently balloon committed logs until CI or operators notice. Add negative fixtures for each #2269 excluded pattern family and assert they never appear under round-<N>/.
- **Suggested revision**: Address the concern above.

### FINDING_17: panel [code-review/accepted]

## risk-integration: skills/review/scripts/review-core.sh:flush_round_log

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] flush_round_log discards all output and ignores failures. Silent loss of round artifacts if larch-log or redaction fails; no operator-visible diagnostic. Emit a quiet breadcrumb or append-tool-failure on non-zero; at minimum tee stderr to IMPLEMENT_TMPDIR when quiet contract allows.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## security: scripts/larch-log.sh:150-175

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] `.result` stripping applies only to basenames matching *cursor*.json while *-output.txt.json includes claude/codex voter sidecars. Codex/Claude JSON sidecars can retain full .result payloads in committed round-<N>/ trees while Cursor sidecars are trimmed; uneven secret/size exposure. Apply result stripping to all included *.json sidecars that are known tool envelopes (or key off TOOL= metadata / explicit suffix list), not only cursor substring.
- **Suggested revision**: Address the concern above.

### FINDING_6: panel [code-review/accepted]

## code-quality: scripts/larch-log.md:57

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] larch-log.md omits write-round from verbs requiring absolute --log-root. Readers may think write-round can run without --log-root. Add write-round to the same bullet/list as write/append.
- **Suggested revision**: Address the concern above.

### FINDING_1: panel [code-review/accepted]

## **Important** `correctness` `scripts/ship-pr.sh:431` and `scripts/ship-pr.sh:507` — The new lint-fix routing captures failing helper calls with `out=$(...)` while `set -e` is active, so a normal `run-relevant-checks-captured.sh` failure exits `ship-pr.sh` before `rc=$?`, redacted-log parsing, or `lint-fix-loop.sh` dispatch. Concrete scenario: `ci-wait.sh` returns `ACTION=evaluate_failure`, `run-relevant-checks-captured.sh` exits 1 after emitting `REDACTED_LOG_FILE`, and line 507 aborts the script, so `/implement` gets an uncontrolled exit 1 instead of the intended lint-fix loop or exit-4 stall path. Wrap these helper invocations, including the `lint-fix-loop.sh` calls at `scripts/ship-pr.sh:445` and `scripts/ship-pr.sh:520`, in explicit `set +e` / `set -e` capture blocks or `if command; then rc=0; else rc=$?; fi` forms.

- **Reviewer**: codex-generalist-output.txt
- **Concern**: 1. **Important** `correctness` `scripts/ship-pr.sh:431` and `scripts/ship-pr.sh:507` — The new lint-fix routing captures failing helper calls with `out=$(...)` while `set -e` is active, so a normal `run-relevant-checks-captured.sh` failure exits `ship-pr.sh` before `rc=$?`, redacted-log parsing, or `lint-fix-loop.sh` dispatch. Concrete scenario: `ci-wait.sh` returns `ACTION=evaluate_failure`, `run-relevant-checks-captured.sh` exits 1 after emitting `REDACTED_LOG_FILE`, and line 507 aborts the script, so `/implement` gets an uncontrolled exit 1 instead of the intended lint-fix loop or exit-4 stall path. Wrap these helper invocations, including the `lint-fix-loop.sh` calls at `scripts/ship-pr.sh:445` and `scripts/ship-pr.sh:520`, in explicit `set +e` / `set -e` capture blocks or `if command; then rc=0; else rc=$?; fi` forms.
- **Suggested revision**: Address the concern above.

### FINDING_12: panel [code-review/accepted]

## correctness: scripts/lib-redact.sh:10-13 (and skills/implement/SKILL.md pre-bump codex-impl-transcript.txt.meta awk)

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] CMD_JSON strip only matches column-1 lines; leading whitespace keeps CMD_JSON lines with secrets. A .meta line like " CMD_JSON=[\"cursor\",...secret...]" survives into committed round-<N> artifacts. Match CMD_JSON= after optional leading whitespace (or use sed/awk anchored pattern); mirror the same rule in SKILL inline awk.
- **Suggested revision**: Address the concern above.

### FINDING_13: panel [code-review/accepted]

## correctness: skills/review-and-fix/scripts/review-and-fix.sh:623-638 scripts/run-step1-plan-log.sh:126-132

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [latent] New batch writes swallow errors with || true Silent loss of parent-issue or pre-review snapshots in larch-logs Surface failures via breadcrumb or execution-issues instead of unconditional true
- **Suggested revision**: Address the concern above.

### FINDING_14: panel [code-review/accepted]

## risk-integration: SECURITY.md:100-118 scripts/larch-log.sh:67-112 docs/run-logs.md:54-59

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] SECURITY.md not updated for new committed round snapshot trimming vs session CMD_JSON policy Auditors misread argv exposure for git-committed round artifacts vs session tmpdir Update SECURITY.md with session vs committed round-<N> meta contract
- **Suggested revision**: Address the concern above.

### FINDING_15: panel [code-review/accepted]

## risk-integration: scripts/run-step1-plan-log.sh:108-115; skills/review-and-fix/scripts/review-and-fix.sh:623-638

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [latent] parent-issue and pre-review larch-log writes use >/dev/null 2>&1 || true. Silent failure means tracking sentinel or snapshots may never reach TMPDIR larch-logs if larch-log.sh fails for a real reason. Log failures with append-tool-failure or stderr capture; avoid blanket || true on larch-log.sh write.
- **Suggested revision**: Address the concern above.

### FINDING_16: panel [code-review/accepted]

## risk-integration: scripts/ship-pr.sh run_evaluate_failure / run_ci_fix_vendor

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [important] Outer retry loop for full run_ci_fix_vendor (up to 3 vendor fix attempts) removed; only inner lint-fix retries remain. Transient launch-cursor-ci / launch-codex-ci failure no longer gets 2 additional full vendor attempts before stall. Reintroduce bounded outer retries for vendor launch failure, or narrow-retry only that phase with documented semantics.
- **Suggested revision**: Address the concern above.

### FINDING_18: panel [code-review/accepted]

## risk-integration: scripts/test-larch-log-write-round.sh

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [nit] write-round never tested with zero included artifacts. found=false / UNCHANGED-only path could regress unnoticed. Add a tmpdir with only excluded files and assert expected envelope.
- **Suggested revision**: Address the concern above.

### FINDING_19: panel [code-review/accepted]

## risk-integration: scripts/test-larch-log-write-round.sh:113-118

- **Reviewer**: cursor-specialist-testing-output.txt
- **Concern**: [latent] .result stripping assertions are gated on jq presence. Environments without jq skip JSON trimmer verification while production uses Python or raw-copy fallback; trimmer regressions slip past CI. Exercise python3-only (or jq-shadowed) path and assert .result absent without relying on jq.
- **Suggested revision**: Address the concern above.

### FINDING_24: panel [code-review/accepted]

## security: scripts/lib-redact.sh:12-38

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] Jq/python JSON trimmer falls back to cp on failure, stderr discarded Malformed voter JSON or jq/python failure copies full sidecar including .result into committed round-<N> after only tmpdir/secret redaction Fail closed or emit explicit error artifact; never cp raw input on trim failure
- **Suggested revision**: Address the concern above.

### FINDING_25: panel [code-review/accepted]

## security: scripts/lib-redact.sh:16-41

- **Reviewer**: cursor-specialist-correctness-output.txt
- **Concern**: [latent] larch_redact_strip_json_result falls back to raw cp when jq and python3 cannot parse. Environment without jq/python leaves .result (possibly large/sensitive) in committed JSON sidecars. Fail closed for write-round when trimming cannot run, or document and accept the risk explicitly.
- **Suggested revision**: Address the concern above.

### FINDING_26: panel [code-review/accepted]

## security: scripts/lib-redact.sh:7-9

- **Reviewer**: cursor-specialist-edge-cases-output.txt
- **Concern**: [important] CMD_JSON strip only when substring starts at column 1 Indented or non-BOL CMD_JSON= lines pass through with argv secrets intact Strip lines matching CMD_JSON= with leading whitespace or delete any CMD_JSON line per contract
- **Suggested revision**: Address the concern above.

### FINDING_27: panel [code-review/accepted]

## security: scripts/ship-pr.sh:438-448

- **Reviewer**: cursor-specialist-security-output.txt
- **Concern**: [important] REDACTED_LOG_FILE from run-relevant-checks stdout is passed to lint-fix-loop --checks-log without confinement to IMPLEMENT_TMPDIR or symlink checks. A compromised or malicious run-relevant-checks-captured.sh can point REDACTED_LOG_FILE at arbitrary readable files; lint-fix-loop ingests that path into an external coder prompt, leaking file contents across a trust boundary. Resolve realpath and require prefix under IMPLEMENT_TMPDIR (or a fixed redacted-log dir), reject symlinks, or stop trusting absolute paths from subprocess output.
- **Suggested revision**: Address the concern above.

### FINDING_5: panel [code-review/accepted]

## code-quality: scripts/larch-log.md:16-19 vs scripts/larch-log.sh:stage_round_artifact

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Doc says *-output*.json trimmed; code only matches *-output.txt.json and *-output-*.txt.json. Misleading contract for future artifact types. Align larch-log.md wording with the exact basename patterns.
- **Suggested revision**: Address the concern above.

### FINDING_7: panel [code-review/accepted]

## code-quality: scripts/test-larch-log-write-round.sh:330-314

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [nit] Jq-only assertions for stripped .result field. Python/cp fallback path for JSON trim is untested. Add a stubbed-PATH case or a jq-absent subtest if feasible.
- **Suggested revision**: Address the concern above.

### FINDING_8: panel [code-review/accepted]

## code-quality: skills/implement/SKILL.md:1639

- **Reviewer**: cursor-specialist-structure-output.txt
- **Concern**: [important] Inline awk duplicates lib-redact CMD_JSON trimming for codex-impl-transcript meta. Two implementations of the same trimmer can diverge; a fix in lib-redact.sh would not affect the pre-bump flush path. Call larch_redact_strip_meta_cmd_json from scripts/lib-redact.sh (or a one-line wrapper script) instead of inlining awk.
- **Suggested revision**: Address the concern above.

