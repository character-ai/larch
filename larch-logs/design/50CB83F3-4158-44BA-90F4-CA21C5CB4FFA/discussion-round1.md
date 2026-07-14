## Decision 1: Python scope — production modules only vs all Python files
- **Question**: Should the lint scan all Python files (including tests) or only production modules?
- **Resolution**: Scan `python/larch/**/*.py` production modules, exempting `python/larch/git/` entirely and the standard exempt filenames (test_*.py, conftest.py, test_support.py, review_test_support.py). This matches every comparable lint in the codebase. "Test fixture suppression via pragma/allowlist" in the issue refers to inline pragma for any production-side exceptions, not a mandate to scan tests.
- **Source**: codebase

## Decision 2: Detection algorithm — list/tuple first-element or run-call argument only
- **Question**: Should the lint detect `["gh", ...]` in ANY context (variable assignments, call arguments) or only when passed to a run-family function?
- **Resolution**: Detect any `ast.List` or `ast.Tuple` whose first element is the string constant `"gh"`, in any expression context. The issue says "argv literals anywhere" — variable assignments like `create_argv = ["gh", "label", ...]` are equally bannable. This is broader than the subprocess-via-runner gh-baseline check but correct for a hard ban.
- **Source**: codebase + issue wording

## Decision 3: Overlap with subprocess-via-runner gh-baseline
- **Question**: Does the new lint subsume the subprocess-via-runner gh-baseline, and should we remove that mechanism?
- **Resolution**: Out of scope. The new lint adds the hard-ban adoption enforcement; subprocess-via-runner gh-baseline migration tracking remains and will naturally empty out as repoint issues land. No changes to subprocess-via-runner in this issue.
- **Source**: issue scope
