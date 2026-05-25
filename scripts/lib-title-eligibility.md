# lib-title-eligibility.sh contract

`scripts/lib-title-eligibility.sh` is a sourced-only Bash 3.2 library for issue-title eligibility grammar shared by `/design` Step 0b and `skills/issue/scripts/list-issues.sh`.

## Purpose

Centralize lifecycle-reject, archival-report, and brainstorm title predicates plus the archival-prefix jq fragment used for Phase 1 dedup filtering. Callers keep their own bash↔jq impedance; this library exports constants and small predicates only.

## Exported grammar

| Constant | Role |
|----------|------|
| `LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER` | Full `select((.title …) \| not)` snippet for list-issues dedup (research / investigate / report-prefix) |
| `LARCH_TITLE_ARCHIVAL_REPORT_REGEX_BASH` | Report-prefix bash ERE: `^\[.*[Rr][Ee][Pp][Oo][Rr][Tt]\]` plus a trailing literal space |
| `LARCH_TITLE_LIFECYCLE_REJECT_REGEX` | Lifecycle reject: `^\[(IMPLEMENTING\|DONE\|DESIGNING\|DESIGNED)\]` (caller uses `nocasematch`) |
| `LARCH_TITLE_BRAINSTORM_REGEX` | Brainstorm word: `^[Bb]…[Mm]([^A-Za-z]\|$)` |

## Predicate functions

Each takes the title as `$1`, returns 0 on match and 1 otherwise. Empty input returns 1 (no false positives).

- `title_has_archival_report_prefix` — report-only subset for `/design` reject
- `title_has_lifecycle_reject_prefix` — on match prints the matched bracket token to stdout (e.g. `[IMPLEMENTING]`)
- `title_starts_with_brainstorm` — leading Brainstorm word

**Mandatory ordering for `/design` Step 0b sub-step 2.5:** (a) `title_has_lifecycle_reject_prefix` (exit on match), (b) `title_has_archival_report_prefix` (exit on match), (c) `title_starts_with_brainstorm` (set flag, continue). Earlier checks short-circuit.

## Bash 3.2 portability

POSIX `[[:space:]]` trimming via `larch_title_trim_leading_ws`; lifecycle case folding via `shopt nocasematch`; brainstorm uses explicit `[Bb]…` classes (no `${var^^}`).

## Primary callers

- **`skills/design/SKILL.md` Step 0b sub-step 2.5** — source `${CLAUDE_PLUGIN_ROOT}/scripts/lib-title-eligibility.sh`
- **`skills/issue/scripts/list-issues.sh`** — `# shellcheck source=scripts/lib-title-eligibility.sh` then `source "$PLUGIN_ROOT/scripts/lib-title-eligibility.sh"`; assign `DEDUP_SKIP_PREFIX_FILTER="$LARCH_TITLE_ARCHIVAL_PREFIX_JQ_FILTER"`. `PLUGIN_ROOT` prefers `CLAUDE_PLUGIN_ROOT` when `scripts/lib-title-eligibility.sh` exists there; otherwise falls back to the repo root via `skills/issue/scripts/../../..` (dev harnesses with a stale cache path).

## Test harness

`scripts/test-lib-title-eligibility.sh` — fixture matrix and jq/bash equivalence. Makefile target `test-lib-title-eligibility` (shard `test-harnesses-1`).

## Edit-in-sync

Change grammar in this `.sh` file, update this `.md`, `scripts/test-lib-title-eligibility.sh`, `skills/design/SKILL.md` Step 0b prose, `scripts/test-design-structure.sh` anchors, and re-run `skills/issue/scripts/test-list-issues.sh` when the jq fragment changes.
