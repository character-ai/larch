#!/bin/bash
# Regression test for issue #1014: post-/design boundary checkpoint reminder
# in skills/implement/SKILL.md Step 1 (normal mode), and the matching
# --emit-load-breadcrumb flag handler in skills/design/scripts/read-design-manifest.sh.
#
# Exit 0 on pass, exit 1 on any assertion failure.

set -euo pipefail

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd -P)
SKILL_MD="$REPO_ROOT/skills/implement/SKILL.md"
READER="$REPO_ROOT/skills/design/scripts/read-design-manifest.sh"

fail() { echo "FAIL: $1" >&2; exit 1; }

[[ -f "$SKILL_MD" ]] || fail "skills/implement/SKILL.md missing"
[[ -f "$READER" ]] || fail "skills/design/scripts/read-design-manifest.sh missing"

# (A) Post-/design boundary checkpoint blockquote present in SKILL.md.
grep -q "Post-/design boundary checkpoint" "$SKILL_MD" \
    || fail "(A) missing 'Post-/design boundary checkpoint' blockquote in SKILL.md"

# (B) Anti-pattern strings present in SKILL.md (case-insensitive).
for s in "returning control" "design phase complete" "handing off"; do
    grep -qi -- "$s" "$SKILL_MD" || fail "(B) missing anti-pattern string: $s"
done

# (C) Both breadcrumb forms present in SKILL.md.
grep -q '🔃 1.r: design plan | rebase' "$SKILL_MD" \
    || fail "(C) missing 1.r rebase breadcrumb literal"
grep -q '🔶 2: implementation' "$SKILL_MD" \
    || fail "(C) missing Step 2 breadcrumb literal"

# (D) NEVER #7 reference present.
grep -q 'NEVER #7' "$SKILL_MD" \
    || fail "(D) missing 'NEVER #7' reference in SKILL.md"

# (E) Manifest-loaded breadcrumb literal present in SKILL.md.
grep -q '📥 1: design plan — manifest loaded' "$SKILL_MD" \
    || fail "(E) missing manifest-loaded breadcrumb literal in SKILL.md"

# (F) read-design-manifest.sh invocation in the post-/design re-run carries
#     --emit-load-breadcrumb so the breadcrumb actually fires.
# shellcheck disable=SC2016 # the literal "$IMPLEMENT_TMPDIR" is intentional — we are searching SKILL.md for an unexpanded shell variable.
grep -q 'read-design-manifest.sh --implement-tmpdir "\$IMPLEMENT_TMPDIR" --emit-load-breadcrumb' "$SKILL_MD" \
    || fail "(F) post-/design re-run in SKILL.md missing --emit-load-breadcrumb forwarding"

# (G) read-design-manifest.sh defines the --emit-load-breadcrumb flag handler.
grep -q -- '--emit-load-breadcrumb' "$READER" \
    || fail "(G) read-design-manifest.sh missing --emit-load-breadcrumb flag handler"

# (H) Reader emits the breadcrumb literal on the success path.
grep -q '📥 1: design plan — manifest loaded' "$READER" \
    || fail "(H) read-design-manifest.sh missing breadcrumb emission"

echo "PASS: post-/design boundary checkpoint regression test"
