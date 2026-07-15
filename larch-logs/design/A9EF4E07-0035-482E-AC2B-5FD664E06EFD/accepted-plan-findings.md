### FINDING_2: Update `_REGISTRY` type annotation
- **Reviewer(s)**: Cursor-Innovation
- **Severity**: minor
- **Concern**: The plan changes `_REGISTRY` values to three-tuples but does not explicitly update its type annotation, potentially causing strict pyright failures.
- **Suggested revisions (informational for voters; coder decides)**:
  - From Cursor-Innovation: Explicitly update the `_REGISTRY` annotation to `dict[tuple[str, str], tuple[str, str, bool]]` in the cli.py section alongside the value migration
  - From Cursor-Innovation: Include the annotation change explicitly in the `python/larch/cli.py` section.


