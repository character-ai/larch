# check-mid-run-dirty-tree.sh

**Purpose**: detect working-tree pollution between a clean orchestration checkpoint and later external-reviewer boundaries. The script is a detector only: it never prompts the operator, never restores files, and always exits 0 so callers can fail closed by parsing `STATUS=unknown`.

**Primary callers**: `scripts/launch-review.sh --tool cursor` and `scripts/launch-review.sh --tool codex` use `--mode baseline --baseline <path> --sidecar <path>` after an external reviewer returns. `scripts/check-phantom-dirty.sh` wraps baseline mode for `/implement` session-wide phantom untracked probes. `/implement`, `/design`, and `/review` prompt prose use `--mode checkpoint` at orchestration boundaries.

**Output contract**:
- Always emits stable key/value lines to stdout.
- `STATUS=clean|dirty|unknown`
- `MODE=baseline|checkpoint`
- `UNTRACKED_BASELINE=present|missing` in baseline mode.
- `TRACKED_PATHS_FILE=<path>` when baseline mode detects staged or unstaged tracked paths.
- `NEW_UNTRACKED_PATHS_FILE=<path>` when baseline mode detects new untracked paths against a present baseline.
- `REASON=<short-token>` whenever `STATUS` is not clean. Consumers must treat missing, empty, or unparsable sidecars as `STATUS=unknown`, never clean.

Baseline mode uses strict git probing: `git status --porcelain`, `git diff --name-only -z`, `git diff --name-only --cached -z`, and `git ls-files --others --exclude-standard -z` each have their exit status checked. Any failure produces `STATUS=unknown` with a command-specific reason.

**Path streams**: tracked and new-untracked path files are NUL-delimited and repo-relative because they come directly from `git -z` path output. Recovery consumers must still validate before acting: reject absolute paths, `..` traversal, `.git/` paths, and consume the streams correctly per command. `git restore` natively accepts the NUL stream — pipe via `git restore --pathspec-from-file=- --pathspec-file-nul -- < TRACKED_PATHS_FILE`. `git clean` does NOT accept `--pathspec-from-file` / `--pathspec-file-nul` (verified: exits 129 with `unknown option`); consume the NUL stream via `xargs` instead. Use the portable stdin form `xargs -0 git clean -f -- < NEW_UNTRACKED_PATHS_FILE` (validated paths pass positionally after `--`); guard with `[ -s NEW_UNTRACKED_PATHS_FILE ]` to skip empty files. Do NOT use `xargs -0 -a FILE …` — the `-a` flag is GNU-only and rejected by macOS BSD xargs.

**Checkpoint invariant**: checkpoint mode only checks whether `git status --porcelain` is non-empty. This is valid only at documented larch orchestration boundaries where the parent skill and child skills have not written to the repo working tree between Step 0 and the probe site; they write only under `$IMPLEMENT_TMPDIR`, `$DESIGN_TMPDIR`, or `$REVIEW_TMPDIR`.

**Limitations**: ignored files are not covered because the detector uses `git ls-files --others --exclude-standard`. A bounded denylist scan for ignored sensitive paths is deferred. If the untracked baseline is missing and current untracked files exist, the detector emits `STATUS=unknown REASON=baseline-missing-untracked-ambiguous` and leaves `NEW_UNTRACKED_PATHS_FILE` absent so callers do not auto-clean files they cannot classify.

**`--auto` carve-out**: dirty-tree recovery prompts are not suppressed by `--auto`. Callers must surface `STATUS=dirty` and `STATUS=unknown` via `AskUserQuestion`.

**Harness**: `scripts/test-check-mid-run-dirty-tree.sh`, wired by `make test-check-mid-run-dirty-tree`.

**Edit-in-sync**: update `scripts/test-check-mid-run-dirty-tree.sh`, `scripts/launch-review.sh --tool cursor`, `scripts/launch-review.sh --tool codex`, `docs/external-reviewers.md`, `SECURITY.md`, and the dirty-tree recovery prose in `skills/implement/SKILL.md`, `skills/design/SKILL.md`, and `skills/review/SKILL.md`.
