## Goal
Implement issue #5841: [IMPLEMENTING] [BUG] #5786 compressed no design/SKILL.md prose — only blank lines removed.

## Implementation Plan
**Severity**: Medium (plan fidelity / accounting; no correctness defect).

**What**: #5786 (PR #5828) is titled "line-level Strunk & White compression of `skills/design/SKILL.md`" and the plan named the ~600-word anti-halt continuation paragraph as the #1 compression target. What shipped: **85 blank-line deletions and zero prose changes**.

**Evidence**:
- The diff is 85 `-` lines, all blank; `diff` of the blank-stripped before/after is byte-identical.
- The named anti-halt paragraph is unchanged to the byte.
- Design token closure moved only **-16 tokens** (consistent with removing near-zero-token blank lines), versus the plan's projected 10-15%.

**Side effect (low impact)**: every blank-line removal fused two adjacent Markdown blocks (lead-in to list, paragraph to paragraph). Because the file is consumed as raw text and all content is preserved (code fences, tables, and `### NEW:` / `### UPDATED:` plan-grammar separators intact), the practical impact is low — but it is line-count-chasing, not compression.

**Consequence**: the round's claimed `/design` prose-density savings were essentially **not realized**, yet #5786 is marked DONE and the ratchet baselined at 705 (zero headroom). The program's books read "/design prose density: mined" when the vein is untouched.

**Ask** (decide one):
- Redo the actual prose compression (convert verbose clauses to imperatives; compress the anti-halt paragraph), or
- Re-scope and document that `/design` prose density was deferred.
- Either way: do **not** delete the load-bearing compaction-resilience duplication (repeated NEVER / anti-halt blocks) — explicitly out of scope per umbrella #5788.

**Origin**: PR #5828 (#5786), umbrella #5788.

## Test plan
(no test plan section in plan-file)
