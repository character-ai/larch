## Goal
Harden post-merge larch-log flush push to prevent orphan commits on local main

## Implementation Plan

Goal: After /implement Step 18, local main == origin/main. Either the flush commit was pushed successfully, or it was abandoned cleanly along with any prior orphans.

### Change 1 — capture-session-transcript.sh: fetch-then-push-or-abandon

Replace lines 155-163 (the current best-effort push block) with:

```bash
current_branch=$(git symbolic-ref --short HEAD 2>/dev/null || true)
if [ "$current_branch" = "main" ]; then
    _expected_subject="chore(larch-logs): flush implement run $RUN_ID"
    _actual_subject=$(git log -1 --format='%s' HEAD 2>/dev/null || true)
    if [ "$_actual_subject" = "$_expected_subject" ]; then
        git fetch origin main --quiet 2>/dev/null || true
        _flush_only=true
        while IFS= read -r _f; do
            case "$_f" in
                "larch-logs/implement/$RUN_ID/"*) ;;
                *) _flush_only=false; break ;;
            esac
        done < <(git diff --name-only origin/main HEAD 2>/dev/null || true)
        ahead_fresh=$(git rev-list --count "origin/main..HEAD" 2>/dev/null || echo 0)
        case "${ahead_fresh:-}" in ''|*[!0-9]*) ahead_fresh=0 ;; esac
        if [ "$_flush_only" = "true" ] && [ "$ahead_fresh" -eq 1 ]; then
            if git push origin main >/dev/null 2>&1; then
                _push_status=pushed
            else
                git reset --hard origin/main >/dev/null 2>&1 || true
                _push_status=push-failed-abandoned
            fi
        elif [ "$_flush_only" = "true" ] && [ "$ahead_fresh" -gt 1 ]; then
            git reset --hard origin/main >/dev/null 2>&1 || true
            _push_status=prior-orphans-abandoned
        elif [ "$_flush_only" = "false" ]; then
            _push_status=push-skipped-non-flush-diff
        else
            _push_status=already-present
        fi
        append_warning "$_push_status" "Step 18 push outcome: $_push_status"
    fi
fi
```

Key changes vs original:
- Drop the stale `ahead -eq 1` check based on pre-fetch local ref
- Fetch before computing ahead count
- Add flush-only safety predicate (diff --name-only scoped to larch-logs/implement/$RUN_ID/)
- On push failure: `git reset --hard origin/main` (abandons commit)
- On prior orphans (ahead > 1, all flush-only): reset too
- On non-flush diff: do nothing (operator must investigate)
- Record outcome in Warnings; `SESSION_TRANSCRIPT_STATUS=captured` still terminal

### Change 2 — capture-session-transcript.md: document new push outcomes

Add the new push outcome status values to the Statuses section.

### Change 3 — local-cleanup.sh: pre-pull orphan cleanup

Before `git pull origin main` (between Step 2 Fetch and Step 3 Pull), insert:

```bash
# Pre-pull orphan cleanup: discard prior flush-only commits before pull
git fetch origin main --quiet >/dev/null 2>&1 || true
ahead_before=$(git rev-list --count origin/main..HEAD 2>/dev/null || echo 0)
case "${ahead_before:-}" in ''|*[!0-9]*) ahead_before=0 ;; esac
if [ "$ahead_before" -gt 0 ]; then
    _all_flushes=true
    while IFS= read -r _subj; do
        case "$_subj" in
            "chore(larch-logs): flush "*) ;;
            *) _all_flushes=false; break ;;
        esac
    done < <(git log origin/main..HEAD --format=%s 2>/dev/null || true)
    if [ "$_all_flushes" = "true" ]; then
        echo "⚠ Dropping $ahead_before prior-run larch-log flush commit(s) before pull..." >&2
        git reset --hard origin/main >/dev/null 2>&1 || true
    fi
fi
```

This runs AFTER the Step 2 Fetch call (which already fetches), but since the
fetch in local-cleanup.sh uses `git fetch origin main` (not `--quiet`),
I'll add a separate explicit fetch in the orphan-cleanup block so it's self-
contained if the Step 2 fetch fails non-fatally. Actually: the existing
Step 2 already fetches, so I can rely on that fetch and use the post-fetch
origin/main ref directly. The code is written to handle either case.

### Change 4 — local-cleanup.md: document pre-pull orphan cleanup

Update the contract doc to mention the orphan cleanup.

### Change 5 — SKILL.md Step 18: update push-behavior prose

Update the paragraph at line 1982 to describe the new fetch-then-push-or-
abandon behavior instead of the old "best-effort push, push failures silently
ignored."

### Change 6 — test-capture-session-transcript.sh: new test cases

Add 4 new test scenarios to the harness:
- `push-fail-abandoned`: mock remote that rejects push → Warnings entry contains
  push-failed-abandoned AND local HEAD reset to origin/main
- `push-orphan-multi`: local main ahead by 2 (2 prior flush commits) →
  Warnings entry contains prior-orphans-abandoned AND reset
- `push-non-flush-diff`: local main ahead with non-flush changes →
  Warnings entry contains push-skipped-non-flush-diff AND no reset
- `push-success`: local main ahead=1 flush-only, push accepted → Warnings
  contains pushed

### Change 7 — test-local-cleanup.sh (new): test pre-pull orphan cleanup

New harness testing:
- With prior flush orphan on local main → orphan cleaned before pull
- With no orphan → standard pull runs unchanged
- With non-flush ahead commit → orphan cleanup skipped (no reset)

### Files to touch
- scripts/capture-session-transcript.sh (Change 1)
- scripts/capture-session-transcript.md (Change 2)
- scripts/local-cleanup.sh (Change 3)
- scripts/local-cleanup.md (Change 4)
- skills/implement/SKILL.md line 1982 (Change 5)
- scripts/test-capture-session-transcript.sh (Change 6)
- scripts/test-local-cleanup.sh [new] (Change 7)


## Test plan
Run /relevant-checks after all edits. Run test harnesses:
  bash scripts/test-capture-session-transcript.sh
  bash scripts/test-local-cleanup.sh
