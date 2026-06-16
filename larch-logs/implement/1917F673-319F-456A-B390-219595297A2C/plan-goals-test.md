## Goal
Implement issue #4478: [IMPLEMENTING] Remove the .claude-plugin/plugin.json restriction from external implementers (Codex/Cursor).

## Implementation Plan
## Problem

External implementers (Codex and Cursor) refuse to edit `.claude-plugin/plugin.json` and the dispatcher blocks it post-hoc. When a plan legitimately includes a `plugin.json` change (e.g. adding a new consumer-facing skill's description), Codex bails immediately with `protected-path-modification-required: plan requires editing .claude-plugin/plugin.json, which Step 2 implementer is forbidden to modify` and the whole run ends as `bailed`.

Observed on issue #4427 run `1BECD343-4DDC-4B54-B7EE-6476FCB2A35D`.

## Root cause

The restriction lives in three places:

1. **`agents/_implementer-base.md:40`** (inherited by `codex-implementer.md` and `cursor-implementer.md`):
   > "NEVER edit `.claude-plugin/plugin.json`. That file is reserved for the `/bump-version` skill."

2. **`python/implement_dispatch.py` `_validate_manifest_paths()`** (line 595): rejects any manifest that lists `.claude-plugin/plugin.json` in `files_touched`.

3. **`python/implement_dispatch.py` `_post_implementer_safety_reason()`** (line 446–449): bails if the file's git hash changed after the implementer ran.

## Why the restriction is now stale

The restriction comment says "reserved for the `/bump-version` skill." Phase 1 (#3364) moved all versioning to `/release`; `/bump-version` no longer exists. `.claude-plugin/plugin.json` now needs routine updates (adding skills to the description, updating the marketplace blurb) that are natural `/implement` tasks, not release tasks.

## Secondary bug

The stall classifier in `python/stall_recovery.py` (and its allowlists in `skills/implement/scripts/stall-recovery-report-allowlists.tsv`) does not map the Codex bail reason token `protected-path-modification-required` to `FAILURE_CLASS=protected-path`. Instead it falls through to `FAILURE_CLASS=unrecoverable` / `MATCHED_CLASSIFIER_PATTERN=no-stall`. The expected pattern from `SKILL.md` §2.2 is `protected-path-edit-required-out-of-scope` — a different string. This means the `step2-impl` inline-recovery path (main Claude implements inline) is never triggered even when it would be appropriate.

## Fix

1. **`agents/_implementer-base.md`**: remove or relax rule 3. The generated `codex-implementer.md` and `cursor-implementer.md` are produced from this base, so updating the base propagates automatically.

2. **`python/implement_dispatch.py`**: remove `.claude-plugin/plugin.json` from the hardcoded block in:
   - `_validate_manifest_paths()` (line 595)
   - `_post_implementer_safety_reason()` (lines 446–449) — or scope it only to the `version` field if version-change protection is still wanted

3. **Stall classifier** (secondary): update the allowlist or classifier pattern so `protected-path-modification-required` maps to `FAILURE_CLASS=protected-path` with `RESUME_HINT=step2-impl`, consistent with the §2.2 SKILL contract.

## Acceptance

- A plan that includes `### UPDATED: .claude-plugin/plugin.json` with a description-only change reaches `STATUS=complete` rather than `STATUS=bailed`.
- The stall classifier maps `protected-path-modification-required` to `FAILURE_CLASS=protected-path`.
- `make lint`, `make py-lint`, `make py-test` pass.

## Test plan
(no test plan section in plan-file)
