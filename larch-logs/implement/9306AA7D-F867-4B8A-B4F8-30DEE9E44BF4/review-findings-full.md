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

