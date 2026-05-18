## Goal
Add Bash 3.2 compliance rule to BASH_AUTHORING.md, create lint-bash32.sh linter, test harness, wire into Makefile

## Implementation Plan

Add Bash 3.2 compliance rule to BASH_AUTHORING.md as section 3, create scripts/lint-bash32.sh linter,
scripts/lint-bash32.md sibling doc, scripts/test-lint-bash32.sh regression harness, wire into Makefile.

Files:
1. BASH_AUTHORING.md — add section 3 with rule text from issue
2. scripts/lint-bash32.sh (NEW) — linter: git ls-files to find bash scripts, skip comment lines,
   detect: declare -A/n, mapfile/readarray, ${var^^}/${var,,}, local -n, &>>, named coprocs;
   supports # lint-bash32: ok skip comment; exits 1 on violations
3. scripts/lint-bash32.md (NEW) — sibling doc
4. scripts/test-lint-bash32.sh (NEW) — regression harness with known-bad and known-good fixtures
5. Makefile — add lint-bash32 and test-lint-bash32 to .PHONY, add targets, add lint-bash32 to lint:
6. skills/issue/scripts/test-allocate-candidates.sh — add # lint-bash32: ok to grep-pattern line
7. skills/umbrella/scripts/test-helpers.sh — add # lint-bash32: ok to grep-pattern line

Testing: make test-lint-bash32 (regression); make lint-bash32 (full tree scan, must exit 0)

## Test plan
(no test plan section in plan-file)
