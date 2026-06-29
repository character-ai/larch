## Proposed Design Outline

### Goals
- Reduce `skills/implement/SKILL.md` line count through Strunk & White in-place prose compression
- Pass `make test-implement-fence-shape` (EXPECTED_OLD=2, EXPECTED_NEW=20) and `make test-implement-structure` with no changes to those test scripts
- Preserve all load-bearing tokens: contract strings, `KEY=value` grammars, step markers, Bash fence content

### Non-goals
- Structural relocation or fold/relocate of content
- Changes to `skills/design/SKILL.md`, references, or test scripts
- Semantic changes: no contract alteration, no behavior changes

### Approach sketch
- Scan every prose section (intro, Protocol Directive, NEVER list, each step) and apply: shorter sentences, active voice, cut filler words
- Preserve exact `require(skill, ...)` and `forbid(skill, ...)` target strings from `test-implement-structure.sh`
- Leave Bash fences byte-exact; old-shape guard lines and new-shape launcher lines unchanged
- Iteratively edit and verify by running `make test-implement-fence-shape` and `make test-implement-structure`

### Surfaces in scope
- `skills/implement/SKILL.md` only

### Open questions
- None.
