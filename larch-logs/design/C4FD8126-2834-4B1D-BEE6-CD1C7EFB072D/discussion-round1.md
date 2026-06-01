## Decision 1: approach — mirror #3305 round_dir pattern
- **Question**: What pattern should --add-dir narrowing use for Step 2?
- **Resolution**: #3305 (CLOSED) uses `--add-dir "$round_dir"` in review-and-fix.sh — per-subdir grant. Step 2 mirrors this with `$IMPLEMENT_TMPDIR/codex-step2-out/`.
- **Source**: codebase

## Decision 2: which files move to subdir
- **Question**: Which files should relocate to codex-step2-out/?
- **Resolution**: manifest.json, qa-pending.json, codex-impl-transcript.txt (Codex-written). MANIFEST_RAW_PATH and SIDECAR_LOG stay in $IMPLEMENT_TMPDIR (not Codex-written; step-7a.sh reads manifest-raw.json hardcoded).
- **Source**: codebase

## Decision 3: additional affected file step-7a.sh
- **Question**: Does anything outside step2-implement.sh read transcript/manifest-raw from $IMPLEMENT_TMPDIR?
- **Resolution**: step-7a.sh reads codex-impl-transcript.txt and siblings at $IMPLEMENT_TMPDIR root; needs update. manifest-raw.json stays (not moved).
- **Source**: codebase
