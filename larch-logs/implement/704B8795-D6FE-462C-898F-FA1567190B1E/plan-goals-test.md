## Goal
Refactor KARPATHY_CLAUDE.md to contain only Karpathy-philosophy sections; extract Bash-authoring sections to new BASH_AUTHORING.md

## Implementation Plan
## Implementation Plan

**Goal**: Refactor KARPATHY_CLAUDE.md to contain only Karpathy-philosophy sections (§1-4); extract the Bash-authoring sections into a new BASH_AUTHORING.md file; wire it into CLAUDE.md.

### Files to modify/create

1. **Create `/Users/zhupanov/larch3/BASH_AUTHORING.md`**
   - Add intro header matching KARPATHY_CLAUDE.md style
   - `## 1. Exit-Code Safety for Bash Probes` — content moved verbatim from KARPATHY_CLAUDE.md §5
   - `## 2. Bash Quoting Hygiene` — new content from issue body

2. **Edit `/Users/zhupanov/larch3/KARPATHY_CLAUDE.md`**
   - Remove §5 "Exit-Code Safety for Bash Probes" section (lines 63-73)
   - Keep `---` separator and closing summary line

3. **Edit `/Users/zhupanov/larch3/CLAUDE.md`**
   - Add `@BASH_AUTHORING.md` after `@KARPATHY_CLAUDE.md`

### Cross-references to update
- AGENTS.md: Only references KARPATHY_CLAUDE.md §1 "Think Before Coding" — no update needed
- CHANGELOG.md: No references to KARPATHY_CLAUDE.md §5 — no update needed

### Verification
- Run `/relevant-checks` (pre-commit + agent-lint)
- Confirm KARPATHY_CLAUDE.md has only §1-4
- Confirm BASH_AUTHORING.md has §1 (Exit-Code Safety) + §2 (Bash Quoting Hygiene)
- Confirm CLAUDE.md @-includes BASH_AUTHORING.md

## Test plan
(no test plan section in plan-file)
