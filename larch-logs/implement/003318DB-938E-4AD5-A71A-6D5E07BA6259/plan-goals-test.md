## Goal
Preserve voter first-pass output as sidecar before parse-retry mv overwrite

## Implementation Plan

Goal: Preserve voter first-pass output as a sidecar before parse-retry mv overwrite.
Fixes: Cursor voter triggering parse-retry in 6/7 rounds with no observability into first-pass content.

### Change 1 — scripts/dispatch-code-voters.sh

In `check_and_retry_voter_parse_rate`, on the retry success branch (immediately before
`mv "$retry_output" "$voter_path"`), compute a sidecar path and copy the first-pass:

  case "$voter_path" in
      *.txt) first_pass_sidecar="${voter_path%.txt}-first-pass.txt" ;;
      *) first_pass_sidecar="${voter_path}-first-pass" ;;
  esac
  cp "$voter_path" "$first_pass_sidecar" 2>/dev/null || true
  emit_breadcrumb "voter-${voter_tool}: first-pass content preserved at $(basename "$first_pass_sidecar") (parse-rate retry succeeded)"

Fail-open: `cp ... || true` so a write failure never breaks the retry path.
No sidecar on the retry-fail path (voter_path IS the first-pass content, no overwrite).
No sidecar on the clean no-retry path.

### Change 2 — scripts/larch-log.sh::round_artifact_included

Add `*-vote-output-first-pass.txt` to the allow-list case arm alongside existing
`*-output-*.txt` (which already matches, but explicit entry makes intent clear).

### Change 3 — scripts/test-dispatch-code-voters.sh

Extend existing retry_success_{claude,codex,cursor} sections:
- Assert <voter>-vote-output-first-pass.txt exists (sidecar was written)
- Assert <voter>-vote-output.txt contains the clean retry content (not the first-pass narrative)
- Assert the two files differ

Extend existing retry_fail_{claude,codex} sections and happy-path scenario:
- Assert <voter>-vote-output-first-pass.txt does NOT exist

### Change 4 — scripts/test-larch-log.sh

In the write-round section, add cursor-vote-output-first-pass.txt to the allowed artifact
list and assert it is committed; assert the denied set remains denied.

### Change 5 — Sibling .md files

Update dispatch-code-voters.md, larch-log.md, test-dispatch-code-voters.md,
test-larch-log.md to document the new sidecar behavior.


## Test plan

Run: make lint (covers lint-bash32, test-dispatch-code-voters.sh, test-larch-log.sh)
